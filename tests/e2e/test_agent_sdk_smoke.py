from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import jwt
from server.agent_registry import build_seeded_agent_api_key
from tests.support import (
    RunningApp,
    insert_api_key_with_manual_entitlement,
    load_python_agent_sdk_module,
)


def _human_jwt_token(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "role": "authenticated",
            "iss": "https://supabase.test/auth/v1",
            "aud": "authenticated",
            "exp": datetime.now(tz=UTC) + timedelta(minutes=5),
        },
        "test-human-secret-key-material-1234",
        algorithm="HS256",
    )


def _human_headers(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_human_jwt_token(user_id)}"}


def test_agent_sdk_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    sdk_module = load_python_agent_sdk_module()
    client = sdk_module.IronCouncilClient(
        base_url=running_seeded_app.base_url,
        api_key=build_seeded_agent_api_key("agent-player-2"),
    )

    profile = client.get_current_agent_profile()
    join = client.join_match(running_seeded_app.secondary_match_id)
    state = client.get_match_state(running_seeded_app.secondary_match_id)
    order_response = client.submit_orders(
        running_seeded_app.secondary_match_id,
        tick=7,
        orders={
            "movements": [],
            "recruitment": [],
            "upgrades": [],
            "transfers": [],
        },
    )

    assert profile.agent_id == "agent-player-2"
    assert join.match_id == running_seeded_app.secondary_match_id
    assert join.player_id == "player-1"
    assert state.match_id == running_seeded_app.secondary_match_id
    assert state.player_id == "player-1"
    assert order_response.status == "accepted"
    assert order_response.player_id == "player-1"


def test_agent_sdk_group_chat_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    sdk_module = load_python_agent_sdk_module()
    creator_client = sdk_module.IronCouncilClient(
        base_url=running_seeded_app.base_url,
        api_key=build_seeded_agent_api_key("agent-player-2"),
    )
    invited_client = sdk_module.IronCouncilClient(
        base_url=running_seeded_app.base_url,
        api_key=build_seeded_agent_api_key("agent-player-3"),
    )

    created_group_chat = creator_client.create_group_chat(
        running_seeded_app.primary_match_id,
        tick=142,
        name="SDK Smoke Council",
        member_ids=["player-3"],
    )
    visible_group_chats = invited_client.get_group_chats(running_seeded_app.primary_match_id)
    sent_message = invited_client.send_group_chat_message(
        running_seeded_app.primary_match_id,
        group_chat_id=created_group_chat.group_chat.group_chat_id,
        tick=142,
        content="SDK smoke ready.",
    )
    messages = creator_client.get_group_chat_messages(
        running_seeded_app.primary_match_id,
        group_chat_id=created_group_chat.group_chat.group_chat_id,
    )

    assert created_group_chat.status == "accepted"
    assert created_group_chat.group_chat.member_ids == ["player-2", "player-3"]
    assert visible_group_chats.group_chats[0].group_chat_id == "group-chat-1"
    assert sent_message.message.content == "SDK smoke ready."
    assert messages.messages[0].sender_id == "player-3"
    assert messages.messages[0].content == "SDK smoke ready."


def test_agent_sdk_briefing_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    sdk_module = load_python_agent_sdk_module()
    viewer_client = sdk_module.IronCouncilClient(
        base_url=running_seeded_app.base_url,
        api_key=build_seeded_agent_api_key("agent-player-2"),
    )
    sender_client = sdk_module.IronCouncilClient(
        base_url=running_seeded_app.base_url,
        api_key=build_seeded_agent_api_key("agent-player-3"),
    )

    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        guidance_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/agents/agent-player-2/guidance",
            json={
                "match_id": running_seeded_app.primary_match_id,
                "tick": 142,
                "content": "SDK guidance fortify the center before any coastal raid.",
            },
            headers=_human_headers("00000000-0000-0000-0000-000000000302"),
        )

    sender_client.send_message(
        running_seeded_app.primary_match_id,
        tick=142,
        channel="direct",
        recipient_id="player-2",
        content="SDK briefing direct.",
    )
    briefing = viewer_client.get_agent_briefing(
        running_seeded_app.primary_match_id,
        since_tick=142,
    )

    assert guidance_response.status_code == 202
    assert briefing.match_id == running_seeded_app.primary_match_id
    assert briefing.player_id == "player-2"
    assert briefing.state.player_id == "player-2"
    assert briefing.alliances[0].alliance_id == "alliance-red"
    assert briefing.messages.direct[0].content == "SDK briefing direct."
    assert (
        briefing.guidance[0].content == "SDK guidance fortify the center before any coastal raid."
    )


def test_agent_sdk_lobby_lifecycle_smoke_flow_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    sdk_module = load_python_agent_sdk_module()
    creator_api_key = "sdk-smoke-creator-key"
    competitor_api_key = "sdk-smoke-competitor-key"
    insert_api_key_with_manual_entitlement(
        database_url=running_seeded_app.database_url,
        api_key_id="11111111-1111-1111-1111-111111111114",
        user_id="11111111-1111-1111-1111-111111111304",
        raw_api_key=creator_api_key,
        elo_rating=1111,
        grant_id="33333333-3333-3333-3333-333333333214",
    )
    insert_api_key_with_manual_entitlement(
        database_url=running_seeded_app.database_url,
        api_key_id="22222222-2222-2222-2222-222222222224",
        user_id="22222222-2222-2222-2222-222222222304",
        raw_api_key=competitor_api_key,
        elo_rating=1099,
        grant_id="44444444-4444-4444-4444-444444444224",
    )
    creator_client = sdk_module.IronCouncilClient(
        base_url=running_seeded_app.base_url,
        api_key=creator_api_key,
    )
    competitor_client = sdk_module.IronCouncilClient(
        base_url=running_seeded_app.base_url,
        api_key=competitor_api_key,
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

    assert created.status == "lobby"
    assert created.creator_player_id == "player-1"
    assert joined.status == "accepted"
    assert joined.player_id == "player-2"
    assert started.status == "active"
    assert started.current_player_count == 2
    assert started.open_slot_count == 2
    assert state.match_id == created.match_id
    assert state.player_id == "player-1"


def test_agent_sdk_example_lobby_lifecycle_command_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    creator_api_key = "sdk-example-creator-key"
    competitor_api_key = "sdk-example-competitor-key"
    insert_api_key_with_manual_entitlement(
        database_url=running_seeded_app.database_url,
        api_key_id="11111111-1111-1111-1111-111111111115",
        user_id="11111111-1111-1111-1111-111111111305",
        raw_api_key=creator_api_key,
        elo_rating=1111,
        grant_id="33333333-3333-3333-3333-333333333215",
    )
    insert_api_key_with_manual_entitlement(
        database_url=running_seeded_app.database_url,
        api_key_id="22222222-2222-2222-2222-222222222225",
        user_id="22222222-2222-2222-2222-222222222305",
        raw_api_key=competitor_api_key,
        elo_rating=1099,
        grant_id="44444444-4444-4444-4444-444444444225",
    )
    command = [
        sys.executable,
        "agent-sdk/python/example_agent.py",
        "--base-url",
        running_seeded_app.base_url,
        "--api-key",
        creator_api_key,
        "--create-lobby",
        "--joiner-api-key",
        competitor_api_key,
        "--auto-start",
    ]

    result = subprocess.run(
        ["uv", "run", *command],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "lobby-lifecycle"
    assert payload["joined_status"] == "accepted"
    assert payload["started"] is True
    assert payload["match_status"] == "active"
