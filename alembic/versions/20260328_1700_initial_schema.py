from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260328_1700"
down_revision = None
branch_labels = None
depends_on = None

match_status_enum = sa.Enum("lobby", "active", "paused", "completed", native_enum=False)
message_channel_type_enum = sa.Enum("dm", "group", "world", native_enum=False)
treaty_type_enum = sa.Enum("non_aggression", "defensive", "trade", native_enum=False)
treaty_status_enum = sa.Enum(
    "active",
    "broken_by_a",
    "broken_by_b",
    "withdrawn",
    native_enum=False,
)


def _uuid_type(dialect_name: str) -> sa.types.TypeEngine[object]:
    if dialect_name == "postgresql":
        return postgresql.UUID(as_uuid=False)
    return sa.String(length=36)


def _json_type(dialect_name: str) -> sa.types.TypeEngine[object]:
    if dialect_name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _tick_log_id_type(dialect_name: str) -> sa.types.TypeEngine[object]:
    if dialect_name == "sqlite":
        return sa.Integer()
    return sa.BigInteger()


def _timestamp_server_default(dialect_name: str) -> sa.DefaultClause | sa.TextClause:
    if dialect_name == "postgresql":
        return sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)")
    return sa.text("CURRENT_TIMESTAMP")


def _create_indexes() -> None:
    op.create_index(op.f("ix_api_keys_user_id"), "api_keys", ["user_id"], unique=False)
    op.create_index(op.f("ix_players_user_id"), "players", ["user_id"], unique=False)


def _drop_indexes() -> None:
    op.drop_index(op.f("ix_players_user_id"), table_name="players")
    op.drop_index(op.f("ix_api_keys_user_id"), table_name="api_keys")


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    uuid_type = _uuid_type(dialect_name)
    json_type = _json_type(dialect_name)
    timestamp_default = _timestamp_server_default(dialect_name)

    op.create_table(
        "matches",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("config", json_type, nullable=False),
        sa.Column("status", match_status_enum, nullable=False),
        sa.Column("current_tick", sa.Integer(), nullable=False),
        sa.Column("state", json_type, nullable=False),
        sa.Column("winner_alliance", uuid_type, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=timestamp_default,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=timestamp_default,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_matches")),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column("elo_rating", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=timestamp_default,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_keys")),
    )
    op.create_table(
        "alliances",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("match_id", uuid_type, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("leader_id", uuid_type, nullable=False),
        sa.Column("formed_tick", sa.Integer(), nullable=False),
        sa.Column("dissolved_tick", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["match_id"], ["matches.id"], name=op.f("fk_alliances_match_id_matches")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alliances")),
    )
    op.create_table(
        "players",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("match_id", uuid_type, nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("is_agent", sa.Boolean(), nullable=False),
        sa.Column("api_key_id", uuid_type, nullable=True),
        sa.Column("elo_rating", sa.Integer(), nullable=False),
        sa.Column("alliance_id", uuid_type, nullable=True),
        sa.Column("alliance_joined_tick", sa.Integer(), nullable=True),
        sa.Column("eliminated_at", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["alliance_id"], ["alliances.id"], name=op.f("fk_players_alliance_id_alliances")
        ),
        sa.ForeignKeyConstraint(
            ["api_key_id"], ["api_keys.id"], name=op.f("fk_players_api_key_id_api_keys")
        ),
        sa.ForeignKeyConstraint(
            ["match_id"], ["matches.id"], name=op.f("fk_players_match_id_matches")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_players")),
    )
    op.create_table(
        "messages",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("match_id", uuid_type, nullable=False),
        sa.Column("sender_id", uuid_type, nullable=False),
        sa.Column("channel_type", message_channel_type_enum, nullable=False),
        sa.Column("channel_id", uuid_type, nullable=True),
        sa.Column("recipient_id", uuid_type, nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tick", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=timestamp_default,
        ),
        sa.ForeignKeyConstraint(
            ["match_id"], ["matches.id"], name=op.f("fk_messages_match_id_matches")
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"], ["players.id"], name=op.f("fk_messages_sender_id_players")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    op.create_table(
        "treaties",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("match_id", uuid_type, nullable=False),
        sa.Column("player_a_id", uuid_type, nullable=False),
        sa.Column("player_b_id", uuid_type, nullable=False),
        sa.Column("treaty_type", treaty_type_enum, nullable=False),
        sa.Column("status", treaty_status_enum, nullable=False),
        sa.Column("signed_tick", sa.Integer(), nullable=False),
        sa.Column("broken_tick", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=timestamp_default,
        ),
        sa.ForeignKeyConstraint(
            ["match_id"], ["matches.id"], name=op.f("fk_treaties_match_id_matches")
        ),
        sa.ForeignKeyConstraint(
            ["player_a_id"], ["players.id"], name=op.f("fk_treaties_player_a_id_players")
        ),
        sa.ForeignKeyConstraint(
            ["player_b_id"], ["players.id"], name=op.f("fk_treaties_player_b_id_players")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_treaties")),
    )
    op.create_table(
        "tick_log",
        sa.Column("id", _tick_log_id_type(dialect_name), primary_key=True, autoincrement=True),
        sa.Column("match_id", uuid_type, nullable=False),
        sa.Column("tick", sa.Integer(), nullable=False),
        sa.Column("state_snapshot", json_type, nullable=False),
        sa.Column("orders", json_type, nullable=False),
        sa.Column("events", json_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=timestamp_default,
        ),
        sa.ForeignKeyConstraint(
            ["match_id"], ["matches.id"], name=op.f("fk_tick_log_match_id_matches")
        ),
    )
    _create_indexes()


def downgrade() -> None:
    _drop_indexes()
    for table_name in _drop_order():
        op.drop_table(table_name)


def _drop_order() -> Sequence[str]:
    return (
        "tick_log",
        "treaties",
        "messages",
        "players",
        "alliances",
        "api_keys",
        "matches",
    )
