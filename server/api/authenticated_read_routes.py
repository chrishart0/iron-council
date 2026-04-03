from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from server.agent_registry import InMemoryMatchRegistry
from server.db.api_key_lifecycle import list_owned_api_keys
from server.db.identity_hydration import get_agent_profile_from_db, get_human_profile_from_db
from server.fog import project_agent_state
from server.models.api import (
    AgentBriefingResponse,
    AgentProfileResponse,
    AuthenticatedAgentContext,
    HumanProfileResponse,
    OwnedApiKeyListResponse,
)
from server.models.fog import AgentStateProjection

from .app_services import ApiKeyHeader, AppServices, AuthorizationHeader
from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError

RegistryProvider = Callable[..., InMemoryMatchRegistry]


def _authenticated_read_route_responses(
    *status_codes: HTTPStatus,
) -> dict[int | str, dict[str, Any]]:
    return {
        int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
        **{int(status_code): API_ERROR_RESPONSE_SCHEMA for status_code in status_codes},
    }


def build_authenticated_read_router(
    *,
    match_registry_provider: RegistryProvider,
    app_services: AppServices,
) -> APIRouter:
    router = APIRouter()
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
    authenticated_api_error_responses: dict[int | str, dict[str, Any]] = {
        int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
    }

    @router.get(
        "/agent/profile",
        response_model=AgentProfileResponse,
        responses=authenticated_api_error_responses,
    )
    async def get_authenticated_agent_profile(
        authenticated_agent: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> AgentProfileResponse:
        profile = (
            get_agent_profile_from_db(
                database_url=app_services.history_database_url,
                agent_id=authenticated_agent.agent_id,
            )
            if app_services.history_database_url is not None
            else registry.get_agent_profile(authenticated_agent.agent_id)
        )
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
        profile = (
            get_agent_profile_from_db(
                database_url=app_services.history_database_url,
                agent_id=agent_id,
            )
            if app_services.history_database_url is not None
            else registry.get_agent_profile(agent_id)
        )
        if profile is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="agent_not_found",
                message=f"Agent '{agent_id}' was not found.",
            )
        return profile

    @router.get(
        "/humans/{human_id}/profile",
        response_model=HumanProfileResponse,
        responses={
            HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA,
            HTTPStatus.SERVICE_UNAVAILABLE: API_ERROR_RESPONSE_SCHEMA,
        },
    )
    async def get_human_profile(human_id: str) -> HumanProfileResponse:
        if app_services.history_database_url is None:
            raise ApiError(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="human_profile_unavailable",
                message="Public human profiles are only available in DB-backed mode.",
            )
        profile = get_human_profile_from_db(
            database_url=app_services.history_database_url,
            human_id=human_id,
        )
        if profile is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="human_not_found",
                message=f"Human '{human_id}' was not found.",
            )
        return profile

    @router.get(
        "/account/api-keys",
        response_model=OwnedApiKeyListResponse,
        responses={
            int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
            int(HTTPStatus.SERVICE_UNAVAILABLE): API_ERROR_RESPONSE_SCHEMA,
        },
    )
    async def list_authenticated_human_api_keys(
        authorization: AuthorizationHeader = None,
    ) -> OwnedApiKeyListResponse:
        if app_services.history_database_url is None:
            raise ApiError(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="api_key_lifecycle_unavailable",
                message="Owned API key lifecycle routes are only available in DB-backed mode.",
            )

        user_id = app_services.require_authenticated_human_user_id(authorization=authorization)
        return OwnedApiKeyListResponse(
            items=list_owned_api_keys(
                database_url=app_services.history_database_url,
                user_id=user_id,
            )
        )

    @router.get(
        "/matches/{match_id}/state",
        response_model=AgentStateProjection,
        responses=_authenticated_read_route_responses(HTTPStatus.NOT_FOUND),
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
        responses=_authenticated_read_route_responses(
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
                record.state,
                player_id=resolved_player_id,
                match_id=match_id,
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

    return router
