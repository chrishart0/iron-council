from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Body

from server.agent_registry import InMemoryMatchRegistry, TreatyTransitionError
from server.models.api import (
    AuthenticatedAgentContext,
    TreatyActionAcceptanceResponse,
    TreatyActionRequest,
    TreatyListResponse,
)

from .abuse import authenticated_write_abuse_dependency
from .app_services import AppServices
from .authenticated_match_route_helpers import (
    BroadcastCurrentMatch,
    MatchRecordResolver,
    authenticated_route_responses,
    authenticated_write_route_responses,
)
from .errors import ApiError


def build_authenticated_match_treaty_router(
    *,
    registry_dependency: Any,
    authenticated_agent_dependency: Any,
    require_match_record: MatchRecordResolver,
    app_services: AppServices,
    broadcast_current_match: BroadcastCurrentMatch,
) -> APIRouter:
    router = APIRouter()
    treaty_action_body = Annotated[TreatyActionRequest, Body()]

    @router.get(
        "/matches/{match_id}/treaties",
        response_model=TreatyListResponse,
        responses=authenticated_route_responses(HTTPStatus.NOT_FOUND),
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
        responses=authenticated_write_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
        dependencies=[authenticated_write_abuse_dependency],
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

    return router
