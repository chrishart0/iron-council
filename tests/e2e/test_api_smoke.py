from __future__ import annotations

import time
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import Any

import httpx
import jwt
from server.agent_registry import build_seeded_agent_api_key
from server.db.registry import load_match_registry_from_database
from server.models.domain import MatchStatus
from tests.support import (
    RunningApp,
    build_persisted_player_id,
    insert_completed_match_fixture,
    insert_seeded_agent_player,
    insert_seeded_human_player,
)
from websockets.sync.client import connect as connect_websocket


def _headers(agent_id: str = "agent-player-2") -> dict[str, str]:
    return {"X-API-Key": build_seeded_agent_api_key(agent_id)}


def _human_jwt_token(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "role": "authenticated",
            "iss": "https://supabase.test/auth/v1",
            "aud": "authenticated",
            "exp": datetime.now(tz=UTC) + timedelta(minutes=5),
        },
        "test-human-secret-key-material-1234",
        algorithm="HS256",
    )


def _human_headers(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_human_jwt_token(user_id)}"}


def test_agent_api_smoke_flow_runs_through_real_process_and_seeded_database(
    running_seeded_app: RunningApp,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = running_seeded_app.primary_match_id
    payload["tick"] = 142
    payload["orders"] = {
        **payload["orders"],
        "movements": [{"army_id": "army-b", "destination": "birmingham"}],
    }
    payload.pop("player_id", None)

    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        health_response = client.get("/health")
        list_response = client.get("/api/v1/matches")
        initial_state_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/state",
            headers=_headers(),
        )
        submit_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/orders",
            json=payload,
            headers=_headers(),
        )
        follow_up_state_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/state",
            headers=_headers(),
        )

    assert health_response.status_code == HTTPStatus.OK
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
    assert initial_state_response.status_code == HTTPStatus.OK
    assert submit_response.status_code == HTTPStatus.ACCEPTED
    assert submit_response.json() == {
        "status": "accepted",
        "match_id": running_seeded_app.primary_match_id,
        "player_id": "player-2",
        "tick": 142,
        "submission_index": 0,
    }
    assert follow_up_state_response.status_code == HTTPStatus.OK
    assert follow_up_state_response.json() == initial_state_response.json()


def test_active_match_ticks_forward_without_manual_advance_endpoint(
    running_fast_tick_app: RunningApp,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = running_fast_tick_app.primary_match_id
    payload["tick"] = 142
    payload["orders"] = {
        "movements": [],
        "recruitment": [{"city": "manchester", "troops": 5}],
        "upgrades": [],
        "transfers": [],
    }
    payload.pop("player_id", None)

    with httpx.Client(base_url=running_fast_tick_app.base_url, timeout=5) as client:
        submit_response = client.post(
            f"/api/v1/matches/{running_fast_tick_app.primary_match_id}/orders",
            json=payload,
            headers=_headers("agent-player-2"),
        )

        deadline = time.monotonic() + 3
        latest_state: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            state_response = client.get(
                f"/api/v1/matches/{running_fast_tick_app.primary_match_id}/state",
                headers=_headers("agent-player-2"),
            )
            assert state_response.status_code == HTTPStatus.OK
            latest_state = state_response.json()
            if latest_state["tick"] >= 143:
                break
            time.sleep(0.1)

    assert submit_response.status_code == HTTPStatus.ACCEPTED
    assert latest_state is not None
    assert latest_state["tick"] == 143
    assert any(
        army["owner"] == "player-2" and army["location"] == "manchester" and army["troops"] == 5
        for army in latest_state["visible_armies"]
    )
    reloaded_registry = load_match_registry_from_database(running_fast_tick_app.database_url)
    reloaded_match = reloaded_registry.get_match(running_fast_tick_app.primary_match_id)
    assert reloaded_match is not None
    assert reloaded_match.state.tick == 143


def test_match_history_and_replay_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        history_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/history"
        )
        replay_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/history/142"
        )

    assert history_response.status_code == HTTPStatus.OK
    assert history_response.json() == {
        "match_id": running_seeded_app.primary_match_id,
        "status": "active",
        "current_tick": 142,
        "tick_interval_seconds": 30,
        "history": [{"tick": 142}],
    }
    assert replay_response.status_code == HTTPStatus.OK
    assert replay_response.json() == {
        "match_id": running_seeded_app.primary_match_id,
        "tick": 142,
        "state_snapshot": {"cities": {"london": {"owner": "Arthur", "population": 12}}},
        "orders": {"movements": [{"army_id": "army-1", "destination": "york"}]},
        "events": {"summary": ["Convoy secured", "Trade revenue collected"]},
    }


