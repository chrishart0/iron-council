from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from server.agent_registry import build_seeded_agent_api_key
from tests.support import RunningApp


def test_example_agent_documented_command_runs_through_real_process(
    running_seeded_app: RunningApp,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    command = [
        "uv",
        "run",
        "python",
        "agent-sdk/python/example_agent.py",
        "--base-url",
        running_seeded_app.base_url,
        "--api-key",
        build_seeded_agent_api_key("agent-player-2"),
        "--match-id",
        running_seeded_app.secondary_match_id,
    ]

    result = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "agent_id": "agent-player-2",
        "mode": "existing-match",
        "match_id": running_seeded_app.secondary_match_id,
        "player_id": "player-1",
        "tick": 7,
        "submission_status": "accepted",
        "submission_index": 0,
    }


def test_example_agent_env_only_command_prefers_joinable_match_over_active_match(
    running_seeded_app: RunningApp,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    command = ["uv", "run", "python", "agent-sdk/python/example_agent.py"]

    env = os.environ.copy()
    env["IRON_COUNCIL_BASE_URL"] = running_seeded_app.base_url
    env["IRON_COUNCIL_API_KEY"] = build_seeded_agent_api_key("agent-player-2")
    env.pop("IRON_COUNCIL_MATCH_ID", None)

    result = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "agent_id": "agent-player-2",
        "mode": "existing-match",
        "match_id": running_seeded_app.secondary_match_id,
        "player_id": "player-1",
        "tick": 7,
        "submission_status": "accepted",
        "submission_index": 0,
    }
