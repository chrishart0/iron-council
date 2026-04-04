from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

import httpx
from server.db.testing import provision_seeded_database
from sqlalchemy import create_engine, text
from websockets.sync.client import connect as connect_websocket

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONTROL = REPO_ROOT / "scripts" / "runtime-control.sh"
JsonObject = dict[str, Any]


def test_packaged_runtime_launch_readiness_smoke_covers_multi_match_websockets_and_restart(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'launch-readiness.db'}"
    provision_seeded_database(database_url=database_url, reset=True)
    _prepare_two_active_matches(database_url)

    env_file = tmp_path / "runtime.env"
    env_file.write_text(f"DATABASE_URL={database_url}\n")
    host = "127.0.0.1"

    with _run_packaged_runtime(env_file=env_file, host=host) as base_url:
        websocket_base_url = base_url.replace("http://", "ws://", 1)

        with (
            connect_websocket(
                f"{websocket_base_url}/ws/match/00000000-0000-0000-0000-000000000101"
                "?viewer=spectator",
                open_timeout=5,
                close_timeout=1,
            ) as primary_socket,
            connect_websocket(
                f"{websocket_base_url}/ws/match/00000000-0000-0000-0000-000000000102"
                "?viewer=spectator",
                open_timeout=5,
                close_timeout=1,
            ) as secondary_socket,
        ):
            primary_initial = _load_socket_payload(primary_socket.recv(timeout=5))
            secondary_initial = _load_socket_payload(secondary_socket.recv(timeout=5))
            primary_tick_update = _load_socket_payload(primary_socket.recv(timeout=5))
            secondary_tick_update = _load_socket_payload(secondary_socket.recv(timeout=5))
            runtime_status = _wait_for_runtime_status(
                base_url=base_url,
                predicate=lambda payload: _matches_have_fanout(
                    payload,
                    expected_match_ids={
                        "00000000-0000-0000-0000-000000000101",
                        "00000000-0000-0000-0000-000000000102",
                    },
                    expected_connection_count=1,
                ),
            )

    observed_ticks_before_restart = {
        match["match_id"]: match["tick"] for match in runtime_status["matches"]
    }

    assert runtime_status["startup_recovery"]["resumed_active_match_count"] == 2
    assert primary_initial["data"]["state"]["tick"] == 142
    assert secondary_initial["data"]["state"]["tick"] == 7
    assert primary_tick_update["data"]["state"]["tick"] > primary_initial["data"]["state"]["tick"]
    assert (
        secondary_tick_update["data"]["state"]["tick"] > secondary_initial["data"]["state"]["tick"]
    )

    with _run_packaged_runtime(env_file=env_file, host=host) as base_url:
        runtime_after_restart = _wait_for_runtime_status(
            base_url=base_url,
            predicate=lambda payload: _matches_resumed_after_restart(
                payload,
                observed_ticks_before_restart=observed_ticks_before_restart,
            ),
        )
        websocket_base_url = base_url.replace("http://", "ws://", 1)

        with (
            connect_websocket(
                f"{websocket_base_url}/ws/match/00000000-0000-0000-0000-000000000101"
                "?viewer=spectator",
                open_timeout=5,
                close_timeout=1,
            ) as primary_socket,
            connect_websocket(
                f"{websocket_base_url}/ws/match/00000000-0000-0000-0000-000000000102"
                "?viewer=spectator",
                open_timeout=5,
                close_timeout=1,
            ) as secondary_socket,
        ):
            primary_restarted = _load_socket_payload(primary_socket.recv(timeout=5))
            secondary_restarted = _load_socket_payload(secondary_socket.recv(timeout=5))
            runtime_with_reconnected_subscribers = _wait_for_runtime_status(
                base_url=base_url,
                predicate=lambda payload: _matches_have_fanout(
                    payload,
                    expected_match_ids={
                        "00000000-0000-0000-0000-000000000101",
                        "00000000-0000-0000-0000-000000000102",
                    },
                    expected_connection_count=1,
                ),
            )

    assert runtime_after_restart["startup_recovery"]["resumed_active_match_count"] == 2
    assert (
        primary_restarted["data"]["state"]["tick"]
        >= observed_ticks_before_restart["00000000-0000-0000-0000-000000000101"]
    )
    assert (
        secondary_restarted["data"]["state"]["tick"]
        >= observed_ticks_before_restart["00000000-0000-0000-0000-000000000102"]
    )
    for match in runtime_with_reconnected_subscribers["matches"]:
        assert match["websocket"]["connection_count"] == 1
        assert match["websocket"]["last_fanout"]["attempted_connections"] == 1
        assert match["websocket"]["last_fanout"]["delivered_connections"] == 1
        assert match["websocket"]["last_fanout"]["dropped_connections"] == 0


