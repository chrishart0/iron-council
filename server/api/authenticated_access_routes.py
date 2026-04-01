from __future__ import annotations

from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from server.agent_registry import InMemoryMatchRegistry, MatchJoinError
from server.auth import hash_api_key
from server.db.registry import (
    MatchLobbyCreationError,
    MatchLobbyStartError,
    create_match_lobby,
    start_match_lobby,
)
from server.db.registry import (
    join_match as join_db_match,
)
from server.fog import project_agent_state
from server.models.api import (
    AgentBriefingResponse,
    AgentProfileResponse,
    AuthenticatedAgentContext,
    AuthenticatedOrderSubmissionRequest,
    MatchJoinRequest,
    MatchJoinResponse,
    MatchLobbyCreateRequest,
    MatchLobbyCreateResponse,
    MatchLobbyStartResponse,
    OrderAcceptanceResponse,
)
from server.models.domain import MatchStatus
from server.models.fog import AgentStateProjection
from server.models.orders import OrderEnvelope

from .app_services import (
    ApiKeyHeader,
    AppServices,
    AuthorizationHeader,
)
from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError

RegistryProvider = Callable[..., InMemoryMatchRegistry]
EnsureMatchRunning = Callable[[str], Awaitable[None]]


def _authenticated_route_responses(
    *status_codes: HTTPStatus,
) -> dict[int | str, dict[str, Any]]:
    return {
        int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
        **{int(status_code): API_ERROR_RESPONSE_SCHEMA for status_code in status_codes},
    }


def build_authenticated_access_router(
    *,
    match_registry_provider: RegistryProvider,
    app_services: AppServices,
    ensure_match_running: EnsureMatchRunning,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    registry_dependency = Depends(match_registry_provider)

    def resolve_authenticated_agent(
        registry: InMemoryMatchRegistry = registry_dependency,
        api_key: ApiKeyHeader = None,
    ) -> AuthenticatedAgentContext:
        return app_services.get_authenticated_agent(
            registry=registry,
            api_key=api_key,
        )

    authenticated_agent_dependency = Depends(resolve_authenticated_agent)
    history_database_url = app_services.history_database_url
    authenticated_api_error_responses: dict[int | str, dict[str, Any]] = {
        int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
    }

    @router.post(
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
        registry: InMemoryMatchRegistry = registry_dependency,
        api_key: ApiKeyHeader = None,
        authorization: AuthorizationHeader = None,
    ) -> MatchLobbyCreateResponse:
        if history_database_url is None and api_key is None and authorization is None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_api_key",
                message="A valid active X-API-Key header is required.",
            )
        authenticated_actor = app_services.resolve_authenticated_lobby_actor(
            registry=registry,
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

    @router.post(
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
        registry: InMemoryMatchRegistry = registry_dependency,
        api_key: ApiKeyHeader = None,
        authorization: AuthorizationHeader = None,
    ) -> MatchLobbyStartResponse:
        if history_database_url is None and api_key is None and authorization is None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_api_key",
                message="A valid active X-API-Key header is required.",
            )
        authenticated_actor = app_services.resolve_authenticated_lobby_actor(
            registry=registry,
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
        await ensure_match_running(match_id)
        return started_lobby.response

    @router.get(
        "/agent/profile",
        response_model=AgentProfileResponse,
        responses=authenticated_api_error_responses,
    )
    async def get_authenticated_agent_profile(
        authenticated_agent: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> AgentProfileResponse:
        profile = registry.get_agent_profile(authenticated_agent.agent_id)
        if profile is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="agent_not_found",
                message=f"Agent '{authenticated_agent.agent_id}' was not found.",
            )
        return profile

    @router.get(
        "/agents/{agent_id}/profile",
        response_model=AgentProfileResponse,
        responses={HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA},
    )
    async def get_agent_profile(
        agent_id: str,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> AgentProfileResponse:
        profile = registry.get_agent_profile(agent_id)
        if profile is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="agent_not_found",
                message=f"Agent '{agent_id}' was not found.",
            )
        return profile

    @router.get(
        "/matches/{match_id}/state",
        response_model=AgentStateProjection,
        responses=_authenticated_route_responses(HTTPStatus.NOT_FOUND),
    )
    async def get_match_state(
        match_id: str,
        registry: InMemoryMatchRegistry = registry_dependency,
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
        resolved_player_id = app_services.resolve_match_player_id(
            registry=registry,
            match_id=match_id,
            api_key=api_key,
            authorization=authorization,
        )
        return project_agent_state(record.state, player_id=resolved_player_id, match_id=match_id)

    @router.get(
        "/matches/{match_id}/agent-briefing",
        response_model=AgentBriefingResponse,
        responses=_authenticated_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
        ),
    )
    async def get_agent_briefing(
        match_id: str,
        authenticated_agent: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
        since_tick: Annotated[int | None, Query(ge=0)] = None,
    ) -> AgentBriefingResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        resolved_player_id = app_services.require_joined_player_id(
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

    @router.post(
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
        registry: InMemoryMatchRegistry = registry_dependency,
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
                    f"Join payload match_id '{join_request.match_id}' does not match route "
                    f"match '{match_id}'."
                ),
            )

        authenticated_actor = app_services.resolve_authenticated_lobby_actor(
            registry=registry,
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

    @router.post(
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
        registry: InMemoryMatchRegistry = registry_dependency,
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
        resolved_player_id = app_services.resolve_match_player_id(
            registry=registry,
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

    return router
