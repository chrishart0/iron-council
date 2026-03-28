from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from server.models.domain import StrictModel
from server.models.orders import OrderBatch
from server.models.state import CityState, MatchState

RESOURCE_FIELDS: tuple[str, str, str] = ("food", "production", "money")
ECONOMY_TIER_MULTIPLIER_NUMERATORS: tuple[int, int, int, int] = (3, 4, 5, 6)
ECONOMY_TIER_MULTIPLIER_DENOMINATOR = 3

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
    city_ids_by_owner: dict[str, list[str]] = {player_id: [] for player_id in match_state.players}
    for city_id, city_state in match_state.cities.items():
        if city_state.owner in city_ids_by_owner:
            city_ids_by_owner[city_state.owner].append(city_id)

    army_upkeep_by_owner: dict[str, int] = {player_id: 0 for player_id in match_state.players}
    for army in match_state.armies:
        if army.owner in army_upkeep_by_owner:
            army_upkeep_by_owner[army.owner] += army.troops

    for player_id, player_state in match_state.players.items():
        updated_resources = player_state.resources.model_dump(mode="python")
        population_upkeep = 0

        for city_id in city_ids_by_owner[player_id]:
            city_state = match_state.cities[city_id]
            population_upkeep += city_state.population
            for resource_name, resource_amount in _city_resource_yield(city_state).items():
                updated_resources[resource_name] += resource_amount

        updated_resources["food"] = max(
            0,
            updated_resources["food"] - population_upkeep - army_upkeep_by_owner[player_id],
        )
        player_state.resources = player_state.resources.model_validate(updated_resources)

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


def _city_resource_yield(city_state: CityState) -> dict[str, int]:
    base_resources = city_state.resources.model_dump(mode="python")
    primary_resource = max(RESOURCE_FIELDS, key=base_resources.__getitem__)
    multiplier_numerator = ECONOMY_TIER_MULTIPLIER_NUMERATORS[city_state.upgrades.economy]

    return {
        resource_name: (
            (resource_amount * multiplier_numerator) // ECONOMY_TIER_MULTIPLIER_DENOMINATOR
            if resource_name == primary_resource
            else resource_amount
        )
        for resource_name, resource_amount in base_resources.items()
    }


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
