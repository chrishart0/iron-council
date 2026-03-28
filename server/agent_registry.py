from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from server.models.domain import MatchStatus
from server.models.orders import OrderEnvelope
from server.models.state import MatchState


@dataclass(slots=True)
class MatchRecord:
    match_id: str
    status: MatchStatus
    tick_interval_seconds: int
    state: MatchState
    order_submissions: list[OrderEnvelope] = field(default_factory=list)


class InMemoryMatchRegistry:
    def __init__(self) -> None:
        self._matches: dict[str, MatchRecord] = {}

    def seed_match(self, record: MatchRecord) -> None:
        self._matches[record.match_id] = MatchRecord(
            match_id=record.match_id,
            status=record.status,
            tick_interval_seconds=record.tick_interval_seconds,
            state=record.state.model_copy(deep=True),
            order_submissions=[
                submission.model_copy(deep=True) for submission in record.order_submissions
            ],
        )

    def reset(self) -> None:
        self._matches.clear()

    def list_matches(self) -> list[MatchRecord]:
        return [self._matches[match_id] for match_id in sorted(self._matches)]

    def get_match(self, match_id: str) -> MatchRecord | None:
        return self._matches.get(match_id)

    def record_submission(self, *, match_id: str, envelope: OrderEnvelope) -> int:
        record = self._matches[match_id]
        record.order_submissions.append(envelope.model_copy(deep=True))
        return len(record.order_submissions) - 1

    def list_order_submissions(self, match_id: str) -> list[dict[str, Any]]:
        record = self._matches.get(match_id)
        if record is None:
            return []
        return [submission.model_dump(mode="json") for submission in record.order_submissions]
