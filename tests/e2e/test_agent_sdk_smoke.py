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
