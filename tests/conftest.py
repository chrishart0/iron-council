import os
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from server.db.testing import prepare_test_database, provision_seeded_database

from tests.support import RunningApp


@pytest.fixture(autouse=True)
def reset_default_app_registry() -> Iterator[None]:
    from server.agent_registry import InMemoryMatchRegistry
    from server.main import app

    app.state.match_registry = InMemoryMatchRegistry()
    yield
    app.state.match_registry = InMemoryMatchRegistry()


@pytest.fixture
def representative_match_state_payload() -> dict[str, Any]:
    return {
        "tick": 142,
        "cities": {
            "london": {
                "owner": "player_uuid",
                "population": 12,
                "resources": {"food": 3, "production": 2, "money": 8},
                "upgrades": {"economy": 2, "military": 1, "fortification": 0},
                "garrison": 15,
                "building_queue": [
                    {"type": "fortification", "tier": 1, "ticks_remaining": 3},
                ],
            }
        },
        "armies": [
            {
                "id": "army_uuid",
                "owner": "player_uuid",
                "troops": 40,
                "location": "birmingham",
                "destination": None,
                "path": None,
                "ticks_remaining": 0,
            }
        ],
        "players": {
            "player_uuid": {
                "resources": {"food": 120, "production": 85, "money": 200},
                "cities_owned": ["london", "southampton", "portsmouth"],
                "alliance_id": None,
                "is_eliminated": False,
            }
        },
        "victory": {
            "leading_alliance": None,
            "cities_held": 13,
            "threshold": 13,
            "countdown_ticks_remaining": None,
        },
    }


@pytest.fixture
def representative_order_payload() -> dict[str, Any]:
    return {
        "match_id": "match_uuid",
        "player_id": "player_uuid",
        "tick": 142,
        "orders": {
            "movements": [{"army_id": "army_uuid", "destination": "birmingham"}],
            "recruitment": [{"city": "london", "troops": 5}],
            "upgrades": [{"city": "portsmouth", "track": "fortification", "target_tier": 1}],
            "transfers": [{"to": "player_ally_uuid", "resource": "money", "amount": 50}],
        },
    }


@pytest.fixture
def migrated_test_database_url(tmp_path: Path) -> str:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'test.db'}"
    prepare_test_database(database_url=database_url, reset=False)
    return database_url


@pytest.fixture
def running_seeded_app(tmp_path: Path) -> Iterator[RunningApp]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'process-test.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    host = "127.0.0.1"
    port = _allocate_tcp_port()
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "server.main:app",
            "--host",
            host,
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env={
            **os.environ,
            "DATABASE_URL": database_url,
            "IRON_COUNCIL_MATCH_REGISTRY_BACKEND": "db",
            "PYTHONUNBUFFERED": "1",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    base_url = f"http://{host}:{port}"
    try:
        _wait_for_running_app(base_url, process)
        yield RunningApp(
            base_url=base_url,
            primary_match_id="00000000-0000-0000-0000-000000000101",
            secondary_match_id="00000000-0000-0000-0000-000000000102",
        )
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _allocate_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_running_app(base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 15
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=1)
            raise AssertionError(
                f"Running app exited before becoming healthy.\nstdout:\n{stdout}\nstderr:\n{stderr}"
            )
        try:
            response = httpx.get(f"{base_url}/health", timeout=0.5)
            if response.status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(0.1)
    process.terminate()
    stdout, stderr = process.communicate(timeout=5)
    raise AssertionError(
        "Running app did not become healthy before timeout.\n"
        f"last_error={last_error!r}\n"
        f"stdout:\n{stdout}\n"
        f"stderr:\n{stderr}"
    )
