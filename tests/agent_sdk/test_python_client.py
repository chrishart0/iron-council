from __future__ import annotations

import os
import subprocess
import sys
from copy import deepcopy
from http import HTTPStatus
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
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
    with TestClient(app, base_url="http://testserver") as session:
        yield sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key=build_seeded_agent_api_key("agent-player-2"),
            session=session,
        )


def test_sdk_module_is_importable_without_repo_server_package() -> None:
    sdk_dir = Path(__file__).resolve().parents[2] / "agent-sdk/python"
    import_script = """
import builtins

real_import = builtins.__import__

def blocked_import(name, *args, **kwargs):
    if name == "server" or name.startswith("server."):
        raise ModuleNotFoundError("server blocked for standalone SDK import")
    return real_import(name, *args, **kwargs)

builtins.__import__ = blocked_import
import iron_council_client
"""

    with pytest.MonkeyPatch.context() as monkeypatch:
        isolated_path = os.pathsep.join([str(sdk_dir)])
        isolated_env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("COVERAGE") and not key.startswith("COV_CORE")
        }
        monkeypatch.chdir(Path("/tmp"))
        result = subprocess.run(
            [sys.executable, "-c", import_script],
            check=False,
            capture_output=True,
            text=True,
            env={**isolated_env, "PYTHONPATH": isolated_path},
        )

    assert result.returncode == 0, result.stderr


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


def test_sdk_submit_command_covers_bundled_authenticated_actions(
    client: Any,
    representative_order_payload: dict[str, Any],
) -> None:
    order_batch = deepcopy(representative_order_payload["orders"])
    order_batch["movements"] = [{"army_id": "army-b", "destination": "birmingham"}]
    order_batch["recruitment"] = []
    order_batch["upgrades"] = []
    order_batch["transfers"] = []
    group_chat = client.create_group_chat(
        "match-alpha",
        tick=142,
        name="SDK Command Council",
        member_ids=["player-1"],
    )

    response = client.submit_command(
        "match-alpha",
        tick=142,
        orders=order_batch,
        messages=[
            {
                "channel": "world",
                "content": "Bundled update.",
            },
            {
                "channel": "group",
                "group_chat_id": group_chat.group_chat.group_chat_id,
                "content": "Bundled group update.",
            },
        ],
        treaties=[
            {
                "counterparty_id": "player-1",
                "action": "propose",
                "treaty_type": "trade",
            }
        ],
        alliance={
            "action": "leave",
            "alliance_id": None,
            "name": None,
        },
    )

    assert response.status == "accepted"
    assert response.match_id == "match-alpha"
    assert response.player_id == "player-2"
    assert response.orders is not None
    assert response.orders.submission_index == 0
    assert response.messages[0].content == "Bundled update."
    assert response.messages[1].message.content == "Bundled group update."
    assert response.treaties[0].treaty.treaty_type == "trade"
    assert response.alliance is not None
    assert response.alliance.player_id == "player-2"


def test_sdk_submit_command_envelope_remains_a_backward_compatible_alias(
    sdk_module: Any,
) -> None:
    captured_request: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["path"] = request.url.path
        return httpx.Response(
            status_code=HTTPStatus.ACCEPTED,
            json={
                "status": "accepted",
                "match_id": "match-alpha",
                "player_id": "player-2",
                "tick": 142,
                "orders": None,
                "messages": [],
                "treaties": [],
                "alliance": None,
            },
        )

    session = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://testserver",
    )
    try:
        client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key="test-key",
            session=session,
        )

        response = client.submit_command_envelope("match-alpha", tick=142)
    finally:
        session.close()

    assert captured_request == {"method": "POST", "path": "/api/v1/matches/match-alpha/command"}
    assert response.status == "accepted"


