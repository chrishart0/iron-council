from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter

from server.db.registry import (
    MatchHistoryNotFoundError,
    TickHistoryNotFoundError,
    get_match_history,
    get_match_replay_tick,
)
from server.models.api import MatchHistoryResponse, MatchReplayTickResponse

from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError


def build_public_history_router(*, history_database_url: str | None) -> APIRouter:
    router = APIRouter()

    def require_history_database_url() -> str:
        if history_database_url is None:
            raise ApiError(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="match_history_unavailable",
                message="Persisted match history is only available in DB-backed mode.",
            )
        return history_database_url

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
