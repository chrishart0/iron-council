from __future__ import annotations

from copy import deepcopy
from http import HTTPStatus
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from server.agent_registry import InMemoryMatchRegistry, build_seeded_match_records
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
