from __future__ import annotations

from copy import deepcopy
from http import HTTPStatus
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from server.agent_registry import InMemoryMatchRegistry, MatchRecord
from server.main import create_app
from server.models.domain import MatchStatus
from server.models.state import MatchState


@pytest.fixture
def seeded_registry(representative_match_state_payload: dict[str, Any]) -> InMemoryMatchRegistry:
    state_payload = deepcopy(representative_match_state_payload)
    state_payload["armies"] = []
    state_payload["players"] = {
        "player-1": state_payload["players"].pop("player_uuid"),
        "player-2": deepcopy(representative_match_state_payload["players"]["player_uuid"]),
    }
    state_payload["cities"]["london"]["owner"] = "player-1"

    registry = InMemoryMatchRegistry()
    registry.seed_match(
        MatchRecord(
            match_id="match-alpha",
            status=MatchStatus.ACTIVE,
            tick_interval_seconds=30,
            state=MatchState.model_validate(state_payload),
        )
    )
    registry.seed_match(
        MatchRecord(
            match_id="match-beta",
            status=MatchStatus.PAUSED,
            tick_interval_seconds=45,
            state=MatchState.model_validate(
                {
                    **state_payload,
                    "tick": 7,
                }
            ),
        )
    )
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
    assert response.json() == {
        "match_id": "match-alpha",
        "tick": 142,
        "player_id": "player-1",
        "resources": {"food": 120, "production": 85, "money": 200},
        "cities": {
            "london": {
                "owner": "player-1",
                "visibility": "full",
                "population": 12,
                "resources": {"food": 3, "production": 2, "money": 8},
                "upgrades": {"economy": 2, "military": 1, "fortification": 0},
                "garrison": 15,
                "building_queue": [{"type": "fortification", "tier": 1, "ticks_remaining": 3}],
            }
        },
        "visible_armies": [],
        "alliance_id": None,
        "alliance_members": ["player-1"],
        "victory": {
            "leading_alliance": None,
            "cities_held": 13,
            "threshold": 13,
            "countdown_ticks_remaining": None,
        },
    }


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
    assert response.json()["paths"]["/api/v1/matches/{match_id}/state"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"] == {"$ref": "#/components/schemas/AgentStateProjection"}


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
async def test_submit_orders_accepts_valid_envelopes_and_records_them_deterministically(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = "match-alpha"
    payload["player_id"] = "player-1"

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

    second_payload = deepcopy(representative_order_payload)
    second_payload["match_id"] = "match-alpha"
    second_payload["player_id"] = "player-2"
    second_payload["tick"] = 143

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


@pytest.mark.asyncio
async def test_submit_orders_rejects_mismatched_match_id_without_mutating_stored_submissions(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = "match-beta"
    payload["player_id"] = "player-1"

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


@pytest.mark.asyncio
async def test_submit_orders_rejects_unknown_player_without_mutating_stored_submissions(
    app_client: AsyncClient,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = "match-alpha"
    payload["player_id"] = "player-missing"

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