def test_packaged_runtime_launch_readiness_smoke_exposes_server_local_runtime_burst_limit(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'launch-readiness-abuse.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    env_file = tmp_path / "runtime.env"
    env_file.write_text(
        "\n".join(
            (
                f"DATABASE_URL={database_url}",
                "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_LIMIT=1",
                "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS=60",
            )
        )
        + "\n"
    )

    with _run_packaged_runtime(env_file=env_file, host="127.0.0.1") as base_url:
        with httpx.Client(base_url=base_url, timeout=5) as client:
            first_response = client.get("/health/runtime")
            second_response = client.get("/health/runtime")

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json() == {
        "error": {
            "code": "rate_limit_exceeded",
            "message": (
                "Public entrypoint burst limit exceeded for this caller on this route. "
                "Retry after the current 60-second window."
            ),
        }
    }


def _prepare_two_active_matches(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE matches
                SET config = :config
                WHERE id = :match_id
                """
            ),
            [
                {
                    "match_id": "00000000-0000-0000-0000-000000000101",
                    "config": (
                        '{"map":"britain","max_players":5,"turn_seconds":1,'
                        '"seed_profile":"agent_api_primary"}'
                    ),
                },
                {
                    "match_id": "00000000-0000-0000-0000-000000000102",
                    "config": (
                        '{"map":"britain","max_players":5,"turn_seconds":1,'
                        '"seed_profile":"agent_api_secondary"}'
                    ),
                },
            ],
        )
        connection.execute(
            text(
                """
                UPDATE matches
                SET status = 'active'
                WHERE id = '00000000-0000-0000-0000-000000000102'
                """
            )
        )


@contextmanager
def _run_packaged_runtime(*, env_file: Path, host: str) -> Iterator[str]:
    last_error: AssertionError | None = None
    for _ in range(5):
        port = _allocate_tcp_port()
        process = subprocess.Popen(
            [str(RUNTIME_CONTROL), "server"],
            cwd=REPO_ROOT,
            env={
                **os.environ,
                "IRON_COUNCIL_ENV_FILE": str(env_file),
                "IRON_COUNCIL_MATCH_REGISTRY_BACKEND": "db",
                "IRON_COUNCIL_SERVER_HOST": host,
                "IRON_COUNCIL_SERVER_PORT": str(port),
                "PYTHONUNBUFFERED": "1",
            },
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        base_url = f"http://{host}:{port}"
        try:
            _wait_for_health(base_url=base_url, process=process)
            try:
                yield base_url
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            return
        except AssertionError as exc:
            last_error = exc
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if "address already in use" not in str(exc).lower():
                raise
            time.sleep(0.1)

    assert last_error is not None
    raise last_error


def _allocate_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(*, base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 15
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=1)
            raise AssertionError(
                "Packaged runtime exited before becoming healthy.\n"
                f"stdout:\n{stdout}\n"
                f"stderr:\n{stderr}"
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
        "Packaged runtime did not become healthy before timeout.\n"
        f"last_error={last_error!r}\n"
        f"stdout:\n{stdout}\n"
        f"stderr:\n{stderr}"
    )


def _wait_for_runtime_status(
    *,
    base_url: str,
    predicate: Callable[[JsonObject], bool],
) -> JsonObject:
    deadline = time.monotonic() + 10
    last_payload: JsonObject | None = None
    with httpx.Client(base_url=base_url, timeout=5) as client:
        while time.monotonic() < deadline:
            response = client.get("/health/runtime")
            response.raise_for_status()
            payload = _as_json_object(response.json())
            last_payload = payload
            if predicate(payload):
                return payload
            time.sleep(0.1)

    raise AssertionError(f"Runtime status never satisfied predicate. last_payload={last_payload!r}")


def _matches_have_fanout(
    payload: JsonObject,
    *,
    expected_match_ids: set[str],
    expected_connection_count: int,
) -> bool:
    if payload["startup_recovery"]["resumed_active_match_count"] != len(expected_match_ids):
        return False

    matches_by_id = {match["match_id"]: match for match in payload["matches"]}
    if set(matches_by_id) != expected_match_ids:
        return False

    return all(
        matches_by_id[match_id]["websocket"]["connection_count"] == expected_connection_count
        and matches_by_id[match_id]["last_tick"] is not None
        and matches_by_id[match_id]["websocket"]["last_fanout"] is not None
        and matches_by_id[match_id]["websocket"]["last_fanout"]["attempted_connections"]
        == expected_connection_count
        and matches_by_id[match_id]["websocket"]["last_fanout"]["delivered_connections"]
        == expected_connection_count
        and matches_by_id[match_id]["websocket"]["last_fanout"]["dropped_connections"] == 0
        for match_id in expected_match_ids
    )


def _matches_resumed_after_restart(
    payload: JsonObject,
    *,
    observed_ticks_before_restart: dict[str, int],
) -> bool:
    startup_recovery = payload["startup_recovery"]
    if startup_recovery["resumed_active_match_count"] != len(observed_ticks_before_restart):
        return False

    resumed_ticks = {
        match["match_id"]: match["tick"] for match in startup_recovery["resumed_active_matches"]
    }
    return all(
        resumed_ticks.get(match_id, -1) >= observed_tick
        for match_id, observed_tick in observed_ticks_before_restart.items()
    )


def _load_socket_payload(raw_payload: str | bytes) -> JsonObject:
    decoded_payload = raw_payload.decode("utf-8") if isinstance(raw_payload, bytes) else raw_payload
    return _as_json_object(json.loads(decoded_payload))


def _as_json_object(payload: Any) -> JsonObject:
    if not isinstance(payload, dict):
        raise AssertionError(f"Expected JSON object payload, got {type(payload)!r}")
    return cast(JsonObject, payload)
