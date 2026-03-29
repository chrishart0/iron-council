from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field

from server.data.maps import CityCoordinates, CityDefinition, MapDefinition, MapEdge
from server.models.domain import FortificationTier, ResourceType, StrictModel, UpgradeTrack
from server.models.orders import MovementOrder, OrderBatch, OrderEnvelope, UpgradeOrder
from server.models.state import (
    ArmyState,
    CityState,
    CityUpgradeState,
    MatchState,
    PlayerState,
    ResourceState,
    VictoryState,
)
from server.order_validation import RejectedOrder, validate_order_envelope
from server.simulation import simulate_ticks


@dataclass(frozen=True)
class RegressionScenario:
    scenario_id: str
    map_definition: MapDefinition
    initial_state: MatchState
    ticks: int
    orders_by_tick: dict[int, list[OrderEnvelope]] = field(default_factory=dict)


class RegressionFailure(StrictModel):
    scenario_id: str
    tick: int
    invariant: str
    detail: str


class RegressionScenarioResult(StrictModel):
    scenario_id: str
    ticks: int
    outcome_digest: str


class RegressionBatchResult(StrictModel):
    total_runs: int
    scenario_results: list[RegressionScenarioResult]
    failures: list[RegressionFailure]


ScenarioSpec = tuple[str, int, dict[int, list[OrderEnvelope]]]


def format_regression_failures(failures: Iterable[RegressionFailure]) -> str:
    return "\n".join(
        (
            f"scenario_id={failure.scenario_id} "
            f"tick={failure.tick} "
            f"invariant={failure.invariant} "
            f"detail={failure.detail}"
        )
        for failure in failures
    )


