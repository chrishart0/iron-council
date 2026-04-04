from __future__ import annotations

import asyncio
import importlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from server.agent_registry import (
    AdvancedMatchTick,
    InMemoryMatchRegistry,
    build_seeded_agent_api_key,
    build_seeded_match_records,
)
from server.api import (
    AppServices,
    build_authenticated_access_router,
    build_authenticated_match_router,
    register_error_handlers,
)
from server.auth import hash_api_key
from server.db import tick_persistence as db_tick_persistence_module
from server.db.guidance import append_owned_agent_guidance
from server.db.identity import build_non_seeded_display_name
from server.db.registry import load_match_registry_from_database, persist_advanced_match_tick
from server.db.testing import provision_seeded_database
from server.main import create_app
from server.models.api import (
    AllianceActionRequest,
    AuthenticatedAgentContext,
    GroupChatCreateRequest,
    GroupChatMessageCreateRequest,
    MatchMessageCreateRequest,
    TreatyActionRequest,
)
from server.models.domain import MatchStatus
from server.models.orders import OrderEnvelope
from server.settings import get_settings
from server.websocket import MatchWebSocketManager, build_match_realtime_envelope
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from starlette.websockets import WebSocketDisconnect
from tests.support import (
    build_persisted_player_id,
    insert_agent_entitlement_grant,
    insert_api_key,
    insert_completed_match_fixture,
    insert_seeded_agent_player,
)


def _army_by_id(payload: dict[str, Any], army_id: str) -> dict[str, Any]:
    return next(army for army in payload["visible_armies"] if army["id"] == army_id)


def _match_state_dump(
    registry: InMemoryMatchRegistry, match_id: str = "match-alpha"
) -> dict[str, Any]:
    record = registry.get_match(match_id)
    assert record is not None
    return record.state.model_dump(mode="json")


async def _record_broadcast(*, broadcasted_match_ids: list[str], match_id: str) -> None:
    broadcasted_match_ids.append(match_id)


def _message_payload(
    *,
    match_id: str = "match-alpha",
    tick: int = 142,
    channel: str = "world",
    recipient_id: str | None = None,
    content: str = "Hold position.",
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "tick": tick,
        "channel": channel,
        "recipient_id": recipient_id,
        "content": content,
    }


def _group_chat_create_payload(
    *,
    match_id: str = "match-alpha",
    tick: int = 142,
    name: str = "War Council",
    member_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "tick": tick,
        "name": name,
        "member_ids": member_ids or ["player-2"],
    }


def _treaty_payload(
    *,
    match_id: str = "match-alpha",
    counterparty_id: str = "player-1",
    action: str = "propose",
    treaty_type: str = "trade",
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "counterparty_id": counterparty_id,
        "action": action,
        "treaty_type": treaty_type,
    }


def _alliance_payload(
    *,
    match_id: str = "match-alpha",
    action: str = "create",
    alliance_id: str | None = None,
    name: str | None = "Northern Pact",
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "action": action,
        "alliance_id": alliance_id,
        "name": name,
    }


def _command_envelope_payload(
    *,
    match_id: str = "match-alpha",
    tick: int = 142,
    orders: dict[str, Any] | None = None,
    messages: list[dict[str, Any]] | None = None,
    treaties: list[dict[str, Any]] | None = None,
    alliance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "tick": tick,
        "orders": orders
        or {
            "movements": [],
            "recruitment": [],
            "upgrades": [],
            "transfers": [],
        },
        "messages": messages or [],
        "treaties": treaties or [],
        "alliance": alliance,
    }


def _command_message(
    *,
    channel: str = "world",
    recipient_id: str | None = None,
    group_chat_id: str | None = None,
    content: str = "Hold position.",
) -> dict[str, Any]:
    return {
        "channel": channel,
        "recipient_id": recipient_id,
        "group_chat_id": group_chat_id,
        "content": content,
    }


def _command_treaty(
    *,
    counterparty_id: str = "player-1",
    action: str = "propose",
    treaty_type: str = "trade",
) -> dict[str, Any]:
    return {
        "counterparty_id": counterparty_id,
        "action": action,
        "treaty_type": treaty_type,
    }


def _command_alliance(
    *,
    action: str = "create",
    alliance_id: str | None = None,
    name: str | None = "Northern Pact",
) -> dict[str, Any]:
    return {
        "action": action,
        "alliance_id": alliance_id,
        "name": name,
    }


def _join_payload(*, match_id: str = "match-beta") -> dict[str, Any]:
    return {"match_id": match_id}


def _owned_agent_guidance_payload(
    *,
    match_id: str = "match-alpha",
    tick: int = 142,
    content: str = "Hold the northern line.",
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "tick": tick,
        "content": content,
    }


def _owned_agent_override_payload(
    *,
    match_id: str = "match-alpha",
    tick: int = 142,
    orders: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "tick": tick,
        "orders": orders
        or {
            "movements": [{"army_id": "army-b", "destination": "london"}],
            "recruitment": [],
            "upgrades": [],
            "transfers": [],
        },
    }


def _briefing_message_contents(payload: dict[str, Any], bucket: str) -> list[str]:
    return [message["content"] for message in payload["messages"][bucket]]


def _briefing_guidance_contents(payload: dict[str, Any]) -> list[str]:
    return [guidance["content"] for guidance in payload["guidance"]]


def _agent_id_for_player(player_id: str) -> str:
    return f"agent-{player_id}"


def _auth_headers_for_agent(agent_id: str) -> dict[str, str]:
    return {"X-API-Key": build_seeded_agent_api_key(agent_id)}


def _auth_headers_for_player(player_id: str) -> dict[str, str]:
    return _auth_headers_for_agent(_agent_id_for_player(player_id))


def _human_jwt_token(
    *,
    user_id: str,
    role: str = "authenticated",
    secret: str = "test-human-secret-key-material-1234",
    issuer: str = "https://supabase.test/auth/v1",
    audience: str = "authenticated",
) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "role": role,
            "iss": issuer,
            "aud": audience,
            "exp": datetime.now(tz=UTC) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )


def _auth_headers_for_human(user_id: str, *, role: str = "authenticated") -> dict[str, str]:
    return {"Authorization": f"Bearer {_human_jwt_token(user_id=user_id, role=role)}"}


def _build_authenticated_access_test_app(
    *,
    registry: InMemoryMatchRegistry,
    history_database_url: str | None,
    include_session_factory: bool,
) -> FastAPI:
    settings = get_settings(
        env={
            "DATABASE_URL": history_database_url or "sqlite+pysqlite:///unused-test.db",
            "IRON_COUNCIL_MATCH_REGISTRY_BACKEND": "db" if history_database_url else "memory",
            "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
            "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
            "HUMAN_JWT_AUDIENCE": "authenticated",
            "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
        }
    )
    engine = create_engine(history_database_url) if history_database_url is not None else None
    app_services = AppServices(
        settings=settings,
        history_database_url=history_database_url,
        history_db_session_factory=(
            sessionmaker(engine, class_=Session)
            if include_session_factory and engine is not None
            else None
        ),
    )
    app = FastAPI()
    register_error_handlers(app)

    async def ensure_match_running(match_id: str) -> None:
        del match_id

    def get_registry() -> InMemoryMatchRegistry:
        return registry

    app.include_router(
        build_authenticated_access_router(
            match_registry_provider=get_registry,
            app_services=app_services,
            ensure_match_running=ensure_match_running,
        )
    )
    return app


def _empty_treaty_reputation_payload() -> dict[str, Any]:
    return {
        "summary": {
            "signed": 0,
            "active": 0,
            "honored": 0,
            "withdrawn": 0,
            "broken_by_self": 0,
            "broken_by_counterparty": 0,
        },
        "history": [],
    }


@pytest.fixture
def seeded_registry() -> InMemoryMatchRegistry:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)
    return registry


@pytest.fixture
def app_client(seeded_registry: InMemoryMatchRegistry) -> AsyncClient:
    app = create_app(
        match_registry=seeded_registry,
        settings_override={
            "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
            "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
            "HUMAN_JWT_AUDIENCE": "authenticated",
            "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
        },
    )
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    )


@pytest.fixture
def websocket_app(seeded_registry: InMemoryMatchRegistry) -> FastAPI:
    return create_app(
        match_registry=seeded_registry,
        settings_override={
            "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
            "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
            "HUMAN_JWT_AUDIENCE": "authenticated",
            "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
        },
    )


@pytest.fixture
def websocket_client(websocket_app: FastAPI) -> TestClient:
    return TestClient(websocket_app, base_url="http://testserver")


def test_create_app_uses_explicit_local_browser_cors_origin_defaults_and_override(
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    default_app = create_app(match_registry=seeded_registry)

    assert default_app.state.settings.allowed_browser_origins == (
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    )

    override_app = create_app(
        match_registry=seeded_registry,
        settings_override={
            "IRON_COUNCIL_BROWSER_ORIGINS": "http://127.0.0.1:3100, http://localhost:3100",
        },
    )

    assert override_app.state.settings.allowed_browser_origins == (
        "http://127.0.0.1:3100",
        "http://localhost:3100",
    )


@pytest.mark.asyncio
async def test_cors_preflight_for_allowed_local_browser_origin_returns_allow_origin_header(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        response = await client.options(
            "/api/v1/matches",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == HTTPStatus.OK
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


@pytest.mark.asyncio
async def test_cors_simple_request_for_allowed_local_browser_origin_returns_allow_origin_header(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        response = await client.get(
            "/api/v1/matches",
            headers={"Origin": "http://127.0.0.1:3000"},
        )

    assert response.status_code == HTTPStatus.OK
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


@pytest.mark.asyncio
async def test_cors_does_not_echo_unlisted_origin(app_client: AsyncClient) -> None:
    async with app_client as client:
        response = await client.get(
            "/api/v1/matches",
            headers={"Origin": "http://127.0.0.1:3999"},
        )

    assert response.status_code == HTTPStatus.OK
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_list_matches_returns_stable_json_summaries(app_client: AsyncClient) -> None:
    async with app_client as client:
        response = await client.get("/api/v1/matches")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "matches": [
            {
                "match_id": "match-alpha",
                "status": "active",
                "map": "britain",
                "tick": 142,
                "tick_interval_seconds": 30,
                "current_player_count": 3,
                "max_player_count": 5,
                "open_slot_count": 2,
            },
            {
                "match_id": "match-beta",
                "status": "paused",
                "map": "britain",
                "tick": 7,
                "tick_interval_seconds": 45,
                "current_player_count": 0,
                "max_player_count": 5,
                "open_slot_count": 5,
            },
        ]
    }


@pytest.mark.asyncio
async def test_list_matches_returns_compact_db_backed_public_browse_rows_and_excludes_completed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from server.db.testing import provision_seeded_database

    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-match-browse.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_completed_match_fixture(database_url)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/matches")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "matches": [
            {
                "match_id": "00000000-0000-0000-0000-000000000101",
                "status": "active",
                "map": "britain",
                "tick": 142,
                "tick_interval_seconds": 30,
                "current_player_count": 3,
                "max_player_count": 5,
                "open_slot_count": 2,
            },
            {
                "match_id": "00000000-0000-0000-0000-000000000102",
                "status": "paused",
                "map": "britain",
                "tick": 7,
                "tick_interval_seconds": 45,
                "current_player_count": 0,
                "max_player_count": 5,
                "open_slot_count": 5,
            },
        ]
    }


@pytest.mark.asyncio
async def test_public_match_detail_route_returns_compact_db_backed_metadata_and_public_roster(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from server.db.testing import provision_seeded_database

    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-match-detail.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/matches/00000000-0000-0000-0000-000000000101")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "match_id": "00000000-0000-0000-0000-000000000101",
        "status": "active",
        "map": "britain",
        "tick": 142,
        "tick_interval_seconds": 30,
        "current_player_count": 3,
        "max_player_count": 5,
        "open_slot_count": 2,
        "roster": [
            {
                "player_id": "player-1",
                "display_name": "Arthur",
                "competitor_kind": "human",
                "agent_id": None,
                "human_id": "human:00000000-0000-0000-0000-000000000301",
            },
            {
                "player_id": "player-3",
                "display_name": "Gawain",
                "competitor_kind": "agent",
                "agent_id": "agent-player-3",
                "human_id": None,
            },
            {
                "player_id": "player-2",
                "display_name": "Morgana",
                "competitor_kind": "agent",
                "agent_id": "agent-player-2",
                "human_id": None,
            },
        ],
    }


@pytest.mark.asyncio
async def test_public_match_detail_route_returns_structured_not_found_for_missing_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from server.db.testing import provision_seeded_database

    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-match-detail-errors.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_completed_match_fixture(database_url)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        completed_response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000201"
        )
        missing_response = await client.get("/api/v1/matches/00000000-0000-0000-0000-000000009999")

    assert completed_response.status_code == HTTPStatus.NOT_FOUND
    assert completed_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match '00000000-0000-0000-0000-000000000201' was not found.",
        }
    }
    assert missing_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match '00000000-0000-0000-0000-000000009999' was not found.",
        }
    }


@pytest.mark.asyncio
async def test_public_match_detail_route_preserves_seeded_memory_fallback_contract() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)
    app = create_app(match_registry=registry)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/matches/match-alpha")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "match_id": "match-alpha",
        "status": "active",
        "map": "britain",
        "tick": 142,
        "tick_interval_seconds": 30,
        "current_player_count": 3,
        "max_player_count": 5,
        "open_slot_count": 2,
        "roster": [
            {
                "player_id": "player-1",
                "display_name": "Arthur",
                "competitor_kind": "human",
                "agent_id": None,
                "human_id": "human:00000000-0000-0000-0000-000000000301",
            },
            {
                "player_id": "player-3",
                "display_name": "Gawain",
                "competitor_kind": "agent",
                "agent_id": "agent-player-3",
                "human_id": None,
            },
            {
                "player_id": "player-2",
                "display_name": "Morgana",
                "competitor_kind": "agent",
                "agent_id": "agent-player-2",
                "human_id": None,
            },
        ],
    }


@pytest.mark.asyncio
async def test_public_match_detail_route_uses_visible_players_when_memory_join_maps_are_empty() -> (
    None
):
    record = build_seeded_match_records(primary_match_id="match-visible-fallback")[0]
    record.joined_agents = {}
    record.joined_humans = {}
    record.current_player_count = 1
    record.public_competitor_kinds = {"player-1": "human"}

    registry = InMemoryMatchRegistry()
    registry.seed_match(record)
    app = create_app(match_registry=registry)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/matches/match-visible-fallback")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["roster"] == [
        {
            "player_id": "player-1",
            "display_name": "Arthur",
            "competitor_kind": "human",
            "agent_id": None,
            "human_id": None,
        }
    ]


@pytest.mark.asyncio
async def test_public_match_detail_route_rejects_unknown_and_completed_in_memory() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    completed_record = build_seeded_match_records(primary_match_id="match-gamma")[0]
    completed_record.status = MatchStatus.COMPLETED
    registry.seed_match(completed_record)

    app = create_app(match_registry=registry)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        missing_response = await client.get("/api/v1/matches/unknown-match")
        completed_response = await client.get("/api/v1/matches/match-gamma")

    assert missing_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match 'unknown-match' was not found.",
        }
    }
    assert completed_response.status_code == HTTPStatus.NOT_FOUND
    assert completed_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match 'match-gamma' was not found.",
        }
    }


@pytest.mark.asyncio
async def test_match_history_routes_return_persisted_entries_and_replay_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from server.db.testing import provision_seeded_database

    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-history.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        history_response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/history"
        )
        replay_response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/history/142"
        )

    assert history_response.status_code == HTTPStatus.OK
    assert history_response.json() == {
        "match_id": "00000000-0000-0000-0000-000000000101",
        "status": "active",
        "current_tick": 142,
        "tick_interval_seconds": 30,
        "competitors": [
            {
                "display_name": "Arthur",
                "competitor_kind": "human",
                "agent_id": None,
                "human_id": "human:00000000-0000-0000-0000-000000000301",
            },
            {
                "display_name": "Gawain",
                "competitor_kind": "agent",
                "agent_id": "agent-player-3",
                "human_id": None,
            },
            {
                "display_name": "Morgana",
                "competitor_kind": "agent",
                "agent_id": "agent-player-2",
                "human_id": None,
            },
        ],
        "history": [{"tick": 142}],
    }
    assert replay_response.status_code == HTTPStatus.OK
    assert replay_response.json() == {
        "match_id": "00000000-0000-0000-0000-000000000101",
        "tick": 142,
        "state_snapshot": {"cities": {"london": {"owner": "Arthur", "population": 12}}},
        "orders": {"movements": [{"army_id": "army-1", "destination": "york"}]},
        "events": {"summary": ["Convoy secured", "Trade revenue collected"]},
    }


@pytest.mark.asyncio
async def test_match_history_routes_return_structured_not_found_and_unavailable_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from server.db.testing import provision_seeded_database

    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-history-errors.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    db_backed_app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=db_backed_app),
        base_url="http://testserver",
    ) as client:
        missing_match_response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000009999/history"
        )
        missing_tick_response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/history/999"
        )

    assert missing_match_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_match_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match '00000000-0000-0000-0000-000000009999' was not found.",
        }
    }
    assert missing_tick_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_tick_response.json() == {
        "error": {
            "code": "tick_not_found",
            "message": (
                "Tick '999' was not found for match '00000000-0000-0000-0000-000000000101'."
            ),
        }
    }

    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "memory")
    memory_registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        memory_registry.seed_match(record)
    memory_app = create_app(match_registry=memory_registry)

    async with AsyncClient(
        transport=ASGITransport(app=memory_app),
        base_url="http://testserver",
    ) as client:
        unavailable_response = await client.get("/api/v1/matches/match-alpha/history")

    assert unavailable_response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert unavailable_response.json() == {
        "error": {
            "code": "match_history_unavailable",
            "message": "Persisted match history is only available in DB-backed mode.",
        }
    }


@pytest.mark.asyncio
async def test_match_history_routes_read_persisted_tick_log_even_when_registry_state_drifts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from server.db.testing import provision_seeded_database

    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-history-source-of-truth.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    db_registry = load_match_registry_from_database(database_url)
    drifted_match = db_registry.get_match("00000000-0000-0000-0000-000000000101")
    assert drifted_match is not None
    drifted_match.state.tick = 999

    app = create_app(match_registry=db_registry)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        history_response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/history"
        )
        replay_response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/history/142"
        )

    assert history_response.status_code == HTTPStatus.OK
    assert history_response.json()["current_tick"] == 142
    assert history_response.json()["competitors"] == [
        {
            "display_name": "Arthur",
            "competitor_kind": "human",
            "agent_id": None,
            "human_id": "human:00000000-0000-0000-0000-000000000301",
        },
        {
            "display_name": "Gawain",
            "competitor_kind": "agent",
            "agent_id": "agent-player-3",
            "human_id": None,
        },
        {
            "display_name": "Morgana",
            "competitor_kind": "agent",
            "agent_id": "agent-player-2",
            "human_id": None,
        },
    ]
    assert history_response.json()["history"] == [{"tick": 142}]
    assert replay_response.status_code == HTTPStatus.OK
    assert replay_response.json()["tick"] == 142
    assert replay_response.json()["state_snapshot"] != {"tick": 999}


@pytest.mark.asyncio
async def test_completed_terminal_tick_is_excluded_from_public_matches_and_served_via_history_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-terminal-completion.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz: object | None = None) -> FrozenDateTime:
            assert tz == UTC
            return cls(2026, 4, 2, 12, 34, 56, tzinfo=UTC)

    monkeypatch.setattr(db_tick_persistence_module, "datetime", FrozenDateTime)

    registry = load_match_registry_from_database(database_url)
    terminal_match = registry.get_match("00000000-0000-0000-0000-000000000101")
    assert terminal_match is not None
    terminal_match.state.victory.threshold = 2
    terminal_match.state.victory.countdown_ticks_remaining = 1
    terminal_tick = registry.advance_match_tick("00000000-0000-0000-0000-000000000101")
    persist_advanced_match_tick(database_url=database_url, advanced_tick=terminal_tick)

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        matches_response = await client.get("/api/v1/matches")
        completed_response = await client.get("/api/v1/matches/completed")
        history_response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/history"
        )
        replay_response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/history/143"
        )

    assert matches_response.status_code == HTTPStatus.OK
    assert [match["match_id"] for match in matches_response.json()["matches"]] == [
        "00000000-0000-0000-0000-000000000102"
    ]

    assert completed_response.status_code == HTTPStatus.OK
    assert completed_response.json()["matches"][0] == {
        "match_id": "00000000-0000-0000-0000-000000000101",
        "map": "britain",
        "final_tick": 143,
        "tick_interval_seconds": 30,
        "player_count": 3,
        "completed_at": "2026-04-02T12:34:56Z",
        "winning_alliance_name": "Western Accord",
        "winning_player_display_names": ["Arthur", "Morgana"],
        "winning_competitors": [
            {
                "display_name": "Arthur",
                "competitor_kind": "human",
                "agent_id": None,
                "human_id": "human:00000000-0000-0000-0000-000000000301",
            },
            {
                "display_name": "Morgana",
                "competitor_kind": "agent",
                "agent_id": "agent-player-2",
                "human_id": None,
            },
        ],
    }

    assert history_response.status_code == HTTPStatus.OK
    assert history_response.json() == {
        "match_id": "00000000-0000-0000-0000-000000000101",
        "status": "completed",
        "current_tick": 143,
        "tick_interval_seconds": 30,
        "competitors": [
            {
                "display_name": "Arthur",
                "competitor_kind": "human",
                "agent_id": None,
                "human_id": "human:00000000-0000-0000-0000-000000000301",
            },
            {
                "display_name": "Gawain",
                "competitor_kind": "agent",
                "agent_id": "agent-player-3",
                "human_id": None,
            },
            {
                "display_name": "Morgana",
                "competitor_kind": "agent",
                "agent_id": "agent-player-2",
                "human_id": None,
            },
        ],
        "history": [{"tick": 142}, {"tick": 143}],
    }
    assert replay_response.status_code == HTTPStatus.OK
    assert replay_response.json()["match_id"] == "00000000-0000-0000-0000-000000000101"
    assert replay_response.json()["tick"] == 143
    assert replay_response.json()["state_snapshot"]["victory"] == {
        "leading_alliance": "alliance-red",
        "cities_held": 3,
        "threshold": 2,
        "countdown_ticks_remaining": 0,
    }


