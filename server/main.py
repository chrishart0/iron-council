from __future__ import annotations

import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from http import HTTPStatus
from typing import Annotated, Any, Final, Literal, cast

from fastapi import APIRouter, Depends, FastAPI, Header, Query, Request, WebSocket
from starlette.websockets import WebSocketState

from server import __version__
from server.agent_registry import (
    AdvancedMatchTick,
    AllianceTransitionError,
    GroupChatAccessError,
    InMemoryMatchRegistry,
    MatchAccessError,
    MatchJoinError,
    MatchRecord,
    TreatyTransitionError,
)
from server.api.errors import API_ERROR_RESPONSE_SCHEMA, ApiError, register_error_handlers
from server.api.public_routes import build_public_api_router, register_public_metadata_routes
from server.api.realtime_routes import register_realtime_routes
from server.auth import (
    HumanJwtValidationError,
    extract_bearer_token,
    hash_api_key,
    validate_human_jwt,
)
from server.db.registry import (
    MatchLobbyCreationError,
    MatchLobbyStartError,
    create_match_lobby,
    load_match_registry_from_database,
    persist_advanced_match_tick,
    resolve_authenticated_agent_context_from_db,
    resolve_human_player_id_from_db,
    start_match_lobby,
)
from server.db.registry import (
    join_match as join_db_match,
)
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
    MatchLobbyCreateRequest,
    MatchLobbyCreateResponse,
    MatchLobbyStartResponse,
    MatchMessageCreateRequest,
    MatchMessageInboxResponse,
    MessageAcceptanceResponse,
    OrderAcceptanceResponse,
    PublicMatchRosterRow,
    TreatyActionAcceptanceResponse,
    TreatyActionRequest,
    TreatyListResponse,
)
from server.models.domain import MatchStatus
from server.models.fog import AgentStateProjection
from server.models.orders import OrderEnvelope
from server.runtime import MatchRuntime
from server.settings import Settings, get_settings
from server.websocket import (
    MatchWebSocketManager,
    broadcast_match_update,
)


def get_match_registry(request: Request) -> InMemoryMatchRegistry:
    return request.app.state.match_registry  # type: ignore[no-any-return]


MatchRegistryDependency = Annotated[InMemoryMatchRegistry, Depends(get_match_registry)]
TickPersistence = Callable[[AdvancedMatchTick], None]
_DEFAULT_TICK_PERSISTENCE: Final = object()
ApiKeyHeader = Annotated[str | None, Header(alias="X-API-Key")]
AuthorizationHeader = Annotated[str | None, Header(alias="Authorization")]
AUTHENTICATED_API_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
}


@dataclass(frozen=True, slots=True)
class AuthenticatedLobbyActor:
    kind: Literal["agent", "human"]
    agent: AuthenticatedAgentContext | None = None
    api_key: str | None = None
    human_user_id: str | None = None


def _authenticated_route_responses(
    *status_codes: HTTPStatus,
) -> dict[int | str, dict[str, Any]]:
    return {
        int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
        **{int(status_code): API_ERROR_RESPONSE_SCHEMA for status_code in status_codes},
    }


def _public_match_status_priority(status: MatchStatus) -> int:
    if status is MatchStatus.LOBBY:
        return 0
    if status is MatchStatus.ACTIVE:
        return 1
    if status is MatchStatus.PAUSED:
        return 2
    return 3


def get_authenticated_agent(
    request: Request,
    registry: MatchRegistryDependency,
    api_key: ApiKeyHeader = None,
) -> AuthenticatedAgentContext:
    authenticated_agent = _resolve_authenticated_agent_context(
        registry=registry,
        history_database_url=cast(str | None, request.app.state.history_database_url),
        api_key=api_key,
    )
    if authenticated_agent is None:
        raise ApiError(
            status_code=HTTPStatus.UNAUTHORIZED,
            code="invalid_api_key",
            message="A valid active X-API-Key header is required.",
        )
    return authenticated_agent