def test_public_leaderboard_and_completed_match_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    insert_completed_match_fixture(running_seeded_app.database_url)

    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        leaderboard_response = client.get("/api/v1/leaderboard")
        completed_matches_response = client.get("/api/v1/matches/completed")

    assert leaderboard_response.status_code == HTTPStatus.OK
    assert leaderboard_response.json() == {
        "leaderboard": [
            {
                "rank": 1,
                "display_name": "Arthur",
                "competitor_kind": "human",
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
            },
        ]
    }


def test_match_browse_smoke_flow_runs_through_real_process_with_compact_db_backed_rows(
    running_seeded_app: RunningApp,
) -> None:
    insert_completed_match_fixture(running_seeded_app.database_url)

    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        response = client.get("/api/v1/matches")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
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


def test_public_match_detail_smoke_flow_runs_through_real_process_with_compact_public_payload(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        response = client.get(f"/api/v1/matches/{running_seeded_app.primary_match_id}")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "match_id": running_seeded_app.primary_match_id,
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
            },
            {
                "player_id": "player-3",
                "display_name": "Gawain",
                "competitor_kind": "agent",
            },
            {
                "player_id": "player-2",
                "display_name": "Morgana",
                "competitor_kind": "agent",
            },
        ],
    }
    assert "history" not in response.json()
    assert "state_snapshot" not in response.json()
    assert "orders" not in response.json()
    assert "events" not in response.json()


def test_match_websocket_smoke_broadcasts_initial_and_tick_updates_for_player_and_spectator(
    running_fast_tick_app: RunningApp,
) -> None:
    websocket_base_url = running_fast_tick_app.base_url.replace("http://", "ws://", 1)
    player_url = (
        f"{websocket_base_url}/ws/match/{running_fast_tick_app.primary_match_id}"
        "?viewer=player"
        f"&token={_human_jwt_token('00000000-0000-0000-0000-000000000301')}"
    )
    spectator_url = (
        f"{websocket_base_url}/ws/match/{running_fast_tick_app.primary_match_id}?viewer=spectator"
    )

    with (
        connect_websocket(player_url, open_timeout=5, close_timeout=1) as player_socket,
        connect_websocket(spectator_url, open_timeout=5, close_timeout=1) as spectator_socket,
        httpx.Client(base_url=running_fast_tick_app.base_url, timeout=5) as client,
    ):
        initial_player = player_socket.recv(timeout=5)
        initial_spectator = spectator_socket.recv(timeout=5)
        assert isinstance(initial_player, str)
        assert isinstance(initial_spectator, str)

        submit_response = client.post(
            f"/api/v1/matches/{running_fast_tick_app.primary_match_id}/orders",
            json={
                "match_id": running_fast_tick_app.primary_match_id,
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "manchester", "troops": 5}],
                    "upgrades": [],
                    "transfers": [],
                },
            },
            headers=_headers("agent-player-2"),
        )
        assert submit_response.status_code == HTTPStatus.ACCEPTED

        tick_player = player_socket.recv(timeout=5)
        tick_spectator = spectator_socket.recv(timeout=5)
        assert isinstance(tick_player, str)
        assert isinstance(tick_spectator, str)

    import json

    initial_player_payload = json.loads(initial_player)
    initial_spectator_payload = json.loads(initial_spectator)
    tick_player_payload = json.loads(tick_player)
    tick_spectator_payload = json.loads(tick_spectator)

    assert initial_player_payload["data"]["viewer_role"] == "player"
    assert initial_player_payload["data"]["state"]["tick"] == 142
    assert (
        initial_player_payload["data"]["state"]["cities"]["birmingham"]["visibility"] == "partial"
    )
    assert initial_spectator_payload["data"]["viewer_role"] == "spectator"
    assert initial_spectator_payload["data"]["state"]["cities"]["birmingham"]["garrison"] == 7
    assert tick_player_payload["data"]["state"]["tick"] == 143
    assert tick_spectator_payload["data"]["state"]["tick"] == 143
    assert any(
        army["owner"] == "player-2" and army["troops"] == 5
        for army in tick_player_payload["data"]["state"]["visible_armies"]
    )
    assert any(
        army["owner"] == "player-2" and army["troops"] == 5
        for army in tick_spectator_payload["data"]["state"]["armies"]
    )


