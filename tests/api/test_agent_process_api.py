from __future__ import annotations

from http import HTTPStatus
from typing import Any

import httpx
from server.agent_registry import build_seeded_agent_api_key
from tests.support import RunningApp


def test_running_app_lists_db_seeded_matches_and_serves_fog_filtered_state(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        list_response = client.get("/api/v1/matches")
        state_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/state",
            params={"player_id": "player-1"},
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
    assert payload["player_id"] == "player-1"
    assert payload["alliance_members"] == ["player-1", "player-2"]
    assert payload["cities"]["london"]["visibility"] == "full"
    assert payload["cities"]["birmingham"]["visibility"] == "partial"
    assert "inverness" not in payload["cities"]


def test_running_app_rejects_non_agent_profile_and_join_requests(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        profile_response = client.get("/api/v1/agents/agent-player-1/profile")
        join_response = client.post(
            f"/api/v1/matches/{running_seeded_app.secondary_match_id}/join",
            json={
                "match_id": running_seeded_app.secondary_match_id,
                "agent_id": "agent-player-1",
            },
        )

    assert profile_response.status_code == HTTPStatus.NOT_FOUND
    assert profile_response.json() == {
        "error": {
            "code": "agent_not_found",
            "message": "Agent 'agent-player-1' was not found.",
        }
    }
    assert join_response.status_code == HTTPStatus.NOT_FOUND
    assert join_response.json() == {
        "error": {
            "code": "agent_not_found",
            "message": "Agent 'agent-player-1' was not found.",
        }
    }


def test_running_app_serves_authenticated_current_agent_profile_from_db_registry(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        response = client.get(
            "/api/v1/agent/profile",
            headers={"X-API-Key": build_seeded_agent_api_key("agent-player-2")},
        )

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
    payload["player_id"] = "player-1"
    payload["tick"] = 141

    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/orders",
            json=payload,
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "error": {
            "code": "tick_mismatch",
            "message": "Order payload tick '141' does not match current match tick '142'.",
        }
    }


def test_running_app_posts_and_filters_visible_messages(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        world_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "sender_id": "player-1",
                "tick": 142,
                "channel": "world",
                "recipient_id": None,
                "content": "Open briefing.",
            },
        )
        direct_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "sender_id": "player-2",
                "tick": 142,
                "channel": "direct",
                "recipient_id": "player-1",
                "content": "Private briefing.",
            },
        )
        visible_to_player_one = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            params={"player_id": "player-1"},
        )
        visible_to_player_three = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            params={"player_id": "player-3"},
        )

    assert world_response.status_code == HTTPStatus.ACCEPTED
    assert direct_response.status_code == HTTPStatus.ACCEPTED
    assert visible_to_player_one.status_code == HTTPStatus.OK
    assert visible_to_player_one.json()["messages"] == [
        {
            "message_id": 0,
            "channel": "world",
            "sender_id": "player-1",
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
    ]
    assert visible_to_player_three.status_code == HTTPStatus.OK
    assert visible_to_player_three.json()["messages"] == [
        {
            "message_id": 0,
            "channel": "world",
            "sender_id": "player-1",
            "recipient_id": None,
            "tick": 142,
            "content": "Open briefing.",
        }
    ]


def test_running_app_processes_treaty_reads_and_public_announcements(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        propose_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/treaties",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "player_id": "player-2",
                "counterparty_id": "player-1",
                "action": "propose",
                "treaty_type": "trade",
            },
        )
        accept_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/treaties",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "player_id": "player-1",
                "counterparty_id": "player-2",
                "action": "accept",
                "treaty_type": "trade",
            },
        )
        treaty_read = client.get(f"/api/v1/matches/{running_seeded_app.primary_match_id}/treaties")
        visible_messages = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            params={"player_id": "player-5"},
        )

    assert propose_response.status_code == HTTPStatus.ACCEPTED
    assert accept_response.status_code == HTTPStatus.ACCEPTED
    assert treaty_read.status_code == HTTPStatus.OK
    assert treaty_read.json() == {
        "match_id": running_seeded_app.primary_match_id,
        "treaties": [
            {
                "treaty_id": 0,
                "player_a_id": "player-1",
                "player_b_id": "player-2",
                "treaty_type": "trade",
                "status": "active",
                "proposed_by": "player-2",
                "proposed_tick": 142,
                "signed_tick": 142,
                "withdrawn_by": None,
                "withdrawn_tick": None,
            }
        ],
    }
    assert visible_messages.status_code == HTTPStatus.OK
    assert visible_messages.json()["messages"] == [
        {
            "message_id": 0,
            "channel": "world",
            "sender_id": "system",
            "recipient_id": None,
            "tick": 142,
            "content": "Treaty signed: player-1 and player-2 entered a trade treaty.",
        }
    ]


def test_running_app_processes_alliance_reads_and_membership_updates(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        create_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/alliances",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "player_id": "player-3",
                "action": "create",
                "alliance_id": None,
                "name": "Northern Pact",
            },
        )
        join_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/alliances",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "player_id": "player-4",
                "action": "join",
                "alliance_id": "alliance-1",
                "name": None,
            },
        )
        alliance_read = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/alliances"
        )
        player_three_state = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/state",
            params={"player_id": "player-3"},
        )

    assert create_response.status_code == HTTPStatus.ACCEPTED
    assert join_response.status_code == HTTPStatus.ACCEPTED
    assert alliance_read.status_code == HTTPStatus.OK
    assert alliance_read.json() == {
        "match_id": running_seeded_app.primary_match_id,
        "alliances": [
            {
                "alliance_id": "alliance-1",
                "name": "Northern Pact",
                "leader_id": "player-3",
                "formed_tick": 142,
                "members": [
                    {"player_id": "player-3", "joined_tick": 142},
                    {"player_id": "player-4", "joined_tick": 142},
                ],
            },
            {
                "alliance_id": "alliance-red",
                "name": "Western Accord",
                "leader_id": "player-1",
                "formed_tick": 120,
                "members": [
                    {"player_id": "player-1", "joined_tick": 120},
                    {"player_id": "player-2", "joined_tick": 120},
                ],
            },
        ],
    }
    assert player_three_state.status_code == HTTPStatus.OK
    assert player_three_state.json()["alliance_id"] == "alliance-1"
    assert player_three_state.json()["alliance_members"] == ["player-3", "player-4"]
    assert player_three_state.json()["victory"] == {
        "leading_alliance": None,
        "cities_held": 2,
        "threshold": 13,
        "countdown_ticks_remaining": None,
    }


def test_running_app_reads_seeded_alliance_metadata_from_db_registry(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        alliance_read = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/alliances"
        )

    assert alliance_read.status_code == HTTPStatus.OK
    assert alliance_read.json() == {
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


def test_running_app_rejects_stale_and_future_messages_without_mutation(
    running_seeded_app: RunningApp,
) -> None:
    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        stale_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "sender_id": "player-1",
                "tick": 141,
                "channel": "world",
                "recipient_id": None,
                "content": "Stale message.",
            },
        )
        future_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "sender_id": "player-1",
                "tick": 143,
                "channel": "world",
                "recipient_id": None,
                "content": "Future message.",
            },
        )
        inbox_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/messages",
            params={"player_id": "player-1"},
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
        "player_id": "player-1",
        "messages": [],
    }
