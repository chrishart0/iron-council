from __future__ import annotations

import asyncio
from http import HTTPStatus
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi import WebSocket
from httpx import ASGITransport, AsyncClient
from server.agent_registry import InMemoryMatchRegistry, build_seeded_match_records
from server.db.registry import load_match_registry_from_database, persist_advanced_match_tick
from server.db.testing import provision_seeded_database
from server.main import create_app
from server.models.api import RuntimeObservabilityResponse
from server.websocket import MatchWebSocketManager, build_match_realtime_envelope


class RecordingSocket:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    async def send_json(self, payload: dict[str, Any]) -> None:
        self.payloads.append(payload)


def _build_seeded_registry() -> InMemoryMatchRegistry:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)
    return registry


async def _get_runtime_status(app: Any) -> RuntimeObservabilityResponse:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health/runtime")

    assert response.status_code == HTTPStatus.OK
    return RuntimeObservabilityResponse.model_validate(response.json())


@pytest.mark.asyncio
async def test_runtime_status_reports_startup_recovery_for_resumed_active_matches() -> None:
    registry = _build_seeded_registry()
    app = create_app(match_registry=registry)

    async with app.router.lifespan_context(app):
        payload = await _get_runtime_status(app)

    assert payload.status == "ok"
    assert payload.startup_recovery is not None
    assert payload.startup_recovery.resumed_active_match_count == 1
    resumed_match = payload.startup_recovery.resumed_active_matches[0]
    assert resumed_match.match_id == "match-alpha"
    assert resumed_match.status == "active"
    assert resumed_match.tick == 142
    assert resumed_match.last_tick is None
    assert resumed_match.websocket.connection_count == 0


@pytest.mark.asyncio
async def test_runtime_status_reports_recent_tick_drift_for_active_matches() -> None:
    registry = _build_seeded_registry()
    active_match = registry.get_match("match-alpha")
    assert active_match is not None
    active_match.tick_interval_seconds = 1
    app = create_app(match_registry=registry)

    async with app.router.lifespan_context(app):
        await asyncio.sleep(1.2)
        payload = await _get_runtime_status(app)

    active_status = next(match for match in payload.matches if match.match_id == "match-alpha")
    assert active_status.tick == 143
    assert active_status.last_tick is not None
    assert active_status.last_tick.resolved_tick == 143
    assert active_status.last_tick.expected_interval_seconds == 1
    assert active_status.last_tick.drift_seconds >= 0
    assert active_status.last_tick.processing_seconds >= 0


@pytest.mark.asyncio
async def test_runtime_status_reports_recent_tick_drift_without_counting_healthy_processing_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _build_seeded_registry()
    active_match = registry.get_match("match-alpha")
    assert active_match is not None
    active_match.tick_interval_seconds = 1

    async def slow_broadcast_match_update(*_: Any, **__: Any) -> None:
        await asyncio.sleep(0.35)

    monkeypatch.setattr("server.main.broadcast_match_update", slow_broadcast_match_update)
    app = create_app(match_registry=registry)

    async with app.router.lifespan_context(app):
        await asyncio.sleep(2.55)
        payload = await _get_runtime_status(app)

    active_status = next(match for match in payload.matches if match.match_id == "match-alpha")
    assert active_status.tick == 144
    assert active_status.last_tick is not None
    assert active_status.last_tick.resolved_tick == 144
    assert active_status.last_tick.processing_seconds >= 0.35
    assert active_status.last_tick.drift_seconds < 0.2


@pytest.mark.asyncio
async def test_runtime_status_uses_db_backed_startup_recovery_for_resumed_active_matches(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'runtime-observability.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    registry = load_match_registry_from_database(database_url)
    advanced_tick = registry.advance_match_tick("00000000-0000-0000-0000-000000000101")
    persist_advanced_match_tick(database_url=database_url, advanced_tick=advanced_tick)

    app = create_app(
        settings_override={
            "DATABASE_URL": database_url,
            "IRON_COUNCIL_MATCH_REGISTRY_BACKEND": "db",
        }
    )

    async with app.router.lifespan_context(app):
        payload = await _get_runtime_status(app)

    assert payload.startup_recovery is not None
    assert payload.startup_recovery.resumed_active_match_count == 1
    resumed_match = payload.startup_recovery.resumed_active_matches[0]
    assert resumed_match.match_id == "00000000-0000-0000-0000-000000000101"
    assert resumed_match.status == "active"
    assert resumed_match.tick == 143
    assert resumed_match.last_tick is None


@pytest.mark.asyncio
async def test_runtime_status_reports_websocket_connection_and_recent_fanout() -> None:
    registry = _build_seeded_registry()
    app = create_app(match_registry=registry)

    async with app.router.lifespan_context(app):
        manager = app.state.match_websocket_manager
        socket = RecordingSocket()
        manager.register(
            match_id="match-alpha",
            websocket=cast(WebSocket, socket),
            viewer_role="spectator",
        )
        await manager.broadcast(
            match_id="match-alpha",
            payload_factory=lambda _: build_match_realtime_envelope(
                registry=registry,
                match_id="match-alpha",
                viewer_role="spectator",
            ),
        )
        payload = await _get_runtime_status(app)

    active_status = next(match for match in payload.matches if match.match_id == "match-alpha")
    assert len(socket.payloads) == 1
    assert active_status.websocket.connection_count == 1
    assert active_status.websocket.last_fanout is not None
    assert active_status.websocket.last_fanout.attempted_connections == 1
    assert active_status.websocket.last_fanout.delivered_connections == 1
    assert active_status.websocket.last_fanout.dropped_connections == 0


@pytest.mark.asyncio
async def test_websocket_fanout_ignores_payload_construction_failures() -> None:
    fanout_events: list[tuple[str, int, int, int]] = []
    manager = MatchWebSocketManager(
        fanout_observer=lambda match_id, attempted, delivered, dropped: fanout_events.append(
            (match_id, attempted, delivered, dropped)
        )
    )
    socket = RecordingSocket()
    manager.register(
        match_id="match-alpha",
        websocket=cast(WebSocket, socket),
        viewer_role="spectator",
    )

    with pytest.raises(RuntimeError, match="payload bug"):
        await manager.broadcast(
            match_id="match-alpha",
            payload_factory=lambda _: (_ for _ in ()).throw(RuntimeError("payload bug")),
        )

    assert manager.connection_count("match-alpha") == 1
    assert socket.payloads == []
    assert fanout_events == []
