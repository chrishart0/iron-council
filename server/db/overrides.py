from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.db.models import OwnedAgentOverride
from server.models.orders import OrderBatch


@dataclass(frozen=True)
class OwnedAgentOverrideEntry:
    id: str
    match_id: str
    owner_user_id: str
    agent_player_id: str
    tick: int
    superseded_submission_count: int
    orders: OrderBatch
    created_at: datetime


def append_owned_agent_override(
    *,
    database_url: str,
    match_id: str,
    owner_user_id: str,
    agent_player_id: str,
    tick: int,
    superseded_submission_count: int,
    orders: OrderBatch,
    created_at: datetime | None = None,
) -> OwnedAgentOverrideEntry:
    engine = create_engine(database_url)
    with Session(engine) as session:
        row = OwnedAgentOverride(
            id=str(uuid4()),
            match_id=match_id,
            owner_user_id=owner_user_id,
            agent_player_id=agent_player_id,
            tick=tick,
            superseded_submission_count=superseded_submission_count,
            orders=orders.model_dump(mode="json"),
            created_at=created_at or datetime.now(tz=UTC),
        )
        session.add(row)
        entry = _build_entry(row)
        session.commit()
        return entry


def list_owned_agent_overrides(
    *,
    database_url: str,
    match_id: str,
    owner_user_id: str,
    agent_player_id: str,
) -> list[OwnedAgentOverrideEntry]:
    engine = create_engine(database_url)
    with Session(engine) as session:
        rows = session.scalars(
            select(OwnedAgentOverride)
            .where(
                OwnedAgentOverride.match_id == match_id,
                OwnedAgentOverride.owner_user_id == owner_user_id,
                OwnedAgentOverride.agent_player_id == agent_player_id,
            )
            .order_by(
                OwnedAgentOverride.tick.asc(),
                OwnedAgentOverride.created_at.asc(),
                OwnedAgentOverride.id.asc(),
            )
        ).all()
        return [_build_entry(row) for row in rows]


def _build_entry(row: OwnedAgentOverride) -> OwnedAgentOverrideEntry:
    return OwnedAgentOverrideEntry(
        id=str(row.id),
        match_id=str(row.match_id),
        owner_user_id=str(row.owner_user_id),
        agent_player_id=str(row.agent_player_id),
        tick=int(row.tick),
        superseded_submission_count=int(row.superseded_submission_count),
        orders=OrderBatch.model_validate(row.orders),
        created_at=row.created_at,
    )