def _resolve_authenticated_agent_context(
    *,
    registry: InMemoryMatchRegistry,
    history_database_url: str | None,
    api_key: str | None,
) -> AuthenticatedAgentContext | None:
    if api_key is None:
        return None

    authenticated_agent = registry.resolve_authenticated_agent(api_key)
    if authenticated_agent is None and history_database_url is not None:
        authenticated_agent = resolve_authenticated_agent_context_from_db(
            database_url=history_database_url,
            api_key=api_key,
        )
    return authenticated_agent


def _resolve_authenticated_human_user_id(
    *,
    settings: Settings,
    authorization: str | None,
) -> str:
    if authorization is None:
        raise ApiError(
            status_code=HTTPStatus.UNAUTHORIZED,
            code="invalid_player_auth",
            message="Player routes require a valid Bearer token or active X-API-Key header.",
        )

    try:
        token = extract_bearer_token(authorization)
        human_context = validate_human_jwt(token, settings=settings)
    except HumanJwtValidationError as exc:
        raise ApiError(
            status_code=HTTPStatus.UNAUTHORIZED,
            code=exc.code,
            message=exc.message,
        ) from exc
    return human_context.user_id


def _resolve_authenticated_lobby_actor(
    *,
    registry: InMemoryMatchRegistry,
    settings: Settings,
    history_database_url: str | None,
    api_key: str | None,
    authorization: str | None,
) -> AuthenticatedLobbyActor:
    authenticated_agent = _resolve_authenticated_agent_context(
        registry=registry,
        history_database_url=history_database_url,
        api_key=api_key,
    )
    if authenticated_agent is not None and api_key is not None:
        return AuthenticatedLobbyActor(
            kind="agent",
            agent=authenticated_agent,
            api_key=api_key,
        )
    if api_key is not None:
        raise ApiError(
            status_code=HTTPStatus.UNAUTHORIZED,
            code="invalid_api_key",
            message="A valid active X-API-Key header is required.",
        )
    if authorization is None and settings.human_jwt_secret is None:
        raise ApiError(
            status_code=HTTPStatus.UNAUTHORIZED,
            code="invalid_api_key",
            message="A valid active X-API-Key header is required.",
        )
    return AuthenticatedLobbyActor(
        kind="human",
        human_user_id=_resolve_authenticated_human_user_id(
            settings=settings,
            authorization=authorization,
        ),
    )


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


def _require_joined_human_player_id(
    *,
    registry: InMemoryMatchRegistry,
    match_id: str,
    user_id: str,
) -> str:
    try:
        return registry.require_joined_human_player_id(match_id=match_id, user_id=user_id)
    except MatchAccessError as exc:
        raise ApiError(
            status_code=HTTPStatus.BAD_REQUEST,
            code=exc.code,
            message=exc.message,
        ) from exc


def _resolve_human_player_id(
    *,
    registry: InMemoryMatchRegistry,
    history_database_url: str | None,
    match_id: str,
    user_id: str,
) -> str:
    resolved_player_id = registry.get_match(match_id)
    if resolved_player_id is None:
        raise ApiError(
            status_code=HTTPStatus.NOT_FOUND,
            code="match_not_found",
            message=f"Match '{match_id}' was not found.",
        )
    if history_database_url is not None:
        db_player_id = resolve_human_player_id_from_db(
            database_url=history_database_url,
            match_id=match_id,
            user_id=user_id,
        )
        if db_player_id is not None:
            return db_player_id
    return _require_joined_human_player_id(
        registry=registry,
        match_id=match_id,
        user_id=user_id,
    )


