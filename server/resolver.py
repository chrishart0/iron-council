from __future__ import annotations

from typing import Literal

from server.models.domain import StrictModel
from server.models.orders import OrderBatch
from server.models.state import MatchState

TickPhaseName = Literal[
    "resource",
    "build",
    "movement",
    "combat",
    "siege",
    "attrition",
    "diplomacy",
    "victory",
]

PHASE_ORDER: tuple[TickPhaseName, ...] = (
    "resource",
    "build",
    "movement",
    "combat",
    "siege",
    "attrition",
    "diplomacy",
    "victory",
)


class TickPhaseMetadata(StrictModel):
    phase: TickPhaseName
    event: str


class TickResolutionResult(StrictModel):
    next_state: MatchState
    phases: list[TickPhaseMetadata]
    events: list[dict[str, str]]


def resolve_tick(match_state: MatchState, validated_orders: OrderBatch) -> TickResolutionResult:
    del validated_orders

    next_state = match_state.model_copy(deep=True)
    phases = [
        TickPhaseMetadata(phase=phase, event=_phase_event_name(phase)) for phase in PHASE_ORDER
    ]

    return TickResolutionResult(
        next_state=next_state,
        phases=phases,
        events=[{"phase": phase.phase, "event": phase.event} for phase in phases],
    )


def _phase_event_name(phase: TickPhaseName) -> str:
    return f"phase.{phase}.completed"
