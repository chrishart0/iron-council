from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Body

from server.agent_registry import AllianceTransitionError, InMemoryMatchRegistry
from server.models.api import (
    AllianceActionAcceptanceResponse,
    AllianceActionRequest,
    AllianceListResponse,
    AuthenticatedAgentContext,
)

from .app_services import AppServices
from .authenticated_match_route_helpers import (
    BroadcastCurrentMatch,
    MatchRecordResolver,
    authenticated_route_responses,
)
from .errors import ApiError


def build_authenticated_match_alliance_router(
    *,
    registry_dependency: Any,
    authenticated_agent_dependency: Any,
    require_match_record: MatchRecordResolver,
    app_services: AppServices,
    broadcast_current_match: BroadcastCurrentMatch,
) -> APIRouter:
    router = APIRouter()
    alliance_action_body = Annotated[AllianceActionRequest, Body()]

    @router.get(
        "/matches/{match_id}/alliances",
        response_model=AllianceListResponse,
        responses=authenticated_route_responses(HTTPStatus.NOT_FOUND),
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
        responses=authenticated_route_responses(
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