@pytest.mark.asyncio
async def test_public_leaderboard_and_completed_match_routes_return_compact_db_backed_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from server.db.testing import provision_seeded_database

    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-public-reads.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_completed_match_fixture(database_url)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        leaderboard_response = await client.get("/api/v1/leaderboard")
        completed_matches_response = await client.get("/api/v1/matches/completed")

    assert leaderboard_response.status_code == HTTPStatus.OK
    assert leaderboard_response.json() == {
        "leaderboard": [
            {
                "rank": 1,
                "display_name": "Arthur",
                "competitor_kind": "human",
                "agent_id": None,
                "human_id": "human:00000000-0000-0000-0000-000000000301",
                "elo": 1234,
                "provisional": False,
                "matches_played": 1,
                "wins": 1,
                "losses": 0,
                "draws": 0,
            },
            {
                "rank": 2,
                "display_name": "Morgana",
                "competitor_kind": "agent",
                "agent_id": "agent-player-2",
                "human_id": None,
                "elo": 1211,
                "provisional": False,
                "matches_played": 2,
                "wins": 1,
                "losses": 0,
                "draws": 1,
            },
            {
                "rank": 3,
                "display_name": "Bedivere",
                "competitor_kind": "human",
                "agent_id": None,
                "human_id": "human:00000000-0000-0000-0000-000000000304",
                "elo": 1190,
                "provisional": False,
                "matches_played": 1,
                "wins": 0,
                "losses": 0,
                "draws": 1,
            },
            {
                "rank": 4,
                "display_name": "Gawain",
                "competitor_kind": "agent",
                "agent_id": "agent-player-3",
                "human_id": None,
                "elo": 1163,
                "provisional": False,
                "matches_played": 1,
                "wins": 0,
                "losses": 1,
                "draws": 0,
            },
        ]
    }
    assert completed_matches_response.status_code == HTTPStatus.OK
    assert completed_matches_response.json() == {
        "matches": [
            {
                "match_id": "00000000-0000-0000-0000-000000000202",
                "map": "mediterranean",
                "final_tick": 200,
                "tick_interval_seconds": 45,
                "player_count": 2,
                "completed_at": "2026-03-29T12:15:00Z",
                "winning_alliance_name": None,
                "winning_player_display_names": [],
                "winning_competitors": [],
            },
            {
                "match_id": "00000000-0000-0000-0000-000000000201",
                "map": "britain",
                "final_tick": 155,
                "tick_interval_seconds": 30,
                "player_count": 3,
                "completed_at": "2026-03-29T08:30:00Z",
                "winning_alliance_name": "Iron Crown",
                "winning_player_display_names": ["Arthur", "Morgana"],
                "winning_competitors": [
                    {
                        "display_name": "Arthur",
                        "competitor_kind": "human",
                        "agent_id": None,
                        "human_id": "human:00000000-0000-0000-0000-000000000301",
                    },
                    {
                        "display_name": "Morgana",
                        "competitor_kind": "agent",
                        "agent_id": "agent-player-2",
                        "human_id": None,
                    },
                ],
            },
        ]
    }


@pytest.mark.asyncio
async def test_public_leaderboard_route_exposes_honest_agent_ids_by_competitor_kind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-public-leaderboard-agent-ids.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_completed_match_fixture(database_url)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        leaderboard_response = await client.get("/api/v1/leaderboard")

    assert leaderboard_response.status_code == HTTPStatus.OK
    rows_by_name = {row["display_name"]: row for row in leaderboard_response.json()["leaderboard"]}
    assert rows_by_name["Arthur"]["competitor_kind"] == "human"
    assert rows_by_name["Arthur"]["agent_id"] is None
    assert rows_by_name["Arthur"]["human_id"] == "human:00000000-0000-0000-0000-000000000301"
    assert rows_by_name["Bedivere"]["competitor_kind"] == "human"
    assert rows_by_name["Bedivere"]["agent_id"] is None
    assert rows_by_name["Bedivere"]["human_id"] == "human:00000000-0000-0000-0000-000000000304"
    assert rows_by_name["Morgana"]["competitor_kind"] == "agent"
    assert rows_by_name["Morgana"]["agent_id"] == "agent-player-2"
    assert rows_by_name["Morgana"]["human_id"] is None
    assert rows_by_name["Gawain"]["competitor_kind"] == "agent"
    assert rows_by_name["Gawain"]["agent_id"] == "agent-player-3"
    assert rows_by_name["Gawain"]["human_id"] is None


