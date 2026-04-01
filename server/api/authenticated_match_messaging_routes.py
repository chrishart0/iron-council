from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Body

from server.agent_registry import GroupChatAccessError, InMemoryMatchRegistry, MatchRecord
from server.models.api import (
    AuthenticatedAgentContext,
    GroupChatCreateAcceptanceResponse,
    GroupChatCreateRequest,
    GroupChatListResponse,
    GroupChatMessageAcceptanceResponse,
    GroupChatMessageCreateRequest,
    GroupChatMessageListResponse,
    MatchMessageCreateRequest,
    MatchMessageInboxResponse,
    MessageAcceptanceResponse,
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


def build_authenticated_match_messaging_router(
    *,
    registry_dependency: Any,
    authenticated_agent_dependency: Any,
    require_match_record: MatchRecordResolver,
    app_services: AppServices,
    broadcast_current_match: BroadcastCurrentMatch,
) -> APIRouter:
    router = APIRouter()
    group_chat_create_body = Annotated[GroupChatCreateRequest, Body()]
    group_chat_message_body = Annotated[GroupChatMessageCreateRequest, Body()]
    match_message_body = Annotated[MatchMessageCreateRequest, Body()]

    @router.get(
        "/matches/{match_id}/messages",
        response_model=MatchMessageInboxResponse,
        responses=_authenticated_route_responses(
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    )
    async def get_match_messages(
        match_id: str,
        authenticated_agent_context: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> MatchMessageInboxResponse:
        require_match_record(registry=registry, match_id=match_id)
        resolved_player_id = app_services.require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent_context,
        )

        return MatchMessageInboxResponse(
            match_id=match_id,
            player_id=resolved_player_id,
            messages=registry.list_visible_messages(
                match_id=match_id, player_id=resolved_player_id
            ),
        )

    @router.get(
        "/matches/{match_id}/group-chats",
        response_model=GroupChatListResponse,
        responses=_authenticated_route_responses(HTTPStatus.NOT_FOUND),
    )
    async def get_match_group_chats(
        match_id: str,
        authenticated_agent_context: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> GroupChatListResponse:
        require_match_record(registry=registry, match_id=match_id)
        resolved_player_id = app_services.require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent_context,
        )
        return GroupChatListResponse(
            match_id=match_id,
            player_id=resolved_player_id,
            group_chats=registry.list_visible_group_chats(
                match_id=match_id,
                player_id=resolved_player_id,
            ),
        )

    @router.post(
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
        group_chat: group_chat_create_body,
        authenticated_agent_context: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> GroupChatCreateAcceptanceResponse:
        record = require_match_record(registry=registry, match_id=match_id)
        if group_chat.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Group chat payload match_id '{group_chat.match_id}' does not match route "
                    f"match '{match_id}'."
                ),
            )
        resolved_player_id = app_services.require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent_context,
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

    @router.get(
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
        authenticated_agent_context: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> GroupChatMessageListResponse:
        require_match_record(registry=registry, match_id=match_id)
        resolved_player_id = app_services.require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent_context,
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

    @router.post(
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
        message: group_chat_message_body,
        authenticated_agent_context: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> GroupChatMessageAcceptanceResponse:
        record = require_match_record(registry=registry, match_id=match_id)
        if message.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Group chat message payload match_id '{message.match_id}' does not match "
                    f"route match '{match_id}'."
                ),
            )
        resolved_player_id = app_services.require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent_context,
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

    @router.post(
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
        message: match_message_body,
        authenticated_agent_context: AuthenticatedAgentContext = authenticated_agent_dependency,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> MessageAcceptanceResponse:
        record = require_match_record(registry=registry, match_id=match_id)
        if message.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Message payload match_id '{message.match_id}' does not match route match "
                    f"'{match_id}'."
                ),
            )
        resolved_player_id = app_services.require_joined_player_id(
            registry=registry,
            match_id=match_id,
            authenticated_agent=authenticated_agent_context,
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

    return router