def test_sdk_submit_command_rejects_invalid_group_messages_without_partial_writes(
    sdk_module: Any,
    seeded_registry: InMemoryMatchRegistry,
    representative_order_payload: dict[str, Any],
) -> None:
    app = create_app(match_registry=seeded_registry)
    with TestClient(app, base_url="http://testserver") as session:
        client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key=build_seeded_agent_api_key("agent-player-2"),
            session=session,
        )

        group_chat = client.create_group_chat(
            "match-alpha",
            tick=142,
            name="SDK Negative Council",
            member_ids=["player-1"],
        )

        with pytest.raises(sdk_module.IronCouncilApiError) as exc_info:
            client.submit_command(
                "match-alpha",
                tick=142,
                orders={
                    **deepcopy(representative_order_payload["orders"]),
                    "movements": [{"army_id": "army-b", "destination": "birmingham"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
                messages=[
                    {"channel": "world", "content": "Rejected bundled update."},
                    {
                        "channel": "group",
                        "group_chat_id": "group-chat-missing",
                        "content": "Rejected bundled group update.",
                    },
                ],
                treaties=[
                    {
                        "counterparty_id": "player-1",
                        "action": "propose",
                        "treaty_type": "trade",
                    }
                ],
                alliance={"action": "leave", "alliance_id": None, "name": None},
            )

        inbox = client.get_messages("match-alpha")
        group_messages = client.get_group_chat_messages(
            "match-alpha",
            group_chat_id=group_chat.group_chat.group_chat_id,
        )
        treaties = client.get_treaties("match-alpha")

    error = exc_info.value
    assert error.status_code == HTTPStatus.BAD_REQUEST
    assert error.error_code == "group_chat_not_visible"
    assert error.message == "Group chat 'group-chat-missing' is not visible to player 'player-2'."
    assert inbox.messages == []
    assert group_messages.messages == []
    assert treaties.treaties == []


def test_sdk_get_agent_briefing_propagates_since_tick_and_parses_typed_response(
    sdk_module: Any,
) -> None:
    captured_request: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["path"] = request.url.path
        captured_request["query"] = dict(request.url.params)
        return httpx.Response(
            status_code=HTTPStatus.OK,
            json={
                "match_id": "match-alpha",
                "player_id": "player-2",
                "state": {
                    "match_id": "match-alpha",
                    "tick": 142,
                    "player_id": "player-2",
                    "resources": {"food": 12, "production": 7, "money": 9},
                    "cities": {},
                    "visible_armies": [],
                    "alliance_id": "alliance-red",
                    "alliance_members": ["player-1", "player-2"],
                    "victory": {
                        "leading_alliance": "alliance-red",
                        "cities_held": 2,
                        "threshold": 18,
                        "countdown_ticks_remaining": None,
                    },
                },
                "alliances": [
                    {
                        "alliance_id": "alliance-red",
                        "name": "Red Pact",
                        "leader_id": "player-1",
                        "formed_tick": 140,
                        "members": [
                            {"player_id": "player-1", "joined_tick": 140},
                            {"player_id": "player-2", "joined_tick": 140},
                        ],
                    }
                ],
                "treaties": [
                    {
                        "treaty_id": 3,
                        "player_a_id": "player-2",
                        "player_b_id": "player-3",
                        "treaty_type": "trade",
                        "status": "active",
                        "proposed_by": "player-2",
                        "proposed_tick": 141,
                        "signed_tick": 142,
                        "withdrawn_by": None,
                        "withdrawn_tick": None,
                    }
                ],
                "group_chats": [
                    {
                        "group_chat_id": "group-chat-7",
                        "name": "Northern Channel",
                        "member_ids": ["player-1", "player-2"],
                        "created_by": "player-2",
                        "created_tick": 141,
                    }
                ],
                "messages": {
                    "direct": [
                        {
                            "message_id": 9,
                            "channel": "direct",
                            "sender_id": "player-1",
                            "recipient_id": "player-2",
                            "tick": 142,
                            "content": "Direct briefing.",
                        }
                    ],
                    "group": [
                        {
                            "message_id": 10,
                            "group_chat_id": "group-chat-7",
                            "sender_id": "player-1",
                            "tick": 142,
                            "content": "Group briefing.",
                        }
                    ],
                    "world": [
                        {
                            "message_id": 11,
                            "channel": "world",
                            "sender_id": "player-3",
                            "recipient_id": None,
                            "tick": 142,
                            "content": "World briefing.",
                        }
                    ],
                },
            },
        )

    session = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://testserver",
    )
    try:
        client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key="test-key",
            session=session,
        )

        briefing = client.get_agent_briefing("match-alpha", since_tick=142)
    finally:
        session.close()

    assert captured_request == {
        "method": "GET",
        "path": "/api/v1/matches/match-alpha/agent-briefing",
        "query": {"since_tick": "142"},
    }
    assert isinstance(briefing, sdk_module.AgentBriefingResponse)
    assert briefing.match_id == "match-alpha"
    assert briefing.player_id == "player-2"
    assert briefing.state.tick == 142
    assert briefing.alliances[0].alliance_id == "alliance-red"
    assert briefing.treaties[0].signed_tick == 142
    assert briefing.group_chats[0].group_chat_id == "group-chat-7"
    assert briefing.messages.direct[0].recipient_id == "player-2"
    assert briefing.messages.group[0].group_chat_id == "group-chat-7"
    assert briefing.messages.world[0].content == "World briefing."


def test_sdk_group_chat_methods_cover_create_list_read_and_send_workflows(
    sdk_module: Any,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    app = create_app(match_registry=seeded_registry)
    with TestClient(app, base_url="http://testserver") as session:
        creator_client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key=build_seeded_agent_api_key("agent-player-2"),
            session=session,
        )
        invited_client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key=build_seeded_agent_api_key("agent-player-4"),
            session=session,
        )

        group_chat = creator_client.create_group_chat(
            "match-alpha",
            tick=142,
            name="War Room",
            member_ids=["player-4"],
        )
        visible_group_chats = creator_client.get_group_chats("match-alpha")
        invited_visible_group_chats = invited_client.get_group_chats("match-alpha")
        sent_group_message = invited_client.send_group_chat_message(
            "match-alpha",
            group_chat_id=group_chat.group_chat.group_chat_id,
            tick=142,
            content="Ready to coordinate.",
        )
        messages = creator_client.get_group_chat_messages(
            "match-alpha",
            group_chat_id=group_chat.group_chat.group_chat_id,
        )

    assert group_chat.status == "accepted"
    assert group_chat.group_chat.group_chat_id == "group-chat-1"
    assert group_chat.group_chat.name == "War Room"
    assert group_chat.group_chat.member_ids == ["player-2", "player-4"]
    assert visible_group_chats.player_id == "player-2"
    assert visible_group_chats.group_chats[0].group_chat_id == "group-chat-1"
    assert invited_visible_group_chats.player_id == "player-4"
    assert invited_visible_group_chats.group_chats[0].member_ids == ["player-2", "player-4"]
    assert sent_group_message.status == "accepted"
    assert sent_group_message.group_chat_id == "group-chat-1"
    assert sent_group_message.message.content == "Ready to coordinate."
    assert messages.player_id == "player-2"
    assert messages.group_chat_id == "group-chat-1"
    assert messages.messages[0].sender_id == "player-4"
    assert messages.messages[0].content == "Ready to coordinate."