@pytest.mark.asyncio
async def test_db_backed_human_profile_route_returns_stable_public_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-human-profile.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_completed_match_fixture(database_url)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO treaties (
                    id, match_id, player_a_id, player_b_id, treaty_type, status, signed_tick,
                    broken_tick, created_at
                ) VALUES (
                    :id, :match_id, :player_a_id, :player_b_id, :treaty_type, :status,
                    :signed_tick, :broken_tick, :created_at
                )
                """
            ),
            {
                "id": "00000000-0000-0000-0000-000000000799",
                "match_id": "00000000-0000-0000-0000-000000000201",
                "player_a_id": build_persisted_player_id(
                    match_id="00000000-0000-0000-0000-000000000201",
                    public_player_id="player-1",
                ),
                "player_b_id": build_persisted_player_id(
                    match_id="00000000-0000-0000-0000-000000000201",
                    public_player_id="player-2",
                ),
                "treaty_type": "defensive",
                "status": "active",
                "signed_tick": 125,
                "broken_tick": None,
                "created_at": "2026-03-29 08:02:00+00:00",
            },
        )

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/humans/human:00000000-0000-0000-0000-000000000301/profile"
        )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "human_id": "human:00000000-0000-0000-0000-000000000301",
        "display_name": "Arthur",
        "rating": {"elo": 1234, "provisional": False},
        "history": {"matches_played": 1, "wins": 1, "losses": 0, "draws": 0},
        "treaty_reputation": {
            "summary": {
                "signed": 2,
                "active": 1,
                "honored": 1,
                "withdrawn": 0,
                "broken_by_self": 0,
                "broken_by_counterparty": 0,
            },
            "history": [
                {
                    "match_id": "00000000-0000-0000-0000-000000000201",
                    "counterparty_display_name": "Morgana",
                    "treaty_type": "defensive",
                    "status": "honored",
                    "signed_tick": 125,
                    "ended_tick": None,
                    "broken_by_self": False,
                },
                {
                    "match_id": "00000000-0000-0000-0000-000000000101",
                    "counterparty_display_name": "Gawain",
                    "treaty_type": "trade",
                    "status": "active",
                    "signed_tick": 141,
                    "ended_tick": None,
                    "broken_by_self": False,
                },
            ],
        },
    }


@pytest.mark.asyncio
async def test_human_profile_route_returns_structured_unavailable_error_without_db_backing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", raising=False)

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/humans/human:00000000-0000-0000-0000-000000000301/profile"
        )

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json() == {
        "error": {
            "code": "human_profile_unavailable",
            "message": "Public human profiles are only available in DB-backed mode.",
        }
    }


@pytest.mark.asyncio
async def test_human_profile_route_returns_deterministic_not_found_for_unknown_or_invalid_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-human-profile-errors.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_completed_match_fixture(database_url)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        unknown_response = await client.get(
            "/api/v1/humans/human:00000000-0000-0000-0000-000000009999/profile"
        )
        invalid_response = await client.get("/api/v1/humans/Arthur/profile")

    assert unknown_response.status_code == HTTPStatus.NOT_FOUND
    assert unknown_response.json() == {
        "error": {
            "code": "human_not_found",
            "message": "Human 'human:00000000-0000-0000-0000-000000009999' was not found.",
        }
    }
    assert invalid_response.status_code == HTTPStatus.NOT_FOUND
    assert invalid_response.json() == {
        "error": {
            "code": "human_not_found",
            "message": "Human 'Arthur' was not found.",
        }
    }


@pytest.mark.asyncio
async def test_db_backed_agent_profile_routes_return_finalized_settlement_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-settled-profile.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_completed_match_fixture(database_url)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        public_profile_response = await client.get("/api/v1/agents/agent-player-2/profile")
        authenticated_profile_response = await client.get(
            "/api/v1/agent/profile",
            headers=_auth_headers_for_agent("agent-player-2"),
        )

    expected_profile = {
        "agent_id": "agent-player-2",
        "display_name": "Morgana",
        "is_seeded": True,
        "rating": {"elo": 1211, "provisional": False},
        "history": {"matches_played": 2, "wins": 1, "losses": 0, "draws": 1},
        "treaty_reputation": _empty_treaty_reputation_payload(),
    }
    assert public_profile_response.status_code == HTTPStatus.OK
    assert public_profile_response.json() == expected_profile
    assert authenticated_profile_response.status_code == HTTPStatus.OK
    assert authenticated_profile_response.json() == expected_profile


@pytest.mark.asyncio
async def test_authenticated_human_api_key_lifecycle_can_list_owned_keys_without_echoing_raw_key_material(  # noqa: E501
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-key-list.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_completed_match_fixture(database_url)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/account/api-keys",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload == {
        "items": [
            {
                "key_id": "00000000-0000-0000-0000-000000000202",
                "agent_id": "agent-api-key-00000000-0000-0000-0000-000000000202",
                "elo_rating": 1211,
                "is_active": True,
                "created_at": "2026-03-29T00:00:00Z",
                "entitlement": {
                    "is_entitled": True,
                    "grant_source": "dev",
                    "concurrent_match_allowance": 1,
                    "granted_at": "2026-03-29T00:00:00Z",
                },
            }
        ]
    }
    assert "api_key" not in response.text
    assert "key_hash" not in response.text


@pytest.mark.asyncio
async def test_authenticated_human_api_key_lifecycle_can_create_and_revoke_owned_key_with_one_time_secret(  # noqa: E501
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-key-lifecycle.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()
    human_headers = _auth_headers_for_human("00000000-0000-0000-0000-000000000301")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post("/api/v1/account/api-keys", headers=human_headers)
        list_response = await client.get("/api/v1/account/api-keys", headers=human_headers)

        created_payload = create_response.json()
        revoke_response = await client.delete(
            f"/api/v1/account/api-keys/{created_payload['summary']['key_id']}",
            headers=human_headers,
        )
        revoked_profile_response = await client.get(
            "/api/v1/agent/profile",
            headers={"X-API-Key": created_payload["api_key"]},
        )

    assert create_response.status_code == HTTPStatus.CREATED
    assert created_payload["api_key"].startswith("iron_")
    assert created_payload["summary"]["agent_id"] == (
        f"agent-api-key-{created_payload['summary']['key_id']}"
    )
    assert created_payload["summary"]["elo_rating"] == 1210
    assert created_payload["summary"]["is_active"] is True
    assert created_payload["summary"]["entitlement"] == {
        "is_entitled": True,
        "grant_source": "dev",
        "concurrent_match_allowance": 1,
        "granted_at": "2026-03-29T00:00:00Z",
    }
    assert "key_hash" not in str(created_payload)

    assert list_response.status_code == HTTPStatus.OK
    list_payload = list_response.json()
    assert {
        "key_id": created_payload["summary"]["key_id"],
        "agent_id": created_payload["summary"]["agent_id"],
        "elo_rating": 1210,
        "is_active": True,
        "created_at": created_payload["summary"]["created_at"],
        "entitlement": {
            "is_entitled": True,
            "grant_source": "dev",
            "concurrent_match_allowance": 1,
            "granted_at": "2026-03-29T00:00:00Z",
        },
    } in list_payload["items"]
    assert created_payload["api_key"] not in list_response.text

    assert revoke_response.status_code == HTTPStatus.OK
    assert revoke_response.json() == {
        "key_id": created_payload["summary"]["key_id"],
        "agent_id": created_payload["summary"]["agent_id"],
        "elo_rating": 1210,
        "is_active": False,
        "created_at": created_payload["summary"]["created_at"],
        "entitlement": {
            "is_entitled": True,
            "grant_source": "dev",
            "concurrent_match_allowance": 1,
            "granted_at": "2026-03-29T00:00:00Z",
        },
    }
    assert revoked_profile_response.status_code == HTTPStatus.UNAUTHORIZED
    assert revoked_profile_response.json() == {
        "error": {
            "code": "invalid_api_key",
            "message": "A valid active X-API-Key header is required.",
        }
    }


@pytest.mark.asyncio
async def test_authenticated_human_api_key_lifecycle_routes_require_bearer_and_hide_other_users_keys(  # noqa: E501
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-key-lifecycle-errors.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        missing_auth_response = await client.get("/api/v1/account/api-keys")
        missing_owner_revoke_response = await client.delete(
            "/api/v1/account/api-keys/00000000-0000-0000-0000-000000000202",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000301"),
        )

    assert missing_auth_response.status_code == HTTPStatus.UNAUTHORIZED
    assert missing_auth_response.json() == {
        "error": {
            "code": "invalid_human_token",
            "message": "A valid human Bearer token is required.",
        }
    }
    assert missing_owner_revoke_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_owner_revoke_response.json() == {
        "error": {
            "code": "api_key_not_found",
            "message": "API key '00000000-0000-0000-0000-000000000202' was not found.",
        }
    }


@pytest.mark.asyncio
async def test_authenticated_human_api_key_lifecycle_rejects_create_without_positive_entitlement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-key-entitlement-required.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()
    human_headers = _auth_headers_for_human("00000000-0000-0000-0000-000000000304")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post("/api/v1/account/api-keys", headers=human_headers)

    assert create_response.status_code == HTTPStatus.FORBIDDEN
    assert create_response.json() == {
        "error": {
            "code": "agent_entitlement_required",
            "message": (
                "Authenticated account lacks an active agent entitlement grant with positive "
                "concurrent match allowance."
            ),
        }
    }


@pytest.mark.asyncio
async def test_public_leaderboard_and_completed_match_routes_return_structured_unavailable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "memory")
    memory_registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        memory_registry.seed_match(record)
    app = create_app(match_registry=memory_registry)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        leaderboard_response = await client.get("/api/v1/leaderboard")
        completed_matches_response = await client.get("/api/v1/matches/completed")

    assert leaderboard_response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert leaderboard_response.json() == {
        "error": {
            "code": "leaderboard_unavailable",
            "message": "Persisted leaderboard is only available in DB-backed mode.",
        }
    }
    assert completed_matches_response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert completed_matches_response.json() == {
        "error": {
            "code": "completed_match_summaries_unavailable",
            "message": "Completed match summaries are only available in DB-backed mode.",
        }
    }


@pytest.mark.asyncio
async def test_app_lifespan_advances_active_match_and_stops_after_shutdown(
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    active_match = seeded_registry.get_match("match-alpha")
    paused_match = seeded_registry.get_match("match-beta")
    assert active_match is not None
    assert paused_match is not None
    active_match.tick_interval_seconds = 1
    paused_match.tick_interval_seconds = 1

    app = create_app(match_registry=seeded_registry)

    async with app.router.lifespan_context(app):
        await asyncio.sleep(1.2)

        assert active_match.state.tick == 143
        assert paused_match.state.tick == 7

    stopped_tick = active_match.state.tick
    await asyncio.sleep(1.2)

    assert active_match.state.tick == stopped_tick


@pytest.mark.asyncio
async def test_app_lifespan_restores_match_state_and_submissions_when_tick_persistence_fails(
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    active_match = seeded_registry.get_match("match-alpha")
    assert active_match is not None
    active_match.tick_interval_seconds = 1
    seeded_registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 5}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    seeded_registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 143,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 1}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    baseline_state = active_match.state.model_dump(mode="json")
    baseline_submissions = [
        submission.model_dump(mode="json") for submission in active_match.order_submissions
    ]
    persistence_calls = 0

    def fail_tick_persistence(_: AdvancedMatchTick) -> None:
        nonlocal persistence_calls
        persistence_calls += 1
        raise RuntimeError("tick persistence failed")

    app = create_app(match_registry=seeded_registry, tick_persistence=fail_tick_persistence)

    async with app.router.lifespan_context(app):
        await asyncio.sleep(1.2)
        runtime_task = app.state.match_runtime._tasks["match-alpha"]
        with pytest.raises(RuntimeError, match="tick persistence failed"):
            await runtime_task

    restored_match = seeded_registry.get_match("match-alpha")
    assert restored_match is not None
    assert restored_match.state.model_dump(mode="json") == baseline_state
    assert [
        submission.model_dump(mode="json") for submission in restored_match.order_submissions
    ] == baseline_submissions
    assert persistence_calls == 1


@pytest.mark.asyncio
async def test_create_app_uses_explicit_tick_persistence_for_injected_registry(
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    active_match = seeded_registry.get_match("match-alpha")
    paused_match = seeded_registry.get_match("match-beta")
    assert active_match is not None
    assert paused_match is not None
    active_match.tick_interval_seconds = 1
    paused_match.tick_interval_seconds = 1
    persisted_ticks: list[AdvancedMatchTick] = []

    def record_tick_persistence(advanced_tick: AdvancedMatchTick) -> None:
        persisted_ticks.append(advanced_tick)

    app = create_app(match_registry=seeded_registry, tick_persistence=record_tick_persistence)

    async with app.router.lifespan_context(app):
        await asyncio.sleep(1.2)

    assert [tick.match_id for tick in persisted_ticks] == ["match-alpha"]
    assert persisted_ticks[0].resolved_tick == 143


@pytest.mark.asyncio
async def test_public_and_authenticated_agent_profile_routes_return_stable_shapes(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        public_profile_response = await client.get("/api/v1/agents/agent-player-2/profile")
        missing_public_profile_response = await client.get("/api/v1/agents/agent-missing/profile")
        missing_key_response = await client.get("/api/v1/agent/profile")
        authenticated_profile_response = await client.get(
            "/api/v1/agent/profile",
            headers=_auth_headers_for_agent("agent-player-2"),
        )

    expected_profile = {
        "agent_id": "agent-player-2",
        "display_name": "Morgana",
        "is_seeded": True,
        "rating": {"elo": 1190, "provisional": True},
        "history": {"matches_played": 0, "wins": 0, "losses": 0, "draws": 0},
        "treaty_reputation": _empty_treaty_reputation_payload(),
    }
    assert public_profile_response.status_code == HTTPStatus.OK
    assert public_profile_response.json() == expected_profile
    assert missing_public_profile_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_public_profile_response.json() == {
        "error": {
            "code": "agent_not_found",
            "message": "Agent 'agent-missing' was not found.",
        }
    }
    assert missing_key_response.status_code == HTTPStatus.UNAUTHORIZED
    assert missing_key_response.json() == {
        "error": {
            "code": "invalid_api_key",
            "message": "A valid active X-API-Key header is required.",
        }
    }
    assert authenticated_profile_response.status_code == HTTPStatus.OK
    assert authenticated_profile_response.json() == expected_profile


@pytest.mark.asyncio
async def test_get_match_state_requires_auth_and_returns_fog_filtered_payload(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        missing_auth_response = await client.get("/api/v1/matches/match-alpha/state")
        response = await client.get(
            "/api/v1/matches/match-alpha/state",
            headers=_auth_headers_for_player("player-1"),
        )

    assert missing_auth_response.status_code == HTTPStatus.UNAUTHORIZED
    assert missing_auth_response.json() == {
        "error": {
            "code": "invalid_player_auth",
            "message": "Player routes require a valid Bearer token or active X-API-Key header.",
        }
    }
    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["match_id"] == "match-alpha"
    assert payload["tick"] == 142
    assert payload["player_id"] == "player-1"
    assert payload["resources"] == {"food": 120, "production": 85, "money": 200}
    assert payload["alliance_id"] == "alliance-red"
    assert payload["alliance_members"] == ["player-1", "player-2"]
    assert payload["cities"]["london"]["visibility"] == "full"
    assert payload["cities"]["manchester"]["visibility"] == "full"
    assert payload["cities"]["birmingham"]["visibility"] == "partial"
    assert payload["cities"]["birmingham"]["garrison"] == "unknown"
    assert "inverness" not in payload["cities"]
    assert _army_by_id(payload, "army-a")["visibility"] == "full"
    assert _army_by_id(payload, "army-b")["visibility"] == "full"
    assert _army_by_id(payload, "army-c")["visibility"] == "partial"
    assert _army_by_id(payload, "army-c")["troops"] == "unknown"
    assert not any(army["id"] == "army-z" for army in payload["visible_armies"])


@pytest.mark.asyncio
async def test_human_jwt_state_route_accepts_valid_bearer_and_rejects_missing_invalid_and_wrong_role(  # noqa: E501
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        missing_auth_response = await client.get("/api/v1/matches/match-alpha/state")
        valid_response = await client.get(
            "/api/v1/matches/match-alpha/state",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )
        invalid_response = await client.get(
            "/api/v1/matches/match-alpha/state",
            headers={"Authorization": "Bearer not-a-jwt"},
        )
        wrong_role_response = await client.get(
            "/api/v1/matches/match-alpha/state",
            headers=_auth_headers_for_human(
                "00000000-0000-0000-0000-000000000302",
                role="service_role",
            ),
        )

    assert missing_auth_response.status_code == HTTPStatus.UNAUTHORIZED
    assert missing_auth_response.json() == {
        "error": {
            "code": "invalid_player_auth",
            "message": "Player routes require a valid Bearer token or active X-API-Key header.",
        }
    }
    assert valid_response.status_code == HTTPStatus.OK
    assert valid_response.json()["player_id"] == "player-2"
    assert invalid_response.status_code == HTTPStatus.UNAUTHORIZED
    assert invalid_response.json() == {
        "error": {
            "code": "invalid_human_token",
            "message": "A valid human Bearer token is required.",
        }
    }
    assert wrong_role_response.status_code == HTTPStatus.UNAUTHORIZED
    assert wrong_role_response.json() == {
        "error": {
            "code": "invalid_human_token_role",
            "message": "Human JWT role claim must be 'authenticated'.",
        }
    }


@pytest.mark.asyncio
async def test_human_jwt_state_route_rejects_malformed_bearer_unjoined_human_and_missing_match(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        malformed_bearer_response = await client.get(
            "/api/v1/matches/match-alpha/state",
            headers={"Authorization": "Token nope"},
        )
        unjoined_human_response = await client.get(
            "/api/v1/matches/match-alpha/state",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000304"),
        )
        missing_match_response = await client.get(
            "/api/v1/matches/match-missing/state",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )

    assert malformed_bearer_response.status_code == HTTPStatus.UNAUTHORIZED
    assert malformed_bearer_response.json() == {
        "error": {
            "code": "invalid_human_token",
            "message": "A valid human Bearer token is required.",
        }
    }
    assert unjoined_human_response.status_code == HTTPStatus.BAD_REQUEST
    assert unjoined_human_response.json() == {
        "error": {
            "code": "human_not_joined",
            "message": (
                "Human user '00000000-0000-0000-0000-000000000304' has not joined match "
                "'match-alpha' as a player."
            ),
        }
    }
    assert missing_match_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_match_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match 'match-missing' was not found.",
        }
    }


@pytest.mark.asyncio
async def test_human_jwt_state_route_resolves_db_backed_human_player_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'human-jwt-state.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/state",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000301"),
        )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["player_id"] == "player-1"


@pytest.mark.asyncio
async def test_create_app_settings_override_is_authoritative_for_db_backed_human_auth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    override_database_url = f"sqlite+pysqlite:///{tmp_path / 'override-human-auth.db'}"
    provision_seeded_database(database_url=override_database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'poisoned.db'}")
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "memory")

    app = create_app(
        settings_override={
            "DATABASE_URL": override_database_url,
            "IRON_COUNCIL_MATCH_REGISTRY_BACKEND": "db",
            "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
            "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
            "HUMAN_JWT_AUDIENCE": "authenticated",
            "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
        }
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/state",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000301"),
        )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["match_id"] == "00000000-0000-0000-0000-000000000101"
    assert response.json()["player_id"] == "player-1"


@pytest.mark.asyncio
async def test_owned_agent_guided_session_route_returns_owned_agent_snapshot_and_queued_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'owned-agent-guided-session.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()
    registry = app.state.match_registry
    record = registry.get_match("00000000-0000-0000-0000-000000000101")
    assert record is not None

    registry.record_submission(
        match_id=record.match_id,
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": record.match_id,
                "player_id": "player-2",
                "tick": record.state.tick,
                "orders": {
                    "movements": [{"army_id": "army-b", "destination": "london"}],
                    "recruitment": [{"city": "manchester", "troops": 3}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    registry.record_message(
        match_id=record.match_id,
        message=MatchMessageCreateRequest.model_validate(
            _message_payload(
                match_id=record.match_id,
                tick=record.state.tick,
                channel="direct",
                recipient_id="player-2",
                content="Hold Manchester.",
            )
        ),
        sender_id="player-1",
    )
    group_chat = registry.create_group_chat(
        match_id=record.match_id,
        request=GroupChatCreateRequest.model_validate(
            _group_chat_create_payload(
                match_id=record.match_id,
                tick=record.state.tick,
                name="Owners Council",
                member_ids=["player-1"],
            )
        ),
        creator_id="player-2",
    )
    registry.record_group_chat_message(
        match_id=record.match_id,
        group_chat_id=group_chat.group_chat_id,
        message=GroupChatMessageCreateRequest(
            match_id=record.match_id,
            tick=record.state.tick,
            content="Queued guidance note.",
        ),
        sender_id="player-2",
    )
    append_owned_agent_guidance(
        database_url=database_url,
        match_id=record.match_id,
        owner_user_id="00000000-0000-0000-0000-000000000302",
        agent_player_id=build_persisted_player_id(
            match_id=record.match_id,
            public_player_id="player-2",
        ),
        tick=record.state.tick,
        content="Hold London unless the coast opens.",
    )
    registry.apply_alliance_action(
        match_id=record.match_id,
        action=AllianceActionRequest.model_validate(
            _alliance_payload(
                match_id=record.match_id,
                action="create",
                name="Eastern Bloc",
            )
        ),
        player_id="player-3",
    )
    registry.apply_treaty_action(
        match_id=record.match_id,
        action=TreatyActionRequest.model_validate(
            _treaty_payload(
                match_id=record.match_id,
                counterparty_id="player-3",
            )
        ),
        player_id="player-2",
    )
    registry.apply_treaty_action(
        match_id=record.match_id,
        action=TreatyActionRequest.model_validate(
            _treaty_payload(
                match_id=record.match_id,
                action="accept",
                counterparty_id="player-2",
            )
        ),
        player_id="player-3",
    )
    registry.apply_treaty_action(
        match_id=record.match_id,
        action=TreatyActionRequest.model_validate(
            _treaty_payload(
                match_id=record.match_id,
                counterparty_id="player-4",
            )
        ),
        player_id="player-1",
    )
    registry.apply_treaty_action(
        match_id=record.match_id,
        action=TreatyActionRequest.model_validate(
            _treaty_payload(
                match_id=record.match_id,
                action="accept",
                counterparty_id="player-1",
            )
        ),
        player_id="player-4",
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/guided-session",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["match_id"] == "00000000-0000-0000-0000-000000000101"
    assert payload["agent_id"] == "agent-player-2"
    assert payload["player_id"] == "player-2"
    assert payload["state"]["match_id"] == "00000000-0000-0000-0000-000000000101"
    assert payload["state"]["player_id"] == "player-2"
    assert payload["state"]["cities"]["manchester"]["visibility"] == "full"
    assert payload["queued_orders"] == {
        "movements": [{"army_id": "army-b", "destination": "london"}],
        "recruitment": [{"city": "manchester", "troops": 3}],
        "upgrades": [],
        "transfers": [],
    }
    assert payload["guidance"] == [
        {
            "guidance_id": payload["guidance"][0]["guidance_id"],
            "match_id": "00000000-0000-0000-0000-000000000101",
            "player_id": "player-2",
            "tick": 142,
            "content": "Hold London unless the coast opens.",
            "created_at": payload["guidance"][0]["created_at"],
        }
    ]
    assert payload["group_chats"] == [
        {
            "group_chat_id": "group-chat-1",
            "name": "Owners Council",
            "member_ids": ["player-1", "player-2"],
            "created_by": "player-2",
            "created_tick": 142,
        }
    ]
    assert _briefing_message_contents(payload, "direct") == ["Hold Manchester."]
    assert _briefing_message_contents(payload, "group") == ["Queued guidance note."]
    assert payload["recent_activity"]["alliances"] == [
        {
            "alliance_id": "alliance-red",
            "name": "Western Accord",
            "leader_id": "player-1",
            "formed_tick": 120,
            "members": [
                {"player_id": "player-1", "joined_tick": 120},
                {"player_id": "player-2", "joined_tick": 120},
            ],
        }
    ]
    assert payload["recent_activity"]["treaties"] == [
        {
            "treaty_id": 1,
            "player_a_id": "player-2",
            "player_b_id": "player-3",
            "treaty_type": "trade",
            "status": "active",
            "proposed_by": "player-2",
            "proposed_tick": 142,
            "signed_tick": 142,
            "withdrawn_by": None,
            "withdrawn_tick": None,
        }
    ]
    assert all(
        payload["player_id"] in {treaty["player_a_id"], treaty["player_b_id"]}
        for treaty in payload["recent_activity"]["treaties"]
    )


@pytest.mark.asyncio
async def test_owned_agent_guided_session_route_requires_human_bearer_and_enforces_ownership_and_match_membership(  # noqa: E501
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'owned-agent-guided-session-errors.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        missing_auth_response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/guided-session"
        )
        wrong_owner_response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/guided-session",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000301"),
        )
        unjoined_agent_response = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000102/agents/agent-player-2/guided-session",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )

    assert missing_auth_response.status_code == HTTPStatus.UNAUTHORIZED
    assert missing_auth_response.json() == {
        "error": {
            "code": "invalid_human_token",
            "message": "A valid human Bearer token is required.",
        }
    }
    assert wrong_owner_response.status_code == HTTPStatus.FORBIDDEN
    assert wrong_owner_response.json() == {
        "error": {
            "code": "agent_not_owned",
            "message": (
                "Authenticated human user '00000000-0000-0000-0000-000000000301' does not "
                "own agent 'agent-player-2'."
            ),
        }
    }
    assert unjoined_agent_response.status_code == HTTPStatus.BAD_REQUEST
    assert unjoined_agent_response.json() == {
        "error": {
            "code": "agent_not_joined",
            "message": (
                "Agent 'agent-player-2' has not joined match "
                "'00000000-0000-0000-0000-000000000102' as a player."
            ),
        }
    }


@pytest.mark.asyncio
async def test_owned_agent_guided_session_route_returns_documented_503_when_app_is_not_db_backed(
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    app = create_app(
        match_registry=seeded_registry,
        settings_override={
            "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
            "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
            "HUMAN_JWT_AUDIENCE": "authenticated",
            "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
        },
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/matches/match-alpha/agents/agent-player-2/guided-session",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json() == {
        "error": {
            "code": "guided_session_unavailable",
            "message": "Owned agent guided-session reads are only available in DB-backed mode.",
        }
    }


@pytest.mark.asyncio
async def test_owned_agent_guidance_write_stays_out_of_message_channels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'owned-agent-guidance-write.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()
    payload = _owned_agent_guidance_payload(
        match_id="00000000-0000-0000-0000-000000000101",
        tick=142,
        content="Prioritize London if the west opens.",
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/guidance",
            json=payload,
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )

    assert response.status_code == HTTPStatus.ACCEPTED
    accepted = response.json()
    assert accepted["status"] == "accepted"
    assert accepted["match_id"] == "00000000-0000-0000-0000-000000000101"
    assert accepted["agent_id"] == "agent-player-2"
    assert accepted["player_id"] == "player-2"
    assert accepted["tick"] == 142
    assert accepted["content"] == "Prioritize London if the west opens."
    assert isinstance(accepted["guidance_id"], str)

    engine = create_engine(database_url)
    with engine.connect() as connection:
        guidance_rows = (
            connection.execute(
                text(
                    """
                SELECT owner_user_id, agent_player_id, tick, content
                FROM owned_agent_guidance
                ORDER BY created_at, id
                """
                )
            )
            .mappings()
            .all()
        )
        message_rows = (
            connection.execute(
                text(
                    "SELECT channel_type, recipient_id, content "
                    "FROM messages ORDER BY created_at, id"
                )
            )
            .mappings()
            .all()
        )

    assert [dict(row) for row in guidance_rows] == [
        {
            "owner_user_id": "00000000-0000-0000-0000-000000000302",
            "agent_player_id": build_persisted_player_id(
                match_id="00000000-0000-0000-0000-000000000101",
                public_player_id="player-2",
            ),
            "tick": 142,
            "content": "Prioritize London if the west opens.",
        }
    ]
    assert all(row["content"] != "Prioritize London if the west opens." for row in message_rows)


@pytest.mark.asyncio
async def test_owned_agent_guidance_write_enforces_auth_ownership_match_and_tick(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'owned-agent-guidance-write-errors.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        missing_auth_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/guidance",
            json=_owned_agent_guidance_payload(
                match_id="00000000-0000-0000-0000-000000000101",
            ),
        )
        wrong_owner_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/guidance",
            json=_owned_agent_guidance_payload(
                match_id="00000000-0000-0000-0000-000000000101",
            ),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000301"),
        )
        unjoined_agent_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000102/agents/agent-player-2/guidance",
            json=_owned_agent_guidance_payload(
                match_id="00000000-0000-0000-0000-000000000102",
                content="Scout the southern coast.",
            ),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )
        tick_mismatch_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/guidance",
            json=_owned_agent_guidance_payload(
                match_id="00000000-0000-0000-0000-000000000101",
                tick=141,
            ),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )

    assert missing_auth_response.status_code == HTTPStatus.UNAUTHORIZED
    assert missing_auth_response.json() == {
        "error": {
            "code": "invalid_human_token",
            "message": "A valid human Bearer token is required.",
        }
    }
    assert wrong_owner_response.status_code == HTTPStatus.FORBIDDEN
    assert wrong_owner_response.json() == {
        "error": {
            "code": "agent_not_owned",
            "message": (
                "Authenticated human user '00000000-0000-0000-0000-000000000301' does not "
                "own agent 'agent-player-2'."
            ),
        }
    }
    assert unjoined_agent_response.status_code == HTTPStatus.BAD_REQUEST
    assert unjoined_agent_response.json() == {
        "error": {
            "code": "agent_not_joined",
            "message": (
                "Agent 'agent-player-2' has not joined match "
                "'00000000-0000-0000-0000-000000000102' as a player."
            ),
        }
    }
    assert tick_mismatch_response.status_code == HTTPStatus.BAD_REQUEST
    assert tick_mismatch_response.json() == {
        "error": {
            "code": "tick_mismatch",
            "message": ("Guidance payload tick '141' does not match current match tick '142'."),
        }
    }


@pytest.mark.asyncio
async def test_owned_agent_guidance_write_returns_not_found_mismatch_and_unavailable_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'owned-agent-guidance-write-route-errors.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    db_app = create_app()
    memory_app = create_app(
        match_registry=seeded_registry,
        settings_override={
            "IRON_COUNCIL_MATCH_REGISTRY_BACKEND": "memory",
            "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
            "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
            "HUMAN_JWT_AUDIENCE": "authenticated",
            "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
        },
    )

    async with AsyncClient(
        transport=ASGITransport(app=db_app),
        base_url="http://testserver",
    ) as client:
        missing_match_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-00000000ffff/agents/agent-player-2/guidance",
            json=_owned_agent_guidance_payload(
                match_id="00000000-0000-0000-0000-00000000ffff",
            ),
        )
        mismatch_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/guidance",
            json=_owned_agent_guidance_payload(
                match_id="00000000-0000-0000-0000-000000000102",
            ),
        )

    async with AsyncClient(
        transport=ASGITransport(app=memory_app),
        base_url="http://testserver",
    ) as client:
        unavailable_response = await client.post(
            "/api/v1/matches/match-alpha/agents/agent-player-2/guidance",
            json=_owned_agent_guidance_payload(match_id="match-alpha"),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )

    assert missing_match_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_match_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match '00000000-0000-0000-0000-00000000ffff' was not found.",
        }
    }
    assert mismatch_response.status_code == HTTPStatus.BAD_REQUEST
    assert mismatch_response.json() == {
        "error": {
            "code": "match_id_mismatch",
            "message": (
                "Guidance payload match_id '00000000-0000-0000-0000-000000000102' does "
                "not match route match '00000000-0000-0000-0000-000000000101'."
            ),
        }
    }
    assert unavailable_response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert unavailable_response.json() == {
        "error": {
            "code": "guided_session_unavailable",
            "message": "Owned agent guidance writes are only available in DB-backed mode.",
        }
    }


@pytest.mark.asyncio
async def test_owned_agent_override_replaces_current_tick_orders_and_records_audit_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'owned-agent-override-write.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()
    registry = app.state.match_registry
    record = registry.get_match("00000000-0000-0000-0000-000000000101")
    assert record is not None

    registry.record_submission(
        match_id=record.match_id,
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": record.match_id,
                "player_id": "player-2",
                "tick": record.state.tick,
                "orders": {
                    "movements": [{"army_id": "army-b", "destination": "york"}],
                    "recruitment": [{"city": "manchester", "troops": 1}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    registry.record_submission(
        match_id=record.match_id,
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": record.match_id,
                "player_id": "player-2",
                "tick": record.state.tick,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "manchester", "troops": 2}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    registry.record_submission(
        match_id=record.match_id,
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": record.match_id,
                "player_id": "player-3",
                "tick": record.state.tick,
                "orders": {
                    "movements": [{"army_id": "army-c", "destination": "oxford"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/override",
            json=_owned_agent_override_payload(
                match_id="00000000-0000-0000-0000-000000000101",
                tick=142,
                orders={
                    "movements": [{"army_id": "army-b", "destination": "london"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            ),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )

    assert response.status_code == HTTPStatus.ACCEPTED
    accepted = response.json()
    assert accepted == {
        "status": "accepted",
        "override_id": accepted["override_id"],
        "match_id": "00000000-0000-0000-0000-000000000101",
        "agent_id": "agent-player-2",
        "player_id": "player-2",
        "tick": 142,
        "submission_index": 1,
        "superseded_submission_count": 2,
        "orders": {
            "movements": [{"army_id": "army-b", "destination": "london"}],
            "recruitment": [],
            "upgrades": [],
            "transfers": [],
        },
    }
    assert isinstance(accepted["override_id"], str)
    assert registry.list_order_submissions("00000000-0000-0000-0000-000000000101") == [
        {
            "match_id": "00000000-0000-0000-0000-000000000101",
            "player_id": "player-3",
            "tick": 142,
            "orders": {
                "movements": [{"army_id": "army-c", "destination": "oxford"}],
                "recruitment": [],
                "upgrades": [],
                "transfers": [],
            },
        },
        {
            "match_id": "00000000-0000-0000-0000-000000000101",
            "player_id": "player-2",
            "tick": 142,
            "orders": {
                "movements": [{"army_id": "army-b", "destination": "london"}],
                "recruitment": [],
                "upgrades": [],
                "transfers": [],
            },
        },
    ]

    engine = create_engine(database_url)
    with engine.connect() as connection:
        override_rows = (
            connection.execute(
                text(
                    """
                SELECT owner_user_id, agent_player_id, tick, superseded_submission_count, orders
                FROM owned_agent_overrides
                ORDER BY created_at, id
                """
                )
            )
            .mappings()
            .all()
        )

    normalized_override_rows = []
    for row in override_rows:
        normalized_row = dict(row)
        if isinstance(normalized_row["orders"], str):
            normalized_row["orders"] = json.loads(normalized_row["orders"])
        normalized_override_rows.append(normalized_row)

    assert normalized_override_rows == [
        {
            "owner_user_id": "00000000-0000-0000-0000-000000000302",
            "agent_player_id": build_persisted_player_id(
                match_id="00000000-0000-0000-0000-000000000101",
                public_player_id="player-2",
            ),
            "tick": 142,
            "superseded_submission_count": 2,
            "orders": {
                "movements": [{"army_id": "army-b", "destination": "london"}],
                "recruitment": [],
                "upgrades": [],
                "transfers": [],
            },
        }
    ]


@pytest.mark.asyncio
async def test_owned_agent_override_rejects_invalid_requests_without_mutating_submissions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'owned-agent-override-write-errors.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    db_app = create_app()
    registry = db_app.state.match_registry
    record = registry.get_match("00000000-0000-0000-0000-000000000101")
    assert record is not None
    registry.record_submission(
        match_id=record.match_id,
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": record.match_id,
                "player_id": "player-2",
                "tick": record.state.tick,
                "orders": {
                    "movements": [{"army_id": "army-b", "destination": "york"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    before_submissions = registry.list_order_submissions(record.match_id)

    memory_app = create_app(
        match_registry=seeded_registry,
        settings_override={
            "IRON_COUNCIL_MATCH_REGISTRY_BACKEND": "memory",
            "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
            "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
            "HUMAN_JWT_AUDIENCE": "authenticated",
            "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
        },
    )

    async with AsyncClient(
        transport=ASGITransport(app=db_app),
        base_url="http://testserver",
    ) as client:
        missing_auth_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/override",
            json=_owned_agent_override_payload(
                match_id="00000000-0000-0000-0000-000000000101",
            ),
        )
        wrong_owner_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/override",
            json=_owned_agent_override_payload(
                match_id="00000000-0000-0000-0000-000000000101",
            ),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000301"),
        )
        late_tick_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/override",
            json=_owned_agent_override_payload(
                match_id="00000000-0000-0000-0000-000000000101",
                tick=141,
            ),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )
        missing_orders_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/override",
            json={
                "match_id": "00000000-0000-0000-0000-000000000101",
                "tick": 142,
            },
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )
        mismatch_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/override",
            json=_owned_agent_override_payload(
                match_id="00000000-0000-0000-0000-000000000102",
            ),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )
        missing_match_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-00000000ffff/agents/agent-player-2/override",
            json=_owned_agent_override_payload(
                match_id="00000000-0000-0000-0000-00000000ffff",
            ),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )
        unjoined_agent_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000102/agents/agent-player-2/override",
            json=_owned_agent_override_payload(
                match_id="00000000-0000-0000-0000-000000000102",
            ),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )

    async with AsyncClient(
        transport=ASGITransport(app=memory_app),
        base_url="http://testserver",
    ) as client:
        unavailable_response = await client.post(
            "/api/v1/matches/match-alpha/agents/agent-player-2/override",
            json=_owned_agent_override_payload(match_id="match-alpha"),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )

    assert missing_auth_response.status_code == HTTPStatus.UNAUTHORIZED
    assert missing_auth_response.json() == {
        "error": {
            "code": "invalid_human_token",
            "message": "A valid human Bearer token is required.",
        }
    }
    assert wrong_owner_response.status_code == HTTPStatus.FORBIDDEN
    assert wrong_owner_response.json() == {
        "error": {
            "code": "agent_not_owned",
            "message": (
                "Authenticated human user '00000000-0000-0000-0000-000000000301' does not "
                "own agent 'agent-player-2'."
            ),
        }
    }
    assert late_tick_response.status_code == HTTPStatus.BAD_REQUEST
    assert late_tick_response.json() == {
        "error": {
            "code": "guided_override_tick_mismatch",
            "message": ("Override payload tick '141' must match current match tick '142'."),
        }
    }
    assert missing_orders_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert missing_orders_response.json()["detail"][0]["loc"] == ["body", "orders"]
    assert mismatch_response.status_code == HTTPStatus.BAD_REQUEST
    assert mismatch_response.json() == {
        "error": {
            "code": "match_id_mismatch",
            "message": (
                "Override payload match_id '00000000-0000-0000-0000-000000000102' does not "
                "match route match '00000000-0000-0000-0000-000000000101'."
            ),
        }
    }
    assert missing_match_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_match_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match '00000000-0000-0000-0000-00000000ffff' was not found.",
        }
    }
    assert unjoined_agent_response.status_code == HTTPStatus.BAD_REQUEST
    assert unjoined_agent_response.json() == {
        "error": {
            "code": "agent_not_joined",
            "message": (
                "Agent 'agent-player-2' has not joined match "
                "'00000000-0000-0000-0000-000000000102' as a player."
            ),
        }
    }
    assert unavailable_response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert unavailable_response.json() == {
        "error": {
            "code": "guided_override_unavailable",
            "message": "Owned agent override writes are only available in DB-backed mode.",
        }
    }
    assert registry.list_order_submissions(record.match_id) == before_submissions

    engine = create_engine(database_url)
    with engine.connect() as connection:
        override_count = connection.execute(
            text("SELECT COUNT(*) FROM owned_agent_overrides")
        ).scalar_one()

    assert override_count == 0


@pytest.mark.asyncio
async def test_owned_agent_override_leaves_queue_unchanged_when_persistence_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'owned-agent-override-persistence-error.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()
    registry = app.state.match_registry
    record = registry.get_match("00000000-0000-0000-0000-000000000101")
    assert record is not None
    registry.record_submission(
        match_id=record.match_id,
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": record.match_id,
                "player_id": "player-2",
                "tick": record.state.tick,
                "orders": {
                    "movements": [{"army_id": "army-b", "destination": "york"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    before_submissions = registry.list_order_submissions(record.match_id)

    def _raise_persistence_error(**_: Any) -> Any:
        raise RuntimeError("override persistence failed")

    monkeypatch.setattr(
        "server.api.authenticated_write_routes.append_owned_agent_override",
        _raise_persistence_error,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        with pytest.raises(RuntimeError, match="override persistence failed"):
            await client.post(
                "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/override",
                json=_owned_agent_override_payload(
                    match_id="00000000-0000-0000-0000-000000000101",
                    tick=142,
                    orders={
                        "movements": [{"army_id": "army-b", "destination": "london"}],
                        "recruitment": [],
                        "upgrades": [],
                        "transfers": [],
                    },
                ),
                headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
            )

    assert registry.list_order_submissions(record.match_id) == before_submissions


@pytest.mark.asyncio
async def test_submit_orders_accepts_human_bearer_auth_from_public_boundary(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = "match-alpha"
    payload["tick"] = 142
    payload["orders"]["movements"] = [{"army_id": "army-b", "destination": "birmingham"}]
    payload.pop("player_id", None)

    async with app_client as client:
        response = await client.post(
            "/api/v1/matches/match-alpha/orders",
            json=payload,
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )

    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "player_id": "player-2",
        "tick": 142,
        "submission_index": 0,
    }
    assert seeded_registry.list_order_submissions("match-alpha") == [
        {
            **payload,
            "player_id": "player-2",
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("headers", "expected_error"),
    [
        (
            {"Authorization": "Bearer not-a-jwt"},
            {
                "code": "invalid_human_token",
                "message": "A valid human Bearer token is required.",
            },
        ),
        (
            _auth_headers_for_human(
                "00000000-0000-0000-0000-000000000302",
                role="service_role",
            ),
            {
                "code": "invalid_human_token_role",
                "message": "Human JWT role claim must be 'authenticated'.",
            },
        ),
    ],
)
async def test_submit_orders_rejects_invalid_human_bearer_auth_without_mutation(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
    headers: dict[str, str],
    expected_error: dict[str, str],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = "match-alpha"
    payload["tick"] = 142
    payload.pop("player_id", None)

    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        response = await client.post(
            "/api/v1/matches/match-alpha/orders",
            json=payload,
            headers=headers,
        )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {"error": expected_error}
    assert _match_state_dump(seeded_registry) == before_state
    assert seeded_registry.list_order_submissions("match-alpha") == []


@pytest.mark.asyncio
async def test_agent_happy_path_covers_list_state_submit_and_follow_up_read(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = "match-alpha"
    payload["tick"] = 142
    payload["orders"]["movements"] = [{"army_id": "army-b", "destination": "birmingham"}]
    payload.pop("player_id", None)

    async with app_client as client:
        list_response = await client.get("/api/v1/matches")
        initial_state_response = await client.get(
            "/api/v1/matches/match-alpha/state",
            headers=_auth_headers_for_player("player-1"),
        )
        submit_response = await client.post(
            "/api/v1/matches/match-alpha/orders",
            json=payload,
            headers=_auth_headers_for_player("player-1"),
        )
        follow_up_state_response = await client.get(
            "/api/v1/matches/match-alpha/state",
            headers=_auth_headers_for_player("player-1"),
        )

    assert list_response.status_code == HTTPStatus.OK
    assert [match["match_id"] for match in list_response.json()["matches"]] == [
        "match-alpha",
        "match-beta",
    ]
    assert initial_state_response.status_code == HTTPStatus.OK
    assert submit_response.status_code == HTTPStatus.ACCEPTED
    assert submit_response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "player_id": "player-1",
        "tick": 142,
        "submission_index": 0,
    }
    assert follow_up_state_response.status_code == HTTPStatus.OK
    assert follow_up_state_response.json() == initial_state_response.json()
    assert seeded_registry.list_order_submissions("match-alpha") == [
        {
            **payload,
            "player_id": "player-1",
        }
    ]


@pytest.mark.asyncio
async def test_submit_orders_rejects_invalid_authenticated_requests_without_mutation(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    stale_payload = deepcopy(representative_order_payload)
    stale_payload["match_id"] = "match-alpha"
    stale_payload["tick"] = 141
    stale_payload.pop("player_id", None)

    malformed_payload = deepcopy(representative_order_payload)
    malformed_payload["match_id"] = "match-alpha"
    malformed_payload["tick"] = 142
    malformed_payload["orders"]["recruitment"] = [{"city": "london", "troops": 0}]
    malformed_payload.pop("player_id", None)
    unknown_match_payload = deepcopy(representative_order_payload)
    unknown_match_payload["match_id"] = "match-missing"
    unknown_match_payload.pop("player_id", None)
    mismatch_payload = deepcopy(representative_order_payload)
    mismatch_payload["match_id"] = "match-beta"
    mismatch_payload.pop("player_id", None)

    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        unknown_match_response = await client.post(
            "/api/v1/matches/match-missing/orders",
            json=unknown_match_payload,
            headers=_auth_headers_for_player("player-1"),
        )
        mismatch_response = await client.post(
            "/api/v1/matches/match-alpha/orders",
            json=mismatch_payload,
            headers=_auth_headers_for_player("player-1"),
        )
        stale_response = await client.post(
            "/api/v1/matches/match-alpha/orders",
            json=stale_payload,
            headers=_auth_headers_for_player("player-1"),
        )
        malformed_response = await client.post(
            "/api/v1/matches/match-alpha/orders",
            json=malformed_payload,
            headers=_auth_headers_for_player("player-1"),
        )

    assert unknown_match_response.status_code == HTTPStatus.NOT_FOUND
    assert unknown_match_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match 'match-missing' was not found.",
        }
    }
    assert mismatch_response.status_code == HTTPStatus.BAD_REQUEST
    assert mismatch_response.json() == {
        "error": {
            "code": "match_id_mismatch",
            "message": (
                "Order payload match_id 'match-beta' does not match route match 'match-alpha'."
            ),
        }
    }
    assert stale_response.status_code == HTTPStatus.BAD_REQUEST
    assert stale_response.json() == {
        "error": {
            "code": "tick_mismatch",
            "message": "Order payload tick '141' does not match current match tick '142'.",
        }
    }
    assert malformed_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert malformed_response.json()["detail"][0]["loc"] == [
        "body",
        "orders",
        "recruitment",
        0,
        "troops",
    ]
    assert seeded_registry.list_order_submissions("match-alpha") == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_post_command_envelope_accepts_orders_messages_treaties_and_alliance_in_one_request(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    seeded_registry.create_group_chat(
        match_id="match-alpha",
        request=GroupChatCreateRequest(
            match_id="match-alpha",
            tick=142,
            name="Envelope Council",
            member_ids=["player-1"],
        ),
        creator_id="player-2",
    )
    payload = _command_envelope_payload(
        orders={
            **deepcopy(representative_order_payload["orders"]),
            "movements": [{"army_id": "army-b", "destination": "birmingham"}],
            "recruitment": [],
            "upgrades": [],
            "transfers": [],
        },
        messages=[
            _command_message(channel="world", recipient_id=None, content="Envelope world update."),
            _command_message(
                channel="direct",
                recipient_id="player-1",
                content="Envelope direct update.",
            ),
            _command_message(
                channel="group",
                group_chat_id="group-chat-1",
                content="Envelope group update.",
            ),
        ],
        treaties=[_command_treaty(counterparty_id="player-3", action="propose")],
        alliance=_command_alliance(action="leave", alliance_id=None, name=None),
    )

    async with app_client as client:
        response = await client.post(
            "/api/v1/matches/match-alpha/command",
            json=payload,
            headers=_auth_headers_for_player("player-2"),
        )

    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "player_id": "player-2",
        "tick": 142,
        "orders": {
            "status": "accepted",
            "match_id": "match-alpha",
            "player_id": "player-2",
            "tick": 142,
            "submission_index": 0,
        },
        "messages": [
            {
                "status": "accepted",
                "match_id": "match-alpha",
                "message_id": 0,
                "channel": "world",
                "sender_id": "player-2",
                "recipient_id": None,
                "tick": 142,
                "content": "Envelope world update.",
            },
            {
                "status": "accepted",
                "match_id": "match-alpha",
                "message_id": 1,
                "channel": "direct",
                "sender_id": "player-2",
                "recipient_id": "player-1",
                "tick": 142,
                "content": "Envelope direct update.",
            },
            {
                "status": "accepted",
                "match_id": "match-alpha",
                "group_chat_id": "group-chat-1",
                "message": {
                    "message_id": 0,
                    "group_chat_id": "group-chat-1",
                    "sender_id": "player-2",
                    "tick": 142,
                    "content": "Envelope group update.",
                },
            },
        ],
        "treaties": [
            {
                "status": "accepted",
                "match_id": "match-alpha",
                "treaty": {
                    "treaty_id": 0,
                    "player_a_id": "player-2",
                    "player_b_id": "player-3",
                    "treaty_type": "trade",
                    "status": "proposed",
                    "proposed_by": "player-2",
                    "proposed_tick": 142,
                    "signed_tick": None,
                    "withdrawn_by": None,
                    "withdrawn_tick": None,
                },
            }
        ],
        "alliance": {
            "status": "accepted",
            "match_id": "match-alpha",
            "player_id": "player-2",
            "alliance": {
                "alliance_id": "alliance-red",
                "name": "alliance-red",
                "leader_id": "player-1",
                "formed_tick": 142,
                "members": [{"player_id": "player-1", "joined_tick": 142}],
            },
        },
    }
    assert seeded_registry.list_order_submissions("match-alpha") == [
        {
            "match_id": "match-alpha",
            "player_id": "player-2",
            "tick": 142,
            "orders": payload["orders"],
        }
    ]
    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    assert [message.content for message in record.messages] == [
        "Envelope world update.",
        "Envelope direct update.",
    ]
    assert [message.content for message in record.group_chats[0].messages] == [
        "Envelope group update."
    ]
    assert [treaty.player_b_id for treaty in record.treaties] == ["player-3"]
    assert record.state.players["player-2"].alliance_id is None


@pytest.mark.asyncio
async def test_post_command_envelope_rejects_invalid_actions_without_partial_mutation(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = _command_envelope_payload(
        orders={
            **deepcopy(representative_order_payload["orders"]),
            "movements": [{"army_id": "army-b", "destination": "birmingham"}],
            "recruitment": [],
            "upgrades": [],
            "transfers": [],
        },
        messages=[
            _command_message(channel="world", recipient_id=None, content="Should not persist."),
            _command_message(
                channel="group",
                group_chat_id="group-chat-missing",
                content="Should not persist in group.",
            ),
        ],
        treaties=[_command_treaty(counterparty_id="player-3", action="propose")],
        alliance=_command_alliance(action="leave", alliance_id=None, name=None),
    )
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        response = await client.post(
            "/api/v1/matches/match-alpha/command",
            json=payload,
            headers=_auth_headers_for_player("player-2"),
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "error": {
            "code": "group_chat_not_visible",
            "message": "Group chat 'group-chat-missing' is not visible to player 'player-2'.",
        }
    }
    assert seeded_registry.list_order_submissions("match-alpha") == []
    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    assert record.messages == []
    assert all(group_chat.messages == [] for group_chat in record.group_chats)
    assert record.treaties == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "expected_error"),
    [
        (
            {
                "match_id": "match-alpha",
                "tick": 142,
                "messages": [
                    {"channel": "world", "content": "first ok"},
                    {"channel": "world", "content": ""},
                ],
            },
            {
                "code": "invalid_message_content",
                "message": "Message content must be at least 1 character long.",
            },
        ),
        (
            {
                "match_id": "match-alpha",
                "messages": [],
            },
            {
                "code": "invalid_command_request",
                "message": "Command request is missing required fields.",
            },
        ),
        (
            {
                "match_id": "match-alpha",
                "tick": "stale",
                "messages": [],
            },
            {
                "code": "invalid_command_request",
                "message": "Command request validation failed.",
            },
        ),
        (
            {
                "match_id": "match-alpha",
                "tick": 142,
                "treaties": [
                    {"counterparty_id": "player-3", "action": "ignore", "treaty_type": "trade"}
                ],
            },
            {
                "code": "invalid_treaty_action",
                "message": "Treaty action must be one of: propose, accept, withdraw.",
            },
        ),
        (
            {
                "match_id": "match-alpha",
                "tick": 142,
                "treaties": [
                    {"counterparty_id": "player-3", "action": "propose", "treaty_type": "ceasefire"}
                ],
            },
            {
                "code": "invalid_treaty_type",
                "message": "Treaty type must be one of: non_aggression, defensive, trade.",
            },
        ),
        (
            {
                "match_id": "match-alpha",
                "tick": 142,
                "alliance": {"action": "create", "alliance_id": "alliance-1", "name": "North"},
            },
            {
                "code": "invalid_alliance_request",
                "message": "Alliance create does not accept alliance_id.",
            },
        ),
        (
            {
                "match_id": "match-alpha",
                "tick": 142,
                "alliance": {"action": "create", "alliance_id": None, "name": None},
            },
            {
                "code": "invalid_alliance_request",
                "message": "Alliance create requires name.",
            },
        ),
        (
            {
                "match_id": "match-alpha",
                "tick": 142,
                "alliance": {"action": "join", "alliance_id": None, "name": None},
            },
            {
                "code": "invalid_alliance_request",
                "message": "Alliance join requires alliance_id.",
            },
        ),
        (
            {
                "match_id": "match-alpha",
                "tick": 142,
                "alliance": {"action": "join", "alliance_id": "alliance-1", "name": "North"},
            },
            {
                "code": "invalid_alliance_request",
                "message": "Alliance join does not accept name.",
            },
        ),
        (
            {
                "match_id": "match-alpha",
                "tick": 142,
                "alliance": {"action": "leave", "alliance_id": "alliance-1", "name": None},
            },
            {
                "code": "invalid_alliance_request",
                "message": "Alliance leave does not accept alliance_id.",
            },
        ),
        (
            {
                "match_id": "match-alpha",
                "tick": 142,
                "alliance": {"action": "leave", "alliance_id": None, "name": "North"},
            },
            {
                "code": "invalid_alliance_request",
                "message": "Alliance leave does not accept name.",
            },
        ),
    ],
)
async def test_command_envelope_validation_errors_are_structured(
    app_client: AsyncClient,
    payload: dict[str, Any],
    expected_error: dict[str, str],
) -> None:
    async with app_client as client:
        response = await client.post(
            "/api/v1/matches/match-alpha/command",
            json=payload,
            headers=_auth_headers_for_player("player-2"),
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json() == {"error": expected_error}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("route_match_id", "payload", "expected_status", "expected_error"),
    [
        (
            "match-missing",
            _command_envelope_payload(match_id="match-missing"),
            HTTPStatus.NOT_FOUND,
            {
                "code": "match_not_found",
                "message": "Match 'match-missing' was not found.",
            },
        ),
        (
            "match-alpha",
            _command_envelope_payload(match_id="match-beta"),
            HTTPStatus.BAD_REQUEST,
            {
                "code": "match_id_mismatch",
                "message": (
                    "Command payload match_id 'match-beta' does not match route match "
                    "'match-alpha'."
                ),
            },
        ),
        (
            "match-alpha",
            _command_envelope_payload(tick=141),
            HTTPStatus.BAD_REQUEST,
            {
                "code": "tick_mismatch",
                "message": "Command payload tick '141' does not match current match tick '142'.",
            },
        ),
        (
            "match-alpha",
            _command_envelope_payload(
                messages=[_command_message(channel="world", recipient_id="player-1")]
            ),
            HTTPStatus.BAD_REQUEST,
            {
                "code": "unsupported_recipient",
                "message": "World messages do not support recipient_id.",
            },
        ),
        (
            "match-alpha",
            _command_envelope_payload(
                messages=[_command_message(channel="direct", recipient_id=None)]
            ),
            HTTPStatus.BAD_REQUEST,
            {
                "code": "unsupported_recipient",
                "message": (
                    "Direct messages require a recipient_id for a player in match 'match-alpha'."
                ),
            },
        ),
        (
            "match-alpha",
            _command_envelope_payload(
                messages=[
                    _command_message(
                        channel="group",
                        group_chat_id="group-chat-missing",
                        content="Secure.",
                    )
                ]
            ),
            HTTPStatus.BAD_REQUEST,
            {
                "code": "group_chat_not_visible",
                "message": "Group chat 'group-chat-missing' is not visible to player 'player-2'.",
            },
        ),
        (
            "match-alpha",
            _command_envelope_payload(treaties=[_command_treaty(counterparty_id="player-missing")]),
            HTTPStatus.BAD_REQUEST,
            {
                "code": "player_not_found",
                "message": "Player 'player-missing' was not found in match 'match-alpha'.",
            },
        ),
        (
            "match-alpha",
            _command_envelope_payload(treaties=[_command_treaty(counterparty_id="player-2")]),
            HTTPStatus.BAD_REQUEST,
            {
                "code": "self_targeted_treaty",
                "message": "Treaty actions require two different players.",
            },
        ),
    ],
)
async def test_command_envelope_rejects_invalid_route_and_action_contracts(
    app_client: AsyncClient,
    payload: dict[str, Any],
    route_match_id: str,
    expected_status: HTTPStatus,
    expected_error: dict[str, str],
) -> None:
    async with app_client as client:
        response = await client.post(
            f"/api/v1/matches/{route_match_id}/command",
            json=payload,
            headers=_auth_headers_for_player("player-2"),
        )

    assert response.status_code == expected_status
    assert response.json() == {"error": expected_error}


@pytest.mark.asyncio
async def test_post_commands_alias_preserves_command_envelope_contract(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        response = await client.post(
            "/api/v1/matches/match-alpha/commands",
            json=_command_envelope_payload(
                messages=[_command_message(channel="world", content="Alias world update.")]
            ),
            headers=_auth_headers_for_player("player-2"),
        )

    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "player_id": "player-2",
        "tick": 142,
        "orders": None,
        "messages": [
            {
                "status": "accepted",
                "message_id": 0,
                "match_id": "match-alpha",
                "channel": "world",
                "sender_id": "player-2",
                "recipient_id": None,
                "tick": 142,
                "content": "Alias world update.",
            }
        ],
        "treaties": [],
        "alliance": None,
    }


@pytest.mark.asyncio
async def test_post_messages_accepts_world_and_direct_messages_and_lists_visible_history(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    world_payload = _message_payload(channel="world", content="World update.")
    direct_payload = _message_payload(
        channel="direct",
        recipient_id="player-1",
        content="Private coordination.",
    )

    async with app_client as client:
        world_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=world_payload,
            headers=_auth_headers_for_player("player-1"),
        )
        direct_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=direct_payload,
            headers=_auth_headers_for_player("player-2"),
        )
        inbox_for_player_one = await client.get(
            "/api/v1/matches/match-alpha/messages",
            headers=_auth_headers_for_player("player-1"),
        )
        inbox_for_player_three = await client.get(
            "/api/v1/matches/match-alpha/messages",
            headers=_auth_headers_for_player("player-3"),
        )

    assert world_response.status_code == HTTPStatus.ACCEPTED
    assert world_response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "message_id": 0,
        "channel": "world",
        "sender_id": "player-1",
        "recipient_id": None,
        "tick": 142,
        "content": "World update.",
    }
    assert direct_response.status_code == HTTPStatus.ACCEPTED
    assert direct_response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "message_id": 1,
        "channel": "direct",
        "sender_id": "player-2",
        "recipient_id": "player-1",
        "tick": 142,
        "content": "Private coordination.",
    }
    assert inbox_for_player_one.status_code == HTTPStatus.OK
    assert inbox_for_player_one.json() == {
        "match_id": "match-alpha",
        "player_id": "player-1",
        "messages": [
            {
                "message_id": 0,
                "channel": "world",
                "sender_id": "player-1",
                "recipient_id": None,
                "tick": 142,
                "content": "World update.",
            },
            {
                "message_id": 1,
                "channel": "direct",
                "sender_id": "player-2",
                "recipient_id": "player-1",
                "tick": 142,
                "content": "Private coordination.",
            },
        ],
    }
    assert inbox_for_player_three.status_code == HTTPStatus.OK
    assert inbox_for_player_three.json() == {
        "match_id": "match-alpha",
        "player_id": "player-3",
        "messages": [
            {
                "message_id": 0,
                "channel": "world",
                "sender_id": "player-1",
                "recipient_id": None,
                "tick": 142,
                "content": "World update.",
            }
        ],
    }
    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    assert len(record.messages) == 2


@pytest.mark.asyncio
async def test_group_chat_creation_visibility_and_member_message_flow(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    create_payload = _group_chat_create_payload(member_ids=["player-2", "player-4"])

    async with app_client as client:
        create_response = await client.post(
            "/api/v1/matches/match-alpha/group-chats",
            json=create_payload,
            headers=_auth_headers_for_player("player-1"),
        )
        creator_group_chats = await client.get(
            "/api/v1/matches/match-alpha/group-chats",
            headers=_auth_headers_for_player("player-1"),
        )
        invited_group_chats = await client.get(
            "/api/v1/matches/match-alpha/group-chats",
            headers=_auth_headers_for_player("player-2"),
        )
        outsider_group_chats = await client.get(
            "/api/v1/matches/match-alpha/group-chats",
            headers=_auth_headers_for_player("player-3"),
        )
        invited_message_response = await client.post(
            "/api/v1/matches/match-alpha/group-chats/group-chat-1/messages",
            json={
                "match_id": "match-alpha",
                "tick": 142,
                "content": "Ready to coordinate.",
            },
            headers=_auth_headers_for_player("player-2"),
        )
        creator_message_read = await client.get(
            "/api/v1/matches/match-alpha/group-chats/group-chat-1/messages",
            headers=_auth_headers_for_player("player-1"),
        )
        outsider_message_read = await client.get(
            "/api/v1/matches/match-alpha/group-chats/group-chat-1/messages",
            headers=_auth_headers_for_player("player-3"),
        )
        outsider_message_post = await client.post(
            "/api/v1/matches/match-alpha/group-chats/group-chat-1/messages",
            json={
                "match_id": "match-alpha",
                "tick": 142,
                "content": "Let me in.",
            },
            headers=_auth_headers_for_player("player-3"),
        )
        direct_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(
                channel="direct",
                recipient_id="player-1",
                content="Direct message still works.",
            ),
            headers=_auth_headers_for_player("player-2"),
        )

    assert create_response.status_code == HTTPStatus.ACCEPTED
    assert create_response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "group_chat": {
            "group_chat_id": "group-chat-1",
            "name": "War Council",
            "member_ids": ["player-1", "player-2", "player-4"],
            "created_by": "player-1",
            "created_tick": 142,
        },
    }
    assert creator_group_chats.status_code == HTTPStatus.OK
    assert creator_group_chats.json() == {
        "match_id": "match-alpha",
        "player_id": "player-1",
        "group_chats": [
            {
                "group_chat_id": "group-chat-1",
                "name": "War Council",
                "member_ids": ["player-1", "player-2", "player-4"],
                "created_by": "player-1",
                "created_tick": 142,
            }
        ],
    }
    assert invited_group_chats.status_code == HTTPStatus.OK
    assert invited_group_chats.json() == {
        "match_id": "match-alpha",
        "player_id": "player-2",
        "group_chats": [
            {
                "group_chat_id": "group-chat-1",
                "name": "War Council",
                "member_ids": ["player-1", "player-2", "player-4"],
                "created_by": "player-1",
                "created_tick": 142,
            }
        ],
    }
    assert outsider_group_chats.status_code == HTTPStatus.OK
    assert outsider_group_chats.json() == {
        "match_id": "match-alpha",
        "player_id": "player-3",
        "group_chats": [],
    }
    assert invited_message_response.status_code == HTTPStatus.ACCEPTED
    assert invited_message_response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "group_chat_id": "group-chat-1",
        "message": {
            "message_id": 0,
            "group_chat_id": "group-chat-1",
            "sender_id": "player-2",
            "tick": 142,
            "content": "Ready to coordinate.",
        },
    }
    assert creator_message_read.status_code == HTTPStatus.OK
    assert creator_message_read.json() == {
        "match_id": "match-alpha",
        "group_chat_id": "group-chat-1",
        "player_id": "player-1",
        "messages": [
            {
                "message_id": 0,
                "group_chat_id": "group-chat-1",
                "sender_id": "player-2",
                "tick": 142,
                "content": "Ready to coordinate.",
            }
        ],
    }
    assert outsider_message_read.status_code == HTTPStatus.FORBIDDEN
    assert outsider_message_read.json() == {
        "error": {
            "code": "group_chat_not_visible",
            "message": "Group chat 'group-chat-1' is not visible to player 'player-3'.",
        }
    }
    assert outsider_message_post.status_code == HTTPStatus.FORBIDDEN
    assert outsider_message_post.json() == outsider_message_read.json()
    assert direct_response.status_code == HTTPStatus.ACCEPTED
    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    assert len(record.messages) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "expected_error"),
    [
        (
            {
                "match_id": "match-alpha",
                "tick": 142,
                "name": "",
                "member_ids": ["player-2"],
            },
            {
                "code": "invalid_group_chat_name",
                "message": "Group chat name must be at least 1 character long.",
            },
        ),
        (
            {
                "match_id": "match-alpha",
                "tick": 142,
                "name": "War Council",
                "member_ids": [],
            },
            {
                "code": "invalid_group_chat_members",
                "message": "Group chat creation requires at least 1 invited member.",
            },
        ),
        (
            {
                "match_id": "match-alpha",
                "name": "War Council",
                "member_ids": ["player-2"],
            },
            {
                "code": "invalid_group_chat_request",
                "message": "Group chat request is missing required fields.",
            },
        ),
        (
            {
                "match_id": "match-alpha",
                "tick": "stale",
                "name": "War Council",
                "member_ids": ["player-2"],
            },
            {
                "code": "invalid_group_chat_request",
                "message": "Group chat request validation failed.",
            },
        ),
    ],
)
async def test_group_chat_creation_validation_errors_are_structured(
    app_client: AsyncClient,
    payload: dict[str, Any],
    expected_error: dict[str, str],
) -> None:
    async with app_client as client:
        response = await client.post(
            "/api/v1/matches/match-alpha/group-chats",
            json=payload,
            headers=_auth_headers_for_player("player-1"),
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json() == {"error": expected_error}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("route_match_id", "payload", "expected_status", "expected_error"),
    [
        (
            "match-missing",
            _group_chat_create_payload(match_id="match-missing"),
            HTTPStatus.NOT_FOUND,
            {
                "code": "match_not_found",
                "message": "Match 'match-missing' was not found.",
            },
        ),
        (
            "match-alpha",
            _group_chat_create_payload(match_id="match-beta"),
            HTTPStatus.BAD_REQUEST,
            {
                "code": "match_id_mismatch",
                "message": (
                    "Group chat payload match_id 'match-beta' does not match route "
                    "match 'match-alpha'."
                ),
            },
        ),
        (
            "match-alpha",
            _group_chat_create_payload(tick=141),
            HTTPStatus.BAD_REQUEST,
            {
                "code": "tick_mismatch",
                "message": (
                    "Group chat payload tick '141' does not match current match tick '142'."
                ),
            },
        ),
        (
            "match-alpha",
            _group_chat_create_payload(member_ids=["player-missing"]),
            HTTPStatus.NOT_FOUND,
            {
                "code": "player_not_found",
                "message": "Player 'player-missing' was not found in match 'match-alpha'.",
            },
        ),
    ],
)
async def test_group_chat_creation_rejects_invalid_route_contracts(
    app_client: AsyncClient,
    payload: dict[str, Any],
    route_match_id: str,
    expected_status: HTTPStatus,
    expected_error: dict[str, str],
) -> None:
    async with app_client as client:
        response = await client.post(
            f"/api/v1/matches/{route_match_id}/group-chats",
            json=payload,
            headers=_auth_headers_for_player("player-1"),
        )

    assert response.status_code == expected_status
    assert response.json() == {"error": expected_error}


@pytest.mark.asyncio
async def test_group_chat_message_routes_return_structured_validation_and_not_found_errors(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        create_response = await client.post(
            "/api/v1/matches/match-alpha/group-chats",
            json=_group_chat_create_payload(member_ids=["player-2"]),
            headers=_auth_headers_for_player("player-1"),
        )
        missing_match_read = await client.get(
            "/api/v1/matches/match-missing/group-chats/group-chat-1/messages",
            headers=_auth_headers_for_player("player-1"),
        )
        missing_match_post = await client.post(
            "/api/v1/matches/match-missing/group-chats/group-chat-1/messages",
            json={
                "match_id": "match-missing",
                "tick": 142,
                "content": "Still coordinating.",
            },
            headers=_auth_headers_for_player("player-1"),
        )
        mismatch_post = await client.post(
            "/api/v1/matches/match-alpha/group-chats/group-chat-1/messages",
            json={
                "match_id": "match-beta",
                "tick": 142,
                "content": "Wrong match id.",
            },
            headers=_auth_headers_for_player("player-1"),
        )
        stale_tick_post = await client.post(
            "/api/v1/matches/match-alpha/group-chats/group-chat-1/messages",
            json={
                "match_id": "match-alpha",
                "tick": 141,
                "content": "Out of date.",
            },
            headers=_auth_headers_for_player("player-1"),
        )
        empty_content_post = await client.post(
            "/api/v1/matches/match-alpha/group-chats/group-chat-1/messages",
            json={
                "match_id": "match-alpha",
                "tick": 142,
                "content": "",
            },
            headers=_auth_headers_for_player("player-1"),
        )
        missing_field_post = await client.post(
            "/api/v1/matches/match-alpha/group-chats/group-chat-1/messages",
            json={
                "match_id": "match-alpha",
                "content": "Missing tick.",
            },
            headers=_auth_headers_for_player("player-1"),
        )

    assert create_response.status_code == HTTPStatus.ACCEPTED
    assert missing_match_read.status_code == HTTPStatus.NOT_FOUND
    assert missing_match_read.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match 'match-missing' was not found.",
        }
    }
    assert missing_match_post.status_code == HTTPStatus.NOT_FOUND
    assert missing_match_post.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match 'match-missing' was not found.",
        }
    }
    assert mismatch_post.status_code == HTTPStatus.BAD_REQUEST
    assert mismatch_post.json() == {
        "error": {
            "code": "match_id_mismatch",
            "message": (
                "Group chat message payload match_id 'match-beta' does not match route "
                "match 'match-alpha'."
            ),
        }
    }
    assert stale_tick_post.status_code == HTTPStatus.BAD_REQUEST
    assert stale_tick_post.json() == {
        "error": {
            "code": "tick_mismatch",
            "message": "Message payload tick '141' does not match current match tick '142'.",
        }
    }
    assert empty_content_post.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert empty_content_post.json() == {
        "error": {
            "code": "invalid_message_content",
            "message": "Message content must be at least 1 character long.",
        }
    }
    assert missing_field_post.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert missing_field_post.json() == {
        "error": {
            "code": "invalid_group_chat_request",
            "message": "Group chat request is missing required fields.",
        }
    }


@pytest.mark.asyncio
async def test_post_messages_rejects_invalid_requests_without_mutating_message_history(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        unknown_match_response = await client.post(
            "/api/v1/matches/match-missing/messages",
            json=_message_payload(match_id="match-missing"),
            headers=_auth_headers_for_player("player-1"),
        )
        mismatch_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(match_id="match-beta"),
            headers=_auth_headers_for_player("player-1"),
        )
        unsupported_recipient_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(channel="direct", recipient_id="player-missing"),
            headers=_auth_headers_for_player("player-1"),
        )
        world_recipient_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(channel="world", recipient_id="player-2"),
            headers=_auth_headers_for_player("player-1"),
        )
        empty_content_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(content=""),
            headers=_auth_headers_for_player("player-1"),
        )
        missing_fields_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json={},
            headers=_auth_headers_for_player("player-1"),
        )

    assert unknown_match_response.status_code == HTTPStatus.NOT_FOUND
    assert mismatch_response.status_code == HTTPStatus.BAD_REQUEST
    assert unsupported_recipient_response.status_code == HTTPStatus.BAD_REQUEST
    assert world_recipient_response.status_code == HTTPStatus.BAD_REQUEST
    assert empty_content_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert empty_content_response.json() == {
        "error": {
            "code": "invalid_message_content",
            "message": "Message content must be at least 1 character long.",
        }
    }
    assert missing_fields_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert missing_fields_response.json() == {
        "error": {
            "code": "invalid_message_request",
            "message": "Message request is missing required fields.",
        }
    }
    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    assert record.messages == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_treaty_lifecycle_reads_are_deterministic_and_world_announcements_are_public(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        initial_read = await client.get(
            "/api/v1/matches/match-alpha/treaties",
            headers=_auth_headers_for_player("player-2"),
        )
        propose_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(counterparty_id="player-1"),
            headers=_auth_headers_for_player("player-2"),
        )
        after_propose_read = await client.get(
            "/api/v1/matches/match-alpha/treaties",
            headers=_auth_headers_for_player("player-2"),
        )
        accept_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(action="accept", counterparty_id="player-2"),
            headers=_auth_headers_for_player("player-1"),
        )
        withdraw_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(action="withdraw", counterparty_id="player-1"),
            headers=_auth_headers_for_player("player-2"),
        )
        final_read = await client.get(
            "/api/v1/matches/match-alpha/treaties",
            headers=_auth_headers_for_player("player-1"),
        )
        world_messages = await client.get(
            "/api/v1/matches/match-alpha/messages",
            headers=_auth_headers_for_player("player-4"),
        )

    assert initial_read.status_code == HTTPStatus.OK
    assert initial_read.json() == {"match_id": "match-alpha", "treaties": []}
    assert propose_response.status_code == HTTPStatus.ACCEPTED
    assert after_propose_read.status_code == HTTPStatus.OK
    assert after_propose_read.json()["treaties"][0]["status"] == "proposed"
    assert accept_response.status_code == HTTPStatus.ACCEPTED
    assert withdraw_response.status_code == HTTPStatus.ACCEPTED
    assert final_read.status_code == HTTPStatus.OK
    assert final_read.json() == {
        "match_id": "match-alpha",
        "treaties": [
            {
                "treaty_id": 0,
                "player_a_id": "player-1",
                "player_b_id": "player-2",
                "treaty_type": "trade",
                "status": "withdrawn",
                "proposed_by": "player-2",
                "proposed_tick": 142,
                "signed_tick": 142,
                "withdrawn_by": "player-2",
                "withdrawn_tick": 142,
            }
        ],
    }
    assert world_messages.status_code == HTTPStatus.OK
    assert world_messages.json()["messages"] == [
        {
            "message_id": 0,
            "channel": "world",
            "sender_id": "system",
            "recipient_id": None,
            "tick": 142,
            "content": "Treaty signed: player-1 and player-2 entered a trade treaty.",
        },
        {
            "message_id": 1,
            "channel": "world",
            "sender_id": "system",
            "recipient_id": None,
            "tick": 142,
            "content": "Treaty withdrawn: player-2 withdrew the trade treaty with player-1.",
        },
    ]


@pytest.mark.asyncio
async def test_automatic_treaty_breaks_surface_through_authenticated_reads(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    record.state.cities["birmingham"].owner = None
    record.state.players["player-2"].cities_owned = ["manchester"]
    record.state.players["player-3"].cities_owned = []
    army_a = next(army for army in record.state.armies if army.id == "army-a")
    army_a.location = "birmingham"
    army_a.destination = None
    army_a.path = None
    army_a.ticks_remaining = 0

    seeded_registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest.model_validate(_treaty_payload(counterparty_id="player-1")),
        player_id="player-2",
    )
    seeded_registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest.model_validate(
            _treaty_payload(action="accept", counterparty_id="player-2")
        ),
        player_id="player-1",
    )
    seeded_registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 142,
                "orders": {
                    "movements": [{"army_id": "army-b", "destination": "birmingham"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    seeded_registry.advance_match_tick("match-alpha")

    async with app_client as client:
        treaty_read = await client.get(
            "/api/v1/matches/match-alpha/treaties",
            headers=_auth_headers_for_player("player-1"),
        )
        briefing_read = await client.get(
            "/api/v1/matches/match-alpha/agent-briefing",
            headers=_auth_headers_for_player("player-2"),
        )
        world_messages = await client.get(
            "/api/v1/matches/match-alpha/messages",
            headers=_auth_headers_for_player("player-4"),
        )

    assert treaty_read.status_code == HTTPStatus.OK
    assert treaty_read.json() == {
        "match_id": "match-alpha",
        "treaties": [
            {
                "treaty_id": 0,
                "player_a_id": "player-1",
                "player_b_id": "player-2",
                "treaty_type": "trade",
                "status": "broken_by_a",
                "proposed_by": "player-2",
                "proposed_tick": 142,
                "signed_tick": 142,
                "withdrawn_by": "player-1",
                "withdrawn_tick": 142,
            }
        ],
    }
    assert briefing_read.status_code == HTTPStatus.OK
    assert briefing_read.json()["treaties"] == treaty_read.json()["treaties"]
    assert world_messages.status_code == HTTPStatus.OK
    assert world_messages.json()["messages"] == [
        {
            "message_id": 0,
            "channel": "world",
            "sender_id": "system",
            "recipient_id": None,
            "tick": 142,
            "content": "Treaty signed: player-1 and player-2 entered a trade treaty.",
        },
        {
            "message_id": 1,
            "channel": "world",
            "sender_id": "system",
            "recipient_id": None,
            "tick": 142,
            "content": "Treaty broken: player-1 attacked player-2 and broke their trade treaty.",
        },
    ]


@pytest.mark.asyncio
async def test_treaty_actions_reject_invalid_authenticated_requests(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        unknown_match_response = await client.post(
            "/api/v1/matches/match-missing/treaties",
            json=_treaty_payload(match_id="match-missing"),
            headers=_auth_headers_for_player("player-2"),
        )
        mismatch_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(match_id="match-beta"),
            headers=_auth_headers_for_player("player-2"),
        )
        unknown_counterparty_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(counterparty_id="player-missing"),
            headers=_auth_headers_for_player("player-2"),
        )
        self_target_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(counterparty_id="player-2"),
            headers=_auth_headers_for_player("player-2"),
        )
        invalid_action_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(action="sign"),
            headers=_auth_headers_for_player("player-2"),
        )

    assert unknown_match_response.status_code == HTTPStatus.NOT_FOUND
    assert mismatch_response.status_code == HTTPStatus.BAD_REQUEST
    assert unknown_counterparty_response.status_code == HTTPStatus.NOT_FOUND
    assert self_target_response.status_code == HTTPStatus.BAD_REQUEST
    assert invalid_action_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_alliance_lifecycle_reads_are_deterministic_and_update_membership(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        initial_read = await client.get(
            "/api/v1/matches/match-alpha/alliances",
            headers=_auth_headers_for_player("player-3"),
        )
        create_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(action="create", name="Northern Pact"),
            headers=_auth_headers_for_player("player-3"),
        )
        join_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(
                action="join",
                alliance_id="alliance-1",
                name=None,
            ),
            headers=_auth_headers_for_player("player-4"),
        )
        joined_read = await client.get(
            "/api/v1/matches/match-alpha/alliances",
            headers=_auth_headers_for_player("player-3"),
        )
        joined_state = await client.get(
            "/api/v1/matches/match-alpha/state",
            headers=_auth_headers_for_player("player-3"),
        )
        leave_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(action="leave", alliance_id=None, name=None),
            headers=_auth_headers_for_player("player-4"),
        )
        after_leave_read = await client.get(
            "/api/v1/matches/match-alpha/alliances",
            headers=_auth_headers_for_player("player-3"),
        )

    assert initial_read.status_code == HTTPStatus.OK
    assert create_response.status_code == HTTPStatus.ACCEPTED
    assert join_response.status_code == HTTPStatus.ACCEPTED
    assert joined_read.status_code == HTTPStatus.OK
    assert joined_read.json()["alliances"][0] == {
        "alliance_id": "alliance-1",
        "name": "Northern Pact",
        "leader_id": "player-3",
        "formed_tick": 142,
        "members": [
            {"player_id": "player-3", "joined_tick": 142},
            {"player_id": "player-4", "joined_tick": 142},
        ],
    }
    assert joined_state.status_code == HTTPStatus.OK
    assert joined_state.json()["alliance_id"] == "alliance-1"
    assert joined_state.json()["alliance_members"] == ["player-3", "player-4"]
    assert leave_response.status_code == HTTPStatus.ACCEPTED
    assert after_leave_read.status_code == HTTPStatus.OK
    assert after_leave_read.json()["alliances"][0] == {
        "alliance_id": "alliance-1",
        "name": "Northern Pact",
        "leader_id": "player-3",
        "formed_tick": 142,
        "members": [{"player_id": "player-3", "joined_tick": 142}],
    }


@pytest.mark.asyncio
async def test_agent_briefing_returns_current_state_and_incremental_message_and_treaty_buckets(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    record = seeded_registry.get_match("match-alpha")
    assert record is not None

    seeded_registry.record_message(
        match_id="match-alpha",
        message=MatchMessageCreateRequest.model_validate(
            _message_payload(tick=140, content="Old world intel.")
        ),
        sender_id="player-1",
    )
    seeded_registry.record_message(
        match_id="match-alpha",
        message=MatchMessageCreateRequest.model_validate(
            _message_payload(
                tick=142,
                channel="direct",
                recipient_id="player-2",
                content="Fresh direct ping.",
            ),
        ),
        sender_id="player-1",
    )
    seeded_registry.record_message(
        match_id="match-alpha",
        message=MatchMessageCreateRequest.model_validate(
            _message_payload(tick=142, content="Fresh world intel.")
        ),
        sender_id="player-3",
    )

    created_group_chat = seeded_registry.create_group_chat(
        match_id="match-alpha",
        request=GroupChatCreateRequest.model_validate(
            _group_chat_create_payload(tick=140, name="Northern Channel", member_ids=["player-1"])
        ),
        creator_id="player-2",
    )
    seeded_registry.record_group_chat_message(
        match_id="match-alpha",
        group_chat_id=created_group_chat.group_chat_id,
        message=GroupChatMessageCreateRequest(
            match_id="match-alpha",
            tick=140,
            content="Old group note.",
        ),
        sender_id="player-1",
    )
    seeded_registry.record_group_chat_message(
        match_id="match-alpha",
        group_chat_id=created_group_chat.group_chat_id,
        message=GroupChatMessageCreateRequest(
            match_id="match-alpha",
            tick=142,
            content="Fresh group note.",
        ),
        sender_id="player-2",
    )

    original_tick = record.state.tick
    record.state.tick = 140
    seeded_registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest.model_validate(_treaty_payload(counterparty_id="player-3")),
        player_id="player-2",
    )
    record.state.tick = 142
    seeded_registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest.model_validate(
            _treaty_payload(action="accept", counterparty_id="player-2")
        ),
        player_id="player-3",
    )
    record.state.tick = original_tick

    async with app_client as client:
        response = await client.get(
            "/api/v1/matches/match-alpha/agent-briefing?since_tick=142",
            headers=_auth_headers_for_player("player-2"),
        )

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["match_id"] == "match-alpha"
    assert payload["player_id"] == "player-2"
    assert payload["state"]["match_id"] == "match-alpha"
    assert payload["state"]["tick"] == 142
    assert payload["state"]["player_id"] == "player-2"
    assert payload["alliances"] == [
        {
            "alliance_id": "alliance-red",
            "name": "alliance-red",
            "leader_id": "player-1",
            "formed_tick": 142,
            "members": [
                {"player_id": "player-1", "joined_tick": 142},
                {"player_id": "player-2", "joined_tick": 142},
            ],
        }
    ]
    assert payload["group_chats"] == [
        {
            "group_chat_id": "group-chat-1",
            "name": "Northern Channel",
            "member_ids": ["player-1", "player-2"],
            "created_by": "player-2",
            "created_tick": 140,
        }
    ]
    assert payload["treaties"] == [
        {
            "treaty_id": 0,
            "player_a_id": "player-2",
            "player_b_id": "player-3",
            "treaty_type": "trade",
            "status": "active",
            "proposed_by": "player-2",
            "proposed_tick": 140,
            "signed_tick": 142,
            "withdrawn_by": None,
            "withdrawn_tick": None,
        }
    ]
    assert payload["messages"]["direct"][0]["recipient_id"] == "player-2"
    assert _briefing_message_contents(payload, "direct") == ["Fresh direct ping."]
    assert _briefing_message_contents(payload, "group") == ["Fresh group note."]
    assert _briefing_message_contents(payload, "world") == [
        "Fresh world intel.",
        "Treaty signed: player-2 and player-3 entered a trade treaty.",
    ]
    assert payload["guidance"] == []


@pytest.mark.asyncio
async def test_agent_briefing_returns_owned_guidance_separately_from_message_buckets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-briefing-guidance.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        guidance_write = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/guidance",
            json=_owned_agent_guidance_payload(
                match_id="00000000-0000-0000-0000-000000000101",
                tick=142,
                content="Guard Edinburgh while the southern army rotates west.",
            ),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )
        briefing_read = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agent-briefing?since_tick=142",
            headers=_auth_headers_for_player("player-2"),
        )

    assert guidance_write.status_code == HTTPStatus.ACCEPTED
    assert briefing_read.status_code == HTTPStatus.OK
    payload = briefing_read.json()
    assert _briefing_guidance_contents(payload) == [
        "Guard Edinburgh while the southern army rotates west."
    ]
    assert payload["guidance"][0]["tick"] == 142
    assert payload["guidance"][0]["created_at"]
    assert _briefing_message_contents(payload, "direct") == []
    assert _briefing_message_contents(payload, "group") == []
    assert _briefing_message_contents(payload, "world") == []


@pytest.mark.asyncio
async def test_agent_briefing_keeps_guidance_empty_when_agent_owner_cannot_be_resolved_from_db(
    tmp_path: Path,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-briefing-no-owner-guidance.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    app = _build_authenticated_access_test_app(
        registry=seeded_registry,
        history_database_url=database_url,
        include_session_factory=False,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        briefing_read = await client.get(
            "/api/v1/matches/match-alpha/agent-briefing?since_tick=142",
            headers=_auth_headers_for_player("player-1"),
        )

    assert briefing_read.status_code == HTTPStatus.OK
    assert briefing_read.json()["guidance"] == []


@pytest.mark.asyncio
async def test_owned_agent_routes_support_db_url_fallback_without_session_factory(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'owned-agent-db-url-fallback.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    registry = load_match_registry_from_database(database_url)
    app = _build_authenticated_access_test_app(
        registry=registry,
        history_database_url=database_url,
        include_session_factory=False,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        guidance_write = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agents/agent-player-2/guidance",
            json=_owned_agent_guidance_payload(
                match_id="00000000-0000-0000-0000-000000000101",
                tick=142,
                content="Fallback session factory path still persists owner guidance.",
            ),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
        )
        briefing_read = await client.get(
            "/api/v1/matches/00000000-0000-0000-0000-000000000101/agent-briefing?since_tick=142",
            headers=_auth_headers_for_player("player-2"),
        )

    assert guidance_write.status_code == HTTPStatus.ACCEPTED
    assert guidance_write.json()["player_id"] == "player-2"
    assert briefing_read.status_code == HTTPStatus.OK
    assert _briefing_guidance_contents(briefing_read.json()) == [
        "Fallback session factory path still persists owner guidance."
    ]


@pytest.mark.asyncio
async def test_agent_briefing_matches_missing_and_unjoined_error_contracts(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        missing_match_response = await client.get(
            "/api/v1/matches/match-missing/agent-briefing",
            headers=_auth_headers_for_player("player-1"),
        )
        unjoined_response = await client.get(
            "/api/v1/matches/match-beta/agent-briefing",
            headers=_auth_headers_for_agent("agent-player-3"),
        )

    assert missing_match_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_match_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match 'match-missing' was not found.",
        }
    }
    assert unjoined_response.status_code == HTTPStatus.BAD_REQUEST
    assert unjoined_response.json() == {
        "error": {
            "code": "agent_not_joined",
            "message": "Agent 'agent-player-3' has not joined match 'match-beta' as a player.",
        }
    }


@pytest.mark.asyncio
async def test_alliance_actions_reject_invalid_authenticated_requests(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        unknown_match_response = await client.post(
            "/api/v1/matches/match-missing/alliances",
            json=_alliance_payload(match_id="match-missing"),
            headers=_auth_headers_for_player("player-3"),
        )
        mismatch_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(match_id="match-beta"),
            headers=_auth_headers_for_player("player-3"),
        )
        invalid_action_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(action="invite"),
            headers=_auth_headers_for_player("player-3"),
        )

    assert unknown_match_response.status_code == HTTPStatus.NOT_FOUND
    assert mismatch_response.status_code == HTTPStatus.BAD_REQUEST
    assert invalid_action_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_join_match_assigns_deterministic_slot_and_returns_idempotent_result(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        first_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(),
            headers=_auth_headers_for_agent("agent-player-2"),
        )
        repeat_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(),
            headers=_auth_headers_for_agent("agent-player-2"),
        )
        second_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(),
            headers=_auth_headers_for_agent("agent-player-3"),
        )

    assert first_response.status_code == HTTPStatus.ACCEPTED
    assert first_response.json() == {
        "status": "accepted",
        "match_id": "match-beta",
        "agent_id": "agent-player-2",
        "player_id": "player-1",
    }
    assert repeat_response.status_code == HTTPStatus.ACCEPTED
    assert repeat_response.json() == first_response.json()
    assert second_response.status_code == HTTPStatus.ACCEPTED
    assert second_response.json() == {
        "status": "accepted",
        "match_id": "match-beta",
        "agent_id": "agent-player-3",
        "player_id": "player-2",
    }


@pytest.mark.asyncio
async def test_create_match_lobby_route_creates_browseable_lobby_and_creator_membership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-create-match-lobby.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    engine = create_engine(database_url)
    fresh_api_key = "fresh-create-lobby-key"
    fresh_api_key_id = "11111111-1111-1111-1111-111111111198"
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO api_keys (
                    id, user_id, key_hash, elo_rating, is_active, created_at
                ) VALUES (
                    :id, :user_id, :key_hash, :elo_rating, :is_active, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": fresh_api_key_id,
                "user_id": "11111111-1111-1111-1111-111111111398",
                "key_hash": hash_api_key(fresh_api_key),
                "elo_rating": 1111,
                "is_active": True,
            },
        )
    insert_agent_entitlement_grant(
        database_url=database_url,
        grant_id="11111111-1111-1111-1111-111111111498",
        user_id="11111111-1111-1111-1111-111111111398",
        grant_source="manual",
        concurrent_match_allowance=1,
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers={"X-API-Key": fresh_api_key},
        )

        assert create_response.status_code == HTTPStatus.CREATED
        created_payload = create_response.json()

        browse_response = await client.get("/api/v1/matches")
        detail_response = await client.get(f"/api/v1/matches/{created_payload['match_id']}")
        state_response = await client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers={"X-API-Key": fresh_api_key},
        )

    reloaded_app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=reloaded_app),
        base_url="http://testserver",
    ) as client:
        reloaded_state_response = await client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers={"X-API-Key": fresh_api_key},
        )

    expected_agent_id = f"agent-api-key-{fresh_api_key_id}"
    assert created_payload == {
        "match_id": created_payload["match_id"],
        "status": "lobby",
        "map": "britain",
        "tick": 0,
        "tick_interval_seconds": 20,
        "current_player_count": 1,
        "max_player_count": 4,
        "open_slot_count": 3,
        "creator_player_id": "player-1",
    }
    assert browse_response.status_code == HTTPStatus.OK
    assert browse_response.json()["matches"][0] == {
        "match_id": created_payload["match_id"],
        "status": "lobby",
        "map": "britain",
        "tick": 0,
        "tick_interval_seconds": 20,
        "current_player_count": 1,
        "max_player_count": 4,
        "open_slot_count": 3,
    }
    assert detail_response.status_code == HTTPStatus.OK
    assert detail_response.json() == {
        "match_id": created_payload["match_id"],
        "status": "lobby",
        "map": "britain",
        "tick": 0,
        "tick_interval_seconds": 20,
        "current_player_count": 1,
        "max_player_count": 4,
        "open_slot_count": 3,
        "roster": [
            {
                "player_id": "player-1",
                "display_name": "Agent 11111111",
                "competitor_kind": "agent",
                "agent_id": expected_agent_id,
                "human_id": None,
            }
        ],
    }
    assert "api_key" not in detail_response.text.lower()
    assert state_response.status_code == HTTPStatus.OK
    assert state_response.json()["match_id"] == created_payload["match_id"]
    assert state_response.json()["player_id"] == "player-1"
    assert reloaded_state_response.status_code == HTTPStatus.OK
    assert reloaded_state_response.json()["match_id"] == created_payload["match_id"]
    assert reloaded_state_response.json()["player_id"] == "player-1"
    reloaded_match = reloaded_app.state.match_registry.get_match(created_payload["match_id"])
    assert reloaded_match is not None
    assert reloaded_match.joined_agents == {expected_agent_id: "player-1"}
    reloaded_profile = reloaded_app.state.match_registry.get_agent_profile(expected_agent_id)
    assert reloaded_profile is not None
    assert reloaded_profile.display_name == "Agent 11111111"


@pytest.mark.asyncio
async def test_create_match_lobby_route_allows_first_time_valid_db_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-create-match-lobby-fresh-key.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    engine = create_engine(database_url)
    fresh_api_key = "fresh-db-agent-key"
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO api_keys (
                    id, user_id, key_hash, elo_rating, is_active, created_at
                ) VALUES (
                    :id, :user_id, :key_hash, :elo_rating, :is_active, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": "00000000-0000-0000-0000-000000000299",
                "user_id": "00000000-0000-0000-0000-000000000399",
                "key_hash": hash_api_key(fresh_api_key),
                "elo_rating": 1111,
                "is_active": True,
            },
        )
    insert_agent_entitlement_grant(
        database_url=database_url,
        grant_id="00000000-0000-0000-0000-000000000399",
        user_id="00000000-0000-0000-0000-000000000399",
        grant_source="manual",
        concurrent_match_allowance=1,
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers={"X-API-Key": fresh_api_key},
        )
        created_payload = create_response.json()
        state_response = await client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers={"X-API-Key": fresh_api_key},
        )
        profile_response = await client.get(
            "/api/v1/agent/profile",
            headers={"X-API-Key": fresh_api_key},
        )

    assert create_response.status_code == HTTPStatus.CREATED
    assert created_payload["creator_player_id"] == "player-1"
    assert state_response.status_code == HTTPStatus.OK
    assert state_response.json()["player_id"] == "player-1"
    assert profile_response.status_code == HTTPStatus.OK
    assert (
        profile_response.json()["agent_id"] == "agent-api-key-00000000-0000-0000-0000-000000000299"
    )


@pytest.mark.asyncio
async def test_create_match_lobby_route_rejects_agent_api_key_at_occupancy_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-create-occupancy-limit.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers=_auth_headers_for_agent("agent-player-2"),
        )
        browse_response = await client.get("/api/v1/matches")

    assert create_response.status_code == HTTPStatus.CONFLICT
    assert create_response.json() == {
        "error": {
            "code": "api_key_match_occupancy_limit_reached",
            "message": "API key already occupies the maximum number of lobby or active matches.",
        }
    }
    assert len(browse_response.json()["matches"]) == 2


@pytest.mark.asyncio
async def test_create_match_lobby_route_rejects_agent_api_key_without_positive_entitlement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-create-entitlement-required.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_agent_entitlement_grant(
        database_url=database_url,
        grant_id="00000000-0000-0000-0000-000000009901",
        user_id="00000000-0000-0000-0000-000000000304",
        grant_source="manual",
        concurrent_match_allowance=0,
    )
    insert_api_key(
        database_url=database_url,
        api_key_id="00000000-0000-0000-0000-000000009902",
        user_id="00000000-0000-0000-0000-000000000304",
        raw_api_key="iron_zero_capacity_create_key",
        elo_rating=1188,
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers={"X-API-Key": "iron_zero_capacity_create_key"},
        )

    assert create_response.status_code == HTTPStatus.FORBIDDEN
    assert create_response.json() == {
        "error": {
            "code": "agent_entitlement_required",
            "message": (
                "Authenticated account lacks an active agent entitlement grant with positive "
                "concurrent match allowance."
            ),
        }
    }


@pytest.mark.asyncio
async def test_human_lobby_routes_accept_valid_bearer_for_create_join_and_creator_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'human-lobby-routes.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000304"),
        )
        created_payload = create_response.json()

        join_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/join",
            json=_join_payload(match_id=created_payload["match_id"]),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000301"),
        )
        start_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/start",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000304"),
        )
        creator_state_response = await client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000304"),
        )
        joined_state_response = await client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000301"),
        )

    reloaded_app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=reloaded_app),
        base_url="http://testserver",
    ) as client:
        reloaded_creator_state_response = await client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000304"),
        )

    assert create_response.status_code == HTTPStatus.CREATED
    assert created_payload == {
        "match_id": created_payload["match_id"],
        "status": "lobby",
        "map": "britain",
        "tick": 0,
        "tick_interval_seconds": 20,
        "current_player_count": 1,
        "max_player_count": 4,
        "open_slot_count": 3,
        "creator_player_id": "player-1",
    }
    assert join_response.status_code == HTTPStatus.ACCEPTED
    assert join_response.json() == {
        "status": "accepted",
        "match_id": created_payload["match_id"],
        "agent_id": "human:00000000-0000-0000-0000-000000000301",
        "player_id": "player-2",
    }
    assert start_response.status_code == HTTPStatus.OK
    assert start_response.json() == {
        "match_id": created_payload["match_id"],
        "status": "active",
        "map": "britain",
        "tick": 0,
        "tick_interval_seconds": 20,
        "current_player_count": 2,
        "max_player_count": 4,
        "open_slot_count": 2,
    }
    assert creator_state_response.status_code == HTTPStatus.OK
    assert creator_state_response.json()["player_id"] == "player-1"
    assert joined_state_response.status_code == HTTPStatus.OK
    assert joined_state_response.json()["player_id"] == "player-2"
    assert reloaded_creator_state_response.status_code == HTTPStatus.OK
    assert reloaded_creator_state_response.json()["player_id"] == "player-1"
    reloaded_match = reloaded_app.state.match_registry.get_match(created_payload["match_id"])
    assert reloaded_match is not None
    assert reloaded_match.joined_humans == {
        "00000000-0000-0000-0000-000000000301": "player-2",
        "00000000-0000-0000-0000-000000000304": "player-1",
    }


@pytest.mark.asyncio
async def test_create_match_lobby_route_rejects_invalid_requests_without_partial_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-create-match-lobby-errors.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        unsupported_map_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "mediterranean",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers=_auth_headers_for_agent("agent-player-2"),
        )
        impossible_config_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 20,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 3,
            },
            headers=_auth_headers_for_agent("agent-player-2"),
        )
        browse_response = await client.get("/api/v1/matches")

    assert unsupported_map_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert unsupported_map_response.json() == {
        "error": {
            "code": "invalid_match_map",
            "message": "Match map must be 'britain'.",
        }
    }
    assert impossible_config_response.status_code == HTTPStatus.BAD_REQUEST
    assert impossible_config_response.json()["error"]["code"] == "invalid_match_lobby_config"
    assert "cannot assign" in impossible_config_response.json()["error"]["message"]
    assert len(browse_response.json()["matches"]) == 2


@pytest.mark.asyncio
async def test_create_match_lobby_route_rejects_missing_auth_and_memory_mode() -> None:
    memory_registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        memory_registry.seed_match(record)
    memory_app = create_app(match_registry=memory_registry)

    async with AsyncClient(
        transport=ASGITransport(app=memory_app),
        base_url="http://testserver",
    ) as client:
        missing_auth_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
        )
        unavailable_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers=_auth_headers_for_agent("agent-player-2"),
        )

    assert missing_auth_response.status_code == HTTPStatus.UNAUTHORIZED
    assert missing_auth_response.json() == {
        "error": {
            "code": "invalid_api_key",
            "message": "A valid active X-API-Key header is required.",
        }
    }
    assert unavailable_response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert unavailable_response.json() == {
        "error": {
            "code": "match_lobby_creation_unavailable",
            "message": "Authenticated match lobby creation is only available in DB-backed mode.",
        }
    }


@pytest.mark.asyncio
async def test_start_match_lobby_route_transitions_ready_creator_lobby_to_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-start-match-lobby.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    creator_api_key = "api-route-start-creator-key"
    creator_api_key_id = "11111111-1111-1111-1111-111111111118"
    insert_api_key(
        database_url=database_url,
        api_key_id=creator_api_key_id,
        user_id="11111111-1111-1111-1111-111111111308",
        raw_api_key=creator_api_key,
        elo_rating=1111,
    )
    insert_agent_entitlement_grant(
        database_url=database_url,
        grant_id="11111111-1111-1111-1111-111111111408",
        user_id="11111111-1111-1111-1111-111111111308",
        grant_source="manual",
        concurrent_match_allowance=1,
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers={"X-API-Key": creator_api_key},
        )
        created_payload = create_response.json()

        insert_seeded_agent_player(
            database_url=database_url,
            match_id=created_payload["match_id"],
            agent_id="agent-player-3",
            persisted_player_id=build_persisted_player_id(
                match_id=created_payload["match_id"],
                public_player_id="player-2",
            ),
        )

        start_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/start",
            headers={"X-API-Key": creator_api_key},
        )
        browse_response = await client.get("/api/v1/matches")
        detail_response = await client.get(f"/api/v1/matches/{created_payload['match_id']}")
        state_response = await client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers={"X-API-Key": creator_api_key},
        )

    assert create_response.status_code == HTTPStatus.CREATED
    assert start_response.status_code == HTTPStatus.OK
    assert start_response.json() == {
        "match_id": created_payload["match_id"],
        "status": "active",
        "map": "britain",
        "tick": 0,
        "tick_interval_seconds": 20,
        "current_player_count": 2,
        "max_player_count": 4,
        "open_slot_count": 2,
    }
    assert browse_response.status_code == HTTPStatus.OK
    assert browse_response.json()["matches"][0] == start_response.json()
    assert detail_response.status_code == HTTPStatus.OK
    assert detail_response.json() == {
        **start_response.json(),
        "roster": [
            {
                "player_id": "player-1",
                "display_name": build_non_seeded_display_name(creator_api_key_id),
                "competitor_kind": "agent",
                "agent_id": f"agent-api-key-{creator_api_key_id}",
                "human_id": None,
            },
            {
                "player_id": "player-2",
                "display_name": "Gawain",
                "competitor_kind": "agent",
                "agent_id": "agent-player-3",
                "human_id": None,
            },
        ],
    }
    assert state_response.status_code == HTTPStatus.OK
    assert state_response.json()["match_id"] == created_payload["match_id"]
    assert state_response.json()["player_id"] == "player-1"

    started_record = app.state.match_registry.get_match(created_payload["match_id"])
    assert started_record is not None
    assert started_record.status == MatchStatus.ACTIVE
    assert started_record.joinable_player_ids == []


@pytest.mark.asyncio
async def test_start_match_lobby_route_rejects_missing_auth_and_memory_mode() -> None:
    memory_registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        memory_registry.seed_match(record)
    memory_app = create_app(match_registry=memory_registry)

    async with AsyncClient(
        transport=ASGITransport(app=memory_app),
        base_url="http://testserver",
    ) as client:
        missing_auth_response = await client.post("/api/v1/matches/match-alpha/start")
        unavailable_response = await client.post(
            "/api/v1/matches/match-alpha/start",
            headers=_auth_headers_for_agent("agent-player-2"),
        )

    assert missing_auth_response.status_code == HTTPStatus.UNAUTHORIZED
    assert missing_auth_response.json() == {
        "error": {
            "code": "invalid_api_key",
            "message": "A valid active X-API-Key header is required.",
        }
    }
    assert unavailable_response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert unavailable_response.json() == {
        "error": {
            "code": "match_lobby_start_unavailable",
            "message": "Authenticated lobby start is only available in DB-backed mode.",
        }
    }


@pytest.mark.asyncio
async def test_start_match_lobby_route_rejects_non_creator_not_ready_and_terminal_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-start-match-lobby-errors.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    creator_api_key = "api-route-start-errors-key"
    second_creator_api_key = "api-route-start-errors-key-2"
    third_creator_api_key = "api-route-start-errors-key-3"
    fourth_creator_api_key = "api-route-start-errors-key-4"
    insert_api_key(
        database_url=database_url,
        api_key_id="11111111-1111-1111-1111-111111111119",
        user_id="11111111-1111-1111-1111-111111111309",
        raw_api_key=creator_api_key,
        elo_rating=1111,
    )
    insert_agent_entitlement_grant(
        database_url=database_url,
        grant_id="11111111-1111-1111-1111-111111111409",
        user_id="11111111-1111-1111-1111-111111111309",
        grant_source="manual",
        concurrent_match_allowance=1,
    )
    insert_api_key(
        database_url=database_url,
        api_key_id="11111111-1111-1111-1111-111111111121",
        user_id="11111111-1111-1111-1111-111111111321",
        raw_api_key=second_creator_api_key,
        elo_rating=1111,
    )
    insert_agent_entitlement_grant(
        database_url=database_url,
        grant_id="11111111-1111-1111-1111-111111111421",
        user_id="11111111-1111-1111-1111-111111111321",
        grant_source="manual",
        concurrent_match_allowance=1,
    )
    insert_api_key(
        database_url=database_url,
        api_key_id="11111111-1111-1111-1111-111111111122",
        user_id="11111111-1111-1111-1111-111111111322",
        raw_api_key=third_creator_api_key,
        elo_rating=1111,
    )
    insert_agent_entitlement_grant(
        database_url=database_url,
        grant_id="11111111-1111-1111-1111-111111111422",
        user_id="11111111-1111-1111-1111-111111111322",
        grant_source="manual",
        concurrent_match_allowance=1,
    )
    insert_api_key(
        database_url=database_url,
        api_key_id="11111111-1111-1111-1111-111111111123",
        user_id="11111111-1111-1111-1111-111111111323",
        raw_api_key=fourth_creator_api_key,
        elo_rating=1111,
    )
    insert_agent_entitlement_grant(
        database_url=database_url,
        grant_id="11111111-1111-1111-1111-111111111423",
        user_id="11111111-1111-1111-1111-111111111323",
        grant_source="manual",
        concurrent_match_allowance=1,
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()
    engine = create_engine(database_url)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        not_ready_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers={"X-API-Key": second_creator_api_key},
        )
        not_ready_start = await client.post(
            f"/api/v1/matches/{not_ready_response.json()['match_id']}/start",
            headers={"X-API-Key": second_creator_api_key},
        )

        outsider_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers={"X-API-Key": third_creator_api_key},
        )
        insert_seeded_agent_player(
            database_url=database_url,
            match_id=outsider_response.json()["match_id"],
            agent_id="agent-player-3",
            persisted_player_id=build_persisted_player_id(
                match_id=outsider_response.json()["match_id"],
                public_player_id="player-2",
            ),
        )
        outsider_start = await client.post(
            f"/api/v1/matches/{outsider_response.json()['match_id']}/start",
            headers=_auth_headers_for_agent("agent-player-3"),
        )

        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO api_keys (
                        id, user_id, key_hash, elo_rating, is_active, created_at
                    ) VALUES (
                        :id, :user_id, :key_hash, :elo_rating, :is_active, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": "00000000-0000-0000-0000-000000000298",
                    "user_id": "11111111-1111-1111-1111-111111111322",
                    "key_hash": hash_api_key("sibling-morgana-key"),
                    "elo_rating": 1190,
                    "is_active": True,
                },
            )
        sibling_key_start = await client.post(
            f"/api/v1/matches/{outsider_response.json()['match_id']}/start",
            headers={"X-API-Key": "sibling-morgana-key"},
        )

        active_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers={"X-API-Key": creator_api_key},
        )
        insert_seeded_agent_player(
            database_url=database_url,
            match_id=active_response.json()["match_id"],
            agent_id="agent-player-3",
            persisted_player_id=build_persisted_player_id(
                match_id=active_response.json()["match_id"],
                public_player_id="player-2",
            ),
        )
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE matches SET status = :status WHERE id = :match_id"),
                {"status": "active", "match_id": active_response.json()["match_id"]},
            )
        active_start = await client.post(
            f"/api/v1/matches/{active_response.json()['match_id']}/start",
            headers={"X-API-Key": creator_api_key},
        )

        completed_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers={"X-API-Key": fourth_creator_api_key},
        )
        insert_seeded_agent_player(
            database_url=database_url,
            match_id=completed_response.json()["match_id"],
            agent_id="agent-player-3",
            persisted_player_id=build_persisted_player_id(
                match_id=completed_response.json()["match_id"],
                public_player_id="player-2",
            ),
        )
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE matches SET status = :status WHERE id = :match_id"),
                {"status": "completed", "match_id": completed_response.json()["match_id"]},
            )
        completed_start = await client.post(
            f"/api/v1/matches/{completed_response.json()['match_id']}/start",
            headers={"X-API-Key": fourth_creator_api_key},
        )

    assert not_ready_start.status_code == HTTPStatus.CONFLICT
    assert not_ready_start.json() == {
        "error": {
            "code": "match_lobby_not_ready",
            "message": (
                f"Match '{not_ready_response.json()['match_id']}' needs at least 2 joined players "
                "before it can start."
            ),
        }
    }
    assert outsider_start.status_code == HTTPStatus.FORBIDDEN
    assert outsider_start.json() == {
        "error": {
            "code": "match_start_forbidden",
            "message": (
                f"Authenticated agent does not own lobby '{outsider_response.json()['match_id']}'."
            ),
        }
    }
    assert sibling_key_start.status_code == HTTPStatus.FORBIDDEN
    assert sibling_key_start.json() == outsider_start.json()
    assert active_start.status_code == HTTPStatus.CONFLICT
    assert active_start.json() == {
        "error": {
            "code": "match_already_active",
            "message": f"Match '{active_response.json()['match_id']}' is already active.",
        }
    }
    assert completed_start.status_code == HTTPStatus.CONFLICT
    assert completed_start.json() == {
        "error": {
            "code": "match_already_completed",
            "message": f"Match '{completed_response.json()['match_id']}' is already completed.",
        }
    }


@pytest.mark.asyncio
async def test_start_match_lobby_route_rejects_missing_match_and_paused_lobby(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-start-match-lobby-extra-errors.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    creator_api_key = "api-route-start-paused-key"
    insert_api_key(
        database_url=database_url,
        api_key_id="11111111-1111-1111-1111-111111111120",
        user_id="11111111-1111-1111-1111-111111111310",
        raw_api_key=creator_api_key,
        elo_rating=1111,
    )
    insert_agent_entitlement_grant(
        database_url=database_url,
        grant_id="11111111-1111-1111-1111-111111111410",
        user_id="11111111-1111-1111-1111-111111111310",
        grant_source="manual",
        concurrent_match_allowance=1,
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()
    engine = create_engine(database_url)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        missing_match_response = await client.post(
            "/api/v1/matches/00000000-0000-0000-0000-000000009999/start",
            headers=_auth_headers_for_agent("agent-player-2"),
        )
        create_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers={"X-API-Key": creator_api_key},
        )
        created_payload = create_response.json()
        insert_seeded_agent_player(
            database_url=database_url,
            match_id=created_payload["match_id"],
            agent_id="agent-player-3",
            persisted_player_id=build_persisted_player_id(
                match_id=created_payload["match_id"],
                public_player_id="player-2",
            ),
        )
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE matches SET status = :status WHERE id = :match_id"),
                {"status": "paused", "match_id": created_payload["match_id"]},
            )
        paused_match_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/start",
            headers={"X-API-Key": creator_api_key},
        )

    assert missing_match_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_match_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match '00000000-0000-0000-0000-000000009999' was not found.",
        }
    }
    assert paused_match_response.status_code == HTTPStatus.CONFLICT
    assert paused_match_response.json() == {
        "error": {
            "code": "match_not_startable",
            "message": (
                f"Match '{created_payload['match_id']}' cannot be started from status 'paused'."
            ),
        }
    }


@pytest.mark.asyncio
async def test_human_lobby_routes_reject_invalid_auth_non_creator_and_not_ready_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'human-lobby-route-errors.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        missing_create_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
        )
        invalid_create_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers={"Authorization": "Bearer not-a-jwt"},
        )

        create_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000304"),
        )
        created_payload = create_response.json()

        missing_join_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/join",
            json=_join_payload(match_id=created_payload["match_id"]),
        )
        invalid_join_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/join",
            json=_join_payload(match_id=created_payload["match_id"]),
            headers={"Authorization": "Token nope"},
        )
        not_ready_start_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/start",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000304"),
        )

        join_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/join",
            json=_join_payload(match_id=created_payload["match_id"]),
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000301"),
        )
        non_creator_start_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/start",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000301"),
        )

    assert create_response.status_code == HTTPStatus.CREATED
    assert missing_create_response.status_code == HTTPStatus.UNAUTHORIZED
    assert missing_create_response.json() == {
        "error": {
            "code": "invalid_player_auth",
            "message": "Player routes require a valid Bearer token or active X-API-Key header.",
        }
    }
    assert invalid_create_response.status_code == HTTPStatus.UNAUTHORIZED
    assert invalid_create_response.json() == {
        "error": {
            "code": "invalid_human_token",
            "message": "A valid human Bearer token is required.",
        }
    }
    assert missing_join_response.status_code == HTTPStatus.UNAUTHORIZED
    assert missing_join_response.json() == missing_create_response.json()
    assert invalid_join_response.status_code == HTTPStatus.UNAUTHORIZED
    assert invalid_join_response.json() == invalid_create_response.json()
    assert not_ready_start_response.status_code == HTTPStatus.CONFLICT
    assert not_ready_start_response.json() == {
        "error": {
            "code": "match_lobby_not_ready",
            "message": (
                f"Match '{created_payload['match_id']}' needs at least 2 joined players "
                "before it can start."
            ),
        }
    }
    assert join_response.status_code == HTTPStatus.ACCEPTED
    assert non_creator_start_response.status_code == HTTPStatus.FORBIDDEN
    assert non_creator_start_response.json() == {
        "error": {
            "code": "match_start_forbidden",
            "message": (f"Authenticated human does not own lobby '{created_payload['match_id']}'."),
        }
    }


@pytest.mark.asyncio
async def test_join_match_rejects_invalid_authenticated_requests(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        missing_auth_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(),
        )
        invalid_auth_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(),
            headers={"X-API-Key": "invalid-key"},
        )
        unknown_match_response = await client.post(
            "/api/v1/matches/match-missing/join",
            json=_join_payload(match_id="match-missing"),
            headers=_auth_headers_for_agent("agent-player-2"),
        )
        mismatch_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(match_id="match-alpha"),
            headers=_auth_headers_for_agent("agent-player-2"),
        )

    assert missing_auth_response.status_code == HTTPStatus.UNAUTHORIZED
    assert invalid_auth_response.status_code == HTTPStatus.UNAUTHORIZED
    assert unknown_match_response.status_code == HTTPStatus.NOT_FOUND
    assert mismatch_response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
async def test_authenticated_write_routes_keep_api_key_precedence_over_human_bearer_auth(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    order_payload = deepcopy(representative_order_payload)
    order_payload["match_id"] = "match-alpha"
    order_payload["tick"] = 142
    order_payload.pop("player_id", None)
    headers = {
        "X-API-Key": "invalid-key",
        **_auth_headers_for_human("00000000-0000-0000-0000-000000000302"),
    }
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        join_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(),
            headers=headers,
        )
        order_response = await client.post(
            "/api/v1/matches/match-alpha/orders",
            json=order_payload,
            headers=headers,
        )

    expected_error = {
        "error": {
            "code": "invalid_api_key",
            "message": "A valid active X-API-Key header is required.",
        }
    }
    assert join_response.status_code == HTTPStatus.UNAUTHORIZED
    assert join_response.json() == expected_error
    assert order_response.status_code == HTTPStatus.UNAUTHORIZED
    assert order_response.json() == expected_error
    assert _match_state_dump(seeded_registry) == before_state
    assert seeded_registry.list_order_submissions("match-alpha") == []


@pytest.mark.asyncio
async def test_join_match_persists_db_backed_lobby_membership_and_remains_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-join-match-lobby.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    engine = create_engine(database_url)
    creator_api_key = "fresh-join-creator-key"
    joiner_api_key = "fresh-join-member-key"
    creator_api_key_id = "22222222-2222-2222-2222-222222222201"
    joiner_api_key_id = "33333333-3333-3333-3333-333333333201"
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO api_keys (
                    id, user_id, key_hash, elo_rating, is_active, created_at
                ) VALUES (
                    :id, :user_id, :key_hash, :elo_rating, :is_active, CURRENT_TIMESTAMP
                )
                """
            ),
            [
                {
                    "id": creator_api_key_id,
                    "user_id": "22222222-2222-2222-2222-222222222301",
                    "key_hash": hash_api_key(creator_api_key),
                    "elo_rating": 1111,
                    "is_active": True,
                },
                {
                    "id": joiner_api_key_id,
                    "user_id": "33333333-3333-3333-3333-333333333301",
                    "key_hash": hash_api_key(joiner_api_key),
                    "elo_rating": 1222,
                    "is_active": True,
                },
            ],
        )
    insert_agent_entitlement_grant(
        database_url=database_url,
        grant_id="22222222-2222-2222-2222-222222222401",
        user_id="22222222-2222-2222-2222-222222222301",
        grant_source="manual",
        concurrent_match_allowance=1,
    )
    insert_agent_entitlement_grant(
        database_url=database_url,
        grant_id="33333333-3333-3333-3333-333333333401",
        user_id="33333333-3333-3333-3333-333333333301",
        grant_source="manual",
        concurrent_match_allowance=1,
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers={"X-API-Key": creator_api_key},
        )
        created_payload = create_response.json()

        join_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/join",
            json=_join_payload(match_id=created_payload["match_id"]),
            headers={"X-API-Key": joiner_api_key},
        )
        repeat_join_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/join",
            json=_join_payload(match_id=created_payload["match_id"]),
            headers={"X-API-Key": joiner_api_key},
        )
        start_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/start",
            headers={"X-API-Key": creator_api_key},
        )

    reloaded_app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=reloaded_app),
        base_url="http://testserver",
    ) as client:
        joined_state_response = await client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers={"X-API-Key": joiner_api_key},
        )

    assert create_response.status_code == HTTPStatus.CREATED
    assert join_response.status_code == HTTPStatus.ACCEPTED
    assert join_response.json() == {
        "status": "accepted",
        "match_id": created_payload["match_id"],
        "agent_id": f"agent-api-key-{joiner_api_key_id}",
        "player_id": "player-2",
    }
    assert repeat_join_response.status_code == HTTPStatus.ACCEPTED
    assert repeat_join_response.json() == join_response.json()
    assert start_response.status_code == HTTPStatus.OK
    assert start_response.json()["status"] == "active"
    assert start_response.json()["current_player_count"] == 2
    assert joined_state_response.status_code == HTTPStatus.OK
    assert joined_state_response.json()["player_id"] == "player-2"


