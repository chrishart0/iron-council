from __future__ import annotations

from collections import deque
from enum import StrEnum
from typing import Literal, cast

from pydantic import Field

from server.data.maps import MapDefinition
from server.models.domain import ResourceType, StrictModel, UpgradeTrack
from server.models.orders import (
    MovementOrder,
    OrderBatch,
    OrderEnvelope,
    RecruitmentOrder,
    TransferOrder,
    UpgradeOrder,
)
from server.models.state import ArmyState, MatchState, PlayerState, ResourceState


class ResourceCost(StrictModel):
    food: int = 0
    production: int = 0
    money: int = 0


RECRUITMENT_COST_PER_TROOP = ResourceCost(food=1, production=5, money=0)
UPGRADE_COSTS: dict[UpgradeTrack, dict[int, ResourceCost]] = {
    UpgradeTrack.ECONOMY: {
        1: ResourceCost(production=7),
        2: ResourceCost(production=11),
        3: ResourceCost(production=15),
    },
    UpgradeTrack.MILITARY: {
        1: ResourceCost(production=8),
        2: ResourceCost(production=12),
        3: ResourceCost(production=16),
    },
    UpgradeTrack.FORTIFICATION: {
        1: ResourceCost(production=6),
        2: ResourceCost(production=10),
        3: ResourceCost(production=14),
    },
}


class ValidationReasonCode(StrEnum):
    LATE_ORDER = "late_order"
    UNKNOWN_PLAYER = "unknown_player"
    UNKNOWN_CITY = "unknown_city"
    UNKNOWN_ARMY = "unknown_army"
    CONFLICTING_DUPLICATE_ORDER = "conflicting_duplicate_order"
    INVALID_OWNERSHIP = "invalid_ownership"
    INVALID_RECIPIENT_RELATION = "invalid_recipient_relation"
    INVALID_ADJACENCY = "invalid_adjacency"
    ARMY_IN_TRANSIT = "army_in_transit"
    INSUFFICIENT_RESOURCES = "insufficient_resources"
    INVALID_TIER_PROGRESSION = "invalid_tier_progression"
    DISCONNECTED_ROUTE = "disconnected_route"


class RejectedOrder(StrictModel):
    order_type: Literal["movement", "recruitment", "upgrade", "transfer"]
    order_index: int
    reason_code: ValidationReasonCode
    message: str


class OrderValidationResult(StrictModel):
    accepted: OrderBatch = Field(default_factory=OrderBatch)
    rejected: list[RejectedOrder] = Field(default_factory=list)


