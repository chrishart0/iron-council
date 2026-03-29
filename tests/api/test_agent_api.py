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
from server.main import create_app


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
    sender_id: str = "player-1",
    tick: int = 142,
    channel: str = "world",
    recipient_id: str | None = None,
    content: str = "Hold position.",
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "sender_id": sender_id,
        "tick": tick,
        "channel": channel,
        "recipient_id": recipient_id,
        "content": content,
    }


def _treaty_payload(
    *,
    match_id: str = "match-alpha",
    player_id: str = "player-2",
    counterparty_id: str = "player-1",
    action: str = "propose",
    treaty_type: str = "trade",
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "counterparty_id": counterparty_id,
        "action": action,
        "treaty_type": treaty_type,
    }


def _alliance_payload(
    *,
    match_id: str = "match-alpha",
    player_id: str = "player-3",
    action: str = "create",
    alliance_id: str | None = None,
    name: str | None = "Northern Pact",
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "action": action,
        "alliance_id": alliance_id,
        "name": name,
    }


def _join_payload(
    *,
    match_id: str = "match-beta",
    agent_id: str = "agent-player-2",
) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "agent_id": agent_id,
    }


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
async def test_list_matches_returns_stable_json_summaries(
    app_client: AsyncClient,
) -> None:
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
async def test_get_match_state_requires_player_id_and_returns_fog_filtered_payload(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        missing_player_response = await client.get("/api/v1/matches/match-alpha/state")
        response = await client.get(
            "/api/v1/matches/match-alpha/state",
            params={"player_id": "player-1"},
        )

    assert missing_player_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
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
    payload["player_id"] = "player-1"
    payload["tick"] = 142
    payload["orders"]["movements"] = [{"army_id": "army-b", "destination": "birmingham"}]

    async with app_client as client:
        list_response = await client.get("/api/v1/matches")
        initial_state_response = await client.get(
            "/api/v1/matches/match-alpha/state",
            params={"player_id": "player-1"},
        )
        submit_response = await client.post("/api/v1/matches/match-alpha/orders", json=payload)
        follow_up_state_response = await client.get(
            "/api/v1/matches/match-alpha/state",
            params={"player_id": "player-1"},
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
    assert seeded_registry.list_order_submissions("match-alpha") == [payload]


@pytest.mark.asyncio
async def test_get_match_state_rejects_unknown_match_and_unknown_player(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        unknown_match_response = await client.get(
            "/api/v1/matches/match-missing/state",
            params={"player_id": "player-1"},
        )
        unknown_player_response = await client.get(
            "/api/v1/matches/match-alpha/state",
            params={"player_id": "player-missing"},
        )

    assert unknown_match_response.status_code == HTTPStatus.NOT_FOUND
    assert unknown_match_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match 'match-missing' was not found.",
        }
    }
    assert unknown_player_response.status_code == HTTPStatus.NOT_FOUND
    assert unknown_player_response.json() == {
        "error": {
            "code": "player_not_found",
            "message": "Player 'player-missing' was not found in match 'match-alpha'.",
        }
    }


@pytest.mark.asyncio
async def test_get_match_state_exposes_agent_state_projection_in_openapi(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        response = await client.get("/openapi.json")

    assert response.status_code == HTTPStatus.OK
    openapi = response.json()
    assert openapi["paths"]["/api/v1/matches/{match_id}/state"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"] == {"$ref": "#/components/schemas/AgentStateProjection"}
    assert "match_id" in openapi["components"]["schemas"]["AgentStateProjection"]["required"]


@pytest.mark.asyncio
async def test_agent_endpoint_openapi_declares_structured_api_error_schemas(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        response = await client.get("/openapi.json")

    assert response.status_code == HTTPStatus.OK
    paths = response.json()["paths"]
    assert paths["/api/v1/matches/{match_id}/state"]["get"]["responses"]["404"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/orders"]["post"]["responses"]["400"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/orders"]["post"]["responses"]["404"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}


@pytest.mark.asyncio
async def test_message_endpoints_expose_stable_openapi_contracts(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        response = await client.get("/openapi.json")

    assert response.status_code == HTTPStatus.OK
    paths = response.json()["paths"]
    assert paths["/api/v1/matches/{match_id}/messages"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/MatchMessageInboxResponse"}
    assert paths["/api/v1/matches/{match_id}/messages"]["get"]["responses"]["404"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/messages"]["get"]["responses"]["422"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/messages"]["post"]["responses"]["202"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/MessageAcceptanceResponse"}
    assert paths["/api/v1/matches/{match_id}/messages"]["post"]["responses"]["400"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/messages"]["post"]["responses"]["404"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/messages"]["post"]["responses"]["422"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}


@pytest.mark.asyncio
async def test_submit_orders_accepts_valid_envelopes_and_records_them_deterministically(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = "match-alpha"
    payload["player_id"] = "player-1"
    payload["tick"] = 142
    payload["orders"]["movements"] = [{"army_id": "army-b", "destination": "birmingham"}]

    async with app_client as client:
        response = await client.post("/api/v1/matches/match-alpha/orders", json=payload)

    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "player_id": "player-1",
        "tick": 142,
        "submission_index": 0,
    }
    assert seeded_registry.list_order_submissions("match-alpha") == [payload]


@pytest.mark.asyncio
async def test_submit_orders_preserves_submission_order_across_multiple_accepted_posts(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    first_payload = deepcopy(representative_order_payload)
    first_payload["match_id"] = "match-alpha"
    first_payload["player_id"] = "player-1"
    first_payload["tick"] = 142
    first_payload["orders"]["movements"] = [{"army_id": "army-b", "destination": "birmingham"}]

    second_payload = deepcopy(representative_order_payload)
    second_payload["match_id"] = "match-alpha"
    second_payload["player_id"] = "player-2"
    second_payload["tick"] = 142
    second_payload["orders"]["movements"] = [{"army_id": "army-a", "destination": "leeds"}]

    async with app_client as client:
        first_response = await client.post("/api/v1/matches/match-alpha/orders", json=first_payload)
        second_response = await client.post(
            "/api/v1/matches/match-alpha/orders",
            json=second_payload,
        )

    assert first_response.status_code == HTTPStatus.ACCEPTED
    assert second_response.status_code == HTTPStatus.ACCEPTED
    assert first_response.json()["submission_index"] == 0
    assert second_response.json()["submission_index"] == 1
    assert seeded_registry.list_order_submissions("match-alpha") == [first_payload, second_payload]


@pytest.mark.asyncio
async def test_submit_orders_rejects_unknown_match_without_mutating_stored_submissions(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = "match-missing"
    payload["player_id"] = "player-1"
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        response = await client.post("/api/v1/matches/match-missing/orders", json=payload)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match 'match-missing' was not found.",
        }
    }
    assert seeded_registry.list_order_submissions("match-alpha") == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_submit_orders_rejects_mismatched_match_id_without_mutating_stored_submissions(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = "match-beta"
    payload["player_id"] = "player-1"
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        response = await client.post("/api/v1/matches/match-alpha/orders", json=payload)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "error": {
            "code": "match_id_mismatch",
            "message": (
                "Order payload match_id 'match-beta' does not match route match 'match-alpha'."
            ),
        }
    }
    assert seeded_registry.list_order_submissions("match-alpha") == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_submit_orders_rejects_stale_tick_without_mutating_stored_submissions(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = "match-alpha"
    payload["player_id"] = "player-1"
    payload["tick"] = 141
    payload["orders"]["movements"] = [{"army_id": "army-b", "destination": "birmingham"}]
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        response = await client.post("/api/v1/matches/match-alpha/orders", json=payload)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "error": {
            "code": "tick_mismatch",
            "message": "Order payload tick '141' does not match current match tick '142'.",
        }
    }
    assert seeded_registry.list_order_submissions("match-alpha") == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_submit_orders_rejects_unknown_player_without_mutating_stored_submissions(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = "match-alpha"
    payload["player_id"] = "player-missing"
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        response = await client.post("/api/v1/matches/match-alpha/orders", json=payload)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        "error": {
            "code": "player_not_found",
            "message": "Player 'player-missing' was not found in match 'match-alpha'.",
        }
    }
    assert seeded_registry.list_order_submissions("match-alpha") == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_submit_orders_rejects_malformed_payloads_with_validation_errors(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = "match-alpha"
    payload["player_id"] = "player-1"
    payload["tick"] = 142
    payload["orders"]["recruitment"] = [{"city": "london", "troops": 0}]
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        response = await client.post("/api/v1/matches/match-alpha/orders", json=payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["detail"][0]["loc"] == ["body", "orders", "recruitment", 0, "troops"]
    assert seeded_registry.list_order_submissions("match-alpha") == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_post_messages_accepts_world_and_direct_messages_and_lists_visible_history(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    world_payload = _message_payload(
        sender_id="player-1",
        channel="world",
        content="World update.",
    )
    direct_payload = _message_payload(
        sender_id="player-2",
        channel="direct",
        recipient_id="player-1",
        content="Private coordination.",
    )

    async with app_client as client:
        world_response = await client.post(
            "/api/v1/matches/match-alpha/messages", json=world_payload
        )
        direct_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=direct_payload,
        )
        inbox_for_player_one = await client.get(
            "/api/v1/matches/match-alpha/messages",
            params={"player_id": "player-1"},
        )
        inbox_for_player_three = await client.get(
            "/api/v1/matches/match-alpha/messages",
            params={"player_id": "player-3"},
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
async def test_post_messages_rejects_invalid_requests_without_mutating_message_history(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        unknown_match_response = await client.post(
            "/api/v1/matches/match-missing/messages",
            json=_message_payload(match_id="match-missing"),
        )
        mismatch_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(match_id="match-beta"),
        )
        unknown_sender_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(sender_id="player-missing"),
        )
        unsupported_recipient_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(channel="direct", recipient_id="player-missing"),
        )
        missing_recipient_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(channel="direct", recipient_id=None),
        )
        world_recipient_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(channel="world", recipient_id="player-2"),
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
                "Message payload match_id 'match-beta' does not match route match 'match-alpha'."
            ),
        }
    }
    assert unknown_sender_response.status_code == HTTPStatus.NOT_FOUND
    assert unknown_sender_response.json() == {
        "error": {
            "code": "player_not_found",
            "message": "Player 'player-missing' was not found in match 'match-alpha'.",
        }
    }
    assert unsupported_recipient_response.status_code == HTTPStatus.BAD_REQUEST
    assert unsupported_recipient_response.json() == {
        "error": {
            "code": "unsupported_recipient",
            "message": (
                "Direct messages require a recipient_id for a player in match 'match-alpha'."
            ),
        }
    }
    assert missing_recipient_response.status_code == HTTPStatus.BAD_REQUEST
    assert missing_recipient_response.json() == {
        "error": {
            "code": "unsupported_recipient",
            "message": (
                "Direct messages require a recipient_id for a player in match 'match-alpha'."
            ),
        }
    }
    assert world_recipient_response.status_code == HTTPStatus.BAD_REQUEST
    assert world_recipient_response.json() == {
        "error": {
            "code": "unsupported_recipient",
            "message": "World messages do not support recipient_id.",
        }
    }
    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    assert record.messages == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_post_messages_rejects_stale_and_future_ticks_without_mutating_message_history(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        stale_tick_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(tick=141),
        )
        future_tick_response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(tick=143),
        )

    assert stale_tick_response.status_code == HTTPStatus.BAD_REQUEST
    assert stale_tick_response.json() == {
        "error": {
            "code": "tick_mismatch",
            "message": "Message payload tick '141' does not match current match tick '142'.",
        }
    }
    assert future_tick_response.status_code == HTTPStatus.BAD_REQUEST
    assert future_tick_response.json() == {
        "error": {
            "code": "tick_mismatch",
            "message": "Message payload tick '143' does not match current match tick '142'.",
        }
    }
    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    assert record.messages == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_get_messages_rejects_unknown_match_and_unknown_player(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        unknown_match_response = await client.get(
            "/api/v1/matches/match-missing/messages",
            params={"player_id": "player-1"},
        )
        unknown_player_response = await client.get(
            "/api/v1/matches/match-alpha/messages",
            params={"player_id": "player-missing"},
        )

    assert unknown_match_response.status_code == HTTPStatus.NOT_FOUND
    assert unknown_match_response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match 'match-missing' was not found.",
        }
    }
    assert unknown_player_response.status_code == HTTPStatus.NOT_FOUND
    assert unknown_player_response.json() == {
        "error": {
            "code": "player_not_found",
            "message": "Player 'player-missing' was not found in match 'match-alpha'.",
        }
    }


@pytest.mark.asyncio
async def test_get_messages_requires_player_id_with_structured_api_error(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        response = await client.get("/api/v1/matches/match-alpha/messages")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json() == {
        "error": {
            "code": "missing_player_id",
            "message": "Query parameter 'player_id' is required.",
        }
    }
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_post_messages_rejects_empty_content_with_structured_api_error(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json=_message_payload(content=""),
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json() == {
        "error": {
            "code": "invalid_message_content",
            "message": "Message content must be at least 1 character long.",
        }
    }
    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    assert record.messages == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_post_messages_rejects_missing_required_fields_with_structured_api_error(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        response = await client.post(
            "/api/v1/matches/match-alpha/messages",
            json={},
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json() == {
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
async def test_get_match_state_preserves_fog_boundaries_across_multiple_players(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        allied_response = await client.get(
            "/api/v1/matches/match-alpha/state",
            params={"player_id": "player-1"},
        )
        enemy_response = await client.get(
            "/api/v1/matches/match-alpha/state",
            params={"player_id": "player-3"},
        )

    assert allied_response.status_code == HTTPStatus.OK
    assert enemy_response.status_code == HTTPStatus.OK

    allied_payload = allied_response.json()
    enemy_payload = enemy_response.json()

    assert allied_payload["cities"]["manchester"]["visibility"] == "full"
    assert allied_payload["cities"]["manchester"]["garrison"] == 9
    assert enemy_payload["cities"]["manchester"]["visibility"] == "partial"
    assert enemy_payload["cities"]["manchester"]["garrison"] == "unknown"
    assert _army_by_id(allied_payload, "army-a")["visibility"] == "full"
    assert _army_by_id(allied_payload, "army-a")["troops"] == 14
    assert _army_by_id(enemy_payload, "army-a")["visibility"] == "partial"
    assert _army_by_id(enemy_payload, "army-a")["troops"] == "unknown"
    assert not any(army["id"] == "army-z" for army in allied_payload["visible_armies"])
    assert not any(army["id"] == "army-z" for army in enemy_payload["visible_armies"])


@pytest.mark.asyncio
async def test_treaty_endpoints_expose_stable_openapi_contracts(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        response = await client.get("/openapi.json")

    assert response.status_code == HTTPStatus.OK
    paths = response.json()["paths"]
    assert paths["/api/v1/matches/{match_id}/treaties"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/TreatyListResponse"}
    assert paths["/api/v1/matches/{match_id}/treaties"]["get"]["responses"]["404"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/treaties"]["post"]["responses"]["202"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/TreatyActionAcceptanceResponse"}
    assert paths["/api/v1/matches/{match_id}/treaties"]["post"]["responses"]["400"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/treaties"]["post"]["responses"]["404"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}


@pytest.mark.asyncio
async def test_treaty_lifecycle_reads_are_deterministic_and_world_announcements_are_public(
    app_client: AsyncClient,
) -> None:
    propose_payload = _treaty_payload()
    accept_payload = _treaty_payload(
        action="accept",
        player_id="player-1",
        counterparty_id="player-2",
    )
    withdraw_payload = _treaty_payload(action="withdraw")

    async with app_client as client:
        initial_read = await client.get("/api/v1/matches/match-alpha/treaties")
        propose_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=propose_payload,
        )
        after_propose_read = await client.get("/api/v1/matches/match-alpha/treaties")
        accept_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=accept_payload,
        )
        first_active_read = await client.get("/api/v1/matches/match-alpha/treaties")
        second_active_read = await client.get("/api/v1/matches/match-alpha/treaties")
        messages_after_accept = await client.get(
            "/api/v1/matches/match-alpha/messages",
            params={"player_id": "player-3"},
        )
        withdraw_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=withdraw_payload,
        )
        first_withdrawn_read = await client.get("/api/v1/matches/match-alpha/treaties")
        second_withdrawn_read = await client.get("/api/v1/matches/match-alpha/treaties")
        messages_after_withdraw = await client.get(
            "/api/v1/matches/match-alpha/messages",
            params={"player_id": "player-4"},
        )

    assert initial_read.status_code == HTTPStatus.OK
    assert initial_read.json() == {"match_id": "match-alpha", "treaties": []}

    assert propose_response.status_code == HTTPStatus.ACCEPTED
    assert propose_response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
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
    assert after_propose_read.status_code == HTTPStatus.OK
    assert after_propose_read.json() == {
        "match_id": "match-alpha",
        "treaties": [propose_response.json()["treaty"]],
    }

    assert accept_response.status_code == HTTPStatus.ACCEPTED
    assert accept_response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "treaty": {
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
        },
    }
    assert first_active_read.status_code == HTTPStatus.OK
    assert first_active_read.json() == {
        "match_id": "match-alpha",
        "treaties": [accept_response.json()["treaty"]],
    }
    assert second_active_read.json() == first_active_read.json()
    assert messages_after_accept.status_code == HTTPStatus.OK
    assert messages_after_accept.json() == {
        "match_id": "match-alpha",
        "player_id": "player-3",
        "messages": [
            {
                "message_id": 0,
                "channel": "world",
                "sender_id": "system",
                "recipient_id": None,
                "tick": 142,
                "content": "Treaty signed: player-1 and player-2 entered a trade treaty.",
            }
        ],
    }

    assert withdraw_response.status_code == HTTPStatus.ACCEPTED
    assert withdraw_response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "treaty": {
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
        },
    }
    assert first_withdrawn_read.status_code == HTTPStatus.OK
    assert first_withdrawn_read.json() == {
        "match_id": "match-alpha",
        "treaties": [withdraw_response.json()["treaty"]],
    }
    assert second_withdrawn_read.json() == first_withdrawn_read.json()
    assert messages_after_withdraw.status_code == HTTPStatus.OK
    assert messages_after_withdraw.json() == {
        "match_id": "match-alpha",
        "player_id": "player-4",
        "messages": [
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
        ],
    }


@pytest.mark.asyncio
async def test_treaty_reads_return_stable_ordering_across_multiple_treaties(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        first_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(
                player_id="player-5",
                counterparty_id="player-3",
                treaty_type="defensive",
            ),
        )
        second_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(
                player_id="player-4",
                counterparty_id="player-1",
                treaty_type="non_aggression",
            ),
        )
        read_response = await client.get("/api/v1/matches/match-alpha/treaties")

    assert first_response.status_code == HTTPStatus.ACCEPTED
    assert second_response.status_code == HTTPStatus.ACCEPTED
    assert read_response.status_code == HTTPStatus.OK
    assert read_response.json() == {
        "match_id": "match-alpha",
        "treaties": [
            {
                "treaty_id": 1,
                "player_a_id": "player-1",
                "player_b_id": "player-4",
                "treaty_type": "non_aggression",
                "status": "proposed",
                "proposed_by": "player-4",
                "proposed_tick": 142,
                "signed_tick": None,
                "withdrawn_by": None,
                "withdrawn_tick": None,
            },
            {
                "treaty_id": 0,
                "player_a_id": "player-3",
                "player_b_id": "player-5",
                "treaty_type": "defensive",
                "status": "proposed",
                "proposed_by": "player-5",
                "proposed_tick": 142,
                "signed_tick": None,
                "withdrawn_by": None,
                "withdrawn_tick": None,
            },
        ],
    }


@pytest.mark.asyncio
async def test_treaty_actions_reject_invalid_requests_without_mutating_state_or_messages(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        unknown_match_response = await client.post(
            "/api/v1/matches/match-missing/treaties",
            json=_treaty_payload(match_id="match-missing"),
        )
        mismatch_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(match_id="match-beta"),
        )
        unknown_player_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(player_id="player-missing"),
        )
        unknown_counterparty_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(counterparty_id="player-missing"),
        )
        self_target_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(player_id="player-1", counterparty_id="player-1"),
        )
        missing_treaty_withdrawal_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(action="withdraw"),
        )
        unsupported_accept_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(action="accept"),
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
                "Treaty payload match_id 'match-beta' does not match route match 'match-alpha'."
            ),
        }
    }
    assert unknown_player_response.status_code == HTTPStatus.NOT_FOUND
    assert unknown_player_response.json() == {
        "error": {
            "code": "player_not_found",
            "message": "Player 'player-missing' was not found in match 'match-alpha'.",
        }
    }
    assert unknown_counterparty_response.status_code == HTTPStatus.NOT_FOUND
    assert unknown_counterparty_response.json() == {
        "error": {
            "code": "player_not_found",
            "message": "Player 'player-missing' was not found in match 'match-alpha'.",
        }
    }
    assert self_target_response.status_code == HTTPStatus.BAD_REQUEST
    assert self_target_response.json() == {
        "error": {
            "code": "self_targeted_treaty",
            "message": "Treaty actions require two different players.",
        }
    }
    assert missing_treaty_withdrawal_response.status_code == HTTPStatus.BAD_REQUEST
    assert missing_treaty_withdrawal_response.json() == {
        "error": {
            "code": "treaty_not_found",
            "message": "No treaty exists for players 'player-1' and 'player-2' with type 'trade'.",
        }
    }
    assert unsupported_accept_response.status_code == HTTPStatus.BAD_REQUEST
    assert unsupported_accept_response.json() == {
        "error": {
            "code": "unsupported_treaty_transition",
            "message": "Cannot accept treaty 'trade' for players 'player-1' and 'player-2'.",
        }
    }
    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    assert record.messages == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_post_treaties_maps_validation_failures_to_structured_api_errors(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        invalid_action_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(action="sign"),
        )
        invalid_treaty_type_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json=_treaty_payload(treaty_type="alliance"),
        )
        missing_fields_response = await client.post(
            "/api/v1/matches/match-alpha/treaties",
            json={},
        )

    assert invalid_action_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert invalid_action_response.json() == {
        "error": {
            "code": "invalid_treaty_action",
            "message": "Treaty action must be one of: propose, accept, withdraw.",
        }
    }
    assert invalid_treaty_type_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert invalid_treaty_type_response.json() == {
        "error": {
            "code": "invalid_treaty_type",
            "message": "Treaty type must be one of: non_aggression, defensive, trade.",
        }
    }
    assert missing_fields_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert missing_fields_response.json() == {
        "error": {
            "code": "invalid_treaty_request",
            "message": "Treaty request is missing required fields.",
        }
    }
    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    assert record.treaties == []
    assert record.messages == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_get_treaties_rejects_unknown_match(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        response = await client.get("/api/v1/matches/match-missing/treaties")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match 'match-missing' was not found.",
        }
    }


