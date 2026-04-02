from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from server.agent_registry import AdvancedMatchTick
from server.db.models import Match, TickLog


def persist_advanced_match_tick(*, database_url: str, advanced_tick: AdvancedMatchTick) -> None:
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        match = session.get(Match, advanced_tick.match_id)
        if match is None:
            raise KeyError(f"Match '{advanced_tick.match_id}' was not found.")

        match.current_tick = advanced_tick.resolved_tick
        match.state = advanced_tick.next_state.model_dump(mode="json")
        session.add(
            TickLog(
                match_id=advanced_tick.match_id,
                tick=advanced_tick.resolved_tick,
                state_snapshot=advanced_tick.next_state.model_dump(mode="json"),
                orders=advanced_tick.accepted_orders.model_dump(mode="json"),
                events=[event.model_dump(mode="json") for event in advanced_tick.events],
            )
        )
