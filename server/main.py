from __future__ import annotations

import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, Header, Query, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from server import __version__
from server.agent_registry import (
    AdvancedMatchTick,
    AllianceTransitionError,
    GroupChatAccessError,
    InMemoryMatchRegistry,
    MatchAccessError,
    MatchJoinError,
    TreatyTransitionError,
)
from server.db.registry import load_match_registry_from_database, persist_advanced_match_tick
from server.fog import project_agent_state
from server.models.api import (
    AgentBriefingResponse,
    AgentCommandEnvelopeRequest,
    AgentCommandEnvelopeResponse,
    AgentProfileResponse,
    AllianceActionAcceptanceResponse,
    AllianceActionRequest,
    AllianceListResponse,
    ApiErrorDetail,
    ApiErrorResponse,
    AuthenticatedAgentContext,
    AuthenticatedOrderSubmissionRequest,
    GroupChatCreateAcceptanceResponse,
    GroupChatCreateRequest,
    GroupChatListResponse,
    GroupChatMessageAcceptanceResponse,
    GroupChatMessageCreateRequest,
    GroupChatMessageListResponse,
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
from server.runtime import MatchRuntime
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
API_ERROR_RESPONSE_SCHEMA: dict[str, Any] = {"model": ApiErrorResponse}
AUTHENTICATED_API_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
}


def _authenticated_route_responses(
    *status_codes: HTTPStatus,
) -> dict[int | str, dict[str, Any]]:
    return {
        int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
        **{int(status_code): API_ERROR_RESPONSE_SCHEMA for status_code in status_codes},
    }


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


