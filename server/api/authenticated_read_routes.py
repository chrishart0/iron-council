from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from server.agent_registry import InMemoryMatchRegistry
from server.agent_registry_commands import combine_submissions_by_player
from server.db.api_key_lifecycle import list_owned_api_keys
from server.db.guidance import list_owned_agent_guidance
from server.db.identity_hydration import get_agent_profile_from_db, get_human_profile_from_db
from server.fog import project_agent_state
from server.models.api import (
    AgentBriefingGuidanceRecord,
    AgentBriefingResponse,
    AgentProfileResponse,
    AllianceRecord,
    AuthenticatedAgentContext,
    HumanProfileResponse,
    OwnedAgentGuidedSessionRecentActivity,
    OwnedAgentGuidedSessionResponse,
    OwnedApiKeyListResponse,
    TreatyRecord,
)
from server.models.fog import AgentStateProjection
from server.models.orders import OrderBatch, OrderEnvelope

from .app_services import ApiKeyHeader, AppServices, AuthorizationHeader
from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError

RegistryProvider = Callable[..., InMemoryMatchRegistry]


def _queued_orders_for_player(
    *, match_record_player_submissions: list[OrderEnvelope]
) -> OrderBatch:
    if not match_record_player_submissions:
        return OrderBatch()
    combined_submission = combine_submissions_by_player(match_record_player_submissions)[0]
    return combined_submission.orders.model_copy(deep=True)


def _authenticated_read_route_responses(
    *status_codes: HTTPStatus,
) -> dict[int | str, dict[str, Any]]:
    return {
        int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
        **{int(status_code): API_ERROR_RESPONSE_SCHEMA for status_code in status_codes},
    }


def _current_alliance_for_player(
    *,
    alliances: list[AllianceRecord],
    current_alliance_id: str | None,
) -> list[AllianceRecord]:
    if current_alliance_id is None:
        return []
    return [alliance for alliance in alliances if alliance.alliance_id == current_alliance_id]


def _recent_treaties_for_player(
    *,
    treaties: list[TreatyRecord],
    player_id: str,
) -> list[TreatyRecord]:
    return [treaty for treaty in treaties if player_id in {treaty.player_a_id, treaty.player_b_id}]


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
        api_key: ApiKeyHeader = None,
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
        guidance: list[AgentBriefingGuidanceRecord] = []
        owner_user_id = app_services.resolve_authenticated_agent_owner_user_id(api_key=api_key)
        if owner_user_id is not None and app_services.history_database_url is not None:
            persisted_player_id = app_services.require_persisted_match_player_id(
                match_id=match_id,
                canonical_player_id=resolved_player_id,
                agent_id=authenticated_agent.agent_id,
            )
            guidance = [
                AgentBriefingGuidanceRecord(
                    guidance_id=entry.id,
                    match_id=entry.match_id,
                    player_id=resolved_player_id,
                    tick=entry.tick,
                    content=entry.content,
                    created_at=entry.created_at,
                )
                for entry in list_owned_agent_guidance(
                    database_url=app_services.history_database_url,
                    match_id=match_id,
                    owner_user_id=owner_user_id,
                    agent_player_id=persisted_player_id,
                )
                if since_tick is None or entry.tick >= since_tick
            ]
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
            guidance=guidance,
        )

    @router.get(
        "/matches/{match_id}/agents/{agent_id}/guided-session",
        response_model=OwnedAgentGuidedSessionResponse,
        responses=_authenticated_read_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.FORBIDDEN,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.SERVICE_UNAVAILABLE,
        ),
    )
    async def get_owned_agent_guided_session(
        match_id: str,
        agent_id: str,
        authorization: AuthorizationHeader = None,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> OwnedAgentGuidedSessionResponse:
        _, owned_agent = app_services.require_owned_agent_context(
            authorization=authorization,
            agent_id=agent_id,
        )

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
            authenticated_agent=owned_agent,
        )
        current_tick = record.state.tick
        player_state = record.state.players[resolved_player_id]
        queued_orders = _queued_orders_for_player(
            match_record_player_submissions=[
                submission
                for submission in record.order_submissions
                if submission.player_id == resolved_player_id and submission.tick == current_tick
            ]
        )
        recent_treaties = _recent_treaties_for_player(
            treaties=registry.list_treaties(
                match_id=match_id,
                since_tick=current_tick,
            ),
            player_id=resolved_player_id,
        )
        return OwnedAgentGuidedSessionResponse(
            match_id=match_id,
            agent_id=owned_agent.agent_id,
            player_id=resolved_player_id,
            state=project_agent_state(
                record.state,
                player_id=resolved_player_id,
                match_id=match_id,
            ),
            queued_orders=queued_orders,
            group_chats=registry.list_visible_group_chats(
                match_id=match_id,
                player_id=resolved_player_id,
            ),
            messages=registry.list_briefing_messages(
                match_id=match_id,
                player_id=resolved_player_id,
                since_tick=current_tick,
            ),
            recent_activity=OwnedAgentGuidedSessionRecentActivity(
                alliances=_current_alliance_for_player(
                    alliances=registry.list_alliances(match_id=match_id),
                    current_alliance_id=player_state.alliance_id,
                ),
                treaties=recent_treaties,
            ),
        )

    return router