def validate_order_envelope(
    envelope: OrderEnvelope,
    match_state: MatchState,
    map_definition: MapDefinition,
) -> OrderValidationResult:
    result = OrderValidationResult()

    if envelope.tick != match_state.tick:
        for rejection in _reject_all_orders_for_tick_mismatch(envelope, match_state.tick):
            result.rejected.append(rejection)
        return result

    player_state = match_state.players.get(envelope.player_id)
    if player_state is None:
        for rejection in _reject_all_orders_for_unknown_player(envelope):
            result.rejected.append(rejection)
        return result

    direct_adjacency = _build_adjacency_index(map_definition)
    land_adjacency = _build_adjacency_index(map_definition, traversal_mode="land")
    armies_by_id = {army.id: army for army in match_state.armies}
    budget = player_state.resources.model_copy(deep=True)
    seen_movement_armies: set[str] = set()
    seen_upgrade_targets: set[tuple[str, UpgradeTrack]] = set()

    for index, movement_order in enumerate(envelope.orders.movements):
        if movement_order.army_id in seen_movement_armies:
            result.rejected.append(
                _reject_conflicting_duplicate_movement_order(
                    order=movement_order,
                    order_index=index,
                )
            )
            continue

        movement_rejection: RejectedOrder | None = _validate_movement_order(
            order=movement_order,
            order_index=index,
            player_id=envelope.player_id,
            armies_by_id=armies_by_id,
            city_ids=set(match_state.cities),
            direct_adjacency=direct_adjacency,
        )
        if movement_rejection is None:
            seen_movement_armies.add(movement_order.army_id)
            result.accepted.movements.append(movement_order)
        else:
            result.rejected.append(movement_rejection)

    for index, recruitment_order in enumerate(envelope.orders.recruitment):
        recruitment_rejection: RejectedOrder | None = _validate_recruitment_order(
            order=recruitment_order,
            order_index=index,
            player_id=envelope.player_id,
            match_state=match_state,
            budget=budget,
        )
        if recruitment_rejection is None:
            result.accepted.recruitment.append(recruitment_order)
        else:
            result.rejected.append(recruitment_rejection)

    for index, upgrade_order in enumerate(envelope.orders.upgrades):
        upgrade_target = (upgrade_order.city, upgrade_order.track)
        if upgrade_target in seen_upgrade_targets:
            result.rejected.append(
                _reject_conflicting_duplicate_upgrade_order(
                    order=upgrade_order,
                    order_index=index,
                )
            )
            continue

        upgrade_rejection: RejectedOrder | None = _validate_upgrade_order(
            order=upgrade_order,
            order_index=index,
            player_id=envelope.player_id,
            match_state=match_state,
            budget=budget,
        )
        if upgrade_rejection is None:
            seen_upgrade_targets.add(upgrade_target)
            result.accepted.upgrades.append(upgrade_order)
        else:
            result.rejected.append(upgrade_rejection)

    for index, transfer_order in enumerate(envelope.orders.transfers):
        transfer_rejection: RejectedOrder | None = _validate_transfer_order(
            order=transfer_order,
            order_index=index,
            player_id=envelope.player_id,
            match_state=match_state,
            budget=budget,
            land_adjacency=land_adjacency,
        )
        if transfer_rejection is None:
            result.accepted.transfers.append(
                transfer_order.model_copy(update={"sender": envelope.player_id})
            )
        else:
            result.rejected.append(transfer_rejection)

    return result


def _reject_conflicting_duplicate_movement_order(
    *,
    order: MovementOrder,
    order_index: int,
) -> RejectedOrder:
    return RejectedOrder(
        order_type="movement",
        order_index=order_index,
        reason_code=ValidationReasonCode.CONFLICTING_DUPLICATE_ORDER,
        message=(
            f"movement order {order_index} conflicts with an earlier movement order for "
            f"army '{order.army_id}' in the same envelope"
        ),
    )


def _reject_conflicting_duplicate_upgrade_order(
    *,
    order: UpgradeOrder,
    order_index: int,
) -> RejectedOrder:
    return RejectedOrder(
        order_type="upgrade",
        order_index=order_index,
        reason_code=ValidationReasonCode.CONFLICTING_DUPLICATE_ORDER,
        message=(
            f"upgrade order {order_index} conflicts with an earlier upgrade order for "
            f"city '{order.city}' track '{order.track.value}' in the same envelope"
        ),
    )


def _reject_all_orders_for_tick_mismatch(
    envelope: OrderEnvelope,
    current_tick: int,
) -> list[RejectedOrder]:
    message = (
        f"order envelope tick {envelope.tick} does not match current match tick {current_tick}"
    )
    return _reject_all_orders(envelope, ValidationReasonCode.LATE_ORDER, message)


def _reject_all_orders_for_unknown_player(envelope: OrderEnvelope) -> list[RejectedOrder]:
    message = f"player '{envelope.player_id}' does not exist in match state"
    return _reject_all_orders(envelope, ValidationReasonCode.UNKNOWN_PLAYER, message)


