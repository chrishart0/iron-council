from __future__ import annotations

import os
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Header, Query, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from server import __version__
from server.agent_registry import (
    AllianceTransitionError,
    InMemoryMatchRegistry,
    MatchJoinError,
    TreatyTransitionError,
)
from server.db.registry import load_match_registry_from_database
from server.fog import project_agent_state
from server.models.api import (
    AgentProfileResponse,
    AllianceActionAcceptanceResponse,
    AllianceActionRequest,
    AllianceListResponse,
    ApiErrorDetail,
    ApiErrorResponse,
    AuthenticatedAgentContext,
    MatchJoinRequest,
    MatchJoinResponse,
    MatchListResponse,
    MatchMessageCreateRequest,
    MatchMessageInboxResponse,
    MatchSummary,
    MessageAcceptanceResponse,
    OrderAcceptanceResponse,
    TreatyActionAcceptanceResponse,
    TreatyActionRequest,
    TreatyListResponse,
)
from server.models.fog import AgentStateProjection
from server.models.orders import OrderEnvelope
from server.settings import get_settings

MATCH_REGISTRY_BACKEND_VARIABLE = "IRON_COUNCIL_MATCH_REGISTRY_BACKEND"


class ApiError(Exception):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def get_match_registry(request: Request) -> InMemoryMatchRegistry:
    return request.app.state.match_registry  # type: ignore[no-any-return]


MatchRegistryDependency = Annotated[InMemoryMatchRegistry, Depends(get_match_registry)]
ApiKeyHeader = Annotated[str | None, Header(alias="X-API-Key")]
PlayerIdQuery = Annotated[str, Query(...)]
API_ERROR_RESPONSE_SCHEMA = {"model": ApiErrorResponse}


def _build_validation_error_response(*, code: str, message: str) -> JSONResponse:
    payload = ApiErrorResponse(error=ApiErrorDetail(code=code, message=message))
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content=payload.model_dump(mode="json"),
    )


def _message_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        location = list(error.get("loc", ()))
        error_type = error.get("type")
        if location == ["query", "player_id"] and error_type == "missing":
            return _build_validation_error_response(
                code="missing_player_id",
                message="Query parameter 'player_id' is required.",
            )
        if location == ["body", "content"] and error_type == "string_too_short":
            return _build_validation_error_response(
                code="invalid_message_content",
                message="Message content must be at least 1 character long.",
            )
        if location and location[0] == "body" and error_type == "missing":
            return _build_validation_error_response(
                code="invalid_message_request",
                message="Message request is missing required fields.",
            )

    return _build_validation_error_response(
        code="invalid_message_request",
        message="Message request validation failed.",
    )


def _treaty_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        location = list(error.get("loc", ()))
        error_type = error.get("type")
        if location and location[0] == "body" and error_type == "missing":
            return _build_validation_error_response(
                code="invalid_treaty_request",
                message="Treaty request is missing required fields.",
            )
        if location == ["body", "action"] and error_type == "literal_error":
            return _build_validation_error_response(
                code="invalid_treaty_action",
                message="Treaty action must be one of: propose, accept, withdraw.",
            )
        if location == ["body", "treaty_type"] and error_type == "literal_error":
            return _build_validation_error_response(
                code="invalid_treaty_type",
                message="Treaty type must be one of: non_aggression, defensive, trade.",
            )

    return _build_validation_error_response(
        code="invalid_treaty_request",
        message="Treaty request validation failed.",
    )


def _alliance_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        location = list(error.get("loc", ()))
        error_type = error.get("type")
        error_message = str(error.get("msg", "")).lower()
        if location and location[0] == "body" and error_type == "missing":
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance request is missing required fields.",
            )
        if location == ["body", "action"] and error_type == "literal_error":
            return _build_validation_error_response(
                code="invalid_alliance_action",
                message="Alliance action must be one of: create, join, leave.",
            )
        if "alliance create does not accept alliance_id" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance create does not accept alliance_id.",
            )
        if "alliance create requires name" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance create requires name.",
            )
        if "alliance join requires alliance_id" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance join requires alliance_id.",
            )
        if "alliance join does not accept name" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance join does not accept name.",
            )
        if "alliance leave does not accept alliance_id" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance leave does not accept alliance_id.",
            )
        if "alliance leave does not accept name" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance leave does not accept name.",
            )

    return _build_validation_error_response(
        code="invalid_alliance_request",
        message="Alliance request validation failed.",
    )


def _join_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        location = list(error.get("loc", ()))
        error_type = error.get("type")
        if location and location[0] == "body" and error_type == "missing":
            return _build_validation_error_response(
                code="invalid_join_request",
                message="Join request is missing required fields.",
            )
        if location == ["body", "agent_id"] and error_type == "string_too_short":
            return _build_validation_error_response(
                code="invalid_join_request",
                message="Join request requires a non-empty agent_id.",
            )

    return _build_validation_error_response(
        code="invalid_join_request",
        message="Join request validation failed.",
    )


