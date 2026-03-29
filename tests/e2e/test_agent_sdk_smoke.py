from __future__ import annotations

from server.agent_registry import build_seeded_agent_api_key
from tests.support import RunningApp, load_python_agent_sdk_module


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

    assert briefing.match_id == running_seeded_app.primary_match_id
    assert briefing.player_id == "player-2"
    assert briefing.state.player_id == "player-2"
    assert briefing.alliances[0].alliance_id == "alliance-red"
    assert briefing.messages.direct[0].content == "SDK briefing direct."
