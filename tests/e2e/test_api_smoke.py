from __future__ import annotations

from copy import deepcopy
from http import HTTPStatus
from typing import Any

import httpx
from server.agent_registry import build_seeded_agent_api_key
from tests.support import RunningApp


def _headers(agent_id: str = "agent-player-2") -> dict[str, str]:
    return {"X-API-Key": build_seeded_agent_api_key(agent_id)}


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
    assert [match["match_id"] for match in list_response.json()["matches"]] == [
        running_seeded_app.primary_match_id,
        running_seeded_app.secondary_match_id,
    ]
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


def test_agent_join_and_profile_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
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
        "rating": {"elo": 1190, "provisional": True},
        "history": {"matches_played": 0, "wins": 0, "losses": 0, "draws": 0},
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
        command_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/commands",
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

    assert command_response.status_code == HTTPStatus.ACCEPTED
    assert command_response.json()["orders"]["submission_index"] == 0
    assert command_response.json()["alliance"]["player_id"] == "player-2"
    assert briefing_response.status_code == HTTPStatus.OK
    assert [message["content"] for message in briefing_response.json()["messages"]["direct"]] == [
        "Smoke bundled direct briefing."
    ]
    assert [message["content"] for message in briefing_response.json()["messages"]["world"]] == [
        "Smoke bundled world briefing."
    ]
    assert briefing_response.json()["treaties"][0]["player_b_id"] == "player-3"
