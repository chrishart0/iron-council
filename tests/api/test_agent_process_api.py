from __future__ import annotations

from http import HTTPStatus
from typing import Any

import httpx
from server.agent_registry import build_seeded_agent_api_key
from tests.support import RunningApp


def _headers(agent_id: str = "agent-player-2") -> dict[str, str]:
    return {"X-API-Key": build_seeded_agent_api_key(agent_id)}


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
                "tick": 142,
                "tick_interval_seconds": 30,
            },
            {
                "match_id": running_seeded_app.secondary_match_id,
                "status": "paused",
                "tick": 7,
                "tick_interval_seconds": 45,
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
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        response = client.get("/api/v1/agent/profile", headers=_headers())

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "agent_id": "agent-player-2",
        "display_name": "Morgana",
        "is_seeded": True,
        "rating": {"elo": 1190, "provisional": True},
        "history": {"matches_played": 0, "wins": 0, "losses": 0, "draws": 0},
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
        },
    }
    assert treaty_read.status_code == HTTPStatus.OK
    assert treaty_read.json() == {
        "match_id": running_seeded_app.primary_match_id,
        "treaties": [
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
        ],
    }


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
