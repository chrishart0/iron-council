from __future__ import annotations

from server.agent_registry_types import (
    GroupChatAccessError,
    MatchAccessError,
    MatchGroupChat,
    MatchGroupChatMessage,
    MatchMessage,
    MatchRecord,
)
from server.models.api import (
    AgentBriefingMessageBuckets,
    AgentCommandMessage,
    GroupChatCreateRequest,
    GroupChatMessageCreateRequest,
    GroupChatMessageRecord,
    GroupChatRecord,
    MatchMessageCreateRequest,
    MatchMessageRecord,
    MessageChannel,
)


def record_message(
    *,
    record: MatchRecord,
    message: MatchMessageCreateRequest,
    sender_id: str,
) -> MatchMessageRecord:
    stored_message = append_message(
        record=record,
        channel=message.channel,
        sender_id=sender_id,
        recipient_id=message.recipient_id,
        tick=message.tick,
        content=message.content,
    )
    return MatchMessageRecord(
        message_id=stored_message.message_id,
        channel=stored_message.channel,
        sender_id=stored_message.sender_id,
        recipient_id=stored_message.recipient_id,
        tick=stored_message.tick,
        content=stored_message.content,
    )


def create_group_chat(
    *,
    record: MatchRecord,
    request: GroupChatCreateRequest,
    creator_id: str,
) -> GroupChatRecord:
    member_ids = sorted({creator_id, *request.member_ids})
    stored_group_chat = MatchGroupChat(
        group_chat_id=_next_group_chat_id(record.group_chats),
        name=request.name,
        member_ids=member_ids,
        created_by=creator_id,
        created_tick=request.tick,
    )
    record.group_chats.append(stored_group_chat)
    return _to_group_chat_record(stored_group_chat)


def list_visible_group_chats(
    *,
    record: MatchRecord | None,
    player_id: str,
) -> list[GroupChatRecord]:
    if record is None:
        return []

    visible_group_chats = [
        _to_group_chat_record(group_chat)
        for group_chat in record.group_chats
        if player_id in group_chat.member_ids
    ]
    return sorted(visible_group_chats, key=lambda group_chat: group_chat.group_chat_id)


def list_group_chat_messages(
    *,
    record: MatchRecord,
    group_chat_id: str,
    player_id: str,
    since_tick: int | None = None,
) -> list[GroupChatMessageRecord]:
    group_chat = require_group_chat_member(
        record=record,
        group_chat_id=group_chat_id,
        player_id=player_id,
    )
    return [
        GroupChatMessageRecord(
            message_id=message.message_id,
            group_chat_id=message.group_chat_id,
            sender_id=message.sender_id,
            tick=message.tick,
            content=message.content,
        )
        for message in group_chat.messages
        if since_tick is None or message.tick >= since_tick
    ]


def record_group_chat_message(
    *,
    record: MatchRecord,
    group_chat_id: str,
    message: GroupChatMessageCreateRequest,
    sender_id: str,
) -> GroupChatMessageRecord:
    group_chat = require_group_chat_member(
        record=record,
        group_chat_id=group_chat_id,
        player_id=sender_id,
    )
    stored_message = MatchGroupChatMessage(
        message_id=len(group_chat.messages),
        group_chat_id=group_chat.group_chat_id,
        sender_id=sender_id,
        tick=message.tick,
        content=message.content,
    )
    group_chat.messages.append(stored_message)
    return GroupChatMessageRecord(
        message_id=stored_message.message_id,
        group_chat_id=stored_message.group_chat_id,
        sender_id=stored_message.sender_id,
        tick=stored_message.tick,
        content=stored_message.content,
    )


def list_visible_messages(
    *,
    record: MatchRecord | None,
    player_id: str,
) -> list[MatchMessageRecord]:
    if record is None:
        return []

    visible_messages: list[MatchMessageRecord] = []
    for message in record.messages:
        is_visible_direct_message = message.channel == "direct" and (
            message.sender_id == player_id or message.recipient_id == player_id
        )
        if message.channel == "world" or is_visible_direct_message:
            visible_messages.append(
                MatchMessageRecord(
                    message_id=message.message_id,
                    channel=message.channel,
                    sender_id=message.sender_id,
                    recipient_id=message.recipient_id,
                    tick=message.tick,
                    content=message.content,
                )
            )
    return visible_messages


