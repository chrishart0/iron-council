from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus

from fastapi import APIRouter, Depends, FastAPI

from server.agent_registry import InMemoryMatchRegistry, MatchRecord
from server.db.registry import (
    MatchHistoryNotFoundError,
    PublicMatchDetailNotFoundError,
    TickHistoryNotFoundError,
    get_completed_match_summaries,
    get_match_history,
    get_match_replay_tick,
    get_public_leaderboard,
    get_public_match_detail,
    get_public_match_summaries,
)
from server.models.api import (
    CompletedMatchSummaryListResponse,
    MatchHistoryResponse,
    MatchListResponse,
    MatchReplayTickResponse,
    MatchSummary,
    PublicLeaderboardResponse,
    PublicMatchDetailResponse,
    PublicMatchRosterRow,
)
from server.models.domain import MatchStatus

from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError

RegistryProvider = Callable[..., InMemoryMatchRegistry]
PublicStatusPriority = Callable[[MatchStatus], int]
PublicRosterBuilder = Callable[[InMemoryMatchRegistry, MatchRecord], list[PublicMatchRosterRow]]


def register_public_metadata_routes(app: FastAPI) -> None:
    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": app.title,
            "status": "ok",
            "version": app.version,
        }

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}


def build_public_api_router(
    *,
    match_registry_provider: RegistryProvider,
    history_database_url: str | None,
    public_match_status_priority: PublicStatusPriority,
    build_in_memory_public_match_roster: PublicRosterBuilder,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    registry_dependency = Depends(match_registry_provider)

    def require_history_database_url() -> str:
        if history_database_url is None:
            raise ApiError(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="match_history_unavailable",
                message="Persisted match history is only available in DB-backed mode.",
            )
        return history_database_url

    def require_db_backed_public_read_database_url(*, code: str, message: str) -> str:
        if history_database_url is None:
            raise ApiError(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code=code,
                message=message,
            )
        return history_database_url

    @router.get("/matches", response_model=MatchListResponse)
    async def list_matches(
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> MatchListResponse:
        if history_database_url is not None:
            return get_public_match_summaries(database_url=history_database_url)

        return MatchListResponse(
            matches=[
                MatchSummary(
                    match_id=record.match_id,
                    status=record.status,
                    map=record.map_id,
                    tick=record.state.tick,
                    tick_interval_seconds=record.tick_interval_seconds,
                    current_player_count=record.public_current_player_count,
                    max_player_count=record.public_max_player_count,
                    open_slot_count=record.public_open_slot_count,
                )
                for record in sorted(
                    registry.list_matches(),
                    key=lambda match: (
                        public_match_status_priority(match.status),
                        -match.state.tick,
                        match.match_id,
                    ),
                )
            ]
        )

    @router.get(
        "/leaderboard",
        response_model=PublicLeaderboardResponse,
        responses={HTTPStatus.SERVICE_UNAVAILABLE: API_ERROR_RESPONSE_SCHEMA},
    )
    async def list_public_leaderboard() -> PublicLeaderboardResponse:
        return get_public_leaderboard(
            database_url=require_db_backed_public_read_database_url(
                code="leaderboard_unavailable",
                message="Persisted leaderboard is only available in DB-backed mode.",
            )
        )

    @router.get(
        "/matches/completed",
        response_model=CompletedMatchSummaryListResponse,
        responses={HTTPStatus.SERVICE_UNAVAILABLE: API_ERROR_RESPONSE_SCHEMA},
    )
    async def list_completed_match_summaries() -> CompletedMatchSummaryListResponse:
        return get_completed_match_summaries(
            database_url=require_db_backed_public_read_database_url(
                code="completed_match_summaries_unavailable",
                message="Completed match summaries are only available in DB-backed mode.",
            )
        )

    @router.get(
        "/matches/{match_id}",
        response_model=PublicMatchDetailResponse,
        responses={HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA},
    )
    async def get_public_match_detail_route(
        match_id: str,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> PublicMatchDetailResponse:
        if history_database_url is not None:
            try:
                return get_public_match_detail(
                    database_url=history_database_url,
                    match_id=match_id,
                )
            except PublicMatchDetailNotFoundError as exc:
                raise ApiError(
                    status_code=HTTPStatus.NOT_FOUND,
                    code="match_not_found",
                    message=f"Match '{match_id}' was not found.",
                ) from exc

        record = registry.get_match(match_id)
        if record is None or record.status is MatchStatus.COMPLETED:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )

        return PublicMatchDetailResponse(
            match_id=record.match_id,
            status=record.status,
            map=record.map_id,
            tick=record.state.tick,
            tick_interval_seconds=record.tick_interval_seconds,
            current_player_count=record.public_current_player_count,
            max_player_count=record.public_max_player_count,
            open_slot_count=record.public_open_slot_count,
            roster=build_in_memory_public_match_roster(registry, record),
        )

    @router.get(
        "/matches/{match_id}/history",
        response_model=MatchHistoryResponse,
        responses={
            HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA,
            HTTPStatus.SERVICE_UNAVAILABLE: API_ERROR_RESPONSE_SCHEMA,
        },
    )
    async def get_persisted_match_history(match_id: str) -> MatchHistoryResponse:
        try:
            return get_match_history(
                database_url=require_history_database_url(),
                match_id=match_id,
            )
        except MatchHistoryNotFoundError as exc:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            ) from exc

    @router.get(
        "/matches/{match_id}/history/{tick}",
        response_model=MatchReplayTickResponse,
        responses={
            HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA,
            HTTPStatus.SERVICE_UNAVAILABLE: API_ERROR_RESPONSE_SCHEMA,
        },
    )
    async def get_persisted_match_replay_tick(match_id: str, tick: int) -> MatchReplayTickResponse:
        try:
            return get_match_replay_tick(
                database_url=require_history_database_url(),
                match_id=match_id,
                tick=tick,
            )
        except MatchHistoryNotFoundError as exc:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            ) from exc
        except TickHistoryNotFoundError as exc:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="tick_not_found",
                message=f"Tick '{tick}' was not found for match '{match_id}'.",
            ) from exc

    return router
