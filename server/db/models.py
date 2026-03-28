from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from server.db.metadata import Base, json_type, tick_log_id_type, uuid_type

MATCH_STATUSES = ("lobby", "active", "paused", "completed")
MESSAGE_CHANNEL_TYPES = ("dm", "group", "world")
TREATY_TYPES = ("non_aggression", "defensive", "trade")
TREATY_STATUSES = ("active", "broken_by_a", "broken_by_b", "withdrawn")


def enum_values(*values: str) -> sa.Enum:
    return sa.Enum(*values, native_enum=False)


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[Any] = mapped_column(uuid_type, primary_key=True)
    config: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    status: Mapped[str] = mapped_column(enum_values(*MATCH_STATUSES), nullable=False)
    current_tick: Mapped[int] = mapped_column(sa.Integer(), nullable=False, default=0)
    state: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    winner_alliance: Mapped[Any | None] = mapped_column(uuid_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[Any] = mapped_column(uuid_type, primary_key=True)
    user_id: Mapped[Any] = mapped_column(uuid_type, nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    elo_rating: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )


class Alliance(Base):
    __tablename__ = "alliances"

    id: Mapped[Any] = mapped_column(uuid_type, primary_key=True)
    match_id: Mapped[Any] = mapped_column(uuid_type, sa.ForeignKey("matches.id"), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    leader_id: Mapped[Any] = mapped_column(uuid_type, nullable=False)
    formed_tick: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    dissolved_tick: Mapped[int | None] = mapped_column(sa.Integer(), nullable=True)


class Player(Base):
    __tablename__ = "players"

    id: Mapped[Any] = mapped_column(uuid_type, primary_key=True)
    user_id: Mapped[Any] = mapped_column(uuid_type, nullable=False, index=True)
    match_id: Mapped[Any] = mapped_column(uuid_type, sa.ForeignKey("matches.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    is_agent: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, default=False)
    api_key_id: Mapped[Any | None] = mapped_column(
        uuid_type,
        sa.ForeignKey("api_keys.id"),
        nullable=True,
    )
    elo_rating: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    alliance_id: Mapped[Any | None] = mapped_column(
        uuid_type,
        sa.ForeignKey("alliances.id"),
        nullable=True,
    )
    alliance_joined_tick: Mapped[int | None] = mapped_column(sa.Integer(), nullable=True)
    eliminated_at: Mapped[int | None] = mapped_column(sa.Integer(), nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[Any] = mapped_column(uuid_type, primary_key=True)
    match_id: Mapped[Any] = mapped_column(uuid_type, sa.ForeignKey("matches.id"), nullable=False)
    sender_id: Mapped[Any] = mapped_column(uuid_type, sa.ForeignKey("players.id"), nullable=False)
    channel_type: Mapped[str] = mapped_column(enum_values(*MESSAGE_CHANNEL_TYPES), nullable=False)
    channel_id: Mapped[Any | None] = mapped_column(uuid_type, nullable=True)
    recipient_id: Mapped[Any | None] = mapped_column(uuid_type, nullable=True)
    content: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    tick: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )


class Treaty(Base):
    __tablename__ = "treaties"

    id: Mapped[Any] = mapped_column(uuid_type, primary_key=True)
    match_id: Mapped[Any] = mapped_column(uuid_type, sa.ForeignKey("matches.id"), nullable=False)
    player_a_id: Mapped[Any] = mapped_column(uuid_type, sa.ForeignKey("players.id"), nullable=False)
    player_b_id: Mapped[Any] = mapped_column(uuid_type, sa.ForeignKey("players.id"), nullable=False)
    treaty_type: Mapped[str] = mapped_column(enum_values(*TREATY_TYPES), nullable=False)
    status: Mapped[str] = mapped_column(enum_values(*TREATY_STATUSES), nullable=False)
    signed_tick: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    broken_tick: Mapped[int | None] = mapped_column(sa.Integer(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )


class TickLog(Base):
    __tablename__ = "tick_log"

    id: Mapped[int] = mapped_column(tick_log_id_type, primary_key=True, autoincrement=True)
    match_id: Mapped[Any] = mapped_column(uuid_type, sa.ForeignKey("matches.id"), nullable=False)
    tick: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    state_snapshot: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    orders: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    events: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
