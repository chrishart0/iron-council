from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from server.agent_registry import build_seeded_agent_api_key, build_seeded_match_records
from server.auth import hash_api_key
from server.db.config import configure_alembic_database_url
from server.db.metadata import bind_utc_datetime_params
from server.db.migrations import reset_database, upgrade_database
from server.db.registry import _build_match_scoped_player_id

ALEMBIC_INI_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"


def build_alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("sqlalchemy.url", database_url)
    configure_alembic_database_url(config)
    return config


def prepare_test_database(
    *, config: Config | None = None, database_url: str | None = None, reset: bool
) -> None:
    resolved_config = config or build_alembic_config(_require_database_url(database_url))
    if reset:
        if database_url is not None and not _database_has_migration_state(database_url):
            upgrade_database(resolved_config)
            return
        reset_database(resolved_config)
        return
    upgrade_database(resolved_config)


def provision_seeded_database(*, database_url: str, reset: bool) -> None:
    ensure_database_exists(database_url)
    prepare_test_database(database_url=database_url, reset=reset)
    seed_database(database_url)


def ensure_database_exists(database_url: str) -> None:
    url = make_url(database_url)
    backend_name = url.get_backend_name()
    if backend_name == "sqlite":
        database = url.database
        if database is None or database == ":memory:":
            return
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        return

    if backend_name != "postgresql" or url.database is None:
        return

    database_name = url.database
    if not database_name.replace("_", "").isalnum():
        raise ValueError(f"Unsupported database name for provisioning: {database_name!r}")

    admin_url = url.set(database="postgres")
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        database_exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
            {"database_name": database_name},
        ).scalar_one_or_none()
        if database_exists is None:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))


