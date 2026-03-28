from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from typing import Literal

from server.data.maps import load_uk_1900_map
from server.models.domain import StrictModel
from server.models.orders import MovementOrder, OrderBatch, UpgradeOrder
from server.models.state import ArmyState, BuildingQueueItem, CityState, MatchState
from server.order_validation import UPGRADE_COSTS

RESOURCE_FIELDS: tuple[str, str, str] = ("food", "production", "money")
ECONOMY_TIER_MULTIPLIER_NUMERATORS: tuple[int, int, int, int] = (3, 4, 5, 6)
ECONOMY_TIER_MULTIPLIER_DENOMINATOR = 3
STARVATION_ATTRITION_LOSS = 1
COMBAT_CASUALTY_DIVISOR = 10
DEFENDER_BONUS_NUMERATOR = 12
DEFENDER_BONUS_DENOMINATOR = 10
FORTIFICATION_MULTIPLIER_NUMERATORS: tuple[int, int, int, int] = (10, 13, 17, 25)
FORTIFICATION_MULTIPLIER_DENOMINATOR = 10
UPGRADE_BUILD_DURATIONS: tuple[int, int, int, int] = (0, 1, 2, 3)

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
    _advance_build_queues(match_state)
    _start_upgrade_orders(match_state, validated_orders.upgrades)
    return _complete_phase(match_state, validated_orders, "build")


def _resolve_movement_phase(
    match_state: MatchState, validated_orders: OrderBatch
) -> TickPhaseOutcome:
    _advance_transit_armies(match_state)
    _start_movement_orders(match_state, validated_orders.movements)
    return _complete_phase(match_state, validated_orders, "movement")


def _resolve_combat_phase(
    match_state: MatchState, validated_orders: OrderBatch
) -> TickPhaseOutcome:
    _resolve_contested_city_combat(match_state)
    _transfer_uncontested_city_control(match_state)
    return _complete_phase(match_state, validated_orders, "combat")


def _resolve_siege_phase(match_state: MatchState, validated_orders: OrderBatch) -> TickPhaseOutcome:
    return _complete_phase(match_state, validated_orders, "siege")


def _resolve_attrition_phase(
    match_state: MatchState, validated_orders: OrderBatch
) -> TickPhaseOutcome:
    starving_players = {
        player_id
        for player_id, player_state in match_state.players.items()
        if player_state.resources.food == 0
    }
    surviving_armies: list[ArmyState] = []

    for army in match_state.armies:
        updated_troops = army.troops
        if army.owner in starving_players:
            updated_troops -= STARVATION_ATTRITION_LOSS

        if updated_troops > 0:
            surviving_armies.append(army.model_copy(update={"troops": updated_troops}))

    match_state.armies = surviving_armies

    owned_city_count_by_player = {player_id: 0 for player_id in match_state.players}
    for city_state in match_state.cities.values():
        if city_state.owner in owned_city_count_by_player:
            owned_city_count_by_player[city_state.owner] += 1

    surviving_army_count_by_player = {player_id: 0 for player_id in match_state.players}
    for army in match_state.armies:
        if army.owner in surviving_army_count_by_player:
            surviving_army_count_by_player[army.owner] += 1

    for player_id, player_state in match_state.players.items():
        player_state.is_eliminated = (
            owned_city_count_by_player[player_id] == 0
            and surviving_army_count_by_player[player_id] == 0
        )

    return _complete_phase(match_state, validated_orders, "attrition")


def _resolve_diplomacy_phase(
    match_state: MatchState, validated_orders: OrderBatch
) -> TickPhaseOutcome:
    return _complete_phase(match_state, validated_orders, "diplomacy")


def _resolve_victory_phase(
    match_state: MatchState, validated_orders: OrderBatch
) -> TickPhaseOutcome:
    coalition_city_counts = _coalition_city_counts(match_state)
    leading_alliance, cities_held = _leading_coalition(coalition_city_counts)
    countdown_ticks_remaining = _updated_victory_countdown(
        match_state,
        leading_alliance=leading_alliance,
        cities_held=cities_held,
    )

    match_state.victory.leading_alliance = leading_alliance
    match_state.victory.cities_held = cities_held
    match_state.victory.countdown_ticks_remaining = countdown_ticks_remaining
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

CoalitionNamespace = Literal["alliance", "solo"]
CoalitionKey = tuple[CoalitionNamespace, str]


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