@pytest.mark.asyncio
async def test_alliance_endpoints_expose_stable_openapi_contracts(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        response = await client.get("/openapi.json")

    assert response.status_code == HTTPStatus.OK
    paths = response.json()["paths"]
    assert paths["/api/v1/matches/{match_id}/alliances"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/AllianceListResponse"}
    assert paths["/api/v1/matches/{match_id}/alliances"]["get"]["responses"]["404"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/alliances"]["post"]["responses"]["202"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/AllianceActionAcceptanceResponse"}
    assert paths["/api/v1/matches/{match_id}/alliances"]["post"]["responses"]["400"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/alliances"]["post"]["responses"]["404"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/alliances"]["post"]["responses"]["422"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}


@pytest.mark.asyncio
async def test_alliance_lifecycle_reads_are_deterministic_and_update_canonical_membership(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    create_payload = _alliance_payload(player_id="player-3", action="create", name="Northern Pact")
    join_payload = _alliance_payload(
        player_id="player-4",
        action="join",
        alliance_id="alliance-1",
        name=None,
    )
    leave_payload = _alliance_payload(
        player_id="player-4",
        action="leave",
        alliance_id=None,
        name=None,
    )

    async with app_client as client:
        initial_read = await client.get("/api/v1/matches/match-alpha/alliances")
        create_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=create_payload,
        )
        after_create_read = await client.get("/api/v1/matches/match-alpha/alliances")
        after_create_state = await client.get(
            "/api/v1/matches/match-alpha/state",
            params={"player_id": "player-3"},
        )
        join_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=join_payload,
        )
        first_join_read = await client.get("/api/v1/matches/match-alpha/alliances")
        second_join_read = await client.get("/api/v1/matches/match-alpha/alliances")
        joined_state = await client.get(
            "/api/v1/matches/match-alpha/state",
            params={"player_id": "player-3"},
        )
        leave_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=leave_payload,
        )
        first_leave_read = await client.get("/api/v1/matches/match-alpha/alliances")
        second_leave_read = await client.get("/api/v1/matches/match-alpha/alliances")
        after_leave_state = await client.get(
            "/api/v1/matches/match-alpha/state",
            params={"player_id": "player-3"},
        )

    assert initial_read.status_code == HTTPStatus.OK
    assert initial_read.json() == {
        "match_id": "match-alpha",
        "alliances": [
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
        ],
    }

    assert create_response.status_code == HTTPStatus.ACCEPTED
    assert create_response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "player_id": "player-3",
        "alliance": {
            "alliance_id": "alliance-1",
            "name": "Northern Pact",
            "leader_id": "player-3",
            "formed_tick": 142,
            "members": [{"player_id": "player-3", "joined_tick": 142}],
        },
    }
    assert after_create_read.status_code == HTTPStatus.OK
    assert after_create_read.json() == {
        "match_id": "match-alpha",
        "alliances": [
            create_response.json()["alliance"],
            initial_read.json()["alliances"][0],
        ],
    }
    assert after_create_state.status_code == HTTPStatus.OK
    assert after_create_state.json()["victory"] == {
        "leading_alliance": "alliance-red",
        "cities_held": 2,
        "threshold": 13,
        "countdown_ticks_remaining": None,
    }

    assert join_response.status_code == HTTPStatus.ACCEPTED
    assert join_response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "player_id": "player-4",
        "alliance": {
            "alliance_id": "alliance-1",
            "name": "Northern Pact",
            "leader_id": "player-3",
            "formed_tick": 142,
            "members": [
                {"player_id": "player-3", "joined_tick": 142},
                {"player_id": "player-4", "joined_tick": 142},
            ],
        },
    }
    assert first_join_read.status_code == HTTPStatus.OK
    assert first_join_read.json() == {
        "match_id": "match-alpha",
        "alliances": [
            join_response.json()["alliance"],
            initial_read.json()["alliances"][0],
        ],
    }
    assert second_join_read.json() == first_join_read.json()
    assert joined_state.status_code == HTTPStatus.OK
    assert joined_state.json()["alliance_id"] == "alliance-1"
    assert joined_state.json()["alliance_members"] == ["player-3", "player-4"]
    assert joined_state.json()["victory"] == {
        "leading_alliance": None,
        "cities_held": 2,
        "threshold": 13,
        "countdown_ticks_remaining": None,
    }

    assert leave_response.status_code == HTTPStatus.ACCEPTED
    assert leave_response.json() == {
        "status": "accepted",
        "match_id": "match-alpha",
        "player_id": "player-4",
        "alliance": {
            "alliance_id": "alliance-1",
            "name": "Northern Pact",
            "leader_id": "player-3",
            "formed_tick": 142,
            "members": [{"player_id": "player-3", "joined_tick": 142}],
        },
    }
    assert first_leave_read.status_code == HTTPStatus.OK
    assert first_leave_read.json() == {
        "match_id": "match-alpha",
        "alliances": [
            leave_response.json()["alliance"],
            initial_read.json()["alliances"][0],
        ],
    }
    assert second_leave_read.json() == first_leave_read.json()
    assert after_leave_state.status_code == HTTPStatus.OK
    assert after_leave_state.json()["victory"] == {
        "leading_alliance": "alliance-red",
        "cities_held": 2,
        "threshold": 13,
        "countdown_ticks_remaining": None,
    }

    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    assert record.state.players["player-3"].alliance_id == "alliance-1"
    assert record.state.players["player-4"].alliance_id is None