def seed_database(database_url: str) -> None:
    engine = create_engine(database_url)
    backend_name = make_url(database_url).get_backend_name()
    seed_timestamp = datetime(2026, 3, 29, 0, 0, tzinfo=UTC)
    seeded_matches = build_seeded_match_records(
        primary_match_id="00000000-0000-0000-0000-000000000101",
        secondary_match_id="00000000-0000-0000-0000-000000000102",
    )

    with engine.begin() as connection:
        for table_name in (
            "messages",
            "treaties",
            "tick_log",
            "player_match_settlements",
            "match_settlements",
            "players",
            "alliances",
            "api_keys",
            "matches",
        ):
            connection.execute(text(f"DELETE FROM {table_name}"))

        connection.execute(
            bind_utc_datetime_params(
                text(
                    """
                INSERT INTO matches (
                    id, config, status, current_tick, state, winner_alliance, created_at, updated_at
                ) VALUES (
                    :id, :config, :status, :current_tick, :state, :winner_alliance,
                    :created_at, :updated_at
                )
                """
                ),
                "created_at",
                "updated_at",
            ),
            [
                {
                    "id": seeded_matches[0].match_id,
                    "config": (
                        '{"map":"britain","max_players":5,"turn_seconds":30,'
                        '"seed_profile":"agent_api_primary"}'
                    ),
                    "status": seeded_matches[0].status.value,
                    "current_tick": seeded_matches[0].state.tick,
                    "state": json.dumps(seeded_matches[0].state.model_dump(mode="json")),
                    "winner_alliance": None,
                    "created_at": seed_timestamp,
                    "updated_at": seed_timestamp,
                },
                {
                    "id": seeded_matches[1].match_id,
                    "config": (
                        '{"map":"britain","max_players":5,"turn_seconds":45,'
                        '"seed_profile":"agent_api_secondary"}'
                    ),
                    "status": seeded_matches[1].status.value,
                    "current_tick": seeded_matches[1].state.tick,
                    "state": json.dumps(seeded_matches[1].state.model_dump(mode="json")),
                    "winner_alliance": None,
                    "created_at": seed_timestamp,
                    "updated_at": seed_timestamp,
                },
            ],
        )
        connection.execute(
            bind_utc_datetime_params(
                text(
                    """
                INSERT INTO api_keys (
                    id, user_id, key_hash, elo_rating, is_active, created_at
                ) VALUES (
                    :id, :user_id, :key_hash, :elo_rating, :is_active, :created_at
                )
                """
                ),
                "created_at",
            ),
            [
                {
                    "id": "00000000-0000-0000-0000-000000000201",
                    "user_id": "00000000-0000-0000-0000-000000000301",
                    "key_hash": hash_api_key(build_seeded_agent_api_key("agent-player-1")),
                    "elo_rating": 1210,
                    "is_active": True,
                    "created_at": seed_timestamp,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000202",
                    "user_id": "00000000-0000-0000-0000-000000000302",
                    "key_hash": hash_api_key(build_seeded_agent_api_key("agent-player-2")),
                    "elo_rating": 1190,
                    "is_active": True,
                    "created_at": seed_timestamp,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000203",
                    "user_id": "00000000-0000-0000-0000-000000000303",
                    "key_hash": hash_api_key(build_seeded_agent_api_key("agent-player-3")),
                    "elo_rating": 1175,
                    "is_active": True,
                    "created_at": seed_timestamp,
                },
            ],
        )
        connection.execute(
            text(
                """
                INSERT INTO alliances (
                    id, match_id, name, leader_id, formed_tick, dissolved_tick
                ) VALUES (
                    :id, :match_id, :name, :leader_id, :formed_tick, :dissolved_tick
                )
                """
            ),
            [
                {
                    "id": "00000000-0000-0000-0000-000000000401",
                    "match_id": "00000000-0000-0000-0000-000000000101",
                    "name": "Western Accord",
                    "leader_id": _build_match_scoped_player_id(
                        match_id="00000000-0000-0000-0000-000000000101",
                        join_index=1,
                    ),
                    "formed_tick": 120,
                    "dissolved_tick": None,
                }
            ],
        )
        connection.execute(
            text(
                """
                INSERT INTO players (
                    id, user_id, match_id, display_name, is_agent, api_key_id, elo_rating,
                    alliance_id, alliance_joined_tick, eliminated_at
                ) VALUES (
                    :id, :user_id, :match_id, :display_name, :is_agent, :api_key_id, :elo_rating,
                    :alliance_id, :alliance_joined_tick, :eliminated_at
                )
                """
            ),
            [
                {
                    "id": _build_match_scoped_player_id(
                        match_id="00000000-0000-0000-0000-000000000101",
                        join_index=1,
                    ),
                    "user_id": "00000000-0000-0000-0000-000000000301",
                    "match_id": "00000000-0000-0000-0000-000000000101",
                    "display_name": "Arthur",
                    "is_agent": False,
                    "api_key_id": "00000000-0000-0000-0000-000000000201",
                    "elo_rating": 1210,
                    "alliance_id": "00000000-0000-0000-0000-000000000401",
                    "alliance_joined_tick": 120,
                    "eliminated_at": None,
                },
                {
                    "id": _build_match_scoped_player_id(
                        match_id="00000000-0000-0000-0000-000000000101",
                        join_index=2,
                    ),
                    "user_id": "00000000-0000-0000-0000-000000000302",
                    "match_id": "00000000-0000-0000-0000-000000000101",
                    "display_name": "Morgana",
                    "is_agent": True,
                    "api_key_id": "00000000-0000-0000-0000-000000000202",
                    "elo_rating": 1190,
                    "alliance_id": "00000000-0000-0000-0000-000000000401",
                    "alliance_joined_tick": 120,
                    "eliminated_at": None,
                },
                {
                    "id": _build_match_scoped_player_id(
                        match_id="00000000-0000-0000-0000-000000000101",
                        join_index=3,
                    ),
                    "user_id": "00000000-0000-0000-0000-000000000303",
                    "match_id": "00000000-0000-0000-0000-000000000101",
                    "display_name": "Gawain",
                    "is_agent": True,
                    "api_key_id": "00000000-0000-0000-0000-000000000203",
                    "elo_rating": 1175,
                    "alliance_id": None,
                    "alliance_joined_tick": None,
                    "eliminated_at": None,
                },
            ],
        )
        connection.execute(
            bind_utc_datetime_params(
                text(
                    """
                INSERT INTO messages (
                    id, match_id, sender_id, channel_type, channel_id, recipient_id, content,
                    tick, created_at
                ) VALUES (
                    :id, :match_id, :sender_id, :channel_type, :channel_id, :recipient_id,
                    :content, :tick, :created_at
                )
                """
                ),
                "created_at",
            ),
            [
                {
                    "id": "00000000-0000-0000-0000-000000000601",
                    "match_id": "00000000-0000-0000-0000-000000000101",
                    "sender_id": _build_match_scoped_player_id(
                        match_id="00000000-0000-0000-0000-000000000101",
                        join_index=1,
                    ),
                    "channel_type": "group",
                    "channel_id": "00000000-0000-0000-0000-000000000401",
                    "recipient_id": None,
                    "content": "Escort the grain convoy through the Irish Sea.",
                    "tick": 142,
                    "created_at": seed_timestamp,
                }
            ],
        )
        connection.execute(
            bind_utc_datetime_params(
                text(
                    """
                INSERT INTO treaties (
                    id, match_id, player_a_id, player_b_id, treaty_type, status, signed_tick,
                    broken_tick, created_at
                ) VALUES (
                    :id, :match_id, :player_a_id, :player_b_id, :treaty_type, :status,
                    :signed_tick, :broken_tick, :created_at
                )
                """
                ),
                "created_at",
            ),
            [
                {
                    "id": "00000000-0000-0000-0000-000000000701",
                    "match_id": "00000000-0000-0000-0000-000000000101",
                    "player_a_id": _build_match_scoped_player_id(
                        match_id="00000000-0000-0000-0000-000000000101",
                        join_index=1,
                    ),
                    "player_b_id": _build_match_scoped_player_id(
                        match_id="00000000-0000-0000-0000-000000000101",
                        join_index=3,
                    ),
                    "treaty_type": "trade",
                    "status": "active",
                    "signed_tick": 141,
                    "broken_tick": None,
                    "created_at": seed_timestamp,
                }
            ],
        )
        connection.execute(
            bind_utc_datetime_params(
                text(
                    """
                INSERT INTO tick_log (
                    id, match_id, tick, state_snapshot, orders, events, created_at
                ) VALUES (
                    :id, :match_id, :tick, :state_snapshot, :orders, :events, :created_at
                )
                """
                ),
                "created_at",
            ),
            [
                {
                    "id": 9001,
                    "match_id": "00000000-0000-0000-0000-000000000101",
                    "tick": 142,
                    "state_snapshot": '{"cities":{"london":{"owner":"Arthur","population":12}}}',
                    "orders": '{"movements":[{"army_id":"army-1","destination":"york"}]}',
                    "events": '{"summary":["Convoy secured","Trade revenue collected"]}',
                    "created_at": seed_timestamp,
                }
            ],
        )
        if backend_name == "postgresql":
            connection.execute(
                text(
                    """
                    SELECT setval(
                        pg_get_serial_sequence('tick_log', 'id'),
                        COALESCE((SELECT MAX(id) FROM tick_log), 1),
                        true
                    )
                    """
                )
            )


def _require_database_url(database_url: str | None) -> str:
    if database_url is None:
        raise ValueError("database_url is required when config is not provided.")
    return database_url


def _database_has_migration_state(database_url: str) -> bool:
    inspector = inspect(create_engine(database_url))
    return "alembic_version" in inspector.get_table_names()