def _resolve_contested_city_combat(match_state: MatchState) -> None:
    casualties_by_army_id: dict[str, int] = {}

    for city_id, city_state in match_state.cities.items():
        armies_at_city = [
            army
            for army in match_state.armies
            if army.location == city_id and army.destination is None
        ]
        owners = {army.owner for army in armies_at_city}
        if len(owners) <= 1:
            continue

        casualties_by_owner = _combat_casualties_by_owner(
            armies_at_city,
            city_owner=city_state.owner,
            fortification_tier=city_state.upgrades.fortification,
        )
        for owner, owner_armies in _armies_by_owner(armies_at_city).items():
            for army_id, losses in _allocate_proportional_casualties(
                owner_armies,
                total_casualties=casualties_by_owner.get(owner, 0),
            ).items():
                casualties_by_army_id[army_id] = casualties_by_army_id.get(army_id, 0) + losses

    surviving_armies: list[ArmyState] = []
    for army in match_state.armies:
        remaining_troops = army.troops - casualties_by_army_id.get(army.id, 0)
        if remaining_troops > 0:
            surviving_armies.append(army.model_copy(update={"troops": remaining_troops}))

    match_state.armies = surviving_armies


def _transfer_uncontested_city_control(match_state: MatchState) -> None:
    for city_id, city_state in match_state.cities.items():
        occupying_owners = {
            army.owner
            for army in match_state.armies
            if army.location == city_id and army.destination is None
        }
        if len(occupying_owners) != 1:
            continue

        occupying_owner = next(iter(occupying_owners))
        if city_state.owner == occupying_owner:
            continue
        if occupying_owner not in match_state.players:
            continue

        previous_owner = city_state.owner
        city_state.owner = occupying_owner
        _remove_city_from_player(match_state, previous_owner, city_id)
        _add_city_to_player(match_state, occupying_owner, city_id)


def _combat_casualties_by_owner(
    armies_at_city: list[ArmyState],
    *,
    city_owner: str | None,
    fortification_tier: int,
) -> dict[str, int]:
    armies_by_owner = _armies_by_owner(armies_at_city)
    troop_totals_by_owner = {
        owner: sum(army.troops for army in owner_armies)
        for owner, owner_armies in armies_by_owner.items()
    }
    effective_strength_by_owner = {
        owner: _effective_combat_strength(
            troops=troops,
            is_defender=owner == city_owner,
            fortification_tier=fortification_tier,
        )
        for owner, troops in troop_totals_by_owner.items()
    }

    casualties_by_owner: dict[str, int] = {}
    for owner, troops in troop_totals_by_owner.items():
        opposing_strength = sum(
            effective_strength
            for opposing_owner, effective_strength in effective_strength_by_owner.items()
            if opposing_owner != owner
        )
        if opposing_strength <= 0:
            continue

        casualties = opposing_strength // COMBAT_CASUALTY_DIVISOR
        casualties_by_owner[owner] = min(troops, casualties)

    return casualties_by_owner


def _armies_by_owner(armies: list[ArmyState]) -> dict[str, list[ArmyState]]:
    armies_by_owner: dict[str, list[ArmyState]] = {}
    for army in armies:
        armies_by_owner.setdefault(army.owner, []).append(army)
    return armies_by_owner


def _remove_city_from_player(match_state: MatchState, player_id: str | None, city_id: str) -> None:
    if player_id is None:
        return

    player_state = match_state.players.get(player_id)
    if player_state is None:
        return

    player_state.cities_owned = [
        owned_city_id for owned_city_id in player_state.cities_owned if owned_city_id != city_id
    ]


def _add_city_to_player(match_state: MatchState, player_id: str, city_id: str) -> None:
    player_state = match_state.players.get(player_id)
    if player_state is None:
        return
    if city_id in player_state.cities_owned:
        return

    player_state.cities_owned.append(city_id)
    player_state.cities_owned.sort()


def _allocate_proportional_casualties(
    armies: list[ArmyState],
    *,
    total_casualties: int,
) -> dict[str, int]:
    if total_casualties <= 0 or not armies:
        return {}

    total_troops = sum(army.troops for army in armies)
    if total_troops <= 0:
        return {}

    ordered_armies = sorted(armies, key=lambda army: army.id)
    casualties_by_army_id = {army.id: 0 for army in ordered_armies}
    remainders: list[tuple[int, str]] = []
    allocated_casualties = 0

    for army in ordered_armies:
        weighted_losses = total_casualties * army.troops
        losses = weighted_losses // total_troops
        casualties_by_army_id[army.id] = losses
        allocated_casualties += losses
        remainders.append((weighted_losses % total_troops, army.id))

    remaining_casualties = total_casualties - allocated_casualties
    for _, army_id in sorted(remainders, key=lambda entry: (-entry[0], entry[1])):
        if remaining_casualties <= 0:
            break
        casualties_by_army_id[army_id] += 1
        remaining_casualties -= 1

    return {army_id: losses for army_id, losses in casualties_by_army_id.items() if losses > 0}