def _group_chat_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        location = list(error.get("loc", ()))
        error_type = error.get("type")
        if location == ["body", "name"] and error_type == "string_too_short":
            return _build_validation_error_response(
                code="invalid_group_chat_name",
                message="Group chat name must be at least 1 character long.",
            )
        if location == ["body", "member_ids"] and error_type == "too_short":
            return _build_validation_error_response(
                code="invalid_group_chat_members",
                message="Group chat creation requires at least 1 invited member.",
            )
        if location == ["body", "content"] and error_type == "string_too_short":
            return _build_validation_error_response(
                code="invalid_message_content",
                message="Message content must be at least 1 character long.",
            )
        if location and location[0] == "body" and error_type == "missing":
            return _build_validation_error_response(
                code="invalid_group_chat_request",
                message="Group chat request is missing required fields.",
            )

    return _build_validation_error_response(
        code="invalid_group_chat_request",
        message="Group chat request validation failed.",
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

    return _build_validation_error_response(
        code="invalid_join_request",
        message="Join request validation failed.",
    )


def _command_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        location = list(error.get("loc", ()))
        error_type = error.get("type")
        error_message = str(error.get("msg", "")).lower()
        if (
            len(location) == 4
            and location[0] == "body"
            and location[1] == "messages"
            and isinstance(location[2], int)
            and location[3] == "content"
            and error_type == "string_too_short"
        ):
            return _build_validation_error_response(
                code="invalid_message_content",
                message="Message content must be at least 1 character long.",
            )
        if (
            len(location) == 4
            and location[0] == "body"
            and location[1] == "treaties"
            and isinstance(location[2], int)
            and location[3] == "action"
            and error_type == "literal_error"
        ):
            return _build_validation_error_response(
                code="invalid_treaty_action",
                message="Treaty action must be one of: propose, accept, withdraw.",
            )
        if (
            len(location) == 4
            and location[0] == "body"
            and location[1] == "treaties"
            and isinstance(location[2], int)
            and location[3] == "treaty_type"
            and error_type == "literal_error"
        ):
            return _build_validation_error_response(
                code="invalid_treaty_type",
                message="Treaty type must be one of: non_aggression, defensive, trade.",
            )
        if location and location[0] == "body" and error_type == "missing":
            return _build_validation_error_response(
                code="invalid_command_request",
                message="Command request is missing required fields.",
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
        code="invalid_command_request",
        message="Command request validation failed.",
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


def _require_joined_player_id(
    *,
    registry: InMemoryMatchRegistry,
    match_id: str,
    authenticated_agent: AuthenticatedAgentContext,
) -> str:
    try:
        return registry.require_joined_player_id(
            match_id=match_id,
            agent_id=authenticated_agent.agent_id,
        )
    except MatchAccessError as exc:
        raise ApiError(
            status_code=HTTPStatus.BAD_REQUEST,
            code=exc.code,
            message=exc.message,
        ) from exc


def create_app(*, match_registry: InMemoryMatchRegistry | None = None) -> FastAPI:
    registry = match_registry or _load_default_match_registry()
    tick_persistence = _load_runtime_tick_persistence(match_registry=match_registry)

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
        app.state.match_registry = registry
        app.state.match_runtime = MatchRuntime(registry, tick_persistence=tick_persistence)
        await app.state.match_runtime.start()
        try:
            yield
        finally:
            await app.state.match_runtime.stop()

    app = FastAPI(title="iron-counsil-server", version=__version__, lifespan=lifespan)
    app.state.match_registry = registry

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
            ("/command", "/commands")
        ):
            return _command_validation_error_response(exc)
        if request.url.path.startswith("/api/v1/matches/") and "/group-chats" in request.url.path:
            return _group_chat_validation_error_response(exc)
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
        responses=AUTHENTICATED_API_ERROR_RESPONSES,
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
        responses=_authenticated_route_responses(HTTPStatus.NOT_FOUND),
    )
    async def get_match_state(
        match_id: str,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
    ) -> AgentStateProjection:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        resolved_player_id = _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
        )

        return project_agent_state(record.state, player_id=resolved_player_id, match_id=match_id)

    @api_router.get(
        "/matches/{match_id}/agent-briefing",
        response_model=AgentBriefingResponse,
        responses=_authenticated_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
        ),
    )
    async def get_agent_briefing(
        match_id: str,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
        since_tick: Annotated[int | None, Query(ge=0)] = None,
    ) -> AgentBriefingResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        resolved_player_id = _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
        )

        return AgentBriefingResponse(
            match_id=match_id,
            player_id=resolved_player_id,
            state=project_agent_state(
                record.state, player_id=resolved_player_id, match_id=match_id
            ),
            alliances=registry.list_alliances(match_id=match_id),
            treaties=registry.list_treaties(match_id=match_id, since_tick=since_tick),
            group_chats=registry.list_visible_group_chats(
                match_id=match_id,
                player_id=resolved_player_id,
            ),
            messages=registry.list_briefing_messages(
                match_id=match_id,
                player_id=resolved_player_id,
                since_tick=since_tick,
            ),
        )

    @api_router.post(
        "/matches/{match_id}/join",
        response_model=MatchJoinResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses=_authenticated_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    )
    async def join_match(
        match_id: str,
        join_request: MatchJoinRequest,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
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

        try:
            return registry.join_match(match_id=match_id, agent_id=authenticated_agent.agent_id)
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
        responses=_authenticated_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
        ),
    )
    async def submit_orders(
        match_id: str,
        submission: AuthenticatedOrderSubmissionRequest,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
    ) -> OrderAcceptanceResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        if submission.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Order payload match_id '{submission.match_id}' does not match route match "
                    f"'{match_id}'."
                ),
            )
        resolved_player_id = _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
        )
        if submission.tick != record.state.tick:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="tick_mismatch",
                message=(
                    f"Order payload tick '{submission.tick}' does not match current match tick "
                    f"'{record.state.tick}'."
                ),
            )

        envelope = OrderEnvelope(
            match_id=submission.match_id,
            player_id=resolved_player_id,
            tick=submission.tick,
            orders=submission.orders,
        )
        submission_index = registry.record_submission(match_id=match_id, envelope=envelope)
        return OrderAcceptanceResponse(
            status="accepted",
            match_id=match_id,
            player_id=envelope.player_id,
            tick=envelope.tick,
            submission_index=submission_index,
        )

    @api_router.post(
        "/matches/{match_id}/command",
        response_model=AgentCommandEnvelopeResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses=_authenticated_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    )
    @api_router.post(
        "/matches/{match_id}/commands",
        response_model=AgentCommandEnvelopeResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses=_authenticated_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
        include_in_schema=False,
    )
    async def post_match_command(
        match_id: str,
        command: AgentCommandEnvelopeRequest,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
    ) -> AgentCommandEnvelopeResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        if command.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Command payload match_id '{command.match_id}' does not match route match "
                    f"'{match_id}'."
                ),
            )
        resolved_player_id = _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
        )
        if command.tick != record.state.tick:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="tick_mismatch",
                message=(
                    f"Command payload tick '{command.tick}' does not match current match tick "
                    f"'{record.state.tick}'."
                ),
            )

        try:
            return registry.apply_command_envelope(
                match_id=match_id,
                command=command,
                player_id=resolved_player_id,
            )
        except (
            MatchAccessError,
            GroupChatAccessError,
            TreatyTransitionError,
            AllianceTransitionError,
        ) as exc:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code=exc.code,
                message=exc.message,
            ) from exc

    @api_router.get(
        "/matches/{match_id}/messages",
        response_model=MatchMessageInboxResponse,
        responses=_authenticated_route_responses(
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    )
    async def get_match_messages(
        match_id: str,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
    ) -> MatchMessageInboxResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        resolved_player_id = _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
        )

        return MatchMessageInboxResponse(
            match_id=match_id,
            player_id=resolved_player_id,
            messages=registry.list_visible_messages(
                match_id=match_id, player_id=resolved_player_id
            ),
        )

    @api_router.get(
        "/matches/{match_id}/group-chats",
        response_model=GroupChatListResponse,
        responses=_authenticated_route_responses(HTTPStatus.NOT_FOUND),
    )
    async def get_match_group_chats(
        match_id: str,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
    ) -> GroupChatListResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )

        resolved_player_id = _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
        )
        return GroupChatListResponse(
            match_id=match_id,
            player_id=resolved_player_id,
            group_chats=registry.list_visible_group_chats(
                match_id=match_id,
                player_id=resolved_player_id,
            ),
        )

    @api_router.post(
        "/matches/{match_id}/group-chats",
        response_model=GroupChatCreateAcceptanceResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses=_authenticated_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    )
    async def post_match_group_chat(
        match_id: str,
        group_chat: GroupChatCreateRequest,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
    ) -> GroupChatCreateAcceptanceResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        if group_chat.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Group chat payload match_id '{group_chat.match_id}' does not match route "
                    f"match '{match_id}'."
                ),
            )
        resolved_player_id = _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
        )
        if group_chat.tick != record.state.tick:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="tick_mismatch",
                message=(
                    f"Group chat payload tick '{group_chat.tick}' does not match current match "
                    f"tick '{record.state.tick}'."
                ),
            )
        for member_id in group_chat.member_ids:
            if member_id not in record.state.players:
                raise ApiError(
                    status_code=HTTPStatus.NOT_FOUND,
                    code="player_not_found",
                    message=f"Player '{member_id}' was not found in match '{match_id}'.",
                )

        accepted_group_chat = registry.create_group_chat(
            match_id=match_id,
            request=group_chat,
            creator_id=resolved_player_id,
        )
        return GroupChatCreateAcceptanceResponse(
            status="accepted",
            match_id=match_id,
            group_chat=accepted_group_chat,
        )

    @api_router.get(
        "/matches/{match_id}/group-chats/{group_chat_id}/messages",
        response_model=GroupChatMessageListResponse,
        responses=_authenticated_route_responses(
            HTTPStatus.FORBIDDEN,
            HTTPStatus.NOT_FOUND,
        ),
    )
    async def get_match_group_chat_messages(
        match_id: str,
        group_chat_id: str,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
    ) -> GroupChatMessageListResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        resolved_player_id = _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
        )

        try:
            messages = registry.list_group_chat_messages(
                match_id=match_id,
                group_chat_id=group_chat_id,
                player_id=resolved_player_id,
            )
        except GroupChatAccessError as exc:
            raise ApiError(
                status_code=HTTPStatus.FORBIDDEN,
                code=exc.code,
                message=exc.message,
            ) from exc

        return GroupChatMessageListResponse(
            match_id=match_id,
            group_chat_id=group_chat_id,
            player_id=resolved_player_id,
            messages=messages,
        )

    @api_router.post(
        "/matches/{match_id}/group-chats/{group_chat_id}/messages",
        response_model=GroupChatMessageAcceptanceResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses=_authenticated_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.FORBIDDEN,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    )
    async def post_match_group_chat_message(
        match_id: str,
        group_chat_id: str,
        message: GroupChatMessageCreateRequest,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
    ) -> GroupChatMessageAcceptanceResponse:
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
                    f"Group chat message payload match_id '{message.match_id}' does not match "
                    f"route match '{match_id}'."
                ),
            )
        resolved_player_id = _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
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

        try:
            accepted_message = registry.record_group_chat_message(
                match_id=match_id,
                group_chat_id=group_chat_id,
                message=message,
                sender_id=resolved_player_id,
            )
        except GroupChatAccessError as exc:
            raise ApiError(
                status_code=HTTPStatus.FORBIDDEN,
                code=exc.code,
                message=exc.message,
            ) from exc

        return GroupChatMessageAcceptanceResponse(
            status="accepted",
            match_id=match_id,
            group_chat_id=group_chat_id,
            message=accepted_message,
        )

    @api_router.post(
        "/matches/{match_id}/messages",
        response_model=MessageAcceptanceResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses=_authenticated_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    )
    async def post_match_message(
        match_id: str,
        message: MatchMessageCreateRequest,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
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
        resolved_player_id = _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
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

        accepted_message = registry.record_message(
            match_id=match_id,
            message=message,
            sender_id=resolved_player_id,
        )
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
        responses=_authenticated_route_responses(HTTPStatus.NOT_FOUND),
    )
    async def get_match_treaties(
        match_id: str,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
    ) -> TreatyListResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )

        _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
        )
        return TreatyListResponse(
            match_id=match_id,
            treaties=registry.list_treaties(match_id=match_id),
        )

    @api_router.post(
        "/matches/{match_id}/treaties",
        response_model=TreatyActionAcceptanceResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses=_authenticated_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    )
    async def post_match_treaty(
        match_id: str,
        treaty_action: TreatyActionRequest,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
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
        resolved_player_id = _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
        )
        if treaty_action.counterparty_id not in record.state.players:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="player_not_found",
                message=(
                    f"Player '{treaty_action.counterparty_id}' was not found in match '{match_id}'."
                ),
            )
        if resolved_player_id == treaty_action.counterparty_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="self_targeted_treaty",
                message="Treaty actions require two different players.",
            )

        try:
            treaty = registry.apply_treaty_action(
                match_id=match_id,
                action=treaty_action,
                player_id=resolved_player_id,
            )
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
        responses=_authenticated_route_responses(HTTPStatus.NOT_FOUND),
    )
    async def get_match_alliances(
        match_id: str,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
    ) -> AllianceListResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )

        _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
        )
        return AllianceListResponse(
            match_id=match_id,
            alliances=registry.list_alliances(match_id=match_id),
        )

    @api_router.post(
        "/matches/{match_id}/alliances",
        response_model=AllianceActionAcceptanceResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses=_authenticated_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    )
    async def post_match_alliance(
        match_id: str,
        alliance_action: AllianceActionRequest,
        registry: MatchRegistryDependency,
        authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)],
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
        resolved_player_id = _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
        )

        try:
            alliance = registry.apply_alliance_action(
                match_id=match_id,
                action=alliance_action,
                player_id=resolved_player_id,
            )
        except AllianceTransitionError as exc:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code=exc.code,
                message=exc.message,
            ) from exc

        return AllianceActionAcceptanceResponse(
            status="accepted",
            match_id=match_id,
            player_id=resolved_player_id,
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


def _load_runtime_tick_persistence(
    *,
    match_registry: InMemoryMatchRegistry | None,
) -> Callable[[AdvancedMatchTick], None] | None:
    if match_registry is not None:
        return None

    backend = os.environ.get(MATCH_REGISTRY_BACKEND_VARIABLE, "memory")
    if backend != "db":
        return None

    database_url = get_settings().database_url

    def persist_tick(advanced_tick: AdvancedMatchTick) -> None:
        persist_advanced_match_tick(database_url=database_url, advanced_tick=advanced_tick)

    return persist_tick


app = create_app()
