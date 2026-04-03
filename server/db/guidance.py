from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.db.models import OwnedAgentGuidance


@dataclass(frozen=True)
class OwnedAgentGuidanceEntry:
    id: str
    match_id: str
    owner_user_id: str
    agent_player_id: str
    content: str
    tick: int
    created_at: datetime


def append_owned_agent_guidance(
    *,
    database_url: str,
    match_id: str,
    owner_user_id: str,
    agent_player_id: str,
    content: str,
    tick: int,
    created_at: datetime | None = None,
) -> OwnedAgentGuidanceEntry:
    engine = create_engine(database_url)
    with Session(engine) as session:
        row = OwnedAgentGuidance(
            id=str(uuid4()),
            match_id=match_id,
            owner_user_id=owner_user_id,
            agent_player_id=agent_player_id,
            content=content,
            tick=tick,
            created_at=created_at or datetime.now(tz=UTC),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _build_entry(row)


def list_owned_agent_guidance(
    *,
    database_url: str,
    match_id: str,
    owner_user_id: str,
    agent_player_id: str,
) -> list[OwnedAgentGuidanceEntry]:
    engine = create_engine(database_url)
    with Session(engine) as session:
        rows = session.scalars(
            select(OwnedAgentGuidance)
            .where(
                OwnedAgentGuidance.match_id == match_id,
                OwnedAgentGuidance.owner_user_id == owner_user_id,
                OwnedAgentGuidance.agent_player_id == agent_player_id,
            )
            .order_by(
                OwnedAgentGuidance.tick.asc(),
                OwnedAgentGuidance.created_at.asc(),
                OwnedAgentGuidance.id.asc(),
            )
        ).all()
        return [_build_entry(row) for row in rows]


def _build_entry(row: OwnedAgentGuidance) -> OwnedAgentGuidanceEntry:
    return OwnedAgentGuidanceEntry(
        id=str(row.id),
        match_id=str(row.match_id),
        owner_user_id=str(row.owner_user_id),
        agent_player_id=str(row.agent_player_id),
        content=row.content,
        tick=int(row.tick),
        created_at=row.created_at,
    )
