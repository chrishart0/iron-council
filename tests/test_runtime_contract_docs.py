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
    readme = (REPO_ROOT / "README.md").read_text()
    docs_index = (REPO_ROOT / "docs" / "index.md").read_text()
    env_contract = (REPO_ROOT / "docs" / "operations" / "runtime-env-contract.md").read_text()
    runbook = (REPO_ROOT / "docs" / "operations" / "runtime-runbook.md").read_text()
    runtime_env = (REPO_ROOT / "env.runtime.example").read_text()
    makefile = (REPO_ROOT / "Makefile").read_text()

    assert "./scripts/runtime-control.sh doctor" in readme
    assert "./scripts/runtime-control.sh server" in readme
    assert "./scripts/runtime-control.sh client-start" in readme
    assert "Runtime environment contract" in readme
    assert "Runtime runbook" in readme
    assert "make launch-readiness-smoke" in readme

    assert "Runtime environment contract" in docs_index
    assert "Runtime runbook" in docs_index

    assert "DATABASE_URL" in runtime_env
    assert "IRON_COUNCIL_MATCH_REGISTRY_BACKEND=db" in runtime_env
    assert "HUMAN_JWT_SECRET" in runtime_env
    assert "HUMAN_JWT_ISSUER" in runtime_env
    assert "HUMAN_JWT_AUDIENCE" in runtime_env
    assert "HUMAN_JWT_REQUIRED_ROLE" in runtime_env
    assert "IRON_COUNCIL_BROWSER_ORIGINS" in runtime_env
    assert "IRON_COUNCIL_SERVER_PORT" in runtime_env
    assert "IRON_COUNCIL_CLIENT_PORT" in runtime_env

    assert "./scripts/runtime-control.sh" in env_contract
    assert "compose.support-services.yaml" in env_contract
    assert "IRON_COUNCIL_ENV_FILE" in env_contract
    assert "IRON_COUNCIL_DB_LANE" in env_contract
    assert "client-build" in env_contract
    assert "client-start" in env_contract

    assert "./scripts/runtime-control.sh doctor" in runbook
    assert "./scripts/runtime-control.sh support-up" in runbook
    assert "./scripts/runtime-control.sh db-setup" in runbook
    assert "curl http://127.0.0.1:8000/health" in runbook
    assert "curl http://127.0.0.1:8000/health/runtime" in runbook
    assert "/health/runtime" in runbook
    assert "make launch-readiness-smoke" in runbook
    assert "launch-readiness-smoke" in makefile