def test_agent_join_and_profile_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    insert_completed_match_fixture(running_seeded_app.database_url)

    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        profile_response = client.get("/api/v1/agents/agent-player-2/profile")
        join_response = client.post(
            f"/api/v1/matches/{running_seeded_app.secondary_match_id}/join",
            json={"match_id": running_seeded_app.secondary_match_id},
            headers=_headers(),
        )
        repeat_join_response = client.post(
            f"/api/v1/matches/{running_seeded_app.secondary_match_id}/join",
            json={"match_id": running_seeded_app.secondary_match_id},
            headers=_headers(),
        )

    assert profile_response.status_code == HTTPStatus.OK
    assert profile_response.json() == {
        "agent_id": "agent-player-2",
        "display_name": "Morgana",
        "is_seeded": True,
        "rating": {"elo": 1211, "provisional": False},
        "history": {"matches_played": 2, "wins": 1, "losses": 0, "draws": 1},
    }
    assert join_response.status_code == HTTPStatus.ACCEPTED
    assert join_response.json() == {
        "status": "accepted",
        "match_id": running_seeded_app.secondary_match_id,
        "agent_id": "agent-player-2",
        "player_id": "player-1",
    }
    assert repeat_join_response.status_code == HTTPStatus.ACCEPTED
    assert repeat_join_response.json() == join_response.json()


def test_create_match_lobby_smoke_flow_runs_through_real_process(
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
            headers=_headers(),
        )
        assert create_response.status_code == HTTPStatus.CREATED
        created_payload = create_response.json()

        browse_response = client.get("/api/v1/matches")
        detail_response = client.get(f"/api/v1/matches/{created_payload['match_id']}")
        state_response = client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers=_headers(),
        )

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
    assert browse_response.json()["matches"][0]["match_id"] == created_payload["match_id"]
    assert browse_response.json()["matches"][0]["current_player_count"] == 1
    assert browse_response.json()["matches"][0]["open_slot_count"] == 3
    assert detail_response.status_code == HTTPStatus.OK
    assert detail_response.json()["roster"] == [
        {"player_id": "player-1", "display_name": "Morgana", "competitor_kind": "agent"}
    ]
    assert "api_key" not in detail_response.text.lower()
    assert state_response.status_code == HTTPStatus.OK
    assert state_response.json()["player_id"] == "player-1"


def test_start_match_lobby_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        create_response = client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 1,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
            headers=_headers(),
        )
        assert create_response.status_code == HTTPStatus.CREATED
        created_payload = create_response.json()

        insert_seeded_agent_player(
            database_url=running_seeded_app.database_url,
            match_id=created_payload["match_id"],
            agent_id="agent-player-3",
            persisted_player_id=build_persisted_player_id(
                match_id=created_payload["match_id"],
                public_player_id="player-2",
            ),
        )

        start_response = client.post(
            f"/api/v1/matches/{created_payload['match_id']}/start",
            headers=_headers(),
        )
        browse_response = client.get("/api/v1/matches")
        detail_response = client.get(f"/api/v1/matches/{created_payload['match_id']}")

        deadline = time.monotonic() + 3
        latest_state: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            state_response = client.get(
                f"/api/v1/matches/{created_payload['match_id']}/state",
                headers=_headers(),
            )
            assert state_response.status_code == HTTPStatus.OK
            latest_state = state_response.json()
            if latest_state["tick"] >= 1:
                break
            time.sleep(0.1)

    assert start_response.status_code == HTTPStatus.OK
    assert start_response.json() == {
        "match_id": created_payload["match_id"],
        "status": "active",
        "map": "britain",
        "tick": 0,
        "tick_interval_seconds": 1,
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
            {"player_id": "player-2", "display_name": "Gawain", "competitor_kind": "agent"},
            {"player_id": "player-1", "display_name": "Morgana", "competitor_kind": "agent"},
        ],
    }
    assert latest_state is not None
    assert latest_state["match_id"] == created_payload["match_id"]
    assert latest_state["player_id"] == "player-1"
    assert latest_state["tick"] >= 1

    reloaded_registry = load_match_registry_from_database(running_seeded_app.database_url)
    reloaded_match = reloaded_registry.get_match(created_payload["match_id"])
    assert reloaded_match is not None
    assert reloaded_match.status == MatchStatus.ACTIVE
    assert reloaded_match.state.tick >= 1


