from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


def load_example_agent_module() -> Any:
    module_path = Path(__file__).resolve().parents[2] / "agent-sdk/python/example_agent.py"
    spec = spec_from_file_location("example_agent", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load example agent module from {module_path}.")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_agent_runs_one_deterministic_cycle_and_prints_json_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    example_agent = load_example_agent_module()
    calls: list[tuple[str, object]] = []

    class FakeClient:
        def __init__(self, base_url: str, api_key: str) -> None:
            calls.append(("init", {"base_url": base_url, "api_key": api_key}))

        def list_matches(self) -> Any:
            calls.append(("list_matches", None))
            return SimpleNamespace(
                matches=[
                    SimpleNamespace(match_id="match-alpha"),
                    SimpleNamespace(match_id="match-beta"),
                ]
            )

        def get_current_agent_profile(self) -> Any:
            calls.append(("get_current_agent_profile", None))
            return SimpleNamespace(agent_id="agent-player-2")

        def join_match(self, match_id: str) -> Any:
            calls.append(("join_match", match_id))
            return SimpleNamespace(player_id="join-player")

        def get_match_state(self, match_id: str) -> Any:
            calls.append(("get_match_state", match_id))
            return SimpleNamespace(match_id=match_id, player_id="state-player", tick=142)

        def submit_orders(self, match_id: str, *, tick: int, orders: Any) -> Any:
            calls.append(("submit_orders", {"match_id": match_id, "tick": tick, "orders": orders}))
            return SimpleNamespace(status="accepted", submission_index=0)

    monkeypatch.setattr(example_agent, "IronCouncilClient", FakeClient)

    exit_code = example_agent.main(
        [
            "--base-url",
            "http://example.test",
            "--api-key",
            "secret-key",
            "--match-id",
            "match-beta",
        ]
    )

    assert exit_code == 0
    assert calls == [
        ("init", {"base_url": "http://example.test", "api_key": "secret-key"}),
        ("get_current_agent_profile", None),
        ("join_match", "match-beta"),
        ("get_match_state", "match-beta"),
        (
            "submit_orders",
            {
                "match_id": "match-beta",
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            },
        ),
    ]

    assert json.loads(capsys.readouterr().out) == {
        "agent_id": "agent-player-2",
        "match_id": "match-beta",
        "player_id": "state-player",
        "tick": 142,
        "submission_status": "accepted",
        "submission_index": 0,
    }


def test_example_agent_uses_env_fallbacks_and_first_listed_match(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    example_agent = load_example_agent_module()
    calls: list[tuple[str, object]] = []

    class FakeClient:
        def __init__(self, base_url: str, api_key: str) -> None:
            calls.append(("init", {"base_url": base_url, "api_key": api_key}))

        def list_matches(self) -> Any:
            calls.append(("list_matches", None))
            return SimpleNamespace(matches=[SimpleNamespace(match_id="match-alpha")])

        def get_current_agent_profile(self) -> Any:
            calls.append(("get_current_agent_profile", None))
            return SimpleNamespace(agent_id="agent-player-3")

        def join_match(self, match_id: str) -> Any:
            calls.append(("join_match", match_id))
            return SimpleNamespace(player_id="join-player")

        def get_match_state(self, match_id: str) -> Any:
            calls.append(("get_match_state", match_id))
            return SimpleNamespace(match_id=match_id, player_id="state-player", tick=7)

        def submit_orders(self, match_id: str, *, tick: int, orders: Any) -> Any:
            calls.append(("submit_orders", {"match_id": match_id, "tick": tick, "orders": orders}))
            return SimpleNamespace(status="accepted", submission_index=1)

    monkeypatch.setattr(example_agent, "IronCouncilClient", FakeClient)
    monkeypatch.setenv("IRON_COUNCIL_BASE_URL", "http://env.test")
    monkeypatch.setenv("IRON_COUNCIL_API_KEY", "env-key")

    exit_code = example_agent.main([])

    assert exit_code == 0
    assert calls == [
        ("init", {"base_url": "http://env.test", "api_key": "env-key"}),
        ("list_matches", None),
        ("get_current_agent_profile", None),
        ("join_match", "match-alpha"),
        ("get_match_state", "match-alpha"),
        (
            "submit_orders",
            {
                "match_id": "match-alpha",
                "tick": 7,
                "orders": {
                    "movements": [],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            },
        ),
    ]

    payload = json.loads(capsys.readouterr().out)
    assert payload["match_id"] == "match-alpha"
    assert payload["player_id"] == "state-player"


def test_readme_documents_setup_and_run_commands() -> None:
    readme = (Path(__file__).resolve().parents[2] / "agent-sdk/README.md").read_text()

    assert "uv sync --extra dev --frozen" in readme
    assert "uv run python agent-sdk/python/example_agent.py --base-url" in readme
    assert "uv run python agent-sdk/python/example_agent.py" in readme


def test_example_agent_is_importable_without_repo_server_package() -> None:
    sdk_dir = Path(__file__).resolve().parents[2] / "agent-sdk/python"
    import_script = """
import builtins

real_import = builtins.__import__

def blocked_import(name, *args, **kwargs):
    if name == "server" or name.startswith("server."):
        raise ModuleNotFoundError("server blocked for standalone example import")
    return real_import(name, *args, **kwargs)

builtins.__import__ = blocked_import
import example_agent
"""

    isolated_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("COVERAGE") and not key.startswith("COV_CORE")
    }
    result = subprocess.run(
        [sys.executable, "-c", import_script],
        check=False,
        capture_output=True,
        text=True,
        env={**isolated_env, "PYTHONPATH": str(sdk_dir)},
    )

    assert result.returncode == 0, result.stderr


def test_example_agent_requires_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    example_agent = load_example_agent_module()
    monkeypatch.delenv("IRON_COUNCIL_BASE_URL", raising=False)
    monkeypatch.delenv("IRON_COUNCIL_API_KEY", raising=False)

    with pytest.raises(SystemExit, match="Missing base URL"):
        example_agent.main([])


def test_example_agent_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    example_agent = load_example_agent_module()
    monkeypatch.delenv("IRON_COUNCIL_API_KEY", raising=False)

    with pytest.raises(SystemExit, match="Missing API key"):
        example_agent.main(["--base-url", "http://example.test"])


def test_example_agent_exits_when_no_matches_are_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    example_agent = load_example_agent_module()

    class FakeClient:
        def __init__(self, base_url: str, api_key: str) -> None:
            del base_url, api_key

        def list_matches(self) -> Any:
            return SimpleNamespace(matches=[])

    monkeypatch.setattr(example_agent, "IronCouncilClient", FakeClient)

    with pytest.raises(SystemExit, match="No matches are available to join."):
        example_agent.main(
            [
                "--base-url",
                "http://example.test",
                "--api-key",
                "secret-key",
            ]
        )