def run_simulation_regression_batch(
    scenarios: Iterable[RegressionScenario],
) -> RegressionBatchResult:
    scenario_results: list[RegressionScenarioResult] = []
    failures: list[RegressionFailure] = []
    total_runs = 0

    for scenario in scenarios:
        total_runs += 1
        scenario_map = scenario.map_definition
        scenario_orders_by_tick = scenario.orders_by_tick
        scenario_failures = _check_state_invariants(
            scenario.initial_state,
            scenario=scenario,
            tick=scenario.initial_state.tick,
            check_victory=False,
        )
        if scenario_failures:
            failures.extend(scenario_failures)
            continue

        rejected_orders_by_tick: dict[int, list[RejectedOrder]] = {}

        def order_provider(
            *,
            tick: int,
            state: MatchState,
            scenario_orders_by_tick: dict[int, list[OrderEnvelope]] = scenario_orders_by_tick,
            scenario_map: MapDefinition = scenario_map,
            rejected_orders_by_tick: dict[int, list[RejectedOrder]] = rejected_orders_by_tick,
        ) -> OrderBatch:
            accepted = OrderBatch()
            rejections: list[RejectedOrder] = []
            for envelope in scenario_orders_by_tick.get(tick, []):
                validation = validate_order_envelope(
                    envelope,
                    state,
                    scenario_map,
                )
                accepted.movements.extend(validation.accepted.movements)
                accepted.recruitment.extend(validation.accepted.recruitment)
                accepted.upgrades.extend(validation.accepted.upgrades)
                accepted.transfers.extend(validation.accepted.transfers)
                rejections.extend(validation.rejected)
            if rejections:
                rejected_orders_by_tick[tick] = rejections
            return accepted

        try:
            simulation = simulate_ticks(
                scenario.initial_state,
                ticks=scenario.ticks,
                order_provider=order_provider,
                map_definition=scenario.map_definition,
            )
        except Exception as exc:  # pragma: no cover - exercised by future regressions
            failures.append(
                RegressionFailure(
                    scenario_id=scenario.scenario_id,
                    tick=scenario.initial_state.tick,
                    invariant="simulation-executes",
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )
            continue

        for simulated_tick in simulation.ticks:
            failures.extend(
                _check_state_invariants(
                    simulated_tick.snapshot,
                    scenario=scenario,
                    tick=simulated_tick.tick,
                )
            )

        scenario_results.append(
            RegressionScenarioResult(
                scenario_id=scenario.scenario_id,
                ticks=scenario.ticks,
                outcome_digest=_outcome_digest(
                    simulation=simulation.model_dump(mode="json"),
                    rejected_orders_by_tick={
                        tick: [rejection.model_dump(mode="json") for rejection in rejected_orders]
                        for tick, rejected_orders in sorted(rejected_orders_by_tick.items())
                    },
                ),
            )
        )

    return RegressionBatchResult(
        total_runs=total_runs,
        scenario_results=scenario_results,
        failures=failures,
    )


def build_regression_scenarios() -> list[RegressionScenario]:
    return [
        *_frontier_campaign_scenarios(),
        *_attrition_pressure_scenarios(),
        *_victory_countdown_scenarios(),
    ]


def _check_state_invariants(
    state: MatchState,
    *,
    scenario: RegressionScenario,
    tick: int,
    check_victory: bool = True,
) -> list[RegressionFailure]:
    failures: list[RegressionFailure] = []
    map_city_ids = set(scenario.map_definition.cities)
    state_city_ids = set(state.cities)
    player_city_ownership: dict[str, set[str]] = {player_id: set() for player_id in state.players}
    coalition_city_counts: dict[str, int] = {}

    if state_city_ids != map_city_ids:
        missing = sorted(map_city_ids - state_city_ids)
        extra = sorted(state_city_ids - map_city_ids)
        failures.append(
            _failure(
                scenario,
                tick=tick,
                invariant="state-cities-match-map",
                detail=f"map/state mismatch missing={missing} extra={extra}",
            )
        )

    for city_id, city_state in state.cities.items():
        if city_state.owner is not None and city_state.owner not in state.players:
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="city-owner-exists",
                    detail=f"city '{city_id}' references unknown owner '{city_state.owner}'",
                )
            )
        if city_state.owner is not None and city_state.owner in player_city_ownership:
            player_city_ownership[city_state.owner].add(city_id)

        if city_state.population < 0:
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="city-population-non-negative",
                    detail=f"city '{city_id}' has negative population {city_state.population}",
                )
            )
        if city_state.garrison < 0:
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="city-garrison-non-negative",
                    detail=f"city '{city_id}' has negative garrison {city_state.garrison}",
                )
            )
        failures.extend(
            _resource_failures(
                scenario,
                tick=tick,
                invariant_prefix=f"city-resource:{city_id}",
                resources=city_state.resources,
            )
        )

        if city_state.owner is not None and city_state.owner in state.players:
            player_state = state.players[city_state.owner]
            coalition_id = player_state.alliance_id or city_state.owner
            coalition_city_counts[coalition_id] = coalition_city_counts.get(coalition_id, 0) + 1

    army_counts_by_owner: dict[str, int] = {}
    for army in state.armies:
        army_counts_by_owner[army.owner] = army_counts_by_owner.get(army.owner, 0) + 1
        if army.owner not in state.players:
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="army-owner-exists",
                    detail=f"army '{army.id}' references unknown owner '{army.owner}'",
                )
            )
        if army.troops <= 0:
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="army-troops-positive",
                    detail=f"army '{army.id}' has non-positive troops {army.troops}",
                )
            )
        if army.location is not None and army.location not in state.cities:
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="army-location-exists",
                    detail=f"army '{army.id}' references unknown location '{army.location}'",
                )
            )
        if army.destination is not None and army.destination not in state.cities:
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="army-destination-exists",
                    detail=f"army '{army.id}' references unknown destination '{army.destination}'",
                )
            )
        if army.path is not None:
            invalid_path_cities = [city_id for city_id in army.path if city_id not in state.cities]
            if invalid_path_cities:
                failures.append(
                    _failure(
                        scenario,
                        tick=tick,
                        invariant="army-path-cities-exist",
                        detail=(
                            f"army '{army.id}' path includes unknown cities {invalid_path_cities}"
                        ),
                    )
                )
    for player_id, player_state in state.players.items():
        failures.extend(
            _resource_failures(
                scenario,
                tick=tick,
                invariant_prefix=f"player-resource:{player_id}",
                resources=player_state.resources,
            )
        )

        unknown_cities = [
            city_id for city_id in player_state.cities_owned if city_id not in state.cities
        ]
        if unknown_cities:
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="player-city-reference-exists",
                    detail=f"player '{player_id}' references unknown cities {unknown_cities}",
                )
            )

        expected_owned = sorted(player_city_ownership[player_id])
        actual_owned = sorted(player_state.cities_owned)
        if actual_owned != expected_owned:
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="player-city-ownership-consistent",
                    detail=(
                        f"player '{player_id}' cities_owned={actual_owned} "
                        f"but owned cities are {expected_owned}"
                    ),
                )
            )

        has_presence = bool(expected_owned) or army_counts_by_owner.get(player_id, 0) > 0
        if player_state.is_eliminated == has_presence:
            state_label = "still has" if has_presence else "has no"
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="player-elimination-consistent",
                    detail=(
                        f"player '{player_id}' elimination={player_state.is_eliminated} "
                        f"but {state_label} cities/armies"
                    ),
                )
            )

    if check_victory:
        failures.extend(
            _victory_failures(
                state,
                scenario=scenario,
                tick=tick,
                coalition_city_counts=coalition_city_counts,
            )
        )
    return failures