def test_human_lobby_smoke_flow_runs_through_real_process(
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
        assert create_response.status_code == HTTPStatus.CREATED
        created_payload = create_response.json()

        join_response = client.post(
            f"/api/v1/matches/{created_payload['match_id']}/join",
            json={"match_id": created_payload["match_id"]},
            headers=_human_headers("00000000-0000-0000-0000-000000000301"),
        )
        start_response = client.post(
            f"/api/v1/matches/{created_payload['match_id']}/start",
            headers=_human_headers("00000000-0000-0000-0000-000000000304"),
        )
        creator_state_response = client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers=_human_headers("00000000-0000-0000-0000-000000000304"),
        )
        joiner_state_response = client.get(
            f"/api/v1/matches/{created_payload['match_id']}/state",
            headers=_human_headers("00000000-0000-0000-0000-000000000301"),
        )

    assert join_response.status_code == HTTPStatus.ACCEPTED
    assert join_response.json()["player_id"] == "player-2"
    assert start_response.status_code == HTTPStatus.OK
    assert start_response.json()["status"] == "active"
    assert start_response.json()["current_player_count"] == 2
    assert creator_state_response.status_code == HTTPStatus.OK
    assert creator_state_response.json()["player_id"] == "player-1"
    assert joiner_state_response.status_code == HTTPStatus.OK
    assert joiner_state_response.json()["player_id"] == "player-2"


