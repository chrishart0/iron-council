from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260403_2100"
down_revision = "20260403_1900"
branch_labels = None
depends_on = None


def _uuid_type(dialect_name: str) -> sa.types.TypeEngine[object]:
    if dialect_name == "postgresql":
        return postgresql.UUID(as_uuid=False)
    return sa.String(length=36)


def _json_type(dialect_name: str) -> sa.types.TypeEngine[object]:
    if dialect_name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _timestamp_server_default(dialect_name: str) -> sa.DefaultClause | sa.TextClause:
    if dialect_name == "postgresql":
        return sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)")
    return sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    uuid_type = _uuid_type(dialect_name)
    json_type = _json_type(dialect_name)
    timestamp_default = _timestamp_server_default(dialect_name)

    op.create_table(
        "owned_agent_overrides",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("match_id", uuid_type, nullable=False),
        sa.Column("owner_user_id", uuid_type, nullable=False),
        sa.Column("agent_player_id", uuid_type, nullable=False),
        sa.Column("tick", sa.Integer(), nullable=False),
        sa.Column("superseded_submission_count", sa.Integer(), nullable=False),
        sa.Column("orders", json_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=timestamp_default,
        ),
        sa.ForeignKeyConstraint(
            ["agent_player_id"],
            ["players.id"],
            name=op.f("fk_owned_agent_overrides_agent_player_id_players"),
        ),
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["matches.id"],
            name=op.f("fk_owned_agent_overrides_match_id_matches"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_owned_agent_overrides")),
    )
    op.create_index(
        op.f("ix_owned_agent_overrides_agent_player_id"),
        "owned_agent_overrides",
        ["agent_player_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_owned_agent_overrides_owner_user_id"),
        "owned_agent_overrides",
        ["owner_user_id"],
        unique=False,
    )


def downgrade() -> None:
    for index_name in _drop_indexes():
        op.drop_index(index_name, table_name="owned_agent_overrides")
    op.drop_table("owned_agent_overrides")


def _drop_indexes() -> Sequence[str]:
    return (
        op.f("ix_owned_agent_overrides_owner_user_id"),
        op.f("ix_owned_agent_overrides_agent_player_id"),
    )