def _resource_failures(
    scenario: RegressionScenario,
    *,
    tick: int,
    invariant_prefix: str,
    resources: ResourceState,
) -> list[RegressionFailure]:
    failures: list[RegressionFailure] = []
    for resource_name in ("food", "production", "money"):
        resource_value = getattr(resources, resource_name)
        if resource_value < 0:
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant=f"{invariant_prefix}:{resource_name}-non-negative",
                    detail=f"{invariant_prefix} has negative {resource_name}={resource_value}",
                )
            )
    return failures


def _victory_failures(
    state: MatchState,
    *,
    scenario: RegressionScenario,
    tick: int,
    coalition_city_counts: dict[str, int],
) -> list[RegressionFailure]:
    failures: list[RegressionFailure] = []
    victory = state.victory
    total_cities = len(state.cities)
    max_cities_held = max(coalition_city_counts.values(), default=0)
    leaders = sorted(
        coalition_id
        for coalition_id, city_count in coalition_city_counts.items()
        if city_count == max_cities_held
    )

    if victory.threshold > total_cities:
        failures.append(
            _failure(
                scenario,
                tick=tick,
                invariant="victory-threshold-in-range",
                detail=f"victory threshold {victory.threshold} exceeds total cities {total_cities}",
            )
        )
    if victory.cities_held != max_cities_held:
        failures.append(
            _failure(
                scenario,
                tick=tick,
                invariant="victory-cities-held-consistent",
                detail=(
                    f"victory cities_held={victory.cities_held} "
                    f"but max coalition holds {max_cities_held}"
                ),
            )
        )
    if victory.leading_alliance is None:
        if victory.countdown_ticks_remaining is not None:
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="victory-countdown-requires-leader",
                    detail="victory countdown is set without a unique leading alliance",
                )
            )
    else:
        expected_leader = leaders[0] if len(leaders) == 1 else None
        if victory.leading_alliance != expected_leader:
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="victory-leader-consistent",
                    detail=(
                        f"victory leading_alliance='{victory.leading_alliance}' "
                        f"but expected '{expected_leader}'"
                    ),
                )
            )
        if victory.leading_alliance not in coalition_city_counts:
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="victory-leader-exists",
                    detail=(
                        f"victory leading_alliance '{victory.leading_alliance}' has no owned cities"
                    ),
                )
            )
        if (
            victory.countdown_ticks_remaining is not None
            and victory.cities_held < victory.threshold
        ):
            failures.append(
                _failure(
                    scenario,
                    tick=tick,
                    invariant="victory-countdown-threshold-consistent",
                    detail=(
                        f"victory countdown is active with cities_held={victory.cities_held} "
                        f"below threshold={victory.threshold}"
                    ),
                )
            )
    return failures