def test_human_lobby_start_smoke_flow_surfaces_not_ready_and_non_creator_errors(
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
        assert create_response.status_code == HTTPStatus.CREATED
        created_payload = create_response.json()

        missing_auth_response = client.post(
            "/api/v1/matches",
            json={
                "map": "britain",
                "tick_interval_seconds": 20,
                "max_players": 4,
                "victory_city_threshold": 13,
                "starting_cities_per_player": 2,
            },
        )
        invalid_join_response = client.post(
            f"/api/v1/matches/{created_payload['match_id']}/join",
            json={"match_id": created_payload["match_id"]},
            headers={"Authorization": "Token nope"},
        )
        not_ready_start_response = client.post(
            f"/api/v1/matches/{created_payload['match_id']}/start",
            headers=_human_headers("00000000-0000-0000-0000-000000000304"),
        )

        insert_seeded_human_player(
            database_url=running_seeded_app.database_url,
            match_id=created_payload["match_id"],
            user_id="00000000-0000-0000-0000-000000000301",
            persisted_player_id=build_persisted_player_id(
                match_id=created_payload["match_id"],
                public_player_id="player-2",
            ),
        )
        non_creator_start_response = client.post(
            f"/api/v1/matches/{created_payload['match_id']}/start",
            headers=_human_headers("00000000-0000-0000-0000-000000000301"),
        )

    assert missing_auth_response.status_code == HTTPStatus.UNAUTHORIZED
    assert missing_auth_response.json() == {
        "error": {
            "code": "invalid_player_auth",
            "message": "Player routes require a valid Bearer token or active X-API-Key header.",
        }
    }
    assert invalid_join_response.status_code == HTTPStatus.UNAUTHORIZED
    assert invalid_join_response.json() == {
        "error": {
            "code": "invalid_human_token",
            "message": "A valid human Bearer token is required.",
        }
    }
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
    assert non_creator_start_response.status_code == HTTPStatus.FORBIDDEN
    assert non_creator_start_response.json() == {
        "error": {
            "code": "match_start_forbidden",
            "message": f"Authenticated human does not own lobby '{created_payload['match_id']}'.",
        }
    }


def test_authenticated_current_agent_profile_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        unauthenticated_response = client.get("/api/v1/agent/profile")
        authenticated_response = client.get(
            "/api/v1/agent/profile",
            headers=_headers(),
        )

    assert unauthenticated_response.status_code == HTTPStatus.UNAUTHORIZED
    assert unauthenticated_response.json() == {
        "error": {
            "code": "invalid_api_key",
            "message": "A valid active X-API-Key header is required.",
        }
    }
    assert authenticated_response.status_code == HTTPStatus.OK
    assert authenticated_response.json() == {
        "agent_id": "agent-player-2",
        "display_name": "Morgana",
        "is_seeded": True,
        "rating": {"elo": 1190, "provisional": True},
        "history": {"matches_played": 0, "wins": 0, "losses": 0, "draws": 0},
    }


def test_authenticated_join_state_and_order_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = running_seeded_app.secondary_match_id
    payload["tick"] = 7
    payload["orders"] = {
        **payload["orders"],
        "movements": [],
        "recruitment": [],
        "upgrades": [],
        "transfers": [],
    }
    payload.pop("player_id", None)

    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        join_response = client.post(
            f"/api/v1/matches/{running_seeded_app.secondary_match_id}/join",
            json={"match_id": running_seeded_app.secondary_match_id},
            headers=_headers(),
        )
        state_response = client.get(
            f"/api/v1/matches/{running_seeded_app.secondary_match_id}/state",
            headers=_headers(),
        )
        order_response = client.post(
            f"/api/v1/matches/{running_seeded_app.secondary_match_id}/orders",
            json=payload,
            headers=_headers(),
        )
        unjoined_response = client.get(
            f"/api/v1/matches/{running_seeded_app.secondary_match_id}/state",
            headers=_headers("agent-player-3"),
        )

    assert join_response.status_code == HTTPStatus.ACCEPTED
    assert join_response.json()["player_id"] == "player-1"
    assert state_response.status_code == HTTPStatus.OK
    assert state_response.json()["player_id"] == "player-1"
    assert order_response.status_code == HTTPStatus.ACCEPTED
    assert order_response.json()["player_id"] == "player-1"
    assert unjoined_response.status_code == HTTPStatus.BAD_REQUEST
    assert unjoined_response.json() == {
        "error": {
            "code": "agent_not_joined",
            "message": (
                "Agent 'agent-player-3' has not joined match "
                f"'{running_seeded_app.secondary_match_id}' as a player."
            ),
        }
    }


def test_group_chat_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        create_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/group-chats",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "name": "Smoke Council",
                "member_ids": ["player-3"],
            },
            headers=_headers(),
        )
        list_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/group-chats",
            headers=_headers("agent-player-3"),
        )
        post_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/group-chats/group-chat-1/messages",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "content": "Smoke test ready.",
            },
            headers=_headers("agent-player-3"),
        )
        read_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/group-chats/group-chat-1/messages",
            headers=_headers(),
        )

    assert create_response.status_code == HTTPStatus.ACCEPTED
    assert create_response.json()["group_chat"]["member_ids"] == ["player-2", "player-3"]
    assert list_response.status_code == HTTPStatus.OK
    assert list_response.json()["group_chats"][0]["group_chat_id"] == "group-chat-1"
    assert post_response.status_code == HTTPStatus.ACCEPTED
    assert post_response.json()["message"]["content"] == "Smoke test ready."
    assert read_response.status_code == HTTPStatus.OK
    assert read_response.json() == {
        "match_id": running_seeded_app.primary_match_id,
        "group_chat_id": "group-chat-1",
        "player_id": "player-2",
        "messages": [
            {
                "message_id": 0,
                "group_chat_id": "group-chat-1",
                "sender_id": "player-3",
                "tick": 142,
                "content": "Smoke test ready.",
            }
        ],
    }