def _reject_all_orders(
    envelope: OrderEnvelope,
    reason_code: ValidationReasonCode,
    message: str,
) -> list[RejectedOrder]:
    rejected: list[RejectedOrder] = []

    for index, _ in enumerate(envelope.orders.movements):
        rejected.append(
            RejectedOrder(
                order_type="movement",
                order_index=index,
                reason_code=reason_code,
                message=message,
            )
        )
    for index, _ in enumerate(envelope.orders.recruitment):
        rejected.append(
            RejectedOrder(
                order_type="recruitment",
                order_index=index,
                reason_code=reason_code,
                message=message,
            )
        )
    for index, _ in enumerate(envelope.orders.upgrades):
        rejected.append(
            RejectedOrder(
                order_type="upgrade",
                order_index=index,
                reason_code=reason_code,
                message=message,
            )
        )
    for index, _ in enumerate(envelope.orders.transfers):
        rejected.append(
            RejectedOrder(
                order_type="transfer",
                order_index=index,
                reason_code=reason_code,
                message=message,
            )
        )

    return rejected


def _validate_movement_order(
    *,
    order: MovementOrder,
    order_index: int,
    player_id: str,
    armies_by_id: dict[str, ArmyState],
    city_ids: set[str],
    direct_adjacency: dict[str, set[str]],
) -> RejectedOrder | None:
    army = armies_by_id.get(order.army_id)
    if army is None:
        return RejectedOrder(
            order_type="movement",
            order_index=order_index,
            reason_code=ValidationReasonCode.UNKNOWN_ARMY,
            message=f"movement order {order_index} references unknown army '{order.army_id}'",
        )

    if order.destination not in city_ids:
        return RejectedOrder(
            order_type="movement",
            order_index=order_index,
            reason_code=ValidationReasonCode.UNKNOWN_CITY,
            message=(
                f"movement order {order_index} references unknown destination '{order.destination}'"
            ),
        )

    if army.owner != player_id:
        return RejectedOrder(
            order_type="movement",
            order_index=order_index,
            reason_code=ValidationReasonCode.INVALID_OWNERSHIP,
            message=(
                f"movement order {order_index} targets army '{order.army_id}' "
                f"not owned by '{player_id}'"
            ),
        )

    if army.destination is not None or army.location is None:
        return RejectedOrder(
            order_type="movement",
            order_index=order_index,
            reason_code=ValidationReasonCode.ARMY_IN_TRANSIT,
            message=(
                f"movement order {order_index} cannot move army '{order.army_id}' "
                f"because it is already in transit to '{army.destination}'"
            ),
        )

    if order.destination not in direct_adjacency.get(army.location, set()):
        return RejectedOrder(
            order_type="movement",
            order_index=order_index,
            reason_code=ValidationReasonCode.INVALID_ADJACENCY,
            message=(
                f"movement order {order_index} destination '{order.destination}' "
                f"is not directly connected to army '{order.army_id}' at '{army.location}'"
            ),
        )

    return None


def _validate_recruitment_order(
    *,
    order: RecruitmentOrder,
    order_index: int,
    player_id: str,
    match_state: MatchState,
    budget: ResourceState,
) -> RejectedOrder | None:
    city_state = match_state.cities.get(order.city)
    if city_state is None:
        return RejectedOrder(
            order_type="recruitment",
            order_index=order_index,
            reason_code=ValidationReasonCode.UNKNOWN_CITY,
            message=f"recruitment order {order_index} references unknown city '{order.city}'",
        )

    if city_state.owner != player_id:
        return RejectedOrder(
            order_type="recruitment",
            order_index=order_index,
            reason_code=ValidationReasonCode.INVALID_OWNERSHIP,
            message=(
                f"recruitment order {order_index} targets city '{order.city}' "
                f"not owned by '{player_id}'"
            ),
        )

    total_cost = ResourceCost(
        food=order.troops * RECRUITMENT_COST_PER_TROOP.food,
        production=order.troops * RECRUITMENT_COST_PER_TROOP.production,
        money=0,
    )
    if not _can_afford(budget, total_cost):
        return RejectedOrder(
            order_type="recruitment",
            order_index=order_index,
            reason_code=ValidationReasonCode.INSUFFICIENT_RESOURCES,
            message=(
                f"recruitment order {order_index} requires {total_cost.food} food and "
                f"{total_cost.production} production, but only {budget.food} food and "
                f"{budget.production} production remain in the validation budget"
            ),
        )

    _spend_budget(budget, total_cost)
    return None


