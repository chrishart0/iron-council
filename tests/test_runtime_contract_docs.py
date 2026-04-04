from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_control_script_is_checked_in_executable_and_reports_doctor_summary(
    tmp_path: Path,
) -> None:
    script = REPO_ROOT / "scripts" / "runtime-control.sh"
    env_file = tmp_path / "runtime.env"
    env_file.write_text("DATABASE_URL=sqlite+pysqlite:///tmp/story-51-1.db\n")

    assert script.is_file()
    assert os.access(script, os.X_OK)

    help_result = subprocess.run(
        [str(script), "help"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    help_output = help_result.stdout
    assert "doctor" in help_output
    assert "support-up" in help_output
    assert "db-setup" in help_output
    assert "server" in help_output
    assert "client-build" in help_output
    assert "client-start" in help_output
    assert "IRON_COUNCIL_ENV_FILE" in help_output

    doctor_result = subprocess.run(
        [str(script), "doctor"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "IRON_COUNCIL_ENV_FILE": str(env_file)},
    )

    doctor_output = doctor_result.stdout
    assert "Runtime doctor summary" in doctor_output
    assert f"- server env file: {env_file}" in doctor_output
    assert "- env file exists: yes" in doctor_output
    assert "- health check: curl http://127.0.0.1:8000/health" in doctor_output
    assert "- runtime status check: curl http://127.0.0.1:8000/health/runtime" in doctor_output


def test_runtime_env_contract_and_runbook_stay_in_sync_with_checked_in_runtime_artifacts() -> None:
    readme = " ".join((REPO_ROOT / "README.md").read_text().split())
    docs_index = " ".join((REPO_ROOT / "docs" / "index.md").read_text().split())
    env_contract = " ".join(
        (REPO_ROOT / "docs" / "operations" / "runtime-env-contract.md").read_text().split()
    )
    runbook = " ".join(
        (REPO_ROOT / "docs" / "operations" / "runtime-runbook.md").read_text().split()
    )
    runtime_env = " ".join((REPO_ROOT / "env.runtime.example").read_text().split())
    makefile = (REPO_ROOT / "Makefile").read_text()

    assert "./scripts/runtime-control.sh doctor" in readme
    assert "./scripts/runtime-control.sh server" in readme
    assert "./scripts/runtime-control.sh client-start" in readme
    assert "Runtime environment contract" in readme
    assert "Runtime runbook" in readme
    assert "make launch-readiness-smoke" in readme
    assert "local in-process request-size and burst-rate controls" in readme
    assert "not distributed, CDN, or WAF defenses" in readme
    assert "/api/v1/matches" in readme
    assert "/health/runtime" in readme
    assert "/ws/match/{match_id}" in readme

    assert "Runtime environment contract" in docs_index
    assert "Runtime runbook" in docs_index
    assert "launch abuse-control posture" in docs_index

    assert "DATABASE_URL" in runtime_env
    assert "IRON_COUNCIL_MATCH_REGISTRY_BACKEND=db" in runtime_env
    assert "HUMAN_JWT_SECRET" in runtime_env
    assert "HUMAN_JWT_ISSUER" in runtime_env
    assert "HUMAN_JWT_AUDIENCE" in runtime_env
    assert "HUMAN_JWT_REQUIRED_ROLE" in runtime_env
    assert "IRON_COUNCIL_BROWSER_ORIGINS" in runtime_env
    assert "IRON_COUNCIL_AUTHENTICATED_WRITE_MAX_BODY_BYTES" in runtime_env
    assert "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_LIMIT" in runtime_env
    assert "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS" in runtime_env
    assert "IRON_COUNCIL_SERVER_PORT" in runtime_env
    assert "IRON_COUNCIL_CLIENT_PORT" in runtime_env
    assert "selected public HTTP entrypoints and match websocket handshakes" in runtime_env
    assert "not a distributed or CDN/WAF control plane" in runtime_env

    assert "./scripts/runtime-control.sh" in env_contract
    assert "compose.support-services.yaml" in env_contract
    assert "IRON_COUNCIL_ENV_FILE" in env_contract
    assert "IRON_COUNCIL_DB_LANE" in env_contract
    assert "IRON_COUNCIL_AUTHENTICATED_WRITE_MAX_BODY_BYTES" in env_contract
    assert "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_LIMIT" in env_contract
    assert "IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS" in env_contract
    assert "413 payload_too_large" in env_contract
    assert "429 rate_limit_exceeded" in env_contract
    assert "client-build" in env_contract
    assert "client-start" in env_contract
    assert "/api/v1/matches" in env_contract
    assert "/health/runtime" in env_contract
    assert "/ws/match/{match_id}" in env_contract
    assert "local in-process only" in env_contract
    assert (
        "does not claim distributed coordination, CDN filtering, or WAF protection" in env_contract
    )

    assert "./scripts/runtime-control.sh doctor" in runbook
    assert "./scripts/runtime-control.sh support-up" in runbook
    assert "./scripts/runtime-control.sh db-setup" in runbook
    assert "curl http://127.0.0.1:8000/health" in runbook
    assert "curl http://127.0.0.1:8000/health/runtime" in runbook
    assert "/health/runtime" in runbook
    assert "make launch-readiness-smoke" in runbook
    assert "local in-process abuse controls" in runbook
    assert "not a CDN, WAF, or distributed rate-limit layer" in runbook
    assert "launch-readiness-smoke" in makefile
