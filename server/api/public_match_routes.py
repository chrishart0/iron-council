from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus

from fastapi import APIRouter, Depends

from server.agent_registry import InMemoryMatchRegistry, MatchRecord
from server.db.registry import (
    PublicMatchDetailNotFoundError,
    get_public_match_detail,
    get_public_match_summaries,
)
from server.models.api import (
    MatchListResponse,
    MatchSummary,
    PublicMatchDetailResponse,
    PublicMatchRosterRow,
)
from server.models.domain import MatchStatus

from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError

RegistryProvider = Callable[..., InMemoryMatchRegistry]
PublicStatusPriority = Callable[[MatchStatus], int]
PublicRosterBuilder = Callable[[InMemoryMatchRegistry, MatchRecord], list[PublicMatchRosterRow]]


def build_public_match_router(
    *,
    match_registry_provider: RegistryProvider,
    history_database_url: str | None,
    public_match_status_priority: PublicStatusPriority,
    build_in_memory_public_match_roster: PublicRosterBuilder,
) -> APIRouter:
    router = APIRouter()
    registry_dependency = Depends(match_registry_provider)

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

    return router