def test_sdk_group_chat_methods_wrap_structured_visibility_errors(
    sdk_module: Any,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    app = create_app(match_registry=seeded_registry)
    with TestClient(app, base_url="http://testserver") as session:
        creator_client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key=build_seeded_agent_api_key("agent-player-2"),
            session=session,
        )
        outsider_client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key=build_seeded_agent_api_key("agent-player-3"),
            session=session,
        )

        created_group_chat = creator_client.create_group_chat(
            "match-alpha",
            tick=142,
            name="Quiet Council",
            member_ids=["player-4"],
        )

        with pytest.raises(sdk_module.IronCouncilApiError) as exc_info:
            outsider_client.get_group_chat_messages(
                "match-alpha",
                group_chat_id=created_group_chat.group_chat.group_chat_id,
            )

    error = exc_info.value
    assert error.status_code == HTTPStatus.FORBIDDEN
    assert error.error_code == "group_chat_not_visible"
    assert error.message == "Group chat 'group-chat-1' is not visible to player 'player-3'."


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        ({"action": "create", "alliance_id": "alliance-1", "name": "North"}, "alliance create"),
        ({"action": "create", "alliance_id": None, "name": None}, "alliance create requires name"),
        (
            {"action": "join", "alliance_id": None, "name": None},
            "alliance join requires alliance_id",
        ),
        (
            {"action": "join", "alliance_id": "alliance-1", "name": "North"},
            "alliance join does not accept name",
        ),
        (
            {"action": "leave", "alliance_id": "alliance-1", "name": None},
            "alliance leave does not accept alliance_id",
        ),
        (
            {"action": "leave", "alliance_id": None, "name": "North"},
            "alliance leave does not accept name",
        ),
    ],
)
def test_sdk_command_alliance_model_rejects_invalid_variants(
    sdk_module: Any,
    payload: dict[str, Any],
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        sdk_module.AgentCommandAllianceAction.model_validate(payload)


def test_sdk_wraps_structured_api_failures_without_leaking_api_key(
    sdk_module: Any,
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    app = create_app(match_registry=seeded_registry)
    api_key = build_seeded_agent_api_key("agent-player-2")
    with TestClient(app, base_url="http://testserver") as session:
        client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key=api_key,
            session=session,
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


def test_sdk_wraps_unstructured_http_errors_with_generic_metadata(sdk_module: Any) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=HTTPStatus.BAD_GATEWAY, text="upstream unavailable")

    session = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://testserver",
    )
    try:
        client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key="test-key",
            session=session,
        )

        with pytest.raises(sdk_module.IronCouncilApiError) as exc_info:
            client.get_messages("match-alpha")
    finally:
        session.close()

    error = exc_info.value
    assert error.status_code == HTTPStatus.BAD_GATEWAY
    assert error.error_code == "http_error"
    assert error.message == "Iron Council API request failed with status 502."


def test_sdk_wraps_transport_failures_in_clear_api_error(sdk_module: Any) -> None:
    class FailingSession:
        def request(
            self,
            method: str,
            url: str,
            *,
            headers: dict[str, str] | None = None,
            json: Any = None,
        ) -> httpx.Response:
            request = httpx.Request(method, url, headers=headers, json=json)
            raise httpx.ConnectError("boom", request=request)

    client = sdk_module.IronCouncilClient(
        base_url="http://testserver",
        api_key=build_seeded_agent_api_key("agent-player-2"),
        session=FailingSession(),
    )

    with pytest.raises(sdk_module.IronCouncilApiError) as exc_info:
        client.list_matches()

    error = exc_info.value
    assert error.status_code is None
    assert error.error_code == "transport_error"
    assert error.message == "Request to Iron Council API failed."