def _validate_upgrade_order(
    *,
    order: UpgradeOrder,
    order_index: int,
    player_id: str,
    match_state: MatchState,
    budget: ResourceState,
) -> RejectedOrder | None:
    city_state = match_state.cities.get(order.city)
    if city_state is None:
        return RejectedOrder(
            order_type="upgrade",
            order_index=order_index,
            reason_code=ValidationReasonCode.UNKNOWN_CITY,
            message=f"upgrade order {order_index} references unknown city '{order.city}'",
        )

    if city_state.owner != player_id:
        return RejectedOrder(
            order_type="upgrade",
            order_index=order_index,
            reason_code=ValidationReasonCode.INVALID_OWNERSHIP,
            message=(
                f"upgrade order {order_index} targets city '{order.city}' "
                f"not owned by '{player_id}'"
            ),
        )

    current_tier = cast(int, getattr(city_state.upgrades, order.track.value))
    if order.target_tier != current_tier + 1:
        return RejectedOrder(
            order_type="upgrade",
            order_index=order_index,
            reason_code=ValidationReasonCode.INVALID_TIER_PROGRESSION,
            message=(
                f"upgrade order {order_index} must advance '{order.track.value}' on "
                f"'{order.city}' from tier {current_tier} to tier {current_tier + 1}, "
                f"not tier {order.target_tier}"
            ),
        )

    total_cost = UPGRADE_COSTS[order.track][int(order.target_tier)]
    if not _can_afford(budget, total_cost):
        return RejectedOrder(
            order_type="upgrade",
            order_index=order_index,
            reason_code=ValidationReasonCode.INSUFFICIENT_RESOURCES,
            message=(
                f"upgrade order {order_index} requires {total_cost.production} production, "
                f"but only {budget.production} production remain in the validation budget"
            ),
        )

    _spend_budget(budget, total_cost)
    return None


def _validate_transfer_order(
    *,
    order: TransferOrder,
    order_index: int,
    player_id: str,
    match_state: MatchState,
    budget: ResourceState,
    land_adjacency: dict[str, set[str]],
) -> RejectedOrder | None:
    recipient_state = match_state.players.get(order.to)
    if recipient_state is None:
        return RejectedOrder(
            order_type="transfer",
            order_index=order_index,
            reason_code=ValidationReasonCode.UNKNOWN_PLAYER,
            message=f"transfer order {order_index} references unknown player '{order.to}'",
        )

    recipient_relation = _classify_transfer_recipient_relation(
        sender_state=match_state.players[player_id],
        recipient_state=recipient_state,
    )
    if recipient_relation == "enemy":
        return RejectedOrder(
            order_type="transfer",
            order_index=order_index,
            reason_code=ValidationReasonCode.INVALID_RECIPIENT_RELATION,
            message=(
                f"transfer order {order_index} cannot target enemy player '{order.to}'; "
                "transfers are limited to allied or neutral players"
            ),
        )

    if order.resource in {
        ResourceType.FOOD,
        ResourceType.PRODUCTION,
    } and not _has_connected_land_route(
        sender_id=player_id,
        recipient_id=order.to,
        match_state=match_state,
        land_adjacency=land_adjacency,
    ):
        return RejectedOrder(
            order_type="transfer",
            order_index=order_index,
            reason_code=ValidationReasonCode.DISCONNECTED_ROUTE,
            message=(
                f"transfer order {order_index} cannot send {order.resource.value} to "
                f"'{order.to}' without a connected land route"
            ),
        )

    total_cost = ResourceCost(**{order.resource.value: order.amount})
    if not _can_afford(budget, total_cost):
        available_amount = getattr(budget, order.resource.value)
        return RejectedOrder(
            order_type="transfer",
            order_index=order_index,
            reason_code=ValidationReasonCode.INSUFFICIENT_RESOURCES,
            message=(
                f"transfer order {order_index} requires {order.amount} {order.resource.value}, "
                f"but only {available_amount} {order.resource.value} remain in the "
                "validation budget"
            ),
        )

    _spend_budget(budget, total_cost)
    return None


