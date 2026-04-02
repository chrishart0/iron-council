from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter

from server.db.registry import get_completed_match_summaries, get_public_leaderboard
from server.models.api import CompletedMatchSummaryListResponse, PublicLeaderboardResponse

from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError


def build_public_summary_router(*, history_database_url: str | None) -> APIRouter:
    router = APIRouter()

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

    return router
