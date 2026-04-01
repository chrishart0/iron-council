from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Body

from server.agent_registry import (
    AllianceTransitionError,
    GroupChatAccessError,
    InMemoryMatchRegistry,
    MatchAccessError,
    MatchRecord,
    TreatyTransitionError,
)
from server.models.api import (
    AgentCommandEnvelopeRequest,
    AgentCommandEnvelopeResponse,
    AuthenticatedAgentContext,
)

from .app_services import AppServices
from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError

MatchRecordResolver = Callable[..., MatchRecord]
BroadcastCurrentMatch = Callable[[str], Awaitable[None]]


def _authenticated_route_responses(
    *status_codes: HTTPStatus,
) -> dict[int | str, dict[str, Any]]:
    return {
        int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
        **{int(status_code): API_ERROR_RESPONSE_SCHEMA for status_code in status_codes},
    }


def build_authenticated_match_command_router(
    *,
    registry_dependency: Any,
    authenticated_agent_dependency: Any,
    require_match_record: MatchRecordResolver,
    app_services: AppServices,
    broadcast_current_match: BroadcastCurrentMatch,
) -> APIRouter:
    router = APIRouter()
    command_request_body = Annotated[AgentCommandEnvelopeRequest, Body()]

    @router.post(
        "/matches/{match_id}/command",
        response_model=AgentCommandEnvelopeResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses=_authenticated_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    )
    @router.post(
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
        command: command_request_body,
        authenticated_agent_context: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> AgentCommandEnvelopeResponse:
        record = require_match_record(registry=registry, match_id=match_id)
        if command.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Command payload match_id '{command.match_id}' does not match route match "
                    f"'{match_id}'."
                ),
            )
        resolved_player_id = app_services.require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent_context,
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

    return router
