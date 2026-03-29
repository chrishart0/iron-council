from __future__ import annotations

from copy import deepcopy
from http import HTTPStatus
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from server.agent_registry import (
    InMemoryMatchRegistry,
    build_seeded_agent_api_key,
    build_seeded_match_records,
)
from server.auth import hash_api_key
from server.main import create_app
from server.models.api import AuthenticatedAgentContext


def _army_by_id(payload: dict[str, Any], army_id: str) -> dict[str, Any]:
    return next(army for army in payload["visible_armies"] if army["id"] == army_id)


def _match_state_dump(
    registry: InMemoryMatchRegistry, match_id: str = "match-alpha"
) -> dict[str, Any]:
    record = registry.get_match(match_id)
    assert record is not None
    return record.state.model_dump(mode="json")


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


def _join_payload(*, match_id: str = "match-beta") -> dict[str, Any]:
    return {"match_id": match_id}


def _agent_id_for_player(player_id: str) -> str:
    return f"agent-{player_id}"


def _auth_headers_for_agent(agent_id: str) -> dict[str, str]:
    return {"X-API-Key": build_seeded_agent_api_key(agent_id)}


def _auth_headers_for_player(player_id: str) -> dict[str, str]:
    return _auth_headers_for_agent(_agent_id_for_player(player_id))


@pytest.fixture
def seeded_registry() -> InMemoryMatchRegistry:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)
    return registry


@pytest.fixture
def app_client(seeded_registry: InMemoryMatchRegistry) -> AsyncClient:
    app = create_app(match_registry=seeded_registry)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    )


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
                "tick": 142,
                "tick_interval_seconds": 30,
            },
            {
                "match_id": "match-beta",
                "status": "paused",
                "tick": 7,
                "tick_interval_seconds": 45,
            },
        ]
    }


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
            "code": "invalid_api_key",
            "message": "A valid active X-API-Key header is required.",
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
    assert paths["/api/v1/matches/{match_id}/orders"]["post"]["responses"]["202"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/OrderAcceptanceResponse"}
