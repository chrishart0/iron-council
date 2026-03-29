from __future__ import annotations

from http import HTTPStatus
from typing import Any

import httpx
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
