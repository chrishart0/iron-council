from __future__ import annotations

from collections.abc import Callable
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


class TickPhaseEvent(StrictModel):
    phase: TickPhaseName
    event: str


class TickPhaseOutcome(StrictModel):
    metadata: TickPhaseMetadata
    event: TickPhaseEvent


class TickResolutionResult(StrictModel):
    next_state: MatchState
    phases: list[TickPhaseMetadata]
    events: list[TickPhaseEvent]


PhaseHandler = Callable[[MatchState, OrderBatch], TickPhaseOutcome]


def resolve_tick(match_state: MatchState, validated_orders: OrderBatch) -> TickResolutionResult:
    next_state = match_state.model_copy(deep=True)
    phase_outcomes = [handler(next_state, validated_orders) for handler in PHASE_HANDLERS]

    return TickResolutionResult(
        next_state=next_state,
        phases=[outcome.metadata for outcome in phase_outcomes],
        events=[outcome.event for outcome in phase_outcomes],
    )


def _resolve_resource_phase(
    match_state: MatchState, validated_orders: OrderBatch
) -> TickPhaseOutcome:
    return _complete_phase(match_state, validated_orders, "resource")


def _resolve_build_phase(match_state: MatchState, validated_orders: OrderBatch) -> TickPhaseOutcome:
    return _complete_phase(match_state, validated_orders, "build")


def _resolve_movement_phase(
    match_state: MatchState, validated_orders: OrderBatch
) -> TickPhaseOutcome:
    return _complete_phase(match_state, validated_orders, "movement")


def _resolve_combat_phase(
    match_state: MatchState, validated_orders: OrderBatch
) -> TickPhaseOutcome:
    return _complete_phase(match_state, validated_orders, "combat")


def _resolve_siege_phase(match_state: MatchState, validated_orders: OrderBatch) -> TickPhaseOutcome:
    return _complete_phase(match_state, validated_orders, "siege")


def _resolve_attrition_phase(
    match_state: MatchState, validated_orders: OrderBatch
) -> TickPhaseOutcome:
    return _complete_phase(match_state, validated_orders, "attrition")


def _resolve_diplomacy_phase(
    match_state: MatchState, validated_orders: OrderBatch
) -> TickPhaseOutcome:
    return _complete_phase(match_state, validated_orders, "diplomacy")


def _resolve_victory_phase(
    match_state: MatchState, validated_orders: OrderBatch
) -> TickPhaseOutcome:
    return _complete_phase(match_state, validated_orders, "victory")


PHASE_HANDLERS: tuple[PhaseHandler, ...] = (
    _resolve_resource_phase,
    _resolve_build_phase,
    _resolve_movement_phase,
    _resolve_combat_phase,
    _resolve_siege_phase,
    _resolve_attrition_phase,
    _resolve_diplomacy_phase,
    _resolve_victory_phase,
)


def _phase_event_name(phase: TickPhaseName) -> str:
    return f"phase.{phase}.completed"


def _complete_phase(
    match_state: MatchState,
    validated_orders: OrderBatch,
    phase: TickPhaseName,
) -> TickPhaseOutcome:
    del match_state
    del validated_orders

    event_name = _phase_event_name(phase)
    return TickPhaseOutcome(
        metadata=TickPhaseMetadata(phase=phase, event=event_name),
        event=TickPhaseEvent(phase=phase, event=event_name),
    )