def _failure(
    scenario: RegressionScenario,
    *,
    tick: int,
    invariant: str,
    detail: str,
) -> RegressionFailure:
    return RegressionFailure(
        scenario_id=scenario.scenario_id,
        tick=tick,
        invariant=invariant,
        detail=detail,
    )


def _outcome_digest(**payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _city(
    name: str,
    *,
    primary_resource: ResourceType,
) -> CityDefinition:
    return CityDefinition(
        name=name,
        region="Regression",
        primary_resource=primary_resource,
        notes="",
        position=CityCoordinates(x=1, y=1),
    )


def _city_state(
    *,
    owner: str | None,
    resources: ResourceState | None = None,
    fortification: int = 0,
) -> CityState:
    return CityState(
        owner=owner,
        population=1,
        resources=resources or ResourceState(food=1, production=1, money=1),
        upgrades=CityUpgradeState(economy=0, military=0, fortification=fortification),
        garrison=5,
        building_queue=[],
    )


def _frontier_campaign_scenarios() -> list[RegressionScenario]:
    scenario_map = MapDefinition(
        map_id="frontier_campaign_regression",
        name="Frontier Campaign Regression",
        cities={
            "alpha": _city("Alpha", primary_resource=ResourceType.PRODUCTION),
            "bravo": _city("Bravo", primary_resource=ResourceType.FOOD),
            "charlie": _city("Charlie", primary_resource=ResourceType.MONEY),
            "delta": _city("Delta", primary_resource=ResourceType.FOOD),
        },
        edges=[
            MapEdge(city_a="alpha", city_b="bravo", distance_ticks=1),
            MapEdge(city_a="bravo", city_b="charlie", distance_ticks=1),
            MapEdge(city_a="alpha", city_b="delta", distance_ticks=1),
        ],
    )
    base_state = MatchState(
        tick=10,
        cities={
            "alpha": _city_state(
                owner="player_1",
                resources=ResourceState(food=1, production=3, money=1),
            ),
            "bravo": _city_state(
                owner="player_2",
                resources=ResourceState(food=1, production=1, money=1),
                fortification=2,
            ),
            "charlie": _city_state(
                owner="player_1",
                resources=ResourceState(food=1, production=1, money=3),
            ),
            "delta": _city_state(
                owner=None,
                resources=ResourceState(food=3, production=1, money=1),
            ),
        },
        armies=[
            ArmyState(
                id="army_main",
                owner="player_1",
                troops=60,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_guard",
                owner="player_1",
                troops=6,
                location="charlie",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_defender",
                owner="player_2",
                troops=20,
                location="bravo",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=500, production=20, money=20),
                cities_owned=["alpha", "charlie"],
                alliance_id=None,
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=4, production=5, money=3),
                cities_owned=["bravo"],
                alliance_id=None,
                is_eliminated=False,
            ),
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=3,
            countdown_ticks_remaining=None,
        ),
    )

    scenario_specs: tuple[ScenarioSpec, ...] = (
        (
            "opening-clash",
            4,
            {
                10: [
                    _order_envelope(
                        match_id="frontier-regression",
                        player_id="player_1",
                        tick=10,
                        orders=OrderBatch(
                            movements=[MovementOrder(army_id="army_main", destination="bravo")],
                        ),
                    )
                ]
            },
        ),
        (
            "late-upgrade",
            6,
            {
                10: [
                    _order_envelope(
                        match_id="frontier-regression",
                        player_id="player_1",
                        tick=10,
                        orders=OrderBatch(
                            movements=[MovementOrder(army_id="army_main", destination="bravo")],
                            upgrades=[
                                UpgradeOrder(
                                    city="charlie",
                                    track=UpgradeTrack.FORTIFICATION,
                                    target_tier=FortificationTier.TRENCHES,
                                )
                            ],
                        ),
                    )
                ]
            },
        ),
        (
            "double-pressure",
            6,
            {
                10: [
                    _order_envelope(
                        match_id="frontier-regression",
                        player_id="player_1",
                        tick=10,
                        orders=OrderBatch(
                            movements=[
                                MovementOrder(army_id="army_main", destination="bravo"),
                                MovementOrder(army_id="army_guard", destination="alpha"),
                            ],
                        ),
                    )
                ],
                11: [
                    _order_envelope(
                        match_id="frontier-regression",
                        player_id="player_2",
                        tick=11,
                        orders=OrderBatch(
                            movements=[
                                MovementOrder(army_id="army_defender", destination="charlie")
                            ]
                        ),
                    )
                ],
            },
        ),
        (
            "extended-pressure",
            8,
            {
                10: [
                    _order_envelope(
                        match_id="frontier-regression",
                        player_id="player_1",
                        tick=10,
                        orders=OrderBatch(
                            movements=[MovementOrder(army_id="army_main", destination="bravo")],
                        ),
                    )
                ],
                12: [
                    _order_envelope(
                        match_id="frontier-regression",
                        player_id="player_1",
                        tick=12,
                        orders=OrderBatch(
                            movements=[MovementOrder(army_id="army_guard", destination="delta")]
                        ),
                    )
                ],
            },
        ),
    )

    return [
        RegressionScenario(
            scenario_id=f"frontier-campaign/ticks={ticks}/variant={variant}",
            map_definition=scenario_map,
            initial_state=base_state.model_copy(deep=True),
            ticks=ticks,
            orders_by_tick=orders_by_tick,
        )
        for variant, ticks, orders_by_tick in scenario_specs
    ]


