from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends

from server.agent_registry import (
    AllianceTransitionError,
    InMemoryMatchRegistry,
    MatchRecord,
    TreatyTransitionError,
)
from server.models.api import (
    AllianceActionAcceptanceResponse,
    AllianceActionRequest,
    AllianceListResponse,
    AuthenticatedAgentContext,
    TreatyActionAcceptanceResponse,
    TreatyActionRequest,
    TreatyListResponse,
)

from .app_services import ApiKeyHeader, AppServices
from .authenticated_match_command_routes import build_authenticated_match_command_router
from .authenticated_match_messaging_routes import build_authenticated_match_messaging_router
from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError

RegistryProvider = Callable[..., InMemoryMatchRegistry]
BroadcastCurrentMatch = Callable[[str], Awaitable[None]]


def _authenticated_route_responses(
    *status_codes: HTTPStatus,
) -> dict[int | str, dict[str, Any]]:
    return {
        int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
        **{int(status_code): API_ERROR_RESPONSE_SCHEMA for status_code in status_codes},
    }


def build_authenticated_match_router(
    *,
    match_registry_provider: RegistryProvider,
    app_services: AppServices,
    broadcast_current_match: BroadcastCurrentMatch,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    registry_dependency = Depends(match_registry_provider)
    treaty_action_body = Annotated[TreatyActionRequest, Body()]
    alliance_action_body = Annotated[AllianceActionRequest, Body()]

    def require_match_record(*, registry: InMemoryMatchRegistry, match_id: str) -> MatchRecord:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        return record

    def resolve_authenticated_agent(
        registry: InMemoryMatchRegistry = registry_dependency,
        api_key: ApiKeyHeader = None,
    ) -> AuthenticatedAgentContext:
        return app_services.get_authenticated_agent(
            registry=registry,
            api_key=api_key,
        )

    authenticated_agent_dependency = Depends(resolve_authenticated_agent)
    router.include_router(
        build_authenticated_match_command_router(
            registry_dependency=registry_dependency,
            authenticated_agent_dependency=authenticated_agent_dependency,
            require_match_record=require_match_record,
            app_services=app_services,
            broadcast_current_match=broadcast_current_match,
        )
    )
    router.include_router(
        build_authenticated_match_messaging_router(
            registry_dependency=registry_dependency,
            authenticated_agent_dependency=authenticated_agent_dependency,
            require_match_record=require_match_record,
            app_services=app_services,
            broadcast_current_match=broadcast_current_match,
        )
    )

    @router.get(
        "/matches/{match_id}/treaties",
        response_model=TreatyListResponse,
        responses=_authenticated_route_responses(HTTPStatus.NOT_FOUND),
    )
    async def get_match_treaties(
        match_id: str,
        authenticated_agent_context: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> TreatyListResponse:
        require_match_record(registry=registry, match_id=match_id)
        app_services.require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent_context,
        )
        return TreatyListResponse(
            match_id=match_id,
            treaties=registry.list_treaties(match_id=match_id),
        )

    @router.post(
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
        treaty_action: treaty_action_body,
        authenticated_agent_context: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> TreatyActionAcceptanceResponse:
        record = require_match_record(registry=registry, match_id=match_id)
        if treaty_action.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Treaty payload match_id '{treaty_action.match_id}' does not match route "
                    f"match '{match_id}'."
                ),
            )
        resolved_player_id = app_services.require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent_context,
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

    @router.get(
        "/matches/{match_id}/alliances",
        response_model=AllianceListResponse,
        responses=_authenticated_route_responses(HTTPStatus.NOT_FOUND),
    )
    async def get_match_alliances(
        match_id: str,
        authenticated_agent_context: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> AllianceListResponse:
        require_match_record(registry=registry, match_id=match_id)
        app_services.require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent_context,
        )
        return AllianceListResponse(
            match_id=match_id,
            alliances=registry.list_alliances(match_id=match_id),
        )

    @router.post(
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
        alliance_action: alliance_action_body,
        authenticated_agent_context: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> AllianceActionAcceptanceResponse:
        require_match_record(registry=registry, match_id=match_id)
        if alliance_action.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Alliance payload match_id '{alliance_action.match_id}' does not match route "
                    f"match '{match_id}'."
                ),
            )
        resolved_player_id = app_services.require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent_context,
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

    return router