def get_authenticated_agent(
    registry: MatchRegistryDependency,
    api_key: ApiKeyHeader = None,
) -> AuthenticatedAgentContext:
    if api_key is None:
        raise ApiError(
            status_code=HTTPStatus.UNAUTHORIZED,
            code="invalid_api_key",
            message="A valid active X-API-Key header is required.",
        )

    authenticated_agent = registry.resolve_authenticated_agent(api_key)
    if authenticated_agent is None:
        raise ApiError(
            status_code=HTTPStatus.UNAUTHORIZED,
            code="invalid_api_key",
            message="A valid active X-API-Key header is required.",
        )
    return authenticated_agent


def create_app(*, match_registry: InMemoryMatchRegistry | None = None) -> FastAPI:
    app = FastAPI(title="iron-counsil-server", version=__version__)
    app.state.match_registry = match_registry or _load_default_match_registry()

    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        payload = ApiErrorResponse(error=ApiErrorDetail(code=exc.code, message=exc.message))
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        if request.url.path.startswith("/api/v1/matches/") and request.url.path.endswith(
            "/messages"
        ):
            return _message_validation_error_response(exc)
        if request.url.path.startswith("/api/v1/matches/") and request.url.path.endswith(
            "/treaties"
        ):
            return _treaty_validation_error_response(exc)
        if request.url.path.startswith("/api/v1/matches/") and request.url.path.endswith(
            "/alliances"
        ):
            return _alliance_validation_error_response(exc)
        if request.url.path.startswith("/api/v1/matches/") and request.url.path.endswith("/join"):
            return _join_validation_error_response(exc)
        return await request_validation_exception_handler(request, exc)

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
        "/agent/profile",
        response_model=AgentProfileResponse,
        responses={HTTPStatus.UNAUTHORIZED: API_ERROR_RESPONSE_SCHEMA},
    )
    async def get_authenticated_agent_profile(
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
        registry: MatchRegistryDependency,
    ) -> AgentProfileResponse:
        profile = registry.get_agent_profile(authenticated_agent.agent_id)
        if profile is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="agent_not_found",
                message=f"Agent '{authenticated_agent.agent_id}' was not found.",
            )
        return profile

    @api_router.get(
        "/agents/{agent_id}/profile",
        response_model=AgentProfileResponse,
        responses={HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA},
    )
    async def get_agent_profile(
        agent_id: str,
        registry: MatchRegistryDependency,
    ) -> AgentProfileResponse:
        profile = registry.get_agent_profile(agent_id)
        if profile is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="agent_not_found",
                message=f"Agent '{agent_id}' was not found.",
            )
        return profile

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
        "/matches/{match_id}/join",
        response_model=MatchJoinResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses={
            HTTPStatus.BAD_REQUEST: API_ERROR_RESPONSE_SCHEMA,
            HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA,
            HTTPStatus.UNPROCESSABLE_ENTITY: API_ERROR_RESPONSE_SCHEMA,
        },
    )
    async def join_match(
        match_id: str,
        join_request: MatchJoinRequest,
        registry: MatchRegistryDependency,
    ) -> MatchJoinResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        if join_request.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Join payload match_id '{join_request.match_id}' does not match route match "
                    f"'{match_id}'."
                ),
            )
        if registry.get_agent_profile(join_request.agent_id) is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="agent_not_found",
                message=f"Agent '{join_request.agent_id}' was not found.",
            )

        try:
            return registry.join_match(match_id=match_id, agent_id=join_request.agent_id)
        except MatchJoinError as exc:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code=exc.code,
                message=exc.message,
            ) from exc

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

    @api_router.get(
        "/matches/{match_id}/messages",
        response_model=MatchMessageInboxResponse,
        responses={
            HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA,
            HTTPStatus.UNPROCESSABLE_ENTITY: API_ERROR_RESPONSE_SCHEMA,
        },
    )
    async def get_match_messages(
        match_id: str,
        registry: MatchRegistryDependency,
        player_id: PlayerIdQuery,
    ) -> MatchMessageInboxResponse:
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

        return MatchMessageInboxResponse(
            match_id=match_id,
            player_id=player_id,
            messages=registry.list_visible_messages(match_id=match_id, player_id=player_id),
        )

    @api_router.post(
        "/matches/{match_id}/messages",
        response_model=MessageAcceptanceResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses={
            HTTPStatus.BAD_REQUEST: API_ERROR_RESPONSE_SCHEMA,
            HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA,
            HTTPStatus.UNPROCESSABLE_ENTITY: API_ERROR_RESPONSE_SCHEMA,
        },
    )
    async def post_match_message(
        match_id: str,
        message: MatchMessageCreateRequest,
        registry: MatchRegistryDependency,
    ) -> MessageAcceptanceResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        if message.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Message payload match_id '{message.match_id}' does not match route match "
                    f"'{match_id}'."
                ),
            )
        if message.sender_id not in record.state.players:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="player_not_found",
                message=f"Player '{message.sender_id}' was not found in match '{match_id}'.",
            )
        if message.tick != record.state.tick:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="tick_mismatch",
                message=(
                    f"Message payload tick '{message.tick}' does not match current match tick "
                    f"'{record.state.tick}'."
                ),
            )
        if message.channel == "world":
            if message.recipient_id is not None:
                raise ApiError(
                    status_code=HTTPStatus.BAD_REQUEST,
                    code="unsupported_recipient",
                    message="World messages do not support recipient_id.",
                )
        elif message.recipient_id not in record.state.players:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="unsupported_recipient",
                message=(
                    f"Direct messages require a recipient_id for a player in match '{match_id}'."
                ),
            )

        accepted_message = registry.record_message(match_id=match_id, message=message)
        return MessageAcceptanceResponse(
            status="accepted",
            match_id=match_id,
            message_id=accepted_message.message_id,
            channel=accepted_message.channel,
            sender_id=accepted_message.sender_id,
            recipient_id=accepted_message.recipient_id,
            tick=accepted_message.tick,
            content=accepted_message.content,
        )

    @api_router.get(
        "/matches/{match_id}/treaties",
        response_model=TreatyListResponse,
        responses={HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA},
    )
    async def get_match_treaties(
        match_id: str,
        registry: MatchRegistryDependency,
    ) -> TreatyListResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )

        return TreatyListResponse(
            match_id=match_id,
            treaties=registry.list_treaties(match_id=match_id),
        )

    @api_router.post(
        "/matches/{match_id}/treaties",
        response_model=TreatyActionAcceptanceResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses={
            HTTPStatus.BAD_REQUEST: API_ERROR_RESPONSE_SCHEMA,
            HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA,
            HTTPStatus.UNPROCESSABLE_ENTITY: API_ERROR_RESPONSE_SCHEMA,
        },
    )
    async def post_match_treaty(
        match_id: str,
        treaty_action: TreatyActionRequest,
        registry: MatchRegistryDependency,
    ) -> TreatyActionAcceptanceResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        if treaty_action.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Treaty payload match_id '{treaty_action.match_id}' does not match route "
                    f"match '{match_id}'."
                ),
            )
        if treaty_action.player_id not in record.state.players:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="player_not_found",
                message=(
                    f"Player '{treaty_action.player_id}' was not found in match '{match_id}'."
                ),
            )
        if treaty_action.counterparty_id not in record.state.players:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="player_not_found",
                message=(
                    f"Player '{treaty_action.counterparty_id}' was not found in match '{match_id}'."
                ),
            )
        if treaty_action.player_id == treaty_action.counterparty_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="self_targeted_treaty",
                message="Treaty actions require two different players.",
            )

        try:
            treaty = registry.apply_treaty_action(match_id=match_id, action=treaty_action)
        except TreatyTransitionError as exc:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code=exc.code,
                message=exc.message,
            ) from exc

        return TreatyActionAcceptanceResponse(
            status="accepted",
            match_id=match_id,
            treaty=treaty,
        )

    @api_router.get(
        "/matches/{match_id}/alliances",
        response_model=AllianceListResponse,
        responses={HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA},
    )
    async def get_match_alliances(
        match_id: str,
        registry: MatchRegistryDependency,
    ) -> AllianceListResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )

        return AllianceListResponse(
            match_id=match_id,
            alliances=registry.list_alliances(match_id=match_id),
        )

    @api_router.post(
        "/matches/{match_id}/alliances",
        response_model=AllianceActionAcceptanceResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses={
            HTTPStatus.BAD_REQUEST: API_ERROR_RESPONSE_SCHEMA,
            HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA,
            HTTPStatus.UNPROCESSABLE_ENTITY: API_ERROR_RESPONSE_SCHEMA,
        },
    )
    async def post_match_alliance(
        match_id: str,
        alliance_action: AllianceActionRequest,
        registry: MatchRegistryDependency,
    ) -> AllianceActionAcceptanceResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        if alliance_action.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Alliance payload match_id '{alliance_action.match_id}' does not match route "
                    f"match '{match_id}'."
                ),
            )
        if alliance_action.player_id not in record.state.players:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="player_not_found",
                message=(
                    f"Player '{alliance_action.player_id}' was not found in match '{match_id}'."
                ),
            )

        try:
            alliance = registry.apply_alliance_action(match_id=match_id, action=alliance_action)
        except AllianceTransitionError as exc:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code=exc.code,
                message=exc.message,
            ) from exc

        return AllianceActionAcceptanceResponse(
            status="accepted",
            match_id=match_id,
            player_id=alliance_action.player_id,
            alliance=alliance,
        )

    app.include_router(api_router)
    return app


def _load_default_match_registry() -> InMemoryMatchRegistry:
    backend = os.environ.get(MATCH_REGISTRY_BACKEND_VARIABLE, "memory")
    if backend == "memory":
        return InMemoryMatchRegistry()
    if backend == "db":
        return load_match_registry_from_database(get_settings().database_url)
    raise ValueError(
        "Unsupported "
        f"{MATCH_REGISTRY_BACKEND_VARIABLE} value {backend!r}; "
        "expected 'memory' or 'db'."
    )


app = create_app()