@pytest.mark.asyncio
async def test_alliance_actions_reject_invalid_requests_without_mutating_state(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        unknown_match_response = await client.post(
            "/api/v1/matches/match-missing/alliances",
            json=_alliance_payload(match_id="match-missing"),
        )
        mismatch_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(match_id="match-beta"),
        )
        unknown_player_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(player_id="player-missing"),
        )
        already_allied_create_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(player_id="player-1", action="create", name="Second Pact"),
        )
        unknown_alliance_join_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(
                player_id="player-3",
                action="join",
                alliance_id="alliance-missing",
                name=None,
            ),
        )
        not_allied_leave_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(
                player_id="player-5", action="leave", alliance_id=None, name=None
            ),
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
                "Alliance payload match_id 'match-beta' does not match route match 'match-alpha'."
            ),
        }
    }
    assert unknown_player_response.status_code == HTTPStatus.NOT_FOUND
    assert unknown_player_response.json() == {
        "error": {
            "code": "player_not_found",
            "message": "Player 'player-missing' was not found in match 'match-alpha'.",
        }
    }
    assert already_allied_create_response.status_code == HTTPStatus.BAD_REQUEST
    assert already_allied_create_response.json() == {
        "error": {
            "code": "player_already_in_alliance",
            "message": "Player 'player-1' is already in alliance 'alliance-red'.",
        }
    }
    assert unknown_alliance_join_response.status_code == HTTPStatus.BAD_REQUEST
    assert unknown_alliance_join_response.json() == {
        "error": {
            "code": "alliance_not_found",
            "message": "Alliance 'alliance-missing' was not found in match 'match-alpha'.",
        }
    }
    assert not_allied_leave_response.status_code == HTTPStatus.BAD_REQUEST
    assert not_allied_leave_response.json() == {
        "error": {
            "code": "player_not_in_alliance",
            "message": "Player 'player-5' is not currently in an alliance.",
        }
    }

    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    assert record.messages == []
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_post_alliances_maps_validation_failures_to_structured_api_errors(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    before_state = _match_state_dump(seeded_registry)

    async with app_client as client:
        invalid_action_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(action="invite"),
        )
        missing_fields_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json={},
        )
        create_with_alliance_id_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(alliance_id="alliance-stray"),
        )
        join_missing_alliance_id_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(action="join", alliance_id=None, name=None),
        )
        join_with_name_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(action="join", alliance_id="alliance-red", name="Stray Name"),
        )
        leave_with_alliance_id_response = await client.post(
            "/api/v1/matches/match-alpha/alliances",
            json=_alliance_payload(
                player_id="player-1",
                action="leave",
                alliance_id="alliance-red",
                name=None,
            ),
        )

    assert invalid_action_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert invalid_action_response.json() == {
        "error": {
            "code": "invalid_alliance_action",
            "message": "Alliance action must be one of: create, join, leave.",
        }
    }
    assert missing_fields_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert missing_fields_response.json() == {
        "error": {
            "code": "invalid_alliance_request",
            "message": "Alliance request is missing required fields.",
        }
    }
    assert create_with_alliance_id_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert create_with_alliance_id_response.json() == {
        "error": {
            "code": "invalid_alliance_request",
            "message": "Alliance create does not accept alliance_id.",
        }
    }
    assert join_missing_alliance_id_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert join_missing_alliance_id_response.json() == {
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

    record = seeded_registry.get_match("match-alpha")
    assert record is not None
    assert _match_state_dump(seeded_registry) == before_state


@pytest.mark.asyncio
async def test_get_alliances_rejects_unknown_match(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        response = await client.get("/api/v1/matches/match-missing/alliances")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        "error": {
            "code": "match_not_found",
            "message": "Match 'match-missing' was not found.",
        }
    }


@pytest.mark.asyncio
async def test_join_match_assigns_deterministic_slot_and_returns_idempotent_result(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        first_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(agent_id="agent-player-2"),
        )
        repeat_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(agent_id="agent-player-2"),
        )
        second_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(agent_id="agent-player-3"),
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
async def test_join_match_rejects_unknown_agent_and_non_joinable_match_without_consuming_slots(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        unknown_agent_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(agent_id="agent-missing"),
        )
        non_joinable_response = await client.post(
            "/api/v1/matches/match-alpha/join",
            json=_join_payload(match_id="match-alpha", agent_id="agent-player-2"),
        )
        follow_up_join_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(agent_id="agent-player-2"),
        )

    assert unknown_agent_response.status_code == HTTPStatus.NOT_FOUND
    assert unknown_agent_response.json() == {
        "error": {
            "code": "agent_not_found",
            "message": "Agent 'agent-missing' was not found.",
        }
    }
    assert non_joinable_response.status_code == HTTPStatus.BAD_REQUEST
    assert non_joinable_response.json() == {
        "error": {
            "code": "match_not_joinable",
            "message": "Match 'match-alpha' does not support agent joins.",
        }
    }
    assert follow_up_join_response.status_code == HTTPStatus.ACCEPTED
    assert follow_up_join_response.json()["player_id"] == "player-1"


