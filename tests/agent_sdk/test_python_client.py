from __future__ import annotations

from copy import deepcopy
from http import HTTPStatus
from typing import Any

import httpx
import pytest
from httpx import ASGITransport
from server.agent_registry import (
    InMemoryMatchRegistry,
    build_seeded_agent_api_key,
    build_seeded_match_records,
)
from server.main import create_app
from tests.support import load_python_agent_sdk_module


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


@pytest.fixture
def seeded_registry() -> InMemoryMatchRegistry:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)
    return registry


@pytest.fixture
def sdk_module() -> Any:
    return load_python_agent_sdk_module()


@pytest.fixture
def client(sdk_module: Any, seeded_registry: InMemoryMatchRegistry) -> Any:
    app = create_app(match_registry=seeded_registry)
    return sdk_module.IronCouncilClient(
        base_url="http://testserver",
        api_key=build_seeded_agent_api_key("agent-player-2"),
        transport=ASGITransport(app=app),
    )


def test_sdk_profile_and_match_methods_return_typed_authenticated_contracts(
    client: Any,
) -> None:
    matches = client.list_matches()
    profile = client.get_current_agent_profile()
    join = client.join_match("match-beta")
    state = client.get_match_state("match-beta")

    assert matches.matches[0].match_id == "match-alpha"
    assert matches.matches[1].match_id == "match-beta"
    assert profile.agent_id == "agent-player-2"
    assert profile.display_name == "Morgana"
    assert join.status == "accepted"
    assert join.match_id == "match-beta"
    assert join.player_id == "player-1"
    assert state.match_id == "match-beta"
    assert state.player_id == "player-1"


def test_sdk_workflow_methods_cover_orders_messages_treaties_and_alliances(
    client: Any,
    representative_order_payload: dict[str, Any],
) -> None:
    client.join_match("match-beta")

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

    order_response = client.submit_orders(
        "match-beta",
        tick=7,
        orders=order_payload["orders"],
    )
    sent_message = client.send_message(
        "match-alpha",
        tick=142,
        channel="world",
        content="Open briefing.",
    )
    inbox = client.get_messages("match-alpha")
    treaty = client.act_on_treaty(
        "match-alpha",
        counterparty_id="player-1",
        action="propose",
        treaty_type="trade",
    )
    treaties = client.get_treaties("match-alpha")
    alliance_response = client.act_on_alliance("match-alpha", action="leave")
    alliances = client.get_alliances("match-alpha")

    assert order_response.status == "accepted"
    assert order_response.match_id == "match-beta"
    assert order_response.player_id == "player-1"
    assert sent_message.status == "accepted"
    assert sent_message.channel == "world"
    assert sent_message.content == "Open briefing."
    assert inbox.player_id == "player-2"
    assert inbox.messages[0].content == "Open briefing."
    assert treaty.status == "accepted"
    assert treaty.treaty.status == "proposed"
    assert treaties.treaties[0].treaty_type == "trade"
    assert alliance_response.status == "accepted"
    assert alliance_response.player_id == "player-2"
    assert alliances.alliances[0].alliance_id == "alliance-red"


def test_sdk_wraps_structured_api_failures_without_leaking_api_key(
    sdk_module: Any,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    app = create_app(match_registry=seeded_registry)
    api_key = build_seeded_agent_api_key("agent-player-2")
    client = sdk_module.IronCouncilClient(
        base_url="http://testserver",
        api_key=api_key,
        transport=ASGITransport(app=app),
    )

    with pytest.raises(sdk_module.IronCouncilApiError) as exc_info:
        client.get_match_state("match-missing")

    error = exc_info.value
    assert error.status_code == HTTPStatus.NOT_FOUND
    assert error.error_code == "match_not_found"
    assert error.message == "Match 'match-missing' was not found."
    assert api_key not in repr(client)
    assert api_key not in str(error)
    assert api_key not in repr(error)


def test_sdk_wraps_transport_failures_in_clear_api_error(sdk_module: Any) -> None:
    class FailingTransport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom", request=request)

    client = sdk_module.IronCouncilClient(
        base_url="http://testserver",
        api_key=build_seeded_agent_api_key("agent-player-2"),
        transport=FailingTransport(),
    )

    with pytest.raises(sdk_module.IronCouncilApiError) as exc_info:
        client.list_matches()

    error = exc_info.value
    assert error.status_code is None
    assert error.error_code == "transport_error"
    assert error.message == "Request to Iron Council API failed."
