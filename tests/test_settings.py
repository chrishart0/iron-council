from pathlib import Path

from server.settings import DEFAULT_DATABASE_URL, ENV_FILE_VARIABLE, get_settings


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


def test_get_settings_falls_back_to_default_database_url_when_no_env_source_exists() -> None:
    settings = get_settings(env={})

    assert settings.database_url == DEFAULT_DATABASE_URL


def test_get_settings_uses_configured_env_file_override(tmp_path: Path) -> None:
    env_file = tmp_path / "alternate.env"
    env_file.write_text(
        "DATABASE_URL=postgresql://override-user:override-pass@127.0.0.1:54321/override_db\n"
    )

    settings = get_settings(env={ENV_FILE_VARIABLE: str(env_file)})

    assert (
        settings.database_url
        == "postgresql://override-user:override-pass@127.0.0.1:54321/override_db"
    )
