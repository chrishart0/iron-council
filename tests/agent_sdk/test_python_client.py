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
from tests.support import insert_api_key, load_python_agent_sdk_module


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
    assert matches.matches[0].map == "britain"
    assert matches.matches[0].current_player_count == 3
    assert matches.matches[0].max_player_count == 5
    assert matches.matches[0].open_slot_count == 2
    assert matches.matches[1].match_id == "match-beta"
    assert matches.matches[1].status == "paused"
    assert profile.agent_id == "agent-player-2"
    assert profile.display_name == "Morgana"
    assert profile.treaty_reputation.summary.honored == 0
    assert profile.treaty_reputation.history == []
    assert join.status == "accepted"
    assert join.match_id == "match-beta"
    assert join.player_id == "player-1"
    assert state.match_id == "match-beta"
    assert state.player_id == "player-1"


def test_sdk_profile_models_accept_honored_treaty_history_status(sdk_module: Any) -> None:
    profile = sdk_module.AgentProfileResponse.model_validate(
        {
            "agent_id": "agent-player-2",
            "display_name": "Morgana",
            "is_seeded": True,
            "rating": {"elo": 1211, "provisional": False},
            "history": {"matches_played": 2, "wins": 1, "losses": 0, "draws": 1},
            "treaty_reputation": {
                "summary": {
                    "signed": 1,
                    "active": 0,
                    "honored": 1,
                    "withdrawn": 0,
                    "broken_by_self": 0,
                    "broken_by_counterparty": 0,
                },
                "history": [
                    {
                        "match_id": "match-completed",
                        "counterparty_display_name": "Arthur",
                        "treaty_type": "trade",
                        "status": "honored",
                        "signed_tick": 141,
                        "ended_tick": None,
                        "broken_by_self": False,
                    }
                ],
            },
        }
    )

    assert profile.treaty_reputation.summary.honored == 1
    assert profile.treaty_reputation.history[0].status == "honored"


def test_sdk_create_match_lobby_returns_typed_authenticated_contract(
    sdk_module: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'sdk-create-match-lobby.db'}"
    from server.db.testing import provision_seeded_database

    provision_seeded_database(database_url=database_url, reset=True)
    creator_api_key = "sdk-fresh-creator-key"
    insert_api_key(
        database_url=database_url,
        api_key_id="11111111-1111-1111-1111-111111111111",
        user_id="11111111-1111-1111-1111-111111111301",
        raw_api_key=creator_api_key,
        elo_rating=1111,
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()
    with TestClient(app, base_url="http://testserver") as session:
        client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key=creator_api_key,
            session=session,
        )
        created = client.create_match_lobby(
            map="britain",
            tick_interval_seconds=20,
            max_players=4,
            victory_city_threshold=13,
            starting_cities_per_player=2,
        )
        state = client.get_match_state(created.match_id)

    assert created.status == "lobby"
    assert created.current_player_count == 1
    assert created.open_slot_count == 3
    assert created.creator_player_id == "player-1"
    assert state.match_id == created.match_id
    assert state.player_id == "player-1"


def test_sdk_start_match_lobby_returns_typed_compact_active_contract(
    sdk_module: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'sdk-start-match-lobby.db'}"
    from server.db.testing import provision_seeded_database

    provision_seeded_database(database_url=database_url, reset=True)
    creator_api_key = "sdk-start-creator-key"
    competitor_api_key = "sdk-start-competitor-key"
    insert_api_key(
        database_url=database_url,
        api_key_id="11111111-1111-1111-1111-111111111112",
        user_id="11111111-1111-1111-1111-111111111302",
        raw_api_key=creator_api_key,
        elo_rating=1111,
    )
    insert_api_key(
        database_url=database_url,
        api_key_id="22222222-2222-2222-2222-222222222222",
        user_id="22222222-2222-2222-2222-222222222302",
        raw_api_key=competitor_api_key,
        elo_rating=1099,
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()
    with TestClient(app, base_url="http://testserver") as session:
        creator_client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key=creator_api_key,
            session=session,
        )
        competitor_client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key=competitor_api_key,
            session=session,
        )

        created = creator_client.create_match_lobby(
            map="britain",
            tick_interval_seconds=20,
            max_players=4,
            victory_city_threshold=13,
            starting_cities_per_player=2,
        )
        joined = competitor_client.join_match(created.match_id)
        started = creator_client.start_match_lobby(created.match_id)
        state = creator_client.get_match_state(created.match_id)

    assert joined.status == "accepted"
    assert joined.match_id == created.match_id
    assert started.match_id == created.match_id
    assert isinstance(started, sdk_module.MatchLobbyStartResponse)
    assert started.status == sdk_module.MatchStatus.ACTIVE
    assert started.current_player_count == 2
    assert started.max_player_count == 4
    assert started.open_slot_count == 2
    assert state.match_id == created.match_id
    assert state.player_id == created.creator_player_id


