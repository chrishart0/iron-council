from __future__ import annotations

import os
import subprocess
from http import HTTPStatus
from pathlib import Path
from typing import Any

import httpx
import jwt
from server.agent_registry import build_seeded_agent_api_key
from server.db.testing import provision_seeded_database
from sqlalchemy import create_engine, text
from tests.conftest import _allocate_tcp_port, _wait_for_running_app
from tests.support import RunningApp, build_persisted_player_id, insert_completed_match_fixture


def _headers(agent_id: str = "agent-player-2") -> dict[str, str]:
    return {"X-API-Key": build_seeded_agent_api_key(agent_id)}


def _human_headers(user_id: str) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": user_id,
            "role": "authenticated",
            "iss": "https://supabase.test/auth/v1",
            "aud": "authenticated",
        },
        "test-human-secret-key-material-1234",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_running_app_lists_db_seeded_matches_and_serves_authenticated_fog_filtered_state(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        list_response = client.get("/api/v1/matches")
        state_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/state",
            headers=_headers(),
        )

    assert list_response.status_code == HTTPStatus.OK
    assert list_response.json() == {
        "matches": [
            {
                "match_id": running_seeded_app.primary_match_id,
                "status": "active",
                "map": "britain",
                "tick": 142,
                "tick_interval_seconds": 30,
                "current_player_count": 3,
                "max_player_count": 5,
                "open_slot_count": 2,
            },
            {
                "match_id": running_seeded_app.secondary_match_id,
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
    assert state_response.status_code == HTTPStatus.OK
    payload = state_response.json()
    assert payload["match_id"] == running_seeded_app.primary_match_id
    assert payload["player_id"] == "player-2"
    assert payload["alliance_members"] == ["player-1", "player-2"]
    assert payload["cities"]["london"]["visibility"] == "full"
    assert payload["cities"]["birmingham"]["visibility"] == "partial"
    assert "inverness" not in payload["cities"]


def test_running_app_rejects_non_agent_public_profile_and_non_agent_api_key_join_attempt(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        profile_response = client.get("/api/v1/agents/agent-player-1/profile")
        human_profile_response = client.get("/api/v1/humans/agent-player-1/profile")
        join_response = client.post(
            f"/api/v1/matches/{running_seeded_app.secondary_match_id}/join",
            json={"match_id": running_seeded_app.secondary_match_id},
            headers=_headers("agent-player-1"),
        )

    assert profile_response.status_code == HTTPStatus.NOT_FOUND
    assert profile_response.json() == {
        "error": {
            "code": "agent_not_found",
            "message": "Agent 'agent-player-1' was not found.",
        }
    }
    assert human_profile_response.status_code == HTTPStatus.NOT_FOUND
    assert human_profile_response.json() == {
        "error": {
            "code": "human_not_found",
            "message": "Human 'agent-player-1' was not found.",
        }
    }
    assert join_response.status_code == HTTPStatus.UNAUTHORIZED
    assert join_response.json() == {
        "error": {
            "code": "invalid_api_key",
            "message": "A valid active X-API-Key header is required.",
        }
    }


def test_running_app_requires_authenticated_join_and_match_scoped_reads(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        unauthenticated_join_response = client.post(
            f"/api/v1/matches/{running_seeded_app.secondary_match_id}/join",
            json={"match_id": running_seeded_app.secondary_match_id},
        )
        pre_join_state_response = client.get(
            f"/api/v1/matches/{running_seeded_app.secondary_match_id}/state",
            headers=_headers(),
        )
        authenticated_join_response = client.post(
            f"/api/v1/matches/{running_seeded_app.secondary_match_id}/join",
            json={"match_id": running_seeded_app.secondary_match_id},
            headers=_headers(),
        )
        state_response = client.get(
            f"/api/v1/matches/{running_seeded_app.secondary_match_id}/state",
            headers=_headers(),
        )

    assert unauthenticated_join_response.status_code == HTTPStatus.UNAUTHORIZED
    assert unauthenticated_join_response.json() == {
        "error": {
            "code": "invalid_api_key",
            "message": "A valid active X-API-Key header is required.",
        }
    }
    assert pre_join_state_response.status_code == HTTPStatus.BAD_REQUEST
    assert pre_join_state_response.json() == {
        "error": {
            "code": "agent_not_joined",
            "message": (
                "Agent 'agent-player-2' has not joined match "
                f"'{running_seeded_app.secondary_match_id}' as a player."
            ),
        }
    }
    assert authenticated_join_response.status_code == HTTPStatus.ACCEPTED
    assert authenticated_join_response.json()["agent_id"] == "agent-player-2"
    assert authenticated_join_response.json()["player_id"] == "player-1"
    assert state_response.status_code == HTTPStatus.OK
    assert state_response.json()["player_id"] == "player-1"


def test_running_app_serves_authenticated_current_agent_profile_from_db_registry(
    running_seeded_app: RunningApp,
) -> None:
    insert_completed_match_fixture(running_seeded_app.database_url)

    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        response = client.get("/api/v1/agent/profile", headers=_headers())

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "agent_id": "agent-player-2",
        "display_name": "Morgana",
        "is_seeded": True,
        "rating": {"elo": 1211, "provisional": False},
        "history": {"matches_played": 2, "wins": 1, "losses": 0, "draws": 1},
        "treaty_reputation": {
            "summary": {
                "signed": 0,
                "active": 0,
                "honored": 0,
                "withdrawn": 0,
                "broken_by_self": 0,
                "broken_by_counterparty": 0,
            },
            "history": [],
        },
    }


def test_running_app_rejects_missing_or_invalid_agent_api_keys_for_current_profile(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        missing_key_response = client.get("/api/v1/agent/profile")
        invalid_key_response = client.get(
            "/api/v1/agent/profile",
            headers={"X-API-Key": "invalid-key"},
        )

    assert missing_key_response.status_code == HTTPStatus.UNAUTHORIZED
    assert missing_key_response.json() == {
        "error": {
            "code": "invalid_api_key",
            "message": "A valid active X-API-Key header is required.",
        }
    }
    assert invalid_key_response.status_code == HTTPStatus.UNAUTHORIZED
    assert invalid_key_response.json() == missing_key_response.json()


def test_running_app_recomputes_api_key_occupancy_after_match_completion(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        create_response = client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers=_human_headers("00000000-0000-0000-0000-000000000304"),
        )
        created_payload = create_response.json()
        blocked_join_response = client.post(
            f"/api/v1/matches/{created_payload['match_id']}/join",
            json={"match_id": created_payload["match_id"]},
            headers=_headers("agent-player-2"),
        )

    engine = create_engine(running_seeded_app.database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE matches
                SET status = 'completed'
                WHERE id = :match_id
                """
            ),
            {"match_id": running_seeded_app.primary_match_id},
        )

    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        recovered_join_response = client.post(
            f"/api/v1/matches/{created_payload['match_id']}/join",
            json={"match_id": created_payload["match_id"]},
            headers=_headers("agent-player-2"),
        )
        state_response = client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers=_headers("agent-player-2"),
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


def test_running_app_supports_human_api_key_lifecycle_create_revoke_and_rejects_revoked_key(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        create_response = client.post(
            "/api/v1/account/api-keys",
            headers=_human_headers("00000000-0000-0000-0000-000000000301"),
        )
        created_payload = create_response.json()
        list_response = client.get(
            "/api/v1/account/api-keys",
            headers=_human_headers("00000000-0000-0000-0000-000000000301"),
        )
        revoke_response = client.delete(
            f"/api/v1/account/api-keys/{created_payload['summary']['key_id']}",
            headers=_human_headers("00000000-0000-0000-0000-000000000301"),
        )
        profile_response = client.get(
            "/api/v1/agent/profile",
            headers={"X-API-Key": created_payload["api_key"]},
        )

    assert create_response.status_code == HTTPStatus.CREATED
    assert created_payload["api_key"].startswith("iron_")
    assert list_response.status_code == HTTPStatus.OK
    assert created_payload["api_key"] not in list_response.text
    assert revoke_response.status_code == HTTPStatus.OK
    assert revoke_response.json()["is_active"] is False
    assert profile_response.status_code == HTTPStatus.UNAUTHORIZED
    assert profile_response.json() == {
        "error": {
            "code": "invalid_api_key",
            "message": "A valid active X-API-Key header is required.",
        }
    }


def test_running_app_rejects_stale_orders_against_db_seeded_match_state(
    running_seeded_app: RunningApp,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = dict(representative_order_payload)
    payload["match_id"] = running_seeded_app.primary_match_id
    payload["tick"] = 141
    payload.pop("player_id", None)

    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/orders",
            json=payload,
            headers=_headers(),
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "error": {
            "code": "tick_mismatch",
            "message": "Order payload tick '141' does not match current match tick '142'.",
        }
    }


def test_running_app_processes_consolidated_command_envelope_without_partial_side_effects(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        group_chat_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/group-chats",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "name": "Process Council",
                "member_ids": ["player-1"],
            },
            headers=_headers(),
        )
        accepted_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/command",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "orders": {
                    "movements": [{"army_id": "army-b", "destination": "birmingham"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
                "messages": [
                    {"channel": "world", "content": "Bundled process update."},
                    {
                        "channel": "direct",
                        "recipient_id": "player-1",
                        "content": "Bundled process direct update.",
                    },
                    {
                        "channel": "group",
                        "group_chat_id": "group-chat-1",
                        "content": "Bundled process group update.",
                    },
                ],
                "treaties": [
                    {
                        "counterparty_id": "player-3",
                        "action": "propose",
                        "treaty_type": "trade",
                    }
                ],
                "alliance": {"action": "leave", "alliance_id": None, "name": None},
            },
            headers=_headers(),
        )
        rejected_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/command",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "orders": {
                    "movements": [{"army_id": "army-b", "destination": "birmingham"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
                "messages": [
                    {"channel": "world", "content": "Should not persist."},
                    {
                        "channel": "group",
                        "group_chat_id": "group-chat-missing",
                        "content": "Should not persist in group either.",
                    },
                ],
                "treaties": [
                    {
                        "counterparty_id": "player-4",
                        "action": "propose",
                        "treaty_type": "trade",
                    }
                ],
                "alliance": {"action": "leave", "alliance_id": None, "name": None},
            },
            headers=_headers(),
        )
        player_two_messages = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            headers=_headers(),
        )
        treaties = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/treaties",
            headers=_headers(),
        )
        player_two_state = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/state",
            headers=_headers(),
        )
        player_three_messages = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            headers=_headers("agent-player-3"),
        )
        group_messages = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/group-chats/group-chat-1/messages",
            headers=_headers(),
        )

    assert group_chat_response.status_code == HTTPStatus.ACCEPTED
    assert accepted_response.status_code == HTTPStatus.ACCEPTED
    assert accepted_response.json()["orders"]["submission_index"] == 0
    assert accepted_response.json()["messages"][0]["content"] == "Bundled process update."
    assert accepted_response.json()["messages"][1]["content"] == "Bundled process direct update."
    assert (
        accepted_response.json()["messages"][2]["message"]["content"]
        == "Bundled process group update."
    )
    assert accepted_response.json()["treaties"][0]["treaty"]["player_b_id"] == "player-3"
    assert accepted_response.json()["alliance"]["player_id"] == "player-2"
    assert rejected_response.status_code == HTTPStatus.BAD_REQUEST
    assert rejected_response.json() == {
        "error": {
            "code": "group_chat_not_visible",
            "message": "Group chat 'group-chat-missing' is not visible to player 'player-2'.",
        }
    }
    assert player_two_messages.status_code == HTTPStatus.OK
    assert [message["content"] for message in player_two_messages.json()["messages"]] == [
        "Bundled process update.",
        "Bundled process direct update.",
    ]
    assert treaties.status_code == HTTPStatus.OK
    assert [treaty["player_b_id"] for treaty in treaties.json()["treaties"]] == [
        "player-3",
        "player-3",
    ]
    assert [treaty["status"] for treaty in treaties.json()["treaties"]] == [
        "active",
        "proposed",
    ]
    assert player_two_state.status_code == HTTPStatus.OK
    assert player_two_state.json()["alliance_id"] is None
    assert player_three_messages.status_code == HTTPStatus.OK
    assert player_three_messages.json()["messages"] == [
        {
            "message_id": 0,
            "channel": "world",
            "sender_id": "player-2",
            "recipient_id": None,
            "tick": 142,
            "content": "Bundled process update.",
        }
    ]
    assert group_messages.status_code == HTTPStatus.OK
    assert [message["content"] for message in group_messages.json()["messages"]] == [
        "Bundled process group update."
    ]


def test_running_app_posts_and_filters_visible_messages_for_authenticated_player(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        world_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "channel": "world",
                "recipient_id": None,
                "content": "Open briefing.",
            },
            headers=_headers(),
        )
        direct_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "channel": "direct",
                "recipient_id": "player-1",
                "content": "Private briefing.",
            },
            headers=_headers(),
        )
        visible_to_player_two = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            headers=_headers(),
        )

    assert world_response.status_code == HTTPStatus.ACCEPTED
    assert direct_response.status_code == HTTPStatus.ACCEPTED
    assert visible_to_player_two.status_code == HTTPStatus.OK
    assert visible_to_player_two.json() == {
        "match_id": running_seeded_app.primary_match_id,
        "player_id": "player-2",
        "messages": [
            {
                "message_id": 0,
                "channel": "world",
                "sender_id": "player-2",
                "recipient_id": None,
                "tick": 142,
                "content": "Open briefing.",
            },
            {
                "message_id": 1,
                "channel": "direct",
                "sender_id": "player-2",
                "recipient_id": "player-1",
                "tick": 142,
                "content": "Private briefing.",
            },
        ],
    }


def test_running_app_processes_treaty_reads_for_authenticated_player(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        propose_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/treaties",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "counterparty_id": "player-1",
                "action": "propose",
                "treaty_type": "trade",
            },
            headers=_headers(),
        )
        treaty_read = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/treaties",
            headers=_headers(),
        )

    assert propose_response.status_code == HTTPStatus.ACCEPTED
    assert propose_response.json() == {
        "status": "accepted",
        "match_id": running_seeded_app.primary_match_id,
        "treaty": {
            "treaty_id": 1,
            "player_a_id": "player-1",
            "player_b_id": "player-2",
            "treaty_type": "trade",
            "status": "proposed",
            "proposed_by": "player-2",
            "proposed_tick": 142,
            "signed_tick": None,
            "withdrawn_by": None,
            "withdrawn_tick": None,
        },
    }
    assert treaty_read.status_code == HTTPStatus.OK
    assert treaty_read.json() == {
        "match_id": running_seeded_app.primary_match_id,
        "treaties": [
            {
                "treaty_id": 1,
                "player_a_id": "player-1",
                "player_b_id": "player-2",
                "treaty_type": "trade",
                "status": "proposed",
                "proposed_by": "player-2",
                "proposed_tick": 142,
                "signed_tick": None,
                "withdrawn_by": None,
                "withdrawn_tick": None,
            },
            {
                "treaty_id": 0,
                "player_a_id": "player-1",
                "player_b_id": "player-3",
                "treaty_type": "trade",
                "status": "active",
                "proposed_by": "player-1",
                "proposed_tick": 141,
                "signed_tick": 141,
                "withdrawn_by": None,
                "withdrawn_tick": None,
            },
        ],
    }


def test_running_app_reads_broken_treaty_statuses_for_authenticated_player(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'process-broken-treaty.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

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
                "match_id": "00000000-0000-0000-0000-000000000101",
                "player_a_id": build_persisted_player_id(
                    match_id="00000000-0000-0000-0000-000000000101",
                    public_player_id="player-1",
                ),
                "player_b_id": build_persisted_player_id(
                    match_id="00000000-0000-0000-0000-000000000101",
                    public_player_id="player-2",
                ),
                "treaty_type": "trade",
                "status": "broken_by_a",
                "signed_tick": 141,
                "broken_tick": 142,
                "created_at": "2026-03-29 07:58:00+00:00",
            },
        )

    host = "127.0.0.1"
    port = _allocate_tcp_port()
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "server.main:app",
            "--host",
            host,
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "DATABASE_URL": database_url,
            "IRON_COUNCIL_MATCH_REGISTRY_BACKEND": "db",
            "HUMAN_JWT_SECRET": "test-human-secret-key-material-1234",
            "HUMAN_JWT_ISSUER": "https://supabase.test/auth/v1",
            "HUMAN_JWT_AUDIENCE": "authenticated",
            "HUMAN_JWT_REQUIRED_ROLE": "authenticated",
            "PYTHONUNBUFFERED": "1",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    base_url = f"http://{host}:{port}"
    try:
        _wait_for_running_app(base_url, process)
        with httpx.Client(base_url=base_url, timeout=5) as client:
            treaty_read = client.get(
                "/api/v1/matches/00000000-0000-0000-0000-000000000101/treaties",
                headers=_headers(),
            )
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    assert treaty_read.status_code == HTTPStatus.OK
    payload = treaty_read.json()
    assert payload["match_id"] == "00000000-0000-0000-0000-000000000101"
    assert payload["treaties"] == [
        {
            "treaty_id": 0,
            "player_a_id": "player-1",
            "player_b_id": "player-2",
            "treaty_type": "trade",
            "status": "broken_by_a",
            "proposed_by": "player-1",
            "proposed_tick": 141,
            "signed_tick": 141,
            "withdrawn_by": "player-1",
            "withdrawn_tick": 142,
        },
        {
            "treaty_id": 1,
            "player_a_id": "player-1",
            "player_b_id": "player-3",
            "treaty_type": "trade",
            "status": "active",
            "proposed_by": "player-1",
            "proposed_tick": 141,
            "signed_tick": 141,
            "withdrawn_by": None,
            "withdrawn_tick": None,
        },
    ]


def test_running_app_reads_and_updates_alliance_membership_for_authenticated_player(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        initial_alliance_read = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/alliances",
            headers=_headers(),
        )
        leave_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/alliances",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "action": "leave",
                "alliance_id": None,
                "name": None,
            },
            headers=_headers(),
        )
        post_leave_alliance_read = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/alliances",
            headers=_headers(),
        )
        player_two_state = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/state",
            headers=_headers(),
        )

    assert initial_alliance_read.status_code == HTTPStatus.OK
    assert initial_alliance_read.json() == {
        "match_id": running_seeded_app.primary_match_id,
        "alliances": [
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
        ],
    }
    assert leave_response.status_code == HTTPStatus.ACCEPTED
    assert leave_response.json() == {
        "status": "accepted",
        "match_id": running_seeded_app.primary_match_id,
        "player_id": "player-2",
        "alliance": {
            "alliance_id": "alliance-red",
            "name": "Western Accord",
            "leader_id": "player-1",
            "formed_tick": 120,
            "members": [{"player_id": "player-1", "joined_tick": 120}],
        },
    }
    assert post_leave_alliance_read.status_code == HTTPStatus.OK
    assert post_leave_alliance_read.json() == {
        "match_id": running_seeded_app.primary_match_id,
        "alliances": [
            {
                "alliance_id": "alliance-red",
                "name": "Western Accord",
                "leader_id": "player-1",
                "formed_tick": 120,
                "members": [{"player_id": "player-1", "joined_tick": 120}],
            }
        ],
    }
    assert player_two_state.status_code == HTTPStatus.OK
    assert player_two_state.json()["alliance_id"] is None
    assert player_two_state.json()["alliance_members"] == ["player-2"]


def test_running_app_rejects_stale_and_future_messages_without_mutation(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        stale_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 141,
                "channel": "world",
                "recipient_id": None,
                "content": "Stale message.",
            },
            headers=_headers(),
        )
        future_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 143,
                "channel": "world",
                "recipient_id": None,
                "content": "Future message.",
            },
            headers=_headers(),
        )
        inbox_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            headers=_headers(),
        )

    assert stale_response.status_code == HTTPStatus.BAD_REQUEST
    assert stale_response.json() == {
        "error": {
            "code": "tick_mismatch",
            "message": "Message payload tick '141' does not match current match tick '142'.",
        }
    }
    assert future_response.status_code == HTTPStatus.BAD_REQUEST
    assert future_response.json() == {
        "error": {
            "code": "tick_mismatch",
            "message": "Message payload tick '143' does not match current match tick '142'.",
        }
    }
    assert inbox_response.status_code == HTTPStatus.OK
    assert inbox_response.json() == {
        "match_id": running_seeded_app.primary_match_id,
        "player_id": "player-2",
        "messages": [],
    }


def test_running_app_processes_group_chat_visibility_and_member_posting(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        create_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/group-chats",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "name": "Alliance Backchannel",
                "member_ids": ["player-3"],
            },
            headers=_headers(),
        )
        invited_group_chats = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/group-chats",
            headers=_headers("agent-player-3"),
        )
        invited_message_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/group-chats/group-chat-1/messages",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "content": "Confirmed.",
            },
            headers=_headers("agent-player-3"),
        )

    assert create_response.status_code == HTTPStatus.ACCEPTED
    assert create_response.json() == {
        "status": "accepted",
        "match_id": running_seeded_app.primary_match_id,
        "group_chat": {
            "group_chat_id": "group-chat-1",
            "name": "Alliance Backchannel",
            "member_ids": ["player-2", "player-3"],
            "created_by": "player-2",
            "created_tick": 142,
        },
    }
    assert invited_group_chats.status_code == HTTPStatus.OK
    assert invited_group_chats.json() == {
        "match_id": running_seeded_app.primary_match_id,
        "player_id": "player-3",
        "group_chats": [
            {
                "group_chat_id": "group-chat-1",
                "name": "Alliance Backchannel",
                "member_ids": ["player-2", "player-3"],
                "created_by": "player-2",
                "created_tick": 142,
            }
        ],
    }
    assert invited_message_response.status_code == HTTPStatus.ACCEPTED
    assert invited_message_response.json() == {
        "status": "accepted",
        "match_id": running_seeded_app.primary_match_id,
        "group_chat_id": "group-chat-1",
        "message": {
            "message_id": 0,
            "group_chat_id": "group-chat-1",
            "sender_id": "player-3",
            "tick": 142,
            "content": "Confirmed.",
        },
    }