def test_agent_briefing_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        create_group_chat_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/group-chats",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "name": "Smoke Council",
                "member_ids": ["player-3"],
            },
            headers=_headers(),
        )
        group_message_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/group-chats/group-chat-1/messages",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "content": "Smoke group briefing.",
            },
            headers=_headers("agent-player-3"),
        )
        treaty_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/treaties",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "counterparty_id": "player-3",
                "action": "propose",
                "treaty_type": "trade",
            },
            headers=_headers(),
        )
        world_message_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "channel": "world",
                "content": "Smoke world briefing.",
            },
            headers=_headers("agent-player-3"),
        )
        direct_message_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "channel": "direct",
                "recipient_id": "player-2",
                "content": "Smoke direct briefing.",
            },
            headers=_headers("agent-player-3"),
        )
        briefing_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/agent-briefing",
            params={"since_tick": 142},
            headers=_headers(),
        )

    assert create_group_chat_response.status_code == HTTPStatus.ACCEPTED
    assert group_message_response.status_code == HTTPStatus.ACCEPTED
    assert treaty_response.status_code == HTTPStatus.ACCEPTED
    assert world_message_response.status_code == HTTPStatus.ACCEPTED
    assert direct_message_response.status_code == HTTPStatus.ACCEPTED
    assert briefing_response.status_code == HTTPStatus.OK
    assert briefing_response.json()["state"]["player_id"] == "player-2"
    assert briefing_response.json()["alliances"][0]["alliance_id"] == "alliance-red"
    assert briefing_response.json()["group_chats"][0]["group_chat_id"] == "group-chat-1"
    assert briefing_response.json()["treaties"][0]["treaty_type"] == "trade"
    assert [message["content"] for message in briefing_response.json()["messages"]["direct"]] == [
        "Smoke direct briefing."
    ]
    assert [message["content"] for message in briefing_response.json()["messages"]["group"]] == [
        "Smoke group briefing."
    ]
    assert [message["content"] for message in briefing_response.json()["messages"]["world"]] == [
        "Smoke world briefing."
    ]


def test_agent_command_envelope_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        group_chat_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/group-chats",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "name": "Smoke Command Council",
                "member_ids": ["player-1"],
            },
            headers=_headers(),
        )
        command_response = client.post(
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
                    {"channel": "world", "content": "Smoke bundled world briefing."},
                    {
                        "channel": "direct",
                        "recipient_id": "player-1",
                        "content": "Smoke bundled direct briefing.",
                    },
                    {
                        "channel": "group",
                        "group_chat_id": "group-chat-1",
                        "content": "Smoke bundled group briefing.",
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
        rejected_command_response = client.post(
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
                    {"channel": "world", "content": "Smoke rejected world briefing."},
                    {
                        "channel": "group",
                        "group_chat_id": "group-chat-missing",
                        "content": "Smoke rejected group briefing.",
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
        briefing_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/agent-briefing",
            params={"since_tick": 142},
            headers=_headers(),
        )

    assert group_chat_response.status_code == HTTPStatus.ACCEPTED
    assert command_response.status_code == HTTPStatus.ACCEPTED
    assert rejected_command_response.status_code == HTTPStatus.BAD_REQUEST
    assert rejected_command_response.json() == {
        "error": {
            "code": "group_chat_not_visible",
            "message": "Group chat 'group-chat-missing' is not visible to player 'player-2'.",
        }
    }
    assert command_response.json()["orders"]["submission_index"] == 0
    assert command_response.json()["alliance"]["player_id"] == "player-2"
    assert briefing_response.status_code == HTTPStatus.OK
    assert [message["content"] for message in briefing_response.json()["messages"]["direct"]] == [
        "Smoke bundled direct briefing."
    ]
    assert [message["content"] for message in briefing_response.json()["messages"]["group"]] == [
        "Smoke bundled group briefing."
    ]
    assert [message["content"] for message in briefing_response.json()["messages"]["world"]] == [
        "Smoke bundled world briefing."
    ]
    assert briefing_response.json()["treaties"][0]["player_b_id"] == "player-3"
