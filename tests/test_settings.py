from pathlib import Path

from server.settings import (
    DEFAULT_DATABASE_URL,
    ENV_FILE_VARIABLE,
    MATCH_REGISTRY_BACKEND_VARIABLE,
    derive_worktree_database_url,
    get_settings,
)


def test_get_settings_loads_database_url_from_local_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / "env.local"
    env_file.write_text(
        "DATABASE_URL=postgresql://file-user:file-password@127.0.0.1:54321/file_db\n"
    )

    settings = get_settings(env={}, env_file=env_file, worktree_path=Path("/tmp/iron-12-3"))

    assert settings.database_url.startswith(
        "postgresql+psycopg://file-user:file-password@127.0.0.1:54321/file_db_iron_12_3_"
    )


def test_get_settings_prefers_explicit_environment_over_local_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / "env.local"
    env_file.write_text(
        "DATABASE_URL=postgresql://file-user:file-password@127.0.0.1:54321/file_db\n"
    )

    settings = get_settings(
        env={"DATABASE_URL": "postgresql://env-user:env-password@127.0.0.1:54321/env_db"},
        env_file=env_file,
        worktree_path=Path("/tmp/iron-12-3"),
    )

    assert settings.database_url.startswith(
        "postgresql+psycopg://env-user:env-password@127.0.0.1:54321/env_db_iron_12_3_"
    )


def test_get_settings_falls_back_to_default_database_url_when_no_env_source_exists(
    tmp_path: Path,
) -> None:
    settings = get_settings(
        env={},
        env_file=tmp_path / "missing.env",
        worktree_path=Path("/tmp/iron-12-3"),
    )

    assert (
        DEFAULT_DATABASE_URL
        == "postgresql+psycopg://iron_council:iron_council@127.0.0.1:54321/iron_council"
    )
    assert settings.database_url != DEFAULT_DATABASE_URL
    assert settings.database_url.startswith(
        "postgresql+psycopg://iron_council:iron_council@127.0.0.1:54321/iron_council_iron_12_3_"
    )


def test_get_settings_uses_configured_env_file_override(tmp_path: Path) -> None:
    env_file = tmp_path / "alternate.env"
    env_file.write_text(
        "DATABASE_URL=postgresql://override-user:override-password@127.0.0.1:54321/override_db\n"
    )

    settings = get_settings(
        env={ENV_FILE_VARIABLE: str(env_file)},
        worktree_path=Path("/tmp/iron-12-3"),
    )

    assert settings.database_url.startswith(
        "postgresql+psycopg://override-user:override-password@127.0.0.1:54321/override_db_iron_12_3_"
    )


def test_derive_worktree_database_url_is_deterministic_for_same_inputs() -> None:
    worktree = Path("/tmp/iron-12-3")

    first = derive_worktree_database_url(DEFAULT_DATABASE_URL, worktree_path=worktree)
    second = derive_worktree_database_url(DEFAULT_DATABASE_URL, worktree_path=worktree)

    assert first == second
    assert first.startswith("postgresql+psycopg://iron_council:iron_council@127.0.0.1:54321/")
    assert first.removeprefix(
        "postgresql+psycopg://iron_council:iron_council@127.0.0.1:54321/"
    ).startswith("iron_council_iron_12_3_")


def test_derive_worktree_database_url_isolates_parallel_lanes() -> None:
    worktree = Path("/tmp/iron-12-3")

    alpha = derive_worktree_database_url(
        DEFAULT_DATABASE_URL,
        worktree_path=worktree,
        lane="alpha",
    )
    beta = derive_worktree_database_url(
        DEFAULT_DATABASE_URL,
        worktree_path=worktree,
        lane="beta",
    )

    assert alpha != beta
    assert alpha.endswith("_alpha")
    assert beta.endswith("_beta")


def test_get_settings_preserves_non_postgres_urls_and_ignores_invalid_env_lines(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "env.local"
    env_file.write_text(
        "# comment-only line\n"
        "this is not valid env syntax\n"
        "DATABASE_URL=sqlite+pysqlite:///tmp/isolated.db\n"
    )

    settings = get_settings(env={}, env_file=env_file, worktree_path=Path("/tmp/iron-12-3"))

    assert settings.database_url == "sqlite+pysqlite:///tmp/isolated.db"


def test_derive_worktree_database_url_ignores_empty_lane_slug() -> None:
    derived = derive_worktree_database_url(
        DEFAULT_DATABASE_URL,
        worktree_path=Path("/tmp/iron-12-3"),
        lane="!!!",
    )

    assert derived.endswith("iron_council_iron_12_3_89b0fbd6")


def test_get_settings_normalizes_legacy_postgresql_scheme_to_psycopg(tmp_path: Path) -> None:
    env_file = tmp_path / "env.local"
    env_file.write_text(
        "DATABASE_URL=postgresql://legacy-user:legacy-password@127.0.0.1:54321/legacy_db\n"
    )

    settings = get_settings(env={}, env_file=env_file, worktree_path=Path("/tmp/iron-12-3"))

    assert settings.database_url.startswith(
        "postgresql+psycopg://legacy-user:legacy-password@127.0.0.1:54321/legacy_db_iron_12_3_"
    )


def test_get_settings_loads_human_jwt_configuration(tmp_path: Path) -> None:
    env_file = tmp_path / "env.local"
    env_file.write_text(
        "HUMAN_JWT_SECRET=test-human-secret-key-material-1234\n"
        "HUMAN_JWT_ISSUER=https://supabase.test/auth/v1\n"
        "HUMAN_JWT_AUDIENCE=authenticated\n"
        "HUMAN_JWT_REQUIRED_ROLE=authenticated\n"
    )

    settings = get_settings(env={}, env_file=env_file, worktree_path=Path("/tmp/iron-12-3"))

    assert settings.human_jwt_secret == "test-human-secret-key-material-1234"
    assert settings.human_jwt_issuer == "https://supabase.test/auth/v1"
    assert settings.human_jwt_audience == "authenticated"
    assert settings.human_jwt_required_role == "authenticated"


def test_get_settings_loads_match_registry_backend_from_environment() -> None:
    settings = get_settings(
        env={MATCH_REGISTRY_BACKEND_VARIABLE: "db"},
        worktree_path=Path("/tmp/iron-12-3"),
    )

    assert settings.match_registry_backend == "db"