def _resolve_match_player_id(
    *,
    registry: InMemoryMatchRegistry,
    settings: Settings,
    history_database_url: str | None,
    match_id: str,
    api_key: str | None,
    authorization: str | None,
) -> str:
    if api_key is not None:
        authenticated_agent = _resolve_authenticated_agent_context(
            registry=registry,
            history_database_url=history_database_url,
            api_key=api_key,
        )
        if authenticated_agent is None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_api_key",
                message="A valid active X-API-Key header is required.",
            )
        return _require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent,
        )
    if authorization is None:
        raise ApiError(
            status_code=HTTPStatus.UNAUTHORIZED,
            code="invalid_player_auth",
            message="Player routes require a valid Bearer token or active X-API-Key header.",
        )
    return _resolve_human_player_id(
        registry=registry,
        history_database_url=history_database_url,
        match_id=match_id,
        user_id=_resolve_authenticated_human_user_id(
            settings=settings,
            authorization=authorization,
        ),
    )


def _resolve_websocket_player_viewer(
    *,
    registry: InMemoryMatchRegistry,
    settings: Settings,
    history_database_url: str | None,
    match_id: str,
    player_id: str | None,
    token: str | None,
) -> str:
    if token is None:
        raise ApiError(
            status_code=HTTPStatus.UNAUTHORIZED,
            code="invalid_websocket_auth",
            message="Player websocket connections require a valid human JWT token query parameter.",
        )
    try:
        human_context = validate_human_jwt(token, settings=settings)
    except HumanJwtValidationError as exc:
        raise ApiError(
            status_code=HTTPStatus.UNAUTHORIZED,
            code="invalid_websocket_auth",
            message=exc.message,
        ) from exc

    resolved_player_id = _resolve_human_player_id(
        registry=registry,
        history_database_url=history_database_url,
        match_id=match_id,
        user_id=human_context.user_id,
    )
    if player_id is not None and resolved_player_id != player_id:
        raise ApiError(
            status_code=HTTPStatus.FORBIDDEN,
            code="player_auth_mismatch",
            message=(
                f"Player websocket auth resolved to player '{resolved_player_id}', not "
                f"'{player_id}'."
            ),
        )
    return resolved_player_id


async def _close_websocket_for_api_error(websocket: WebSocket, exc: ApiError) -> None:
    if websocket.client_state is WebSocketState.CONNECTED:
        await websocket.close(code=1008, reason=exc.code)
        return
    await websocket.close(code=1008, reason=exc.code)


async def _send_websocket_auth_error(websocket: WebSocket, exc: ApiError) -> None:
    if websocket.client_state is not WebSocketState.CONNECTED:
        await websocket.accept()
    payload = ApiErrorResponse(error=ApiErrorDetail(code=exc.code, message=exc.message))
    await websocket.send_json(payload.model_dump(mode="json"))
    await websocket.close(code=1008, reason=exc.code)