def test_sdk_start_match_lobby_wraps_creator_only_and_not_ready_errors(
    sdk_module: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'sdk-start-match-lobby-errors.db'}"
    from server.db.testing import provision_seeded_database

    provision_seeded_database(database_url=database_url, reset=True)
    creator_api_key = "sdk-error-creator-key"
    second_creator_api_key = "sdk-error-creator-key-2"
    competitor_api_key = "sdk-error-competitor-key"
    insert_api_key(
        database_url=database_url,
        api_key_id="11111111-1111-1111-1111-111111111113",
        user_id="11111111-1111-1111-1111-111111111303",
        raw_api_key=creator_api_key,
        elo_rating=1111,
    )
    insert_api_key(
        database_url=database_url,
        api_key_id="11111111-1111-1111-1111-111111111114",
        user_id="11111111-1111-1111-1111-111111111304",
        raw_api_key=second_creator_api_key,
        elo_rating=1111,
    )
    insert_api_key(
        database_url=database_url,
        api_key_id="22222222-2222-2222-2222-222222222223",
        user_id="22222222-2222-2222-2222-222222222303",
        raw_api_key=competitor_api_key,
        elo_rating=1099,
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("IRON_COUNCIL_MATCH_REGISTRY_BACKEND", "db")

    app = create_app()
    with TestClient(app, base_url="http://testserver") as session:
        creator_client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key=creator_api_key,
            session=session,
        )
        second_creator_client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key=second_creator_api_key,
            session=session,
        )
        competitor_client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key=competitor_api_key,
            session=session,
        )

        not_ready = creator_client.create_match_lobby(
            map="britain",
            tick_interval_seconds=20,
            max_players=4,
            victory_city_threshold=13,
            starting_cities_per_player=2,
        )
        with pytest.raises(sdk_module.IronCouncilApiError) as not_ready_exc_info:
            creator_client.start_match_lobby(not_ready.match_id)

        ready_forbidden = second_creator_client.create_match_lobby(
            map="britain",
            tick_interval_seconds=20,
            max_players=4,
            victory_city_threshold=13,
            starting_cities_per_player=2,
        )
        competitor_client.join_match(ready_forbidden.match_id)
        with pytest.raises(sdk_module.IronCouncilApiError) as forbidden_exc_info:
            competitor_client.start_match_lobby(ready_forbidden.match_id)

    not_ready_error = not_ready_exc_info.value
    assert not_ready_error.status_code == HTTPStatus.CONFLICT
    assert not_ready_error.error_code == "match_lobby_not_ready"
    assert "needs at least 2 joined players" in not_ready_error.message

    forbidden_error = forbidden_exc_info.value
    assert forbidden_error.status_code == HTTPStatus.FORBIDDEN
    assert forbidden_error.error_code == "match_start_forbidden"
    assert ready_forbidden.match_id in forbidden_error.message


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


def test_sdk_parses_broken_treaty_statuses_from_briefing_payload(sdk_module: Any) -> None:
    captured_request: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request.update(
            {
                "method": request.method,
                "path": request.url.path,
                "query": dict(request.url.params),
            }
        )
        return httpx.Response(
            200,
            json={
                "match_id": "match-alpha",
                "player_id": "player-2",
                "state": {
                    "match_id": "match-alpha",
                    "tick": 143,
                    "player_id": "player-2",
                    "resources": {"food": 12, "production": 7, "money": 9},
                    "cities": {},
                    "visible_armies": [],
                    "alliance_id": None,
                    "alliance_members": [],
                    "victory": {
                        "leading_alliance": None,
                        "cities_held": 1,
                        "threshold": 18,
                        "countdown_ticks_remaining": None,
                    },
                },
                "alliances": [],
                "treaties": [
                    {
                        "treaty_id": 5,
                        "player_a_id": "player-1",
                        "player_b_id": "player-2",
                        "treaty_type": "trade",
                        "status": "broken_by_a",
                        "proposed_by": "player-2",
                        "proposed_tick": 142,
                        "signed_tick": 142,
                        "withdrawn_by": "player-1",
                        "withdrawn_tick": 142,
                    }
                ],
                "group_chats": [],
                "messages": {"direct": [], "group": [], "world": []},
            },
        )

    session = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://testserver",
    )
    try:
        client = sdk_module.IronCouncilClient(
            base_url="http://testserver",
            api_key="***",
            session=session,
        )

        briefing = client.get_agent_briefing("match-alpha")
    finally:
        session.close()

    assert captured_request == {
        "method": "GET",
        "path": "/api/v1/matches/match-alpha/agent-briefing",
        "query": {},
    }
    assert briefing.treaties[0].status == "broken_by_a"
    assert briefing.treaties[0].withdrawn_by == "player-1"
    assert briefing.treaties[0].withdrawn_tick == 142


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


def test_sdk_alliance_models_accept_valid_create_join_and_leave_variants(sdk_module: Any) -> None:
    route_create = sdk_module.AllianceActionRequest.model_validate(
        {"match_id": "match-alpha", "action": "create", "name": "North"}
    )
    route_join = sdk_module.AllianceActionRequest.model_validate(
        {"match_id": "match-alpha", "action": "join", "alliance_id": "alliance-1"}
    )
    route_leave = sdk_module.AllianceActionRequest.model_validate(
        {"match_id": "match-alpha", "action": "leave"}
    )

    command_create = sdk_module.AgentCommandAllianceAction.model_validate(
        {"action": "create", "name": "North"}
    )
    command_join = sdk_module.AgentCommandAllianceAction.model_validate(
        {"action": "join", "alliance_id": "alliance-1"}
    )
    command_leave = sdk_module.AgentCommandAllianceAction.model_validate({"action": "leave"})

    assert route_create.name == "North"
    assert route_join.alliance_id == "alliance-1"
    assert route_leave.action == "leave"
    assert command_create.name == "North"
    assert command_join.alliance_id == "alliance-1"
    assert command_leave.action == "leave"


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
