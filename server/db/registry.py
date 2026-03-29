from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.agent_registry import InMemoryMatchRegistry, MatchRecord
from server.db.models import Match
from server.models.domain import MatchStatus
from server.models.state import MatchState


def load_match_registry_from_database(database_url: str) -> InMemoryMatchRegistry:
    registry = InMemoryMatchRegistry()
    engine = create_engine(database_url)
    with Session(engine) as session:
        matches = session.scalars(select(Match).order_by(Match.id)).all()

    for match in matches:
        registry.seed_match(
            MatchRecord(
                match_id=str(match.id),
                status=MatchStatus(match.status),
                tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
                state=MatchState.model_validate(match.state),
            )
        )
    return registry