def list_briefing_messages(
    *,
    record: MatchRecord | None,
    player_id: str,
    since_tick: int | None = None,
) -> AgentBriefingMessageBuckets:
    visible_messages = list_visible_messages(record=record, player_id=player_id)
    filtered_messages = [
        message for message in visible_messages if since_tick is None or message.tick >= since_tick
    ]
    group_messages = list_visible_group_chat_messages(
        record=record,
        player_id=player_id,
        since_tick=since_tick,
    )
    return AgentBriefingMessageBuckets(
        direct=[message for message in filtered_messages if message.channel == "direct"],
        group=group_messages,
        world=[message for message in filtered_messages if message.channel == "world"],
    )


def list_visible_group_chat_messages(
    *,
    record: MatchRecord | None,
    player_id: str,
    since_tick: int | None = None,
) -> list[GroupChatMessageRecord]:
    if record is None:
        return []

    visible_messages = [
        GroupChatMessageRecord(
            message_id=message.message_id,
            group_chat_id=group_chat.group_chat_id,
            sender_id=message.sender_id,
            tick=message.tick,
            content=message.content,
        )
        for group_chat in record.group_chats
        if player_id in group_chat.member_ids
        for message in group_chat.messages
        if since_tick is None or message.tick >= since_tick
    ]
    return sorted(
        visible_messages,
        key=lambda message: (message.tick, message.group_chat_id, message.message_id),
    )


def append_message(
    *,
    record: MatchRecord,
    channel: MessageChannel,
    sender_id: str,
    recipient_id: str | None,
    tick: int,
    content: str,
) -> MatchMessage:
    stored_message = MatchMessage(
        message_id=len(record.messages),
        channel=channel,
        sender_id=sender_id,
        recipient_id=recipient_id,
        tick=tick,
        content=content,
    )
    record.messages.append(stored_message)
    return stored_message


def validate_command_message(
    *,
    record: MatchRecord,
    match_id: str,
    message: AgentCommandMessage,
    player_id: str,
) -> None:
    if message.channel == "group":
        if message.recipient_id is not None:
            raise MatchAccessError(
                code="unsupported_recipient",
                message="Group chat messages do not support recipient_id.",
            )
        if message.group_chat_id is None:
            raise MatchAccessError(
                code="unsupported_recipient",
                message="Group chat messages require group_chat_id.",
            )
        require_group_chat_member(
            record=record,
            group_chat_id=message.group_chat_id,
            player_id=player_id,
        )
        return

    if message.channel == "world":
        if message.recipient_id is not None:
            raise MatchAccessError(
                code="unsupported_recipient",
                message="World messages do not support recipient_id.",
            )
        return

    if message.group_chat_id is not None:
        raise MatchAccessError(
            code="unsupported_recipient",
            message="Direct messages do not support group_chat_id.",
        )

    if message.recipient_id not in record.state.players:
        raise MatchAccessError(
            code="unsupported_recipient",
            message=f"Direct messages require a recipient_id for a player in match '{match_id}'.",
        )


def require_group_chat_member(
    *,
    record: MatchRecord,
    group_chat_id: str,
    player_id: str,
) -> MatchGroupChat:
    group_chat = next(
        (
            group_chat
            for group_chat in record.group_chats
            if group_chat.group_chat_id == group_chat_id
        ),
        None,
    )
    if group_chat is None or player_id not in group_chat.member_ids:
        raise GroupChatAccessError(
            code="group_chat_not_visible",
            message=f"Group chat '{group_chat_id}' is not visible to player '{player_id}'.",
        )
    return group_chat


def _to_group_chat_record(group_chat: MatchGroupChat) -> GroupChatRecord:
    return GroupChatRecord(
        group_chat_id=group_chat.group_chat_id,
        name=group_chat.name,
        member_ids=list(group_chat.member_ids),
        created_by=group_chat.created_by,
        created_tick=group_chat.created_tick,
    )


def _next_group_chat_id(group_chats: list[MatchGroupChat]) -> str:
    next_index = 1
    existing_group_chat_ids = {group_chat.group_chat_id for group_chat in group_chats}
    while f"group-chat-{next_index}" in existing_group_chat_ids:
        next_index += 1
    return f"group-chat-{next_index}"
