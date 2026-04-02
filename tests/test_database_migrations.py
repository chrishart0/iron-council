from __future__ import annotations

import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest
from alembic.config import Config
from server.db.config import configure_alembic_database_url
from server.db.testing import (
    ALEMBIC_INI_PATH,
    build_alembic_config,
    prepare_test_database,
    provision_seeded_database,
)
from sqlalchemy import create_engine, inspect, text


def test_makefile_exposes_stable_database_setup_and_reset_commands() -> None:
    setup_result = subprocess.run(
        ["make", "-n", "db-setup"],
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

    assert setup_result.returncode == 0
    assert "uv run python -m server.db.tooling setup" in setup_result.stdout
    assert reset_result.returncode == 0
    assert "uv run python -m server.db.tooling reset" in reset_result.stdout


def test_makefile_exposes_stable_real_api_and_smoke_commands() -> None:
    real_api_result = subprocess.run(
        ["make", "-n", "test-real-api"],
        check=False,
        capture_output=True,
        text=True,
    )
    smoke_result = subprocess.run(
        ["make", "-n", "test-smoke"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert real_api_result.returncode == 0
    assert "uv run pytest --no-cov tests/api/test_agent_process_api.py" in real_api_result.stdout
    assert smoke_result.returncode == 0
    assert "uv run pytest --no-cov tests/e2e/test_api_smoke.py" in smoke_result.stdout


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
        "match_settlements",
        "messages",
        "player_match_settlements",
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


def test_prepare_test_database_requires_database_url_when_no_config_is_provided() -> None:
    with pytest.raises(ValueError, match="database_url is required"):
        prepare_test_database(reset=False)


def test_provision_seeded_database_converges_to_deterministic_data_after_reset(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'seeded.db'}"

    provision_seeded_database(database_url=database_url, reset=False)
    baseline = _seeded_database_snapshot(database_url)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM messages"))
        connection.execute(text("DELETE FROM treaties"))
        connection.execute(text("DELETE FROM tick_log"))
        connection.execute(text("DELETE FROM players"))
        connection.execute(text("DELETE FROM alliances"))
        connection.execute(text("DELETE FROM api_keys"))
        connection.execute(text("DELETE FROM matches"))

    provision_seeded_database(database_url=database_url, reset=True)

    assert _seeded_database_snapshot(database_url) == baseline


def test_seed_database_reuses_stable_tick_log_ids_on_postgres_repeated_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeConnection:
        def __init__(self) -> None:
            self.tables: dict[str, list[dict[str, object]]] = {"tick_log": []}
            self.next_tick_log_id = 1

        def __enter__(self) -> FakeConnection:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def execute(
            self,
            statement: object,
            parameters: Sequence[dict[str, object]] | dict[str, object] | None = None,
        ) -> None:
            sql = str(statement)
            if sql.startswith("DELETE FROM "):
                table_name = sql.removeprefix("DELETE FROM ").strip()
                self.tables.setdefault(table_name, []).clear()
                return

            if "INSERT INTO tick_log" not in sql:
                return

            assert isinstance(parameters, list)
            for row in parameters:
                seeded_row = dict(row)
                seeded_row.setdefault("id", self.next_tick_log_id)
                self.next_tick_log_id += 1
                self.tables["tick_log"].append(seeded_row)

    class FakeEngine:
        def __init__(self) -> None:
            self.connection = FakeConnection()

        def begin(self) -> FakeConnection:
            return self.connection

    engine = FakeEngine()
    monkeypatch.setattr("server.db.testing.create_engine", lambda _database_url: engine)

    from server.db.testing import seed_database

    seed_database("postgresql://example/test_db")
    first_run = tuple(engine.connection.tables["tick_log"])

    seed_database("postgresql://example/test_db")
    second_run = tuple(engine.connection.tables["tick_log"])

    assert first_run == second_run
    assert second_run == (
        {
            "id": 9001,
            "match_id": "00000000-0000-0000-0000-000000000101",
            "tick": 142,
            "state_snapshot": '{"cities":{"london":{"owner":"Arthur","population":12}}}',
            "orders": '{"movements":[{"army_id":"army-1","destination":"york"}]}',
            "events": '{"summary":["Convoy secured","Trade revenue collected"]}',
            "created_at": datetime(2026, 3, 29, 0, 0, tzinfo=UTC),
        },
    )


def test_db_backed_test_fixture_applies_migrations_before_test_execution(
    migrated_test_database_url: str,
) -> None:
    inspector = inspect(create_engine(migrated_test_database_url))

    assert "matches" in inspector.get_table_names()


def test_ensure_database_exists_creates_missing_postgres_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = Mock()
    connection.execute.side_effect = [Mock(scalar_one_or_none=lambda: None), None]
    connect_context = Mock()
    connect_context.__enter__ = Mock(return_value=connection)
    connect_context.__exit__ = Mock(return_value=None)
    engine = Mock(connect=Mock(return_value=connect_context))

    monkeypatch.setattr("server.db.testing.create_engine", lambda *args, **kwargs: engine)

    from server.db.testing import ensure_database_exists

    ensure_database_exists("postgresql://iron_counsil:iron_counsil@127.0.0.1:54321/seed_db")

    assert connection.execute.call_count == 2
    assert "CREATE DATABASE" in str(connection.execute.call_args_list[1].args[0])


def _seeded_database_snapshot(database_url: str) -> dict[str, Sequence[tuple[object, ...]]]:
    engine = create_engine(database_url)
    queries = {
        "matches": "SELECT id, status, current_tick, winner_alliance FROM matches ORDER BY id",
        "api_keys": "SELECT id, user_id, elo_rating, is_active FROM api_keys ORDER BY id",
        "alliances": "SELECT id, match_id, leader_id, formed_tick FROM alliances ORDER BY id",
        "players": (
            "SELECT id, user_id, match_id, display_name, is_agent, api_key_id, alliance_id "
            "FROM players ORDER BY id"
        ),
        "messages": (
            "SELECT id, match_id, sender_id, channel_type, channel_id, recipient_id, tick "
            "FROM messages ORDER BY id"
        ),
        "treaties": (
            "SELECT id, match_id, player_a_id, player_b_id, treaty_type, status, signed_tick "
            "FROM treaties ORDER BY id"
        ),
        "tick_log": "SELECT id, match_id, tick FROM tick_log ORDER BY id",
    }

    with engine.begin() as connection:
        return {
            table_name: tuple(connection.execute(text(query)).tuples().all())
            for table_name, query in queries.items()
        }
