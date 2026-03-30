from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import WebSocket

from server.agent_registry import InMemoryMatchRegistry, MatchRecord
from server.fog import project_agent_state
from server.models.api import MatchMessageRecord
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
    def __init__(self) -> None:
        self._connections: dict[str, list[MatchWebSocketSubscription]] = {}

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
        for subscription in list(self._connections.get(match_id, [])):
            try:
                payload = payload_factory(subscription)
                await subscription.websocket.send_json(payload.model_dump(mode="json"))
            except Exception:
                self.unregister(match_id=match_id, websocket=subscription.websocket)


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