def create_app(
    *,
    match_registry: InMemoryMatchRegistry | None = None,
    tick_persistence: TickPersistence | None | object = _DEFAULT_TICK_PERSISTENCE,
    settings_override: dict[str, str] | None = None,
) -> FastAPI:
    settings_env = dict(os.environ)
    if settings_override is not None:
        settings_env.update(settings_override)
    settings = get_settings(env=settings_env)
    registry = match_registry or _load_default_match_registry(settings=settings)
    websocket_manager = MatchWebSocketManager()
    runtime_tick_persistence = (
        _load_runtime_tick_persistence(settings=settings, match_registry=match_registry)
        if tick_persistence is _DEFAULT_TICK_PERSISTENCE
        else cast(TickPersistence | None, tick_persistence)
    )
    history_database_url = _load_history_database_url(settings=settings)

    async def broadcast_current_match(match_id: str) -> None:
        await broadcast_match_update(
            registry=registry,
            manager=websocket_manager,
            match_id=match_id,
        )

    async def broadcast_advanced_tick(advanced_tick: AdvancedMatchTick) -> None:
        await broadcast_current_match(advanced_tick.match_id)

    match_runtime = MatchRuntime(
        registry,
        tick_persistence=runtime_tick_persistence,
        tick_broadcast=broadcast_advanced_tick,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
        app.state.match_registry = registry
        app.state.match_websocket_manager = websocket_manager
        app.state.match_runtime = match_runtime
        app.state.settings = settings
        app.state.history_database_url = history_database_url
        await match_runtime.start()
        try:
            yield
        finally:
            await match_runtime.stop()

    app = FastAPI(title="iron-council-server", version=__version__, lifespan=lifespan)
    app.state.match_registry = registry
    app.state.match_websocket_manager = websocket_manager
    app.state.match_runtime = match_runtime
    app.state.settings = settings
    app.state.history_database_url = history_database_url

    register_error_handlers(app)
    register_public_metadata_routes(app)
    register_realtime_routes(
        app,
        registry=registry,
        websocket_manager=websocket_manager,
        settings=settings,
        history_database_url=history_database_url,
        resolve_websocket_player_viewer=_resolve_websocket_player_viewer,
        send_websocket_auth_error=_send_websocket_auth_error,
        close_websocket_for_api_error=_close_websocket_for_api_error,
    )
    app.include_router(
        build_public_api_router(
            match_registry_provider=get_match_registry,
            history_database_url=history_database_url,
            public_match_status_priority=_public_match_status_priority,
            build_in_memory_public_match_roster=(
                lambda registry, record: _build_in_memory_public_match_roster(
                    registry=registry,
                    record=record,
                )
            ),
        )
    )

    api_router = APIRouter(prefix="/api/v1")

    @api_router.post(
        "/matches",
        response_model=MatchLobbyCreateResponse,
        status_code=HTTPStatus.CREATED,
        responses=_authenticated_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.SERVICE_UNAVAILABLE,
        ),
    )
    async def create_match_lobby_route(
        create_request: MatchLobbyCreateRequest,
        registry: MatchRegistryDependency,
        api_key: ApiKeyHeader = None,
        authorization: AuthorizationHeader = None,
    ) -> MatchLobbyCreateResponse:
        if history_database_url is None and api_key is None and authorization is None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_api_key",
                message="A valid active X-API-Key header is required.",
            )
        authenticated_actor = _resolve_authenticated_lobby_actor(
            registry=registry,
            settings=settings,
            history_database_url=history_database_url,
            api_key=api_key,
            authorization=authorization,
        )
        if history_database_url is None:
            raise ApiError(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="match_lobby_creation_unavailable",
                message="Authenticated match lobby creation is only available in DB-backed mode.",
            )
        try:
            created_lobby = create_match_lobby(
                database_url=history_database_url,
                authenticated_agent_id=(
                    authenticated_actor.agent.agent_id
                    if authenticated_actor.agent is not None
                    else None
                ),
                authenticated_agent_display_name=(
                    authenticated_actor.agent.display_name
                    if authenticated_actor.agent is not None
                    else None
                ),
                authenticated_api_key_hash=(
                    hash_api_key(authenticated_actor.api_key)
                    if authenticated_actor.api_key is not None
                    else None
                ),
                authenticated_human_user_id=authenticated_actor.human_user_id,
                request=create_request,
            )
        except MatchLobbyCreationError as exc:
            raise ApiError(
                status_code=(
                    HTTPStatus.UNAUTHORIZED
                    if exc.code in {"invalid_api_key", "invalid_player_auth"}
                    else HTTPStatus.BAD_REQUEST
                ),
                code=exc.code,
                message=exc.message,
            ) from exc

        registry.seed_match(created_lobby.record)
        return created_lobby.response

    @api_router.post(
        "/matches/{match_id}/start",
        response_model=MatchLobbyStartResponse,
        responses=_authenticated_route_responses(
            HTTPStatus.NOT_FOUND,
            HTTPStatus.FORBIDDEN,
            HTTPStatus.CONFLICT,
            HTTPStatus.SERVICE_UNAVAILABLE,
        ),
    )
    async def start_match_lobby_route(
        match_id: str,
        request: Request,
        registry: MatchRegistryDependency,
        api_key: ApiKeyHeader = None,
        authorization: AuthorizationHeader = None,
    ) -> MatchLobbyStartResponse:
        if history_database_url is None and api_key is None and authorization is None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_api_key",
                message="A valid active X-API-Key header is required.",
            )
        authenticated_actor = _resolve_authenticated_lobby_actor(
            registry=registry,
            settings=settings,
            history_database_url=history_database_url,
            api_key=api_key,
            authorization=authorization,
        )
        if history_database_url is None:
            raise ApiError(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="match_lobby_start_unavailable",
                message="Authenticated lobby start is only available in DB-backed mode.",
            )
        try:
            started_lobby = start_match_lobby(
                database_url=history_database_url,
                match_id=match_id,
                authenticated_api_key_hash=(
                    hash_api_key(authenticated_actor.api_key)
                    if authenticated_actor.api_key is not None
                    else None
                ),
                authenticated_human_user_id=authenticated_actor.human_user_id,
            )
        except MatchLobbyStartError as exc:
            status_code = HTTPStatus.BAD_REQUEST
            if exc.code in {"invalid_api_key", "invalid_player_auth"}:
                status_code = HTTPStatus.UNAUTHORIZED
            elif exc.code == "match_not_found":
                status_code = HTTPStatus.NOT_FOUND
            elif exc.code == "match_start_forbidden":
                status_code = HTTPStatus.FORBIDDEN
            elif exc.code in {
                "match_lobby_not_ready",
                "match_already_active",
                "match_already_completed",
                "match_not_startable",
            }:
                status_code = HTTPStatus.CONFLICT
            raise ApiError(
                status_code=status_code,
                code=exc.code,
                message=exc.message,
            ) from exc

        registry.seed_match(started_lobby.record)
        await request.app.state.match_runtime.ensure_match_running(match_id)
        return started_lobby.response

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
        api_key: ApiKeyHeader = None,
        authorization: AuthorizationHeader = None,
    ) -> AgentStateProjection:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        resolved_player_id = _resolve_match_player_id(
            registry=registry,
            settings=settings,
            history_database_url=history_database_url,
            match_id=match_id,
            api_key=api_key,
            authorization=authorization,
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
        api_key: ApiKeyHeader = None,
        authorization: AuthorizationHeader = None,
    ) -> MatchJoinResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        if api_key is None and authorization is None and record.status is not MatchStatus.LOBBY:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_api_key",
                message="A valid active X-API-Key header is required.",
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

        authenticated_actor = _resolve_authenticated_lobby_actor(
            registry=registry,
            settings=settings,
            history_database_url=history_database_url,
            api_key=api_key,
            authorization=authorization,
        )
        try:
            if history_database_url is not None:
                joined_match = join_db_match(
                    database_url=history_database_url,
                    match_id=match_id,
                    authenticated_api_key_hash=(
                        hash_api_key(authenticated_actor.api_key)
                        if authenticated_actor.api_key is not None
                        else None
                    ),
                    authenticated_human_user_id=authenticated_actor.human_user_id,
                )
                registry.seed_match(joined_match.record)
                return joined_match.response
            if authenticated_actor.agent is None:
                raise ApiError(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                    code="match_join_unavailable",
                    message="Authenticated human joins are only available in DB-backed mode.",
                )
            return registry.join_match(
                match_id=match_id,
                agent_id=authenticated_actor.agent.agent_id,
            )
        except MatchJoinError as exc:
            status_code = HTTPStatus.BAD_REQUEST
            if exc.code in {"invalid_api_key", "invalid_player_auth"}:
                status_code = HTTPStatus.UNAUTHORIZED
            elif exc.code == "match_not_found":
                status_code = HTTPStatus.NOT_FOUND
            raise ApiError(status_code=status_code, code=exc.code, message=exc.message) from exc

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
        api_key: ApiKeyHeader = None,
        authorization: AuthorizationHeader = None,
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
        resolved_player_id = _resolve_match_player_id(
            registry=registry,
            settings=settings,
            history_database_url=history_database_url,
            match_id=match_id,
            api_key=api_key,
            authorization=authorization,
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
            response = registry.apply_command_envelope(
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

        if command.alliance is not None or command.treaties or command.messages:
            await broadcast_current_match(match_id)
        return response

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
        await broadcast_current_match(match_id)
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

        await broadcast_current_match(match_id)
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
        await broadcast_current_match(match_id)
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

        response = TreatyActionAcceptanceResponse(
            status="accepted",
            match_id=match_id,
            treaty=treaty,
        )
        await broadcast_current_match(match_id)
        return response

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

        response = AllianceActionAcceptanceResponse(
            status="accepted",
            match_id=match_id,
            player_id=resolved_player_id,
            alliance=alliance,
        )
        await broadcast_current_match(match_id)
        return response

    app.include_router(api_router)
    return app


def _load_default_match_registry(*, settings: Settings) -> InMemoryMatchRegistry:
    if settings.match_registry_backend == "memory":
        return InMemoryMatchRegistry()
    if settings.match_registry_backend == "db":
        return load_match_registry_from_database(settings.database_url)
    raise ValueError(
        "Unsupported "
        f"IRON_COUNCIL_MATCH_REGISTRY_BACKEND value {settings.match_registry_backend!r}; "
        "expected 'memory' or 'db'."
    )


def _load_runtime_tick_persistence(
    *,
    settings: Settings,
    match_registry: InMemoryMatchRegistry | None,
) -> Callable[[AdvancedMatchTick], None] | None:
    if match_registry is not None:
        return None

    if settings.match_registry_backend != "db":
        return None

    database_url = settings.database_url

    def persist_tick(advanced_tick: AdvancedMatchTick) -> None:
        persist_advanced_match_tick(database_url=database_url, advanced_tick=advanced_tick)

    return persist_tick


def _load_history_database_url(*, settings: Settings) -> str | None:
    if settings.match_registry_backend != "db":
        return None
    return settings.database_url


def _build_in_memory_public_match_roster(
    *, registry: InMemoryMatchRegistry, record: MatchRecord
) -> list[PublicMatchRosterRow]:
    visible_player_ids = [
        player_id
        for player_id, player_state in sorted(record.state.players.items())
        if player_state.cities_owned and not player_state.is_eliminated
    ]
    joined_human_player_ids = sorted(set(record.joined_humans.values()))
    joined_agent_player_ids = sorted(
        {
            player_id
            for agent_id, player_id in record.joined_agents.items()
            if agent_id.startswith("agent-")
        }
    )

    if (
        joined_human_player_ids
        and len(joined_human_player_ids) == record.public_current_player_count
    ):
        roster_player_ids = joined_human_player_ids
    else:
        joined_player_ids = sorted(set(joined_human_player_ids) | set(joined_agent_player_ids))
        roster_player_ids = joined_player_ids or visible_player_ids

    if not roster_player_ids:
        roster_player_ids = visible_player_ids

    human_player_ids = set(joined_human_player_ids)
    roster = [
        PublicMatchRosterRow(
            player_id=player_id,
            display_name=profile.display_name,
            competitor_kind=record.public_competitor_kinds.get(
                player_id,
                "human" if player_id in human_player_ids else "agent",
            ),
        )
        for player_id in roster_player_ids
        if (profile := registry.get_agent_profile(f"agent-{player_id}")) is not None
    ]
    ordered_roster = sorted(
        roster,
        key=lambda row: (
            row.display_name.casefold(),
            0 if row.competitor_kind == "human" else 1,
            row.display_name,
        ),
    )
    return ordered_roster[: record.public_current_player_count]


app = create_app()
