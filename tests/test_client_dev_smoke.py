import os
import signal
import socket
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CLIENT_ROOT = REPO_ROOT / "client"
NEXT_ENV = CLIENT_ROOT / "next-env.d.ts"
NEXT_BIN = CLIENT_ROOT / "node_modules/next/dist/bin/next"
WORKSPACE_WARNING = "inferred your workspace root"
EXPECTED_NEXT_ENV_IMPORT = 'import "./.next/types/routes.d.ts";'


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _read_next_env() -> str:
    return NEXT_ENV.read_text()


def _collect_dev_output(port: int) -> str:
    process = subprocess.Popen(
        ["npm", "run", "dev", "--", "--hostname", "127.0.0.1", "--port", str(port)],
        cwd=CLIENT_ROOT,
        env={**os.environ, "CI": "1"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )

    lines: list[str] = []
    ready_markers = (
        "Ready in",
        "Local:",
        f"127.0.0.1:{port}",
    )
    deadline = time.monotonic() + 30

    try:
        while time.monotonic() < deadline:
            if process.stdout is None:
                raise AssertionError("next dev did not expose stdout")

            line = process.stdout.readline()
            if line:
                lines.append(line)
                if any(marker in line for marker in ready_markers):
                    break
                continue

            if process.poll() is not None:
                break

            time.sleep(0.1)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)

    output = "".join(lines)
    if process.returncode not in (0, None, 130, -2):
        raise AssertionError(f"next dev exited early with code {process.returncode}:\n{output}")

    return output


def test_next_dev_uses_client_workspace_without_warning_or_generated_type_drift() -> None:
    if not NEXT_BIN.exists():
        pytest.skip("client Next.js dependencies are not installed in this worktree")

    before = _read_next_env()
    assert EXPECTED_NEXT_ENV_IMPORT in before

    output = _collect_dev_output(_reserve_port())

    after = _read_next_env()

    assert WORKSPACE_WARNING not in output
    assert before == after
