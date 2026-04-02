from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260402_1200"
down_revision = "20260328_1700"
branch_labels = None
depends_on = None

settlement_outcome_enum = sa.Enum("win", "loss", "draw", native_enum=False)


def _uuid_type(dialect_name: str) -> sa.types.TypeEngine[object]:
    if dialect_name == "postgresql":
        return postgresql.UUID(as_uuid=False)
    return sa.String(length=36)


def _timestamp_server_default(dialect_name: str) -> sa.DefaultClause | sa.TextClause:
    if dialect_name == "postgresql":
        return sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)")
    return sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    uuid_type = _uuid_type(dialect_name)
    timestamp_default = _timestamp_server_default(dialect_name)

    op.create_table(
        "match_settlements",
        sa.Column("match_id", uuid_type, nullable=False),
        sa.Column(
            "settled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=timestamp_default,
        ),
        sa.ForeignKeyConstraint(
            ["match_id"], ["matches.id"], name=op.f("fk_match_settlements_match_id_matches")
        ),
        sa.PrimaryKeyConstraint("match_id", name=op.f("pk_match_settlements")),
    )
    op.create_table(
        "player_match_settlements",
        sa.Column("player_id", uuid_type, nullable=False),
        sa.Column("match_id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("api_key_id", uuid_type, nullable=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("is_agent", sa.Boolean(), nullable=False),
        sa.Column("outcome", settlement_outcome_enum, nullable=False),
        sa.Column("elo_before", sa.Integer(), nullable=False),
        sa.Column("elo_after", sa.Integer(), nullable=False),
        sa.Column(
            "settled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=timestamp_default,
        ),
        sa.ForeignKeyConstraint(
            ["api_key_id"],
            ["api_keys.id"],
            name=op.f("fk_player_match_settlements_api_key_id_api_keys"),
        ),
        sa.ForeignKeyConstraint(
            ["match_id"], ["matches.id"], name=op.f("fk_player_match_settlements_match_id_matches")
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name=op.f("fk_player_match_settlements_player_id_players"),
        ),
        sa.PrimaryKeyConstraint("player_id", name=op.f("pk_player_match_settlements")),
    )
    op.create_index(
        op.f("ix_player_match_settlements_match_id"),
        "player_match_settlements",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_player_match_settlements_user_id"),
        "player_match_settlements",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_player_match_settlements_api_key_id"),
        "player_match_settlements",
        ["api_key_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_player_match_settlements_api_key_id"), table_name="player_match_settlements"
    )
    op.drop_index(
        op.f("ix_player_match_settlements_user_id"), table_name="player_match_settlements"
    )
    op.drop_index(
        op.f("ix_player_match_settlements_match_id"), table_name="player_match_settlements"
    )
    for table_name in _drop_order():
        op.drop_table(table_name)


def _drop_order() -> Sequence[str]:
    return ("player_match_settlements", "match_settlements")