def _attrition_pressure_scenarios() -> list[RegressionScenario]:
    scenario_map = MapDefinition(
        map_id="attrition_pressure_regression",
        name="Attrition Pressure Regression",
        cities={
            "north": _city("North", primary_resource=ResourceType.FOOD),
            "south": _city("South", primary_resource=ResourceType.PRODUCTION),
            "east": _city("East", primary_resource=ResourceType.MONEY),
        },
        edges=[
            MapEdge(city_a="north", city_b="south", distance_ticks=1),
            MapEdge(city_a="south", city_b="east", distance_ticks=1),
        ],
    )
    base_state = MatchState(
        tick=5,
        cities={
            "north": _city_state(
                owner="player_1",
                resources=ResourceState(food=1, production=1, money=1),
            ),
            "south": _city_state(
                owner="player_2",
                resources=ResourceState(food=1, production=2, money=1),
            ),
            "east": _city_state(
                owner=None,
                resources=ResourceState(food=1, production=1, money=3),
            ),
        },
        armies=[
            ArmyState(
                id="army_hungry",
                owner="player_1",
                troops=3,
                location="north",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_watch",
                owner="player_2",
                troops=5,
                location="south",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=0, production=3, money=3),
                cities_owned=["north"],
                alliance_id=None,
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=8, production=4, money=4),
                cities_owned=["south"],
                alliance_id=None,
                is_eliminated=False,
            ),
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=2,
            countdown_ticks_remaining=None,
        ),
    )

    scenario_specs: tuple[ScenarioSpec, ...] = (
        ("starving-start", 2, {}),
        (
            "desperate-march",
            3,
            {
                5: [
                    _order_envelope(
                        match_id="attrition-regression",
                        player_id="player_1",
                        tick=5,
                        orders=OrderBatch(
                            movements=[MovementOrder(army_id="army_hungry", destination="south")]
                        ),
                    )
                ]
            },
        ),
        (
            "counter-march",
            4,
            {
                5: [
                    _order_envelope(
                        match_id="attrition-regression",
                        player_id="player_2",
                        tick=5,
                        orders=OrderBatch(
                            movements=[MovementOrder(army_id="army_watch", destination="north")]
                        ),
                    )
                ]
            },
        ),
        (
            "delayed-contact",
            5,
            {
                6: [
                    _order_envelope(
                        match_id="attrition-regression",
                        player_id="player_2",
                        tick=6,
                        orders=OrderBatch(
                            movements=[MovementOrder(army_id="army_watch", destination="east")]
                        ),
                    )
                ]
            },
        ),
    )

    return [
        RegressionScenario(
            scenario_id=f"attrition-line/ticks={ticks}/variant={variant}",
            map_definition=scenario_map,
            initial_state=base_state.model_copy(deep=True),
            ticks=ticks,
            orders_by_tick=orders_by_tick,
        )
        for variant, ticks, orders_by_tick in scenario_specs
    ]