def _effective_combat_strength(
    *,
    troops: int,
    is_defender: bool,
    fortification_tier: int,
) -> int:
    if not is_defender:
        return troops

    fortification_numerator = FORTIFICATION_MULTIPLIER_NUMERATORS[fortification_tier]
    return (
        troops
        * DEFENDER_BONUS_NUMERATOR
        * fortification_numerator
        // (DEFENDER_BONUS_DENOMINATOR * FORTIFICATION_MULTIPLIER_DENOMINATOR)
    )


def _advance_transit_armies(match_state: MatchState) -> None:
    for army in match_state.armies:
        if army.destination is None:
            continue

        army.ticks_remaining -= 1
        if army.ticks_remaining == 0:
            army.location = army.destination
            army.destination = None
            army.path = None


def _start_movement_orders(match_state: MatchState, movement_orders: list[MovementOrder]) -> None:
    if not movement_orders:
        return

    armies_by_id = {army.id: army for army in match_state.armies}
    edge_distances = _edge_distance_by_route()

    for order in movement_orders:
        army = armies_by_id.get(order.army_id)
        if army is None or army.location is None or army.destination is not None:
            continue

        route = frozenset((army.location, order.destination))
        distance = edge_distances.get(route)
        if distance is None:
            continue

        army.location = None
        army.destination = order.destination
        army.path = [order.destination]
        army.ticks_remaining = distance


def _advance_build_queues(match_state: MatchState) -> None:
    for city_state in match_state.cities.values():
        remaining_queue: list[BuildingQueueItem] = []

        for queue_item in city_state.building_queue:
            updated_ticks_remaining = queue_item.ticks_remaining - 1
            if updated_ticks_remaining == 0:
                setattr(city_state.upgrades, queue_item.type.value, int(queue_item.tier))
                continue

            remaining_queue.append(
                queue_item.model_copy(update={"ticks_remaining": updated_ticks_remaining})
            )

        city_state.building_queue = remaining_queue


def _start_upgrade_orders(match_state: MatchState, upgrade_orders: list[UpgradeOrder]) -> None:
    for order in upgrade_orders:
        city_state = match_state.cities.get(order.city)
        if city_state is None or city_state.owner is None:
            continue

        if any(queue_item.type == order.track for queue_item in city_state.building_queue):
            continue

        player_state = match_state.players.get(city_state.owner)
        if player_state is None:
            continue

        player_state.resources.production -= UPGRADE_COSTS[order.track][
            int(order.target_tier)
        ].production
        city_state.building_queue.append(
            BuildingQueueItem(
                type=order.track,
                tier=order.target_tier,
                ticks_remaining=UPGRADE_BUILD_DURATIONS[int(order.target_tier)],
            )
        )


@lru_cache(maxsize=1)
def _edge_distance_by_route() -> dict[frozenset[str], int]:
    return {
        frozenset((edge.city_a, edge.city_b)): edge.distance_ticks
        for edge in load_uk_1900_map().edges
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


def _coalition_city_counts(match_state: MatchState) -> dict[CoalitionKey, int]:
    coalition_city_counts: dict[CoalitionKey, int] = {}

    for city_state in match_state.cities.values():
        if city_state.owner is None:
            continue

        player_state = match_state.players.get(city_state.owner)
        if player_state is None:
            continue

        coalition_id = _coalition_key(
            player_id=city_state.owner,
            alliance_id=player_state.alliance_id,
        )
        coalition_city_counts[coalition_id] = coalition_city_counts.get(coalition_id, 0) + 1

    return coalition_city_counts


def _coalition_key(*, player_id: str, alliance_id: str | None) -> CoalitionKey:
    if alliance_id is not None:
        return ("alliance", alliance_id)
    return ("solo", player_id)


def _public_coalition_id(coalition_key: CoalitionKey) -> str:
    return coalition_key[1]


def _leading_coalition(
    coalition_city_counts: dict[CoalitionKey, int],
) -> tuple[str | None, int]:
    if not coalition_city_counts:
        return None, 0

    cities_held = max(coalition_city_counts.values())
    leaders = [
        coalition_id
        for coalition_id, city_count in coalition_city_counts.items()
        if city_count == cities_held
    ]
    leading_alliance = _public_coalition_id(leaders[0]) if len(leaders) == 1 else None

    return leading_alliance, cities_held


def _updated_victory_countdown(
    match_state: MatchState,
    *,
    leading_alliance: str | None,
    cities_held: int,
) -> int | None:
    victory_state = match_state.victory

    if leading_alliance is None or cities_held < victory_state.threshold:
        return None
    if victory_state.leading_alliance is None:
        return victory_state.threshold
    if victory_state.leading_alliance != leading_alliance:
        return None
    if victory_state.countdown_ticks_remaining is None:
        return victory_state.threshold
    return max(0, victory_state.countdown_ticks_remaining - 1)