@pytest.mark.asyncio
async def test_get_agent_profile_returns_stable_profile_shape_and_404_for_unknown_agent(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        profile_response = await client.get("/api/v1/agents/agent-player-2/profile")
        missing_response = await client.get("/api/v1/agents/agent-missing/profile")

    assert profile_response.status_code == HTTPStatus.OK
    assert profile_response.json() == {
        "agent_id": "agent-player-2",
        "display_name": "Morgana",
        "is_seeded": True,
        "rating": {"elo": 1190, "provisional": True},
        "history": {"matches_played": 0, "wins": 0, "losses": 0, "draws": 0},
    }
    assert missing_response.status_code == HTTPStatus.NOT_FOUND
    assert missing_response.json() == {
        "error": {
            "code": "agent_not_found",
            "message": "Agent 'agent-missing' was not found.",
        }
    }


@pytest.mark.asyncio
async def test_authenticated_agent_profile_requires_valid_active_api_key(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        missing_key_response = await client.get("/api/v1/agent/profile")
        invalid_key_response = await client.get(
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


@pytest.mark.asyncio
async def test_authenticated_agent_profile_rejects_inactive_seeded_api_keys(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    seeded_registry.deactivate_agent_api_key("agent-player-2")

    async with app_client as client:
        response = await client.get(
            "/api/v1/agent/profile",
            headers={"X-API-Key": build_seeded_agent_api_key("agent-player-2")},
        )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {
        "error": {
            "code": "invalid_api_key",
            "message": "A valid active X-API-Key header is required.",
        }
    }


@pytest.mark.asyncio
async def test_authenticated_agent_profile_returns_current_agent_without_exposing_api_key(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        response = await client.get(
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
    assert "api_key" not in response.text.lower()


@pytest.mark.asyncio
async def test_join_and_profile_endpoints_expose_stable_openapi_contracts(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        response = await client.get("/openapi.json")

    assert response.status_code == HTTPStatus.OK
    paths = response.json()["paths"]
    assert paths["/api/v1/matches/{match_id}/join"]["post"]["responses"]["202"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/MatchJoinResponse"}
    assert paths["/api/v1/matches/{match_id}/join"]["post"]["responses"]["400"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/join"]["post"]["responses"]["404"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/matches/{match_id}/join"]["post"]["responses"]["422"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/agents/{agent_id}/profile"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/AgentProfileResponse"}
    assert paths["/api/v1/agents/{agent_id}/profile"]["get"]["responses"]["404"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiErrorResponse"}
    assert paths["/api/v1/agent/profile"]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/AgentProfileResponse"}
    assert paths["/api/v1/agent/profile"]["get"]["responses"]["401"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/ApiErrorResponse"}


@pytest.mark.asyncio
async def test_join_match_rejects_unknown_match_mismatched_payload_and_invalid_validation(
    app_client: AsyncClient,
) -> None:
    async with app_client as client:
        unknown_match_response = await client.post(
            "/api/v1/matches/match-missing/join",
            json=_join_payload(match_id="match-missing", agent_id="agent-player-2"),
        )
        mismatch_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json=_join_payload(match_id="match-alpha", agent_id="agent-player-2"),
        )
        missing_agent_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json={"match_id": "match-beta"},
        )
        invalid_agent_response = await client.post(
            "/api/v1/matches/match-beta/join",
            json={"match_id": "match-beta", "agent_id": 123},
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
                "Join payload match_id 'match-alpha' does not match route match 'match-beta'."
            ),
        }
    }
    assert missing_agent_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert missing_agent_response.json() == {
        "error": {
            "code": "invalid_join_request",
            "message": "Join request is missing required fields.",
        }
    }
    assert invalid_agent_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert invalid_agent_response.json() == {
        "error": {
            "code": "invalid_join_request",
            "message": "Join request validation failed.",
        }
    }
