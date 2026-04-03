from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260403_1200"
down_revision = "20260402_1200"
branch_labels = None
depends_on = None

agent_entitlement_grant_source_enum = sa.Enum("manual", "dev", native_enum=False)


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
        "agent_entitlement_grants",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("grant_source", agent_entitlement_grant_source_enum, nullable=False),
        sa.Column("concurrent_match_allowance", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_entitlement_grants")),
    )
    op.create_index(
        op.f("ix_agent_entitlement_grants_user_id"),
        "agent_entitlement_grants",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_agent_entitlement_grants_user_id"), table_name="agent_entitlement_grants"
    )
    op.drop_table("agent_entitlement_grants")
