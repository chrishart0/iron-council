from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, FastAPI

from server.db.registry import (
    MatchHistoryNotFoundError,
    TickHistoryNotFoundError,
    get_completed_match_summaries,
    get_match_history,
    get_match_replay_tick,
    get_public_leaderboard,
)
from server.models.api import (
    CompletedMatchSummaryListResponse,
    MatchHistoryResponse,
    MatchReplayTickResponse,
    PublicLeaderboardResponse,
)

from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError
from .public_match_routes import (
    PublicRosterBuilder,
    PublicStatusPriority,
    RegistryProvider,
    build_public_match_router,
)


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

    # Keep static `/matches/completed` above the dynamic `/matches/{match_id}` route.
    router.include_router(
        build_public_match_router(
            match_registry_provider=match_registry_provider,
            history_database_url=history_database_url,
            public_match_status_priority=public_match_status_priority,
            build_in_memory_public_match_roster=build_in_memory_public_match_roster,
        )
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
