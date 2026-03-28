from __future__ import annotations

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from server import __version__
from server.agent_registry import InMemoryMatchRegistry
from server.fog import project_agent_state
from server.models.api import (
    ApiErrorDetail,
    ApiErrorResponse,
    MatchListResponse,
    MatchSummary,
    OrderAcceptanceResponse,
)
from server.models.fog import AgentStateProjection
from server.models.orders import OrderEnvelope


class ApiError(Exception):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def get_match_registry(request: Request) -> InMemoryMatchRegistry:
    return request.app.state.match_registry  # type: ignore[no-any-return]


MatchRegistryDependency = Annotated[InMemoryMatchRegistry, Depends(get_match_registry)]
PlayerIdQuery = Annotated[str, Query(...)]
API_ERROR_RESPONSE_SCHEMA = {"model": ApiErrorResponse}


def create_app(*, match_registry: InMemoryMatchRegistry | None = None) -> FastAPI:
    app = FastAPI(title="iron-counsil-server", version=__version__)
    app.state.match_registry = match_registry or InMemoryMatchRegistry()

    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        payload = ApiErrorResponse(error=ApiErrorDetail(code=exc.code, message=exc.message))
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump(mode="json"))

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

    api_router = APIRouter(prefix="/api/v1")

    @api_router.get("/matches", response_model=MatchListResponse)
    async def list_matches(
        registry: MatchRegistryDependency,
    ) -> MatchListResponse:
        return MatchListResponse(
            matches=[
                MatchSummary(
                    match_id=record.match_id,
                    status=record.status,
                    tick=record.state.tick,
                    tick_interval_seconds=record.tick_interval_seconds,
                )
                for record in registry.list_matches()
            ]
        )

    @api_router.get(
        "/matches/{match_id}/state",
        response_model=AgentStateProjection,
        responses={HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA},
    )
    async def get_match_state(
        match_id: str,
        registry: MatchRegistryDependency,
        player_id: PlayerIdQuery,
    ) -> AgentStateProjection:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        if player_id not in record.state.players:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="player_not_found",
                message=f"Player '{player_id}' was not found in match '{match_id}'.",
            )

        return project_agent_state(record.state, player_id=player_id, match_id=match_id)

    @api_router.post(
        "/matches/{match_id}/orders",
        response_model=OrderAcceptanceResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses={
            HTTPStatus.BAD_REQUEST: API_ERROR_RESPONSE_SCHEMA,
            HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA,
        },
    )
    async def submit_orders(
        match_id: str,
        envelope: OrderEnvelope,
        registry: MatchRegistryDependency,
    ) -> OrderAcceptanceResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        if envelope.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Order payload match_id '{envelope.match_id}' does not match route match "
                    f"'{match_id}'."
                ),
            )
        if envelope.player_id not in record.state.players:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="player_not_found",
                message=f"Player '{envelope.player_id}' was not found in match '{match_id}'.",
            )
        if envelope.tick != record.state.tick:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="tick_mismatch",
                message=(
                    f"Order payload tick '{envelope.tick}' does not match current match tick "
                    f"'{record.state.tick}'."
                ),
            )

        submission_index = registry.record_submission(match_id=match_id, envelope=envelope)
        return OrderAcceptanceResponse(
            status="accepted",
            match_id=match_id,
            player_id=envelope.player_id,
            tick=envelope.tick,
            submission_index=submission_index,
        )

    app.include_router(api_router)
    return app


app = create_app()
