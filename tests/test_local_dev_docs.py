from pathlib import Path

from server.settings import DEFAULT_DATABASE_URL

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_local_postgres_defaults_stay_in_sync_across_settings_and_docs() -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    env_example = (REPO_ROOT / "env.local.example").read_text()
    support_services = (REPO_ROOT / "compose.support-services.yaml").read_text()

    assert (
        DEFAULT_DATABASE_URL
        == "postgresql+psycopg://iron_council:iron_council@127.0.0.1:54321/iron_council"
    )
    assert f"DATABASE_URL={DEFAULT_DATABASE_URL}" in env_example
    assert DEFAULT_DATABASE_URL in readme
    assert "docker compose -f compose.support-services.yaml down -v" in readme
    assert "older `iron_counsil` support-services volume" in readme
    assert "POSTGRES_DB: iron_council" in support_services
    assert "POSTGRES_USER: iron_council" in support_services
    assert "POSTGRES_PASSWORD: iron_council" in support_services


def test_readme_explains_how_to_run_a_focused_pytest_without_the_coverage_gate() -> None:
    readme = (REPO_ROOT / "README.md").read_text()

    assert "uv run pytest --no-cov tests/api/test_health.py" in readme
    assert "coverage gate" in readme


def test_readme_documents_worktree_local_database_setup_and_reset_workflow() -> None:
    readme = (REPO_ROOT / "README.md").read_text()

    assert "make db-setup" in readme
    assert "make db-reset" in readme
    assert "IRON_COUNCIL_DB_LANE" in readme
    assert "current worktree path" in readme


def test_readme_documents_real_process_api_targets_and_db_registry_mode() -> None:
    readme = (REPO_ROOT / "README.md").read_text()

    assert "make test-real-api" in readme
    assert "make test-smoke" in readme
    assert "IRON_COUNCIL_MATCH_REGISTRY_BACKEND=db" in readme
    assert "temporary migrated and deterministically seeded SQLite database" in readme


def test_readme_documents_public_match_browser_client_workflow() -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    client_env_example = (REPO_ROOT / "client" / ".env.example").read_text()

    assert "make client-install" in readme
    assert "npm run dev" in readme
    assert "http://127.0.0.1:3000/matches" in readme
    assert "http://127.0.0.1:3000/matches/<match_id>" in readme
    assert "http://127.0.0.1:3000/matches/<match_id>/live" in readme
    assert "http://127.0.0.1:3000/matches/<match_id>/play" in readme
    assert "http://127.0.0.1:3000/lobby" in readme
    assert "No client env vars are required" in readme
    assert "browser session panel stores the API base URL" in readme
    assert "human bearer token" in readme
    assert "Public pages stay available without auth" in readme
    assert "make client-lint" in readme
    assert "make client-test" in readme
    assert "make client-build" in readme
    assert "No client environment variables are required for this story." in client_env_example


def test_readme_and_env_example_document_local_browser_cors_workflow() -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    env_example = (REPO_ROOT / "env.local.example").read_text()

    assert "IRON_COUNCIL_BROWSER_ORIGINS" in readme
    assert "http://127.0.0.1:3000" in readme
    assert "http://localhost:3000" in readme
    assert "alternate local browser ports or hosts" in readme
    assert "IRON_COUNCIL_BROWSER_ORIGINS" in env_example


def test_core_architecture_documents_actual_public_and_authenticated_surface() -> None:
    architecture = (REPO_ROOT / "core-architecture.md").read_text()

    assert "/api/v1/leaderboard" in architecture
    assert "/api/v1/matches/completed" in architecture
    assert "/api/v1/matches/{id}/history" in architecture
    assert "/api/v1/agents/{agent_id}/profile" in architecture
    assert "/api/v1/humans/{human_id}/profile" in architecture
    assert "IRON_COUNCIL_BROWSER_ORIGINS" in architecture
    assert "viewer=spectator" in architecture
    assert "viewer=player&player_id={player_id}&token={token}" in architecture
    assert "Spectators are read-only" in architecture
    assert (
        "Player websocket connections require a valid human JWT token query parameter."
        in architecture
    )


def test_public_entrypoint_docs_highlight_browse_history_and_profile_pages() -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    docs_index = (REPO_ROOT / "docs" / "index.md").read_text()

    assert "/leaderboard" in readme
    assert "/matches/completed" in readme
    assert "/matches/<match_id>/history" in readme
    assert "/agents/<agent_id>" in readme
    assert "/humans/<human_id>" in readme
    assert "public leaderboard" in docs_index
    assert "completed-match summaries" in docs_index
    assert "history/replay" in docs_index
    assert "public human/agent profile pages" in docs_index


def test_readme_docs_index_and_agent_sdk_document_self_serve_agent_key_lifecycle() -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    docs_index = (REPO_ROOT / "docs" / "index.md").read_text()
    agent_sdk = (REPO_ROOT / "agent-sdk" / "README.md").read_text()

    assert "/api/v1/account/api-keys" in readme
    assert "once only" in readme
    assert "Billing and entitlement rules are still" in readme
    assert "manual" in readme
    assert "dev" in readme
    assert "/api/v1/account/api-keys" in docs_index
    assert "one-time secret reveal" in docs_index
    assert "manual/dev inspection" in docs_index
    assert "POST /api/v1/account/api-keys" in agent_sdk
    assert "compact summaries only" in agent_sdk
    assert "manual" in agent_sdk
    assert "dev" in agent_sdk