def _build_adjacency_index(
    map_definition: MapDefinition,
    *,
    traversal_mode: Literal["land", "sea"] | None = None,
) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {city_id: set() for city_id in map_definition.cities}

    for edge in map_definition.edges:
        if traversal_mode is not None and edge.traversal_mode != traversal_mode:
            continue
        adjacency[edge.city_a].add(edge.city_b)
        adjacency[edge.city_b].add(edge.city_a)

    return adjacency


def _has_connected_land_route(
    *,
    sender_id: str,
    recipient_id: str,
    match_state: MatchState,
    land_adjacency: dict[str, set[str]],
) -> bool:
    sender_state = match_state.players[sender_id]
    recipient_state = match_state.players[recipient_id]
    sender_cities = {
        city_id
        for city_id, city_state in match_state.cities.items()
        if city_state.owner == sender_id
    }
    recipient_cities = {
        city_id
        for city_id, city_state in match_state.cities.items()
        if city_state.owner == recipient_id
    }

    if not sender_cities or not recipient_cities:
        return False

    traversable_owners = _connected_route_owner_ids(
        sender_id=sender_id,
        sender_state=sender_state,
        recipient_id=recipient_id,
        recipient_state=recipient_state,
        match_state=match_state,
    )
    traversable_cities = {
        city_id
        for city_id, city_state in match_state.cities.items()
        if city_state.owner in traversable_owners
    }

    queue = deque(sorted(sender_cities & traversable_cities))
    visited = set(queue)
    goal_cities = recipient_cities & traversable_cities

    while queue:
        city_id = queue.popleft()
        if city_id in goal_cities:
            return True
        for adjacent_city_id in sorted(land_adjacency.get(city_id, set())):
            if adjacent_city_id in visited or adjacent_city_id not in traversable_cities:
                continue
            visited.add(adjacent_city_id)
            queue.append(adjacent_city_id)

    return False


def _classify_transfer_recipient_relation(
    *,
    sender_state: PlayerState,
    recipient_state: PlayerState,
) -> Literal["allied", "enemy", "neutral"]:
    if (
        sender_state.alliance_id is not None
        and sender_state.alliance_id == recipient_state.alliance_id
    ):
        return "allied"
    if (
        sender_state.alliance_id is not None
        and recipient_state.alliance_id is not None
        and sender_state.alliance_id != recipient_state.alliance_id
    ):
        return "enemy"
    return "neutral"


def _connected_route_owner_ids(
    *,
    sender_id: str,
    sender_state: PlayerState,
    recipient_id: str,
    recipient_state: PlayerState,
    match_state: MatchState,
) -> set[str]:
    owner_ids = {sender_id, recipient_id}

    if (
        sender_state.alliance_id is not None
        and sender_state.alliance_id == recipient_state.alliance_id
    ):
        for player_id, player_state in match_state.players.items():
            if player_state.alliance_id == sender_state.alliance_id:
                owner_ids.add(player_id)

    return owner_ids


def _can_afford(budget: ResourceState, cost: ResourceCost) -> bool:
    return (
        budget.food >= cost.food
        and budget.production >= cost.production
        and budget.money >= cost.money
    )


def _spend_budget(budget: ResourceState, cost: ResourceCost) -> None:
    budget.food -= cost.food
    budget.production -= cost.production
    budget.money -= cost.money
