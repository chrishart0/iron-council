from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends

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
    AllianceActionAcceptanceResponse,
    AllianceActionRequest,
    AllianceListResponse,
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
    TreatyActionAcceptanceResponse,
    TreatyActionRequest,
    TreatyListResponse,
)

from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError

RegistryProvider = Callable[..., InMemoryMatchRegistry]
AuthenticatedAgentDependency = Callable[..., AuthenticatedAgentContext]
RequireJoinedPlayerId = Callable[..., str]
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
    authenticated_agent_dependency: AuthenticatedAgentDependency,
    require_joined_player_id: RequireJoinedPlayerId,
    broadcast_current_match: BroadcastCurrentMatch,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    registry_dependency = Annotated[
        InMemoryMatchRegistry,
        Depends(match_registry_provider),
    ]
    authenticated_agent_context_dependency = Annotated[
        AuthenticatedAgentContext,
        Depends(authenticated_agent_dependency),
    ]
    command_request_body = Annotated[AgentCommandEnvelopeRequest, Body()]
    group_chat_create_body = Annotated[GroupChatCreateRequest, Body()]
    group_chat_message_body = Annotated[GroupChatMessageCreateRequest, Body()]
    match_message_body = Annotated[MatchMessageCreateRequest, Body()]
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
        registry: registry_dependency,
        authenticated_agent_context: authenticated_agent_context_dependency,
        command: command_request_body,
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
        resolved_player_id = require_joined_player_id(
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
        registry: registry_dependency,
        authenticated_agent_context: authenticated_agent_context_dependency,
    ) -> MatchMessageInboxResponse:
        require_match_record(registry=registry, match_id=match_id)
        resolved_player_id = require_joined_player_id(
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
        registry: registry_dependency,
        authenticated_agent_context: authenticated_agent_context_dependency,
    ) -> GroupChatListResponse:
        require_match_record(registry=registry, match_id=match_id)
        resolved_player_id = require_joined_player_id(
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
        registry: registry_dependency,
        authenticated_agent_context: authenticated_agent_context_dependency,
        group_chat: group_chat_create_body,
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
        resolved_player_id = require_joined_player_id(
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
        registry: registry_dependency,
        authenticated_agent_context: authenticated_agent_context_dependency,
    ) -> GroupChatMessageListResponse:
        require_match_record(registry=registry, match_id=match_id)
        resolved_player_id = require_joined_player_id(
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
        registry: registry_dependency,
        authenticated_agent_context: authenticated_agent_context_dependency,
        message: group_chat_message_body,
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
        resolved_player_id = require_joined_player_id(
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
        registry: registry_dependency,
        authenticated_agent_context: authenticated_agent_context_dependency,
        message: match_message_body,
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
        resolved_player_id = require_joined_player_id(
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

    @router.get(
        "/matches/{match_id}/treaties",
        response_model=TreatyListResponse,
        responses=_authenticated_route_responses(HTTPStatus.NOT_FOUND),
    )
    async def get_match_treaties(
        match_id: str,
        registry: registry_dependency,
        authenticated_agent_context: authenticated_agent_context_dependency,
    ) -> TreatyListResponse:
        require_match_record(registry=registry, match_id=match_id)
        require_joined_player_id(
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
        registry: registry_dependency,
        authenticated_agent_context: authenticated_agent_context_dependency,
        treaty_action: treaty_action_body,
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
        resolved_player_id = require_joined_player_id(
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
        registry: registry_dependency,
        authenticated_agent_context: authenticated_agent_context_dependency,
    ) -> AllianceListResponse:
        require_match_record(registry=registry, match_id=match_id)
        require_joined_player_id(
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
        registry: registry_dependency,
        authenticated_agent_context: authenticated_agent_context_dependency,
        alliance_action: alliance_action_body,
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
        resolved_player_id = require_joined_player_id(
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
