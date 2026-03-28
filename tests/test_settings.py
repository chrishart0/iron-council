from pathlib import Path

from server.settings import get_settings


def test_get_settings_loads_database_url_from_local_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / "env.local"
    env_file.write_text("DATABASE_URL=postgresql://file-user:file-pass@127.0.0.1:54321/file_db\n")

    settings = get_settings(env={}, env_file=env_file)

    assert settings.database_url == "postgresql://file-user:file-pass@127.0.0.1:54321/file_db"


def test_get_settings_prefers_explicit_environment_over_local_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / "env.local"
    env_file.write_text("DATABASE_URL=postgresql://file-user:file-pass@127.0.0.1:54321/file_db\n")

    settings = get_settings(
        env={"DATABASE_URL": "postgresql://env-user:env-pass@127.0.0.1:54321/env_db"},
        env_file=env_file,
    )

    assert settings.database_url == "postgresql://env-user:env-pass@127.0.0.1:54321/env_db"
