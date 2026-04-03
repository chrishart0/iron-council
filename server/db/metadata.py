from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = sa.MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = metadata


uuid_type = sa.String(length=36).with_variant(postgresql.UUID(as_uuid=False), "postgresql")
json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
tick_log_id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


class UTCDateTime(sa.types.TypeDecorator[datetime]):
    impl = sa.DateTime(timezone=True)
    cache_ok = True

    def load_dialect_impl(self, dialect: sa.Dialect) -> sa.types.TypeEngine[Any]:
        if dialect.name == "sqlite":
            return dialect.type_descriptor(sa.String())
        return dialect.type_descriptor(sa.DateTime(timezone=True))

    def process_bind_param(
        self,
        value: datetime | None,
        dialect: sa.Dialect,
    ) -> datetime | str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime requires timezone-aware datetime values.")

        utc_value = value.astimezone(UTC)
        if dialect.name == "sqlite":
            return utc_value.isoformat(sep=" ")
        return utc_value

    def process_result_value(
        self,
        value: datetime | str | None,
        dialect: sa.Dialect,
    ) -> datetime | None:
        if value is None:
            return None

        parsed_value = datetime.fromisoformat(value) if isinstance(value, str) else value
        if parsed_value.tzinfo is None:
            return parsed_value.replace(tzinfo=UTC)
        return parsed_value.astimezone(UTC)


utc_datetime_type = UTCDateTime()


def bind_utc_datetime_params(statement: sa.TextClause, *names: str) -> sa.TextClause:
    return statement.bindparams(*(sa.bindparam(name, type_=utc_datetime_type) for name in names))
