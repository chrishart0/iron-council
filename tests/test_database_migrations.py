from __future__ import annotations

import subprocess
from pathlib import Path

from alembic.config import Config
from server.db.config import configure_alembic_database_url
from server.db.testing import ALEMBIC_INI_PATH, build_alembic_config, prepare_test_database
from sqlalchemy import create_engine, inspect, text


def test_makefile_exposes_stable_database_upgrade_and_reset_commands() -> None:
    upgrade_result = subprocess.run(
        ["make", "-n", "db-upgrade"],
        check=False,
        capture_output=True,
        text=True,
    )
    reset_result = subprocess.run(
        ["make", "-n", "db-reset"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert upgrade_result.returncode == 0
    assert "uv run alembic upgrade head" in upgrade_result.stdout
    assert reset_result.returncode == 0
    assert "uv run alembic downgrade base" in reset_result.stdout
    assert "uv run alembic upgrade head" in reset_result.stdout


def test_alembic_config_falls_back_to_settings_database_url(tmp_path: Path) -> None:
    env_file = tmp_path / "env.local"
    env_file.write_text("DATABASE_URL=sqlite+pysqlite:///configured-from-settings.db\n")

    config = Config(str(ALEMBIC_INI_PATH))
    database_url = configure_alembic_database_url(config, env={}, env_file=env_file)

    assert database_url == "sqlite+pysqlite:///configured-from-settings.db"
    assert config.get_main_option("sqlalchemy.url") == database_url


def test_build_alembic_config_preserves_explicit_database_url_override(tmp_path: Path) -> None:
    explicit_database_url = f"sqlite+pysqlite:///{tmp_path / 'explicit.db'}"

    config = build_alembic_config(explicit_database_url)

    assert config.get_main_option("sqlalchemy.url") == explicit_database_url


def test_alembic_upgrade_creates_persistence_schema_for_an_empty_database(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'fresh.db'}"

    config = build_alembic_config(database_url)
    prepare_test_database(config=config, reset=False)

    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert set(inspector.get_table_names()) == {
        "alembic_version",
        "alliances",
        "api_keys",
        "matches",
        "messages",
        "players",
        "tick_log",
        "treaties",
    }
    assert {column["name"] for column in inspector.get_columns("matches")} >= {
        "id",
        "config",
        "status",
        "current_tick",
        "state",
        "winner_alliance",
        "created_at",
        "updated_at",
    }
    assert {column["name"] for column in inspector.get_columns("players")} >= {
        "id",
        "user_id",
        "match_id",
        "display_name",
        "is_agent",
        "api_key_id",
        "elo_rating",
        "alliance_id",
        "alliance_joined_tick",
        "eliminated_at",
    }


def test_prepare_test_database_resets_to_head_after_existing_data(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'reset.db'}"
    config = build_alembic_config(database_url)
    prepare_test_database(config=config, reset=False)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO matches (
                    id, config, status, current_tick, state, winner_alliance
                ) VALUES (
                    '00000000-0000-0000-0000-000000000001',
                    '{}',
                    'lobby',
                    0,
                    '{}',
                    NULL
                )
                """
            )
        )

    prepare_test_database(config=config, reset=True)

    with engine.begin() as connection:
        count = connection.execute(text("SELECT COUNT(*) FROM matches")).scalar_one()

    assert count == 0


def test_db_backed_test_fixture_applies_migrations_before_test_execution(
    migrated_test_database_url: str,
) -> None:
    inspector = inspect(create_engine(migrated_test_database_url))

    assert "matches" in inspector.get_table_names()