def _victory_countdown_scenarios() -> list[RegressionScenario]:
    scenario_map = MapDefinition(
        map_id="victory_countdown_regression",
        name="Victory Countdown Regression",
        cities={
            "alpha": _city("Alpha", primary_resource=ResourceType.MONEY),
            "bravo": _city("Bravo", primary_resource=ResourceType.PRODUCTION),
            "charlie": _city("Charlie", primary_resource=ResourceType.FOOD),
            "delta": _city("Delta", primary_resource=ResourceType.FOOD),
        },
        edges=[
            MapEdge(city_a="alpha", city_b="bravo", distance_ticks=1),
            MapEdge(city_a="bravo", city_b="charlie", distance_ticks=1),
            MapEdge(city_a="charlie", city_b="delta", distance_ticks=1),
        ],
    )
    base_state = MatchState(
        tick=20,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_1"),
            "charlie": _city_state(owner="player_2"),
            "delta": _city_state(owner="player_1"),
        },
        armies=[
            ArmyState(
                id="army_anchor",
                owner="player_1",
                troops=14,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_foe",
                owner="player_2",
                troops=7,
                location="charlie",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=20, production=10, money=10),
                cities_owned=["alpha", "bravo", "delta"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=20, production=10, money=10),
                cities_owned=["charlie"],
                alliance_id="alliance_blue",
                is_eliminated=False,
            ),
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=3,
            countdown_ticks_remaining=None,
        ),
    )

    scenario_specs: tuple[ScenarioSpec, ...] = (
        ("alliance-hold", 2, {}),
        ("alliance-countdown", 4, {}),
        (
            "pressure-charlie",
            4,
            {
                20: [
                    _order_envelope(
                        match_id="victory-regression",
                        player_id="player_1",
                        tick=20,
                        orders=OrderBatch(
                            movements=[MovementOrder(army_id="army_anchor", destination="bravo")]
                        ),
                    )
                ]
            },
        ),
        (
            "defender-shift",
            5,
            {
                21: [
                    _order_envelope(
                        match_id="victory-regression",
                        player_id="player_2",
                        tick=21,
                        orders=OrderBatch(
                            movements=[MovementOrder(army_id="army_foe", destination="delta")]
                        ),
                    )
                ]
            },
        ),
    )

    return [
        RegressionScenario(
            scenario_id=f"victory-race/ticks={ticks}/variant={variant}",
            map_definition=scenario_map,
            initial_state=base_state.model_copy(deep=True),
            ticks=ticks,
            orders_by_tick=orders_by_tick,
        )
        for variant, ticks, orders_by_tick in scenario_specs
    ]


def _order_envelope(
    *,
    match_id: str,
    player_id: str,
    tick: int,
    orders: OrderBatch,
) -> OrderEnvelope:
    return OrderEnvelope(match_id=match_id, player_id=player_id, tick=tick, orders=orders)