@pytest.mark.asyncio
async def test_join_match_rejects_agent_api_key_at_occupancy_limit_and_recovers_after_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-join-occupancy-limit.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000304"),
        )
        created_payload = create_response.json()

        blocked_join_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/join",
            json=_join_payload(match_id=created_payload["match_id"]),
            headers=_auth_headers_for_agent("agent-player-2"),
        )

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE matches
                SET status = 'completed'
                WHERE id = :match_id
                """
            ),
            {"match_id": "00000000-0000-0000-0000-000000000101"},
        )

    reloaded_app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=reloaded_app),
        base_url="http://testserver",
    ) as client:
        recovered_join_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/join",
            json=_join_payload(match_id=created_payload["match_id"]),
            headers=_auth_headers_for_agent("agent-player-2"),
        )
        state_response = await client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers=_auth_headers_for_agent("agent-player-2"),
        )

    assert create_response.status_code == HTTPStatus.CREATED
    assert blocked_join_response.status_code == HTTPStatus.CONFLICT
    assert blocked_join_response.json() == {
        "error": {
            "code": "api_key_match_occupancy_limit_reached",
            "message": "API key already occupies the maximum number of lobby or active matches.",
        }
    }
    assert recovered_join_response.status_code == HTTPStatus.ACCEPTED
    assert recovered_join_response.json() == {
        "status": "accepted",
        "match_id": created_payload["match_id"],
        "agent_id": "agent-player-2",
        "player_id": "player-2",
    }
    assert state_response.status_code == HTTPStatus.OK
    assert state_response.json()["player_id"] == "player-2"


@pytest.mark.asyncio
async def test_join_match_rejects_agent_api_key_without_positive_entitlement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-api-join-entitlement-required.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    insert_agent_entitlement_grant(
        database_url=database_url,
        grant_id="00000000-0000-0000-0000-000000009903",
        user_id="00000000-0000-0000-0000-000000000304",
        grant_source="manual",
        concurrent_match_allowance=0,
    )
    insert_api_key(
        database_url=database_url,
        api_key_id="00000000-0000-0000-0000-000000009904",
        user_id="00000000-0000-0000-0000-000000000304",
        raw_api_key="iron_zero_capacity_join_key",
        elo_rating=1188,
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000301"),
        )
        created_payload = create_response.json()
        join_response = await client.post(
            f"/api/v1/matches/{created_payload['match_id']}/join",
            json=_join_payload(match_id=created_payload["match_id"]),
            headers={"X-API-Key": "iron_zero_capacity_join_key"},
        )

    assert create_response.status_code == HTTPStatus.CREATED
    assert join_response.status_code == HTTPStatus.FORBIDDEN
    assert join_response.json() == {
        "error": {
            "code": "agent_entitlement_required",
            "message": (
                "Authenticated account lacks an active agent entitlement grant with positive "
                "concurrent match allowance."
            ),
        }
    }


@pytest.mark.asyncio
async def test_authenticated_match_access_derives_joined_player_and_rejects_unjoined(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    order_payload = deepcopy(representative_order_payload)
    order_payload["match_id"] = "match-beta"
    order_payload["tick"] = 7
    order_payload["orders"] = {
        **order_payload["orders"],
        "movements": [],
        "recruitment": [],
        "upgrades": [],
        "transfers": [],
    }
    order_payload.pop("player_id", None)
    before_state = _match_state_dump(seeded_registry, "match-beta")

    async with app_client as client:
        join_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(),
            headers=_auth_headers_for_agent("agent-player-2"),
        )
        state_response = await client.get(
            "/api/v1/matches/match-beta/state",
            headers=_auth_headers_for_agent("agent-player-2"),
        )
        order_response = await client.post(
            "/api/v1/matches/match-beta/orders",
            json=order_payload,
            headers=_auth_headers_for_agent("agent-player-2"),
        )
        message_response = await client.post(
            "/api/v1/matches/match-beta/messages",
            json=_message_payload(match_id="match-beta", tick=7, content="Open channel."),
            headers=_auth_headers_for_agent("agent-player-2"),
        )
        unjoined_state_response = await client.get(
            "/api/v1/matches/match-beta/state",
            headers=_auth_headers_for_agent("agent-player-3"),
        )

    assert join_response.status_code == HTTPStatus.ACCEPTED
    assert state_response.status_code == HTTPStatus.OK
    assert state_response.json()["player_id"] == "player-1"
    assert order_response.status_code == HTTPStatus.ACCEPTED
    assert order_response.json()["player_id"] == "player-1"
    assert seeded_registry.list_order_submissions("match-beta") == [
        {
            **order_payload,
            "player_id": "player-1",
        }
    ]
    assert message_response.status_code == HTTPStatus.ACCEPTED
    assert message_response.json()["sender_id"] == "player-1"
    assert unjoined_state_response.status_code == HTTPStatus.BAD_REQUEST
    assert unjoined_state_response.json() == {
        "error": {
            "code": "agent_not_joined",
            "message": "Agent 'agent-player-3' has not joined match 'match-beta' as a player.",
        }
    }
    assert _match_state_dump(seeded_registry, "match-beta") == before_state


@pytest.mark.asyncio
async def test_authenticated_match_access_surfaces_structured_route_and_transition_errors(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    fresh_agent_id = "agent-fresh"
    fresh_agent_key = build_seeded_agent_api_key(fresh_agent_id)
    seeded_registry.seed_authenticated_agent_key(
        AuthenticatedAgentContext(
            agent_id=fresh_agent_id,
            display_name="Fresh Agent",
            is_seeded=False,
        ),
        key_hash=hash_api_key(fresh_agent_key),
    )

    async with app_client as client:
        non_joinable_join_response = await client.post(
            "/api/v1/matches/match-alpha/join",
            json={"match_id": "match-alpha"},
            headers={"X-API-Key": fresh_agent_key},
        )
        missing_state_response = await client.get(
            "/api/v1/matches/match-missing/state",
            headers=_auth_headers_for_player("player-1"),
        )
        missing_messages_response = await client.get(
            "/api/v1/matches/match-missing/messages",
            headers=_auth_headers_for_player("player-1"),
        )
        stale_message_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(tick=141, content="Too late."),
            headers=_auth_headers_for_player("player-1"),
        )
        missing_treaties_response = await client.get(
            "/api/v1/matches/match-missing/treaties",
            headers=_auth_headers_for_player("player-1"),
        )
        treaty_transition_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(
                counterparty_id="player-2",
                action="accept",
                treaty_type="trade",
            ),
            headers=_auth_headers_for_player("player-1"),
        )
        missing_alliances_response = await client.get(
            "/api/v1/matches/match-missing/alliances",
            headers=_auth_headers_for_player("player-1"),
        )
        alliance_transition_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(
                action="leave",
                alliance_id=None,
                name=None,
            ),
            headers=_auth_headers_for_player("player-5"),
        )

    assert non_joinable_join_response.status_code == HTTPStatus.BAD_REQUEST
    assert non_joinable_join_response.json() == {
        "error": {
            "code": "match_not_joinable",
            "message": "Match 'match-alpha' does not support agent joins.",
        }
    }
    assert missing_state_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_state_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match 'match-missing' was not found.",
        }
    }
    assert missing_messages_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_messages_response.json() == missing_state_response.json()
    assert stale_message_response.status_code == HTTPStatus.BAD_REQUEST
    assert stale_message_response.json() == {
        "error": {
            "code": "tick_mismatch",
            "message": "Message payload tick '141' does not match current match tick '142'.",
        }
    }
    assert missing_treaties_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_treaties_response.json() == missing_state_response.json()
    assert treaty_transition_response.status_code == HTTPStatus.BAD_REQUEST
    assert treaty_transition_response.json() == {
        "error": {
            "code": "unsupported_treaty_transition",
            "message": "Cannot accept treaty 'trade' for players 'player-1' and 'player-2'.",
        }
    }
    assert missing_alliances_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_alliances_response.json() == missing_state_response.json()
    assert alliance_transition_response.status_code == HTTPStatus.BAD_REQUEST
    assert alliance_transition_response.json() == {
        "error": {
            "code": "player_not_in_alliance",
            "message": "Player 'player-5' is not currently in an alliance.",
        }
    }


@pytest.mark.asyncio
async def test_authenticated_match_routes_map_validation_failures_to_structured_errors(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        missing_message_field_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json={
                "match_id": "match-alpha",
                "tick": 142,
                "channel": "world",
                "recipient_id": None,
            },
            headers=_auth_headers_for_player("player-1"),
        )
        missing_treaty_field_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json={"match_id": "match-alpha", "counterparty_id": "player-2"},
            headers=_auth_headers_for_player("player-1"),
        )
        invalid_treaty_type_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json={
                "match_id": "match-alpha",
                "counterparty_id": "player-2",
                "action": "propose",
                "treaty_type": "peace",
            },
            headers=_auth_headers_for_player("player-1"),
        )
        missing_alliance_field_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json={"match_id": "match-alpha"},
            headers=_auth_headers_for_player("player-1"),
        )
        invalid_alliance_action_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json={"match_id": "match-alpha", "action": "merge"},
            headers=_auth_headers_for_player("player-1"),
        )
        create_with_alliance_id_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(
                action="create",
                alliance_id="alliance-red",
                name="Northern Pact",
            ),
            headers=_auth_headers_for_player("player-1"),
        )
        create_without_name_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(
                action="create",
                alliance_id=None,
                name=None,
            ),
            headers=_auth_headers_for_player("player-1"),
        )
        join_without_alliance_id_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(
                action="join",
                alliance_id=None,
                name=None,
            ),
            headers=_auth_headers_for_player("player-5"),
        )
        join_with_name_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(
                action="join",
                alliance_id="alliance-red",
                name="Nope",
            ),
            headers=_auth_headers_for_player("player-5"),
        )
        leave_with_alliance_id_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(
                action="leave",
                alliance_id="alliance-red",
                name=None,
            ),
            headers=_auth_headers_for_player("player-5"),
        )
        leave_with_name_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(
                action="leave",
                alliance_id=None,
                name="Nope",
            ),
            headers=_auth_headers_for_player("player-5"),
        )
        missing_join_field_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json={},
            headers=_auth_headers_for_agent("agent-player-2"),
        )
    assert missing_message_field_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert missing_message_field_response.json() == {
        "error": {
            "code": "invalid_message_request",
            "message": "Message request is missing required fields.",
        }
    }
    assert missing_treaty_field_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert missing_treaty_field_response.json() == {
        "error": {
            "code": "invalid_treaty_request",
            "message": "Treaty request is missing required fields.",
        }
    }
    assert invalid_treaty_type_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert invalid_treaty_type_response.json() == {
        "error": {
            "code": "invalid_treaty_type",
            "message": "Treaty type must be one of: non_aggression, defensive, trade.",
        }
    }
    assert missing_alliance_field_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert missing_alliance_field_response.json() == {
        "error": {
            "code": "invalid_alliance_request",
            "message": "Alliance request is missing required fields.",
        }
    }
    assert invalid_alliance_action_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert invalid_alliance_action_response.json() == {
        "error": {
            "code": "invalid_alliance_action",
            "message": "Alliance action must be one of: create, join, leave.",
        }
    }
    assert create_with_alliance_id_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert create_with_alliance_id_response.json() == {
        "error": {
            "code": "invalid_alliance_request",
            "message": "Alliance create does not accept alliance_id.",
        }
    }
    assert create_without_name_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert create_without_name_response.json() == {
        "error": {
            "code": "invalid_alliance_request",
            "message": "Alliance create requires name.",
        }
    }
    assert join_without_alliance_id_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert join_without_alliance_id_response.json() == {
        "error": {
            "code": "invalid_alliance_request",
            "message": "Alliance join requires alliance_id.",
        }
    }
    assert join_with_name_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert join_with_name_response.json() == {
        "error": {
            "code": "invalid_alliance_request",
            "message": "Alliance join does not accept name.",
        }
    }
    assert leave_with_alliance_id_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert leave_with_alliance_id_response.json() == {
        "error": {
            "code": "invalid_alliance_request",
            "message": "Alliance leave does not accept alliance_id.",
        }
    }
    assert leave_with_name_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert leave_with_name_response.json() == {
        "error": {
            "code": "invalid_alliance_request",
            "message": "Alliance leave does not accept name.",
        }
    }
    assert missing_join_field_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert missing_join_field_response.json() == {
        "error": {
            "code": "invalid_join_request",
            "message": "Join request is missing required fields.",
        }
    }


@pytest.mark.asyncio
async def test_openapi_declares_secured_match_route_contracts(app_client: AsyncClient) -> None:
    async with app_client as client:
        response = await client.get("/openapi.json")

    assert response.status_code == HTTPStatus.OK
    paths = response.json()["paths"]
    assert paths["/api/v1/agent/profile"]["get"]["responses"]["401"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/state"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/AgentStateProjection"}
    assert paths["/api/v1/matches/{match_id}/agent-briefing"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/AgentBriefingResponse"}
    assert paths["/api/v1/matches/{match_id}/agents/{agent_id}/guided-session"]["get"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/OwnedAgentGuidedSessionResponse"
    }
    assert paths["/api/v1/matches/{match_id}/agents/{agent_id}/override"]["post"]["responses"][
        "202"
    ]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/OwnedAgentOverrideAcceptanceResponse"
    }
    assert paths["/api/v1/matches/{match_id}/orders"]["post"]["responses"]["202"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/OrderAcceptanceResponse"}
    assert paths["/api/v1/matches/{match_id}/command"]["post"]["responses"]["401"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert "/api/v1/matches/{match_id}/commands" not in paths
    assert paths["/api/v1/matches/{match_id}/treaties"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/TreatyListResponse"}
    assert paths["/api/v1/matches/{match_id}/treaties"]["post"]["responses"]["202"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/TreatyActionAcceptanceResponse"}
    assert paths["/api/v1/matches/{match_id}/alliances"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/AllianceListResponse"}
    assert paths["/api/v1/matches/{match_id}/alliances"]["post"]["responses"]["202"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/AllianceActionAcceptanceResponse"}
    assert paths["/api/v1/matches/{match_id}/messages"]["post"]["responses"]["401"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}


@pytest.mark.asyncio
async def test_orders_only_command_envelope_does_not_broadcast_match_refresh(
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    broadcasted_match_ids: list[str] = []
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(
        build_authenticated_match_router(
            match_registry_provider=lambda: seeded_registry,
            app_services=AppServices(
                settings=get_settings(
                    env={
                        "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
                        "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
                        "HUMAN_JWT_AUDIENCE": "authenticated",
                        "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
                    }
                ),
                history_database_url=None,
            ),
            broadcast_current_match=lambda match_id: _record_broadcast(
                broadcasted_match_ids=broadcasted_match_ids,
                match_id=match_id,
            ),
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/matches/match-alpha/command",
            json=_command_envelope_payload(
                orders={
                    "movements": [{"army_id": "army-b", "destination": "birmingham"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                }
            ),
            headers=_auth_headers_for_player("player-2"),
        )

    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "player_id": "player-2",
        "tick": 142,
        "orders": {
            "status": "accepted",
            "match_id": "match-alpha",
            "player_id": "player-2",
            "tick": 142,
            "submission_index": 0,
        },
        "messages": [],
        "treaties": [],
        "alliance": None,
    }
    assert broadcasted_match_ids == []


def test_server_api_modules_expose_extracted_route_seams() -> None:
    errors = importlib.import_module("server.api.errors")
    public_history_routes = importlib.import_module("server.api.public_history_routes")
    public_routes = importlib.import_module("server.api.public_routes")
    public_summary_routes = importlib.import_module("server.api.public_summary_routes")
    realtime_routes = importlib.import_module("server.api.realtime_routes")

    assert hasattr(errors, "ApiError")
    assert hasattr(errors, "register_error_handlers")
    assert hasattr(public_history_routes, "build_public_history_router")
    assert hasattr(public_routes, "build_public_api_router")
    assert hasattr(public_summary_routes, "build_public_summary_router")
    assert hasattr(realtime_routes, "register_realtime_routes")


@pytest.mark.asyncio
async def test_openapi_declares_public_read_contracts(app_client: AsyncClient) -> None:
    async with app_client as client:
        root_response = await client.get("/")
        health_response = await client.get("/health")
        openapi_response = await client.get("/openapi.json")

    assert root_response.status_code == HTTPStatus.OK
    assert root_response.json()["service"] == "iron-council-server"
    assert root_response.json()["status"] == "ok"
    assert root_response.json()["version"]

    assert health_response.status_code == HTTPStatus.OK
    assert health_response.json() == {"status": "ok"}

    assert openapi_response.status_code == HTTPStatus.OK
    paths = openapi_response.json()["paths"]
    assert paths["/api/v1/matches"]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/MatchListResponse"}
    assert paths["/api/v1/leaderboard"]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/PublicLeaderboardResponse"}
    leaderboard_entry_schema = openapi_response.json()["components"]["schemas"]["LeaderboardEntry"]
    assert leaderboard_entry_schema["properties"]["agent_id"] == {
        "anyOf": [{"type": "string"}, {"type": "null"}],
        "title": "Agent Id",
    }
    assert leaderboard_entry_schema["properties"]["human_id"] == {
        "anyOf": [{"type": "string"}, {"type": "null"}],
        "title": "Human Id",
    }
    assert paths["/api/v1/humans/{human_id}/profile"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/HumanProfileResponse"}
    assert paths["/api/v1/humans/{human_id}/profile"]["get"]["responses"]["404"] == {
        "description": "Not Found",
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/ApiErrorResponse"}}
        },
    }
    assert paths["/api/v1/humans/{human_id}/profile"]["get"]["responses"]["503"] == {
        "description": "Service Unavailable",
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/ApiErrorResponse"}}
        },
    }
    assert paths["/api/v1/matches/completed"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/CompletedMatchSummaryListResponse"}
    assert paths["/api/v1/matches/{match_id}"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/PublicMatchDetailResponse"}
    assert paths["/api/v1/matches/{match_id}/history"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/MatchHistoryResponse"}
    assert paths["/api/v1/matches/{match_id}/history/{tick}"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/MatchReplayTickResponse"}


def test_match_websocket_registers_player_connection_and_sends_initial_fog_filtered_payload(
    websocket_app: FastAPI,
    websocket_client: TestClient,
) -> None:
    manager = websocket_app.state.match_websocket_manager

    with websocket_client.websocket_connect(
        "/ws/match/match-alpha?viewer=player"
        f"&token={_human_jwt_token(user_id='00000000-0000-0000-0000-000000000302')}"
    ) as websocket:
        payload = websocket.receive_json()

        assert payload["type"] == "tick_update"
        assert payload["data"]["viewer_role"] == "player"
        assert payload["data"]["player_id"] == "player-2"
        assert payload["data"]["state"]["match_id"] == "match-alpha"
        assert payload["data"]["state"]["cities"]["manchester"]["visibility"] == "full"
        assert payload["data"]["state"]["cities"]["birmingham"]["visibility"] == "partial"
        assert payload["data"]["state"]["cities"]["birmingham"]["garrison"] == "unknown"
        assert payload["data"]["direct_messages"] == []
        assert payload["data"]["group_chats"] == []
        assert payload["data"]["group_messages"] == []
        assert payload["data"]["alliances"] == [
            {
                "alliance_id": "alliance-red",
                "name": "alliance-red",
                "leader_id": "player-1",
                "formed_tick": 142,
                "members": [
                    {"player_id": "player-1", "joined_tick": 142},
                    {"player_id": "player-2", "joined_tick": 142},
                ],
            }
        ]
        assert manager.connection_count("match-alpha") == 1


def test_legacy_match_websocket_route_preserves_initial_envelope_contract(
    websocket_client: TestClient,
) -> None:
    with websocket_client.websocket_connect(
        "/ws/matches/match-alpha?viewer=player"
        f"&token={_human_jwt_token(user_id='00000000-0000-0000-0000-000000000302')}"
    ) as websocket:
        payload = websocket.receive_json()

    assert payload["type"] == "tick_update"
    assert payload["data"]["viewer_role"] == "player"
    assert payload["data"]["player_id"] == "player-2"
    assert payload["data"]["state"]["match_id"] == "match-alpha"


def test_match_websocket_registers_spectator_connection_and_sends_full_visibility_payload(
    seeded_registry: InMemoryMatchRegistry,
    websocket_client: TestClient,
) -> None:
    seeded_registry.record_message(
        match_id="match-alpha",
        message=MatchMessageCreateRequest.model_validate(
            _message_payload(
                tick=142,
                channel="direct",
                recipient_id="player-2",
                content="Fresh direct ping.",
            )
        ),
        sender_id="player-1",
    )
    created_group_chat = seeded_registry.create_group_chat(
        match_id="match-alpha",
        request=GroupChatCreateRequest.model_validate(
            _group_chat_create_payload(member_ids=["player-2"])
        ),
        creator_id="player-1",
    )
    seeded_registry.record_group_chat_message(
        match_id="match-alpha",
        group_chat_id=created_group_chat.group_chat_id,
        message=GroupChatMessageCreateRequest(
            match_id="match-alpha",
            tick=142,
            content="Fresh group note.",
        ),
        sender_id="player-2",
    )
    with websocket_client.websocket_connect("/ws/match/match-alpha?viewer=spectator") as websocket:
        payload = websocket.receive_json()

    assert payload["type"] == "tick_update"
    assert payload["data"]["viewer_role"] == "spectator"
    assert payload["data"]["player_id"] is None
    assert payload["data"]["state"]["match_id"] == "match-alpha"
    assert payload["data"]["state"]["cities"]["birmingham"]["garrison"] == 7
    assert payload["data"]["state"]["players"]["player-2"]["resources"]["money"] == 110
    assert payload["data"]["state"]["armies"][0]["id"] == "army-a"
    assert payload["data"]["direct_messages"] == [
        {
            "message_id": 0,
            "channel": "direct",
            "sender_id": "player-1",
            "recipient_id": "player-2",
            "tick": 142,
            "content": "Fresh direct ping.",
        }
    ]
    assert payload["data"]["group_chats"] == [
        {
            "group_chat_id": "group-chat-1",
            "name": "War Council",
            "member_ids": ["player-1", "player-2"],
            "created_by": "player-1",
            "created_tick": 142,
        }
    ]
    assert payload["data"]["group_messages"] == [
        {
            "message_id": 0,
            "group_chat_id": "group-chat-1",
            "sender_id": "player-2",
            "tick": 142,
            "content": "Fresh group note.",
        }
    ]


def test_match_websocket_unregisters_connection_on_disconnect(
    websocket_app: FastAPI,
    websocket_client: TestClient,
) -> None:
    manager = websocket_app.state.match_websocket_manager

    with websocket_client.websocket_connect("/ws/match/match-alpha?viewer=spectator"):
        assert manager.connection_count("match-alpha") == 1

    assert manager.connection_count("match-alpha") == 0


def test_match_websocket_rejects_player_connection_when_api_key_does_not_match_player(
    websocket_client: TestClient,
) -> None:
    with websocket_client.websocket_connect(
        "/ws/match/match-alpha?viewer=player"
        "&token="
        + _human_jwt_token(
            user_id="00000000-0000-0000-0000-000000000302",
            role="service_role",
        )
    ) as websocket:
        assert websocket.receive_json() == {
            "error": {
                "code": "invalid_websocket_auth",
                "message": "Human JWT role claim must be 'authenticated'.",
            }
        }
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_match_websocket_rejects_player_connection_without_required_auth_query_params(
    websocket_client: TestClient,
) -> None:
    with websocket_client.websocket_connect(
        "/ws/match/match-alpha?viewer=player&player_id=player-2"
    ) as websocket:
        assert websocket.receive_json() == {
            "error": {
                "code": "invalid_websocket_auth",
                "message": (
                    "Player websocket connections require a valid human JWT token query parameter."
                ),
            }
        }
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_match_websocket_resolves_player_from_canonical_token_without_player_id(
    websocket_client: TestClient,
) -> None:
    with websocket_client.websocket_connect(
        "/ws/match/match-alpha?viewer=player"
        f"&token={_human_jwt_token(user_id='00000000-0000-0000-0000-000000000302')}"
    ) as websocket:
        payload = websocket.receive_json()

    assert payload["type"] == "tick_update"
    assert payload["data"]["viewer_role"] == "player"
    assert payload["data"]["player_id"] == "player-2"


def test_db_backed_human_state_and_websocket_resolution_share_player_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'human-state-websocket-resolution.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")
    monkeypatch.setenv("HUMAN_JWT_SECRET", "test-human-secret-key-material-1234")
    monkeypatch.setenv("HUMAN_JWT_ISSUER", "https://supabase.test/auth/v1")
    monkeypatch.setenv("HUMAN_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("HUMAN_JWT_REQUIRED_ROLE", "authenticated")

    app = create_app()
    with TestClient(app, base_url="http://testserver") as client:
        create_response = client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000304"),
        )
        assert create_response.status_code == HTTPStatus.CREATED
        created_payload = create_response.json()

        state_response = client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers=_auth_headers_for_human("00000000-0000-0000-0000-000000000304"),
        )
        assert state_response.status_code == HTTPStatus.OK

        with client.websocket_connect(
            "/ws/match/"
            f"{created_payload['match_id']}?viewer=player"
            f"&token={_human_jwt_token(user_id='00000000-0000-0000-0000-000000000304')}"
        ) as websocket:
            payload = websocket.receive_json()

    assert state_response.json()["player_id"] == "player-1"
    assert payload["type"] == "tick_update"
    assert payload["data"]["viewer_role"] == "player"
    assert payload["data"]["player_id"] == state_response.json()["player_id"]
    assert payload["data"]["state"]["player_id"] == state_response.json()["player_id"]


def test_match_websocket_rejects_invalid_and_wrong_role_human_tokens(
    websocket_client: TestClient,
) -> None:
    with websocket_client.websocket_connect(
        "/ws/match/match-alpha?viewer=player&token=not-a-jwt"
    ) as websocket:
        assert websocket.receive_json() == {
            "error": {
                "code": "invalid_websocket_auth",
                "message": "A valid human Bearer token is required.",
            }
        }
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()

    with websocket_client.websocket_connect(
        "/ws/match/match-alpha?viewer=player"
        "&token="
        + _human_jwt_token(
            user_id="00000000-0000-0000-0000-000000000302",
            role="service_role",
        )
    ) as websocket:
        assert websocket.receive_json() == {
            "error": {
                "code": "invalid_websocket_auth",
                "message": "Human JWT role claim must be 'authenticated'.",
            }
        }
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_match_websocket_rejects_invalid_viewer_and_unknown_match(
    websocket_client: TestClient,
) -> None:
    with pytest.raises(WebSocketDisconnect):
        with websocket_client.websocket_connect("/ws/match/match-alpha?viewer=marshal"):
            pass

    with pytest.raises(WebSocketDisconnect):
        with websocket_client.websocket_connect("/ws/match/match-missing?viewer=spectator"):
            pass


def test_world_message_broadcasts_refresh_to_connected_player_and_spectator(
    websocket_client: TestClient,
) -> None:
    with (
        websocket_client.websocket_connect(
            "/ws/match/match-alpha?viewer=player"
            f"&token={_human_jwt_token(user_id='00000000-0000-0000-0000-000000000302')}"
        ) as player_socket,
        websocket_client.websocket_connect(
            "/ws/match/match-alpha?viewer=spectator"
        ) as spectator_socket,
    ):
        player_socket.receive_json()
        spectator_socket.receive_json()

        response = websocket_client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(content="War drums.", channel="world"),
            headers=_auth_headers_for_player("player-2"),
        )

        player_update = player_socket.receive_json()
        spectator_update = spectator_socket.receive_json()

    assert response.status_code == HTTPStatus.ACCEPTED
    assert player_update["data"]["world_messages"][-1]["content"] == "War drums."
    assert spectator_update["data"]["world_messages"][-1]["content"] == "War drums."


def test_private_chat_events_broadcast_refresh_with_full_spectator_visibility(
    websocket_client: TestClient,
) -> None:
    with (
        websocket_client.websocket_connect(
            "/ws/match/match-alpha?viewer=player"
            f"&token={_human_jwt_token(user_id='00000000-0000-0000-0000-000000000301')}"
        ) as player_one_socket,
        websocket_client.websocket_connect(
            "/ws/match/match-alpha?viewer=player"
            f"&token={_human_jwt_token(user_id='00000000-0000-0000-0000-000000000302')}"
        ) as player_two_socket,
        websocket_client.websocket_connect(
            "/ws/match/match-alpha?viewer=spectator"
        ) as spectator_socket,
    ):
        player_one_socket.receive_json()
        player_two_socket.receive_json()
        spectator_socket.receive_json()

        direct_response = websocket_client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(
                channel="direct",
                recipient_id="player-2",
                content="Quiet flank update.",
            ),
            headers=_auth_headers_for_player("player-1"),
        )

        player_one_direct_update = player_one_socket.receive_json()
        player_two_direct_update = player_two_socket.receive_json()
        spectator_direct_update = spectator_socket.receive_json()

        create_response = websocket_client.post(
            "/api/v1/matches/match-alpha/group-chats",
            json=_group_chat_create_payload(member_ids=["player-2"]),
            headers=_auth_headers_for_player("player-1"),
        )

        player_one_group_create_update = player_one_socket.receive_json()
        player_two_group_create_update = player_two_socket.receive_json()
        spectator_group_create_update = spectator_socket.receive_json()

        group_message_response = websocket_client.post(
            "/api/v1/matches/match-alpha/group-chats/group-chat-1/messages",
            json={
                "match_id": "match-alpha",
                "tick": 142,
                "content": "Advance at dawn.",
            },
            headers=_auth_headers_for_player("player-2"),
        )

        player_one_group_message_update = player_one_socket.receive_json()
        player_two_group_message_update = player_two_socket.receive_json()
        spectator_group_message_update = spectator_socket.receive_json()

    assert direct_response.status_code == HTTPStatus.ACCEPTED
    assert (
        player_one_direct_update["data"]["direct_messages"][-1]["content"] == "Quiet flank update."
    )
    assert (
        player_two_direct_update["data"]["direct_messages"][-1]["content"] == "Quiet flank update."
    )
    assert (
        spectator_direct_update["data"]["direct_messages"][-1]["content"] == "Quiet flank update."
    )

    assert create_response.status_code == HTTPStatus.ACCEPTED
    assert player_one_group_create_update["data"]["group_chats"] == [
        {
            "group_chat_id": "group-chat-1",
            "name": "War Council",
            "member_ids": ["player-1", "player-2"],
            "created_by": "player-1",
            "created_tick": 142,
        }
    ]
    assert player_two_group_create_update["data"]["group_chats"] == [
        {
            "group_chat_id": "group-chat-1",
            "name": "War Council",
            "member_ids": ["player-1", "player-2"],
            "created_by": "player-1",
            "created_tick": 142,
        }
    ]
    assert spectator_group_create_update["data"]["group_chats"] == [
        {
            "group_chat_id": "group-chat-1",
            "name": "War Council",
            "member_ids": ["player-1", "player-2"],
            "created_by": "player-1",
            "created_tick": 142,
        }
    ]

    assert group_message_response.status_code == HTTPStatus.ACCEPTED
    assert player_one_group_message_update["data"]["group_messages"] == [
        {
            "message_id": 0,
            "group_chat_id": "group-chat-1",
            "sender_id": "player-2",
            "tick": 142,
            "content": "Advance at dawn.",
        }
    ]
    assert player_two_group_message_update["data"]["group_messages"] == [
        {
            "message_id": 0,
            "group_chat_id": "group-chat-1",
            "sender_id": "player-2",
            "tick": 142,
            "content": "Advance at dawn.",
        }
    ]
    assert spectator_group_message_update["data"]["group_messages"] == [
        {
            "message_id": 0,
            "group_chat_id": "group-chat-1",
            "sender_id": "player-2",
            "tick": 142,
            "content": "Advance at dawn.",
        }
    ]


def test_command_envelope_message_writes_broadcast_private_chat_refresh(
    websocket_client: TestClient,
) -> None:
    websocket_client.post(
        "/api/v1/matches/match-alpha/group-chats",
        json=_group_chat_create_payload(member_ids=["player-2"]),
        headers=_auth_headers_for_player("player-1"),
    )

    with (
        websocket_client.websocket_connect(
            "/ws/match/match-alpha?viewer=player"
            f"&token={_human_jwt_token(user_id='00000000-0000-0000-0000-000000000301')}"
        ) as player_one_socket,
        websocket_client.websocket_connect(
            "/ws/match/match-alpha?viewer=player"
            f"&token={_human_jwt_token(user_id='00000000-0000-0000-0000-000000000302')}"
        ) as player_two_socket,
        websocket_client.websocket_connect(
            "/ws/match/match-alpha?viewer=spectator"
        ) as spectator_socket,
    ):
        player_one_socket.receive_json()
        player_two_socket.receive_json()
        spectator_socket.receive_json()

        response = websocket_client.post(
            "/api/v1/matches/match-alpha/command",
            json=_command_envelope_payload(
                messages=[
                    {
                        "channel": "direct",
                        "recipient_id": "player-2",
                        "content": "Envelope direct update.",
                    },
                    {
                        "channel": "group",
                        "group_chat_id": "group-chat-1",
                        "content": "Envelope group update.",
                    },
                ]
            ),
            headers=_auth_headers_for_player("player-1"),
        )

        player_one_update = player_one_socket.receive_json()
        player_two_update = player_two_socket.receive_json()
        spectator_update = spectator_socket.receive_json()

    assert response.status_code == HTTPStatus.ACCEPTED
    assert player_one_update["data"]["direct_messages"][-1]["content"] == "Envelope direct update."
    assert player_two_update["data"]["direct_messages"][-1]["content"] == "Envelope direct update."
    assert player_one_update["data"]["group_messages"][-1]["content"] == "Envelope group update."
    assert player_two_update["data"]["group_messages"][-1]["content"] == "Envelope group update."
    assert spectator_update["data"]["direct_messages"][-1]["content"] == "Envelope direct update."
    assert spectator_update["data"]["group_messages"][-1]["content"] == "Envelope group update."
    assert spectator_update["data"]["group_chats"] == [
        {
            "group_chat_id": "group-chat-1",
            "name": "War Council",
            "member_ids": ["player-1", "player-2"],
            "created_by": "player-1",
            "created_tick": 142,
        }
    ]


def test_treaty_and_alliance_writes_broadcast_match_refresh(
    websocket_client: TestClient,
) -> None:
    with (
        websocket_client.websocket_connect(
            "/ws/match/match-alpha?viewer=player"
            f"&token={_human_jwt_token(user_id='00000000-0000-0000-0000-000000000302')}"
        ) as player_two_socket,
        websocket_client.websocket_connect(
            "/ws/match/match-alpha?viewer=spectator"
        ) as spectator_socket,
    ):
        player_two_socket.receive_json()
        spectator_socket.receive_json()

        treaty_response = websocket_client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(counterparty_id="player-1"),
            headers=_auth_headers_for_player("player-2"),
        )

        player_treaty_update = player_two_socket.receive_json()
        spectator_treaty_update = spectator_socket.receive_json()

        alliance_response = websocket_client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(action="leave", alliance_id=None, name=None),
            headers=_auth_headers_for_player("player-2"),
        )

        player_alliance_update = player_two_socket.receive_json()
        spectator_alliance_update = spectator_socket.receive_json()

    assert treaty_response.status_code == HTTPStatus.ACCEPTED
    assert player_treaty_update["data"]["treaties"] == [
        {
            "treaty_id": 0,
            "player_a_id": "player-1",
            "player_b_id": "player-2",
            "treaty_type": "trade",
            "status": "proposed",
            "proposed_by": "player-2",
            "proposed_tick": 142,
            "signed_tick": None,
            "withdrawn_by": None,
            "withdrawn_tick": None,
        }
    ]
    assert spectator_treaty_update["data"]["treaties"] == player_treaty_update["data"]["treaties"]

    assert alliance_response.status_code == HTTPStatus.ACCEPTED
    assert player_alliance_update["data"]["alliances"] == [
        {
            "alliance_id": "alliance-red",
            "name": "alliance-red",
            "leader_id": "player-1",
            "formed_tick": 142,
            "members": [{"player_id": "player-1", "joined_tick": 142}],
        }
    ]
    assert (
        spectator_alliance_update["data"]["alliances"]
        == player_alliance_update["data"]["alliances"]
    )


def test_runtime_broadcasts_post_tick_payload_to_connected_player_and_spectator(
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    seeded_match = seeded_registry.get_match("match-alpha")
    assert seeded_match is not None
    seeded_match.tick_interval_seconds = 1

    with TestClient(
        create_app(
            match_registry=seeded_registry,
            settings_override={
                "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
                "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
                "HUMAN_JWT_AUDIENCE": "authenticated",
                "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
            },
        ),
        base_url="http://testserver",
    ) as client:
        with (
            client.websocket_connect(
                "/ws/match/match-alpha?viewer=player"
                f"&token={_human_jwt_token(user_id='00000000-0000-0000-0000-000000000302')}"
            ) as player_socket,
            client.websocket_connect("/ws/match/match-alpha?viewer=spectator") as spectator_socket,
        ):
            initial_player = player_socket.receive_json()
            initial_spectator = spectator_socket.receive_json()
            assert initial_player["data"]["state"]["tick"] == 142
            assert initial_spectator["data"]["state"]["tick"] == 142

            response = client.post(
                "/api/v1/matches/match-alpha/orders",
                json={
                    "match_id": "match-alpha",
                    "tick": 142,
                    "orders": {
                        "movements": [],
                        "recruitment": [{"city": "manchester", "troops": 5}],
                        "upgrades": [],
                        "transfers": [],
                    },
                },
                headers=_auth_headers_for_player("player-2"),
            )
            assert response.status_code == HTTPStatus.ACCEPTED

            player_update = player_socket.receive_json()
            spectator_update = spectator_socket.receive_json()

    assert player_update["data"]["state"]["tick"] == 143
    assert spectator_update["data"]["state"]["tick"] == 143
    assert any(
        army["owner"] == "player-2" and army["troops"] == 5
        for army in spectator_update["data"]["state"]["armies"]
    )
    assert any(
        army["owner"] == "player-2" and army["troops"] == 5
        for army in player_update["data"]["state"]["visible_armies"]
    )


@pytest.mark.asyncio
async def test_websocket_manager_drops_failed_and_slow_connections(
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    class FailingSocket:
        async def send_json(self, _: dict[str, Any]) -> None:
            raise RuntimeError("disconnect")

    class SlowSocket:
        async def send_json(self, _: dict[str, Any]) -> None:
            await asyncio.sleep(0.2)

    manager = MatchWebSocketManager()
    socket = FailingSocket()
    slow_socket = SlowSocket()
    manager.register(
        match_id="match-alpha",
        websocket=socket,  # type: ignore[arg-type]
        viewer_role="spectator",
    )
    manager.register(
        match_id="match-alpha",
        websocket=slow_socket,  # type: ignore[arg-type]
        viewer_role="spectator",
    )

    started = asyncio.get_running_loop().time()
    await manager.broadcast(
        match_id="match-alpha",
        payload_factory=lambda _: build_match_realtime_envelope(
            registry=seeded_registry,
            match_id="match-alpha",
            viewer_role="spectator",
        ),
    )
    elapsed = asyncio.get_running_loop().time() - started

    assert manager.connection_count("match-alpha") == 0
    assert elapsed < 0.2
    with pytest.raises(ValueError, match="match-missing"):
        build_match_realtime_envelope(
            registry=seeded_registry,
            match_id="match-missing",
            viewer_role="spectator",
        )
