from pathlib import Path

from server.settings import DEFAULT_DATABASE_URL

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_local_postgres_defaults_stay_in_sync_across_settings_and_docs() -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    env_example = (REPO_ROOT / "env.local.example").read_text()
    support_services = (REPO_ROOT / "compose.support-services.yaml").read_text()

    assert (
        DEFAULT_DATABASE_URL
        == "postgresql://iron_counsil:iron_counsil@127.0.0.1:54321/iron_counsil"
    )
    assert f"DATABASE_URL={DEFAULT_DATABASE_URL}" in env_example
    assert DEFAULT_DATABASE_URL in readme
    assert "POSTGRES_DB: iron_counsil" in support_services
    assert "POSTGRES_USER: iron_counsil" in support_services
    assert "POSTGRES_PASSWORD: iron_counsil" in support_services


def test_readme_explains_how_to_run_a_focused_pytest_without_the_coverage_gate() -> None:
    readme = (REPO_ROOT / "README.md").read_text()

    assert "uv run pytest --no-cov tests/api/test_health.py" in readme
    assert "coverage gate" in readme
