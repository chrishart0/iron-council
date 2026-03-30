from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import WebSocket

from server.agent_registry import InMemoryMatchRegistry, MatchRecord
from server.fog import project_agent_state
from server.models.api import GroupChatMessageRecord, GroupChatRecord, MatchMessageRecord
from server.models.realtime import (
    MatchRealtimeEnvelope,
    MatchRealtimePayload,
    RealtimeViewerRole,
    SpectatorStateProjection,
)


@dataclass(slots=True)
class MatchWebSocketSubscription:
    websocket: WebSocket
    viewer_role: RealtimeViewerRole
    player_id: str | None = None


class MatchWebSocketManager:
    def __init__(
        self,
        *,
        send_timeout_seconds: float = 0.1,
        max_concurrent_sends: int = 16,
    ) -> None:
        self._connections: dict[str, list[MatchWebSocketSubscription]] = {}
        self._send_timeout_seconds = send_timeout_seconds
        self._max_concurrent_sends = max_concurrent_sends

    def register(
        self,
        *,
        match_id: str,
        websocket: WebSocket,
        viewer_role: RealtimeViewerRole,
        player_id: str | None = None,
    ) -> MatchWebSocketSubscription:
        subscription = MatchWebSocketSubscription(
            websocket=websocket,
            viewer_role=viewer_role,
            player_id=player_id,
        )
        self._connections.setdefault(match_id, []).append(subscription)
        return subscription

    def unregister(self, *, match_id: str, websocket: WebSocket) -> None:
        remaining = [
            subscription
            for subscription in self._connections.get(match_id, [])
            if subscription.websocket is not websocket
        ]
        if remaining:
            self._connections[match_id] = remaining
            return
        self._connections.pop(match_id, None)

    def connection_count(self, match_id: str) -> int:
        return len(self._connections.get(match_id, []))

    async def broadcast(
        self,
        *,
        match_id: str,
        payload_factory: Callable[[MatchWebSocketSubscription], MatchRealtimeEnvelope],
    ) -> None:
        subscriptions = list(self._connections.get(match_id, []))
        if not subscriptions:
            return

        semaphore = asyncio.Semaphore(self._max_concurrent_sends)

        async def send_to_subscription(subscription: MatchWebSocketSubscription) -> None:
            try:
                payload = payload_factory(subscription)
                async with semaphore:
                    await asyncio.wait_for(
                        subscription.websocket.send_json(payload.model_dump(mode="json")),
                        timeout=self._send_timeout_seconds,
                    )
            except Exception:
                self.unregister(match_id=match_id, websocket=subscription.websocket)

        await asyncio.gather(
            *(send_to_subscription(subscription) for subscription in subscriptions),
            return_exceptions=True,
        )


def build_match_realtime_envelope(
    *,
    registry: InMemoryMatchRegistry,
    match_id: str,
    viewer_role: RealtimeViewerRole,
    player_id: str | None = None,
) -> MatchRealtimeEnvelope:
    record = registry.get_match(match_id)
    if record is None:
        raise ValueError(f"Match '{match_id}' was not found.")

    projected_state = (
        project_agent_state(record.state, player_id=player_id or "", match_id=match_id)
        if viewer_role == "player"
        else _project_spectator_state(record=record)
    )
    return MatchRealtimeEnvelope(
        type="tick_update",
        data=MatchRealtimePayload(
            match_id=match_id,
            viewer_role=viewer_role,
            player_id=player_id,
            state=projected_state,
            world_messages=_list_world_messages(record=record),
            direct_messages=(
                _list_direct_messages(
                    registry=registry,
                    match_id=match_id,
                    player_id=player_id or "",
                )
                if viewer_role == "player"
                else _list_all_direct_messages(record=record)
            ),
            group_chats=(
                registry.list_visible_group_chats(match_id=match_id, player_id=player_id or "")
                if viewer_role == "player"
                else _list_all_group_chats(record=record)
            ),
            group_messages=(
                registry.list_visible_group_chat_messages(
                    match_id=match_id,
                    player_id=player_id or "",
                )
                if viewer_role == "player"
                else _list_all_group_chat_messages(record=record)
            ),
            treaties=registry.list_treaties(match_id=match_id),
            alliances=registry.list_alliances(match_id=match_id),
        ),
    )


async def broadcast_match_update(
    *,
    registry: InMemoryMatchRegistry,
    manager: MatchWebSocketManager,
    match_id: str,
) -> None:
    await manager.broadcast(
        match_id=match_id,
        payload_factory=lambda subscription: build_match_realtime_envelope(
            registry=registry,
            match_id=match_id,
            viewer_role=subscription.viewer_role,
            player_id=subscription.player_id,
        ),
    )


def _project_spectator_state(*, record: MatchRecord) -> SpectatorStateProjection:
    return SpectatorStateProjection(
        match_id=record.match_id,
        tick=record.state.tick,
        cities={
            city_id: city_state.model_copy(deep=True)
            for city_id, city_state in sorted(record.state.cities.items())
        },
        armies=[
            army.model_copy(deep=True)
            for army in sorted(record.state.armies, key=lambda army: army.id)
        ],
        players={
            player_id: player_state.model_copy(deep=True)
            for player_id, player_state in sorted(record.state.players.items())
        },
        victory=record.state.victory.model_copy(deep=True),
    )


def _list_world_messages(*, record: MatchRecord) -> list[MatchMessageRecord]:
    return [
        MatchMessageRecord(
            message_id=message.message_id,
            channel=message.channel,
            sender_id=message.sender_id,
            recipient_id=message.recipient_id,
            tick=message.tick,
            content=message.content,
        )
        for message in record.messages
        if message.channel == "world"
    ]


def _list_direct_messages(
    *,
    registry: InMemoryMatchRegistry,
    match_id: str,
    player_id: str,
) -> list[MatchMessageRecord]:
    return [
        message
        for message in registry.list_visible_messages(match_id=match_id, player_id=player_id)
        if message.channel == "direct"
    ]


def _list_all_direct_messages(*, record: MatchRecord) -> list[MatchMessageRecord]:
    return [
        MatchMessageRecord(
            message_id=message.message_id,
            channel=message.channel,
            sender_id=message.sender_id,
            recipient_id=message.recipient_id,
            tick=message.tick,
            content=message.content,
        )
        for message in record.messages
        if message.channel == "direct"
    ]


def _list_all_group_chats(*, record: MatchRecord) -> list[GroupChatRecord]:
    return [
        GroupChatRecord(
            group_chat_id=group_chat.group_chat_id,
            name=group_chat.name,
            member_ids=list(group_chat.member_ids),
            created_by=group_chat.created_by,
            created_tick=group_chat.created_tick,
        )
        for group_chat in sorted(
            record.group_chats, key=lambda group_chat: group_chat.group_chat_id
        )
    ]


def _list_all_group_chat_messages(*, record: MatchRecord) -> list[GroupChatMessageRecord]:
    visible_messages = [
        GroupChatMessageRecord(
            message_id=message.message_id,
            group_chat_id=group_chat.group_chat_id,
            sender_id=message.sender_id,
            tick=message.tick,
            content=message.content,
        )
        for group_chat in record.group_chats
        for message in group_chat.messages
    ]
    return sorted(
        visible_messages,
        key=lambda message: (message.tick, message.group_chat_id, message.message_id),
    )
