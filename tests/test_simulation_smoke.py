from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pytest
from server.data.maps import CityCoordinates, CityDefinition, MapDefinition, MapEdge
from server.models.domain import FortificationTier, ResourceType, UpgradeTrack
from server.models.orders import MovementOrder, OrderBatch, OrderEnvelope, UpgradeOrder
from server.models.state import (
    ArmyState,
    BuildingQueueItem,
    CityState,
    CityUpgradeState,
    MatchState,
    PlayerState,
    ResourceState,
    VictoryState,
)
from server.order_validation import RejectedOrder, ValidationReasonCode, validate_order_envelope
from server.simulation import SimulationResult, simulate_ticks


@dataclass(frozen=True)
class SmokeScenario:
    name: str
    map_definition: MapDefinition
    initial_state: MatchState
    ticks: int
    orders_by_tick: dict[int, list[OrderEnvelope]]
    expected_rejections_by_tick: dict[int, list[tuple[str, ValidationReasonCode, str]]]
    assert_outcomes: Callable[[SmokeScenarioRun], None]


@dataclass(frozen=True)
class SmokeScenarioRun:
    simulation: SimulationResult
    rejected_orders_by_tick: dict[int, list[RejectedOrder]]


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


def _smoke_city(name: str, primary_resource: ResourceType) -> CityDefinition:
    return CityDefinition(
        name=name,
        region="Smoke",
        primary_resource=primary_resource,
        notes="",
        position=CityCoordinates(x=1, y=1),
    )


def _frontier_campaign_smoke_scenario() -> SmokeScenario:
    scenario_map = MapDefinition(
        map_id="frontier_campaign_smoke",
        name="Frontier Campaign Smoke",
        cities={
            "alpha": _smoke_city("Alpha", ResourceType.PRODUCTION),
            "bravo": _smoke_city("Bravo", ResourceType.FOOD),
            "charlie": _smoke_city("Charlie", ResourceType.MONEY),
            "delta": _smoke_city("Delta", ResourceType.FOOD),
        },
        edges=[
            MapEdge(city_a="alpha", city_b="bravo", distance_ticks=1),
            MapEdge(city_a="bravo", city_b="charlie", distance_ticks=1),
            MapEdge(city_a="alpha", city_b="delta", distance_ticks=1),
        ],
    )
    initial_state = MatchState(
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
                resources=ResourceState(food=0, production=5, money=0),
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
    orders_by_tick = {
        10: [
            OrderEnvelope(
                match_id="frontier-campaign",
                player_id="player_1",
                tick=10,
                orders=OrderBatch(
                    movements=[
                        MovementOrder(army_id="army_main", destination="bravo"),
                        MovementOrder(army_id="army_guard", destination="delta"),
                    ],
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
    }
    return SmokeScenario(
        name="frontier_campaign",
        map_definition=scenario_map,
        initial_state=initial_state,
        ticks=6,
        orders_by_tick=orders_by_tick,
        expected_rejections_by_tick={
            10: [
                (
                    "movement",
                    ValidationReasonCode.INVALID_ADJACENCY,
                    "movement order 1 destination 'delta' is not directly connected to "
                    "army 'army_guard' at 'charlie'",
                )
            ]
        },
        assert_outcomes=_assert_frontier_campaign_outcomes,
    )


def _run_smoke_scenario(scenario: SmokeScenario, *, ticks: int) -> SmokeScenarioRun:
    rejected_orders_by_tick: dict[int, list[RejectedOrder]] = {}

    def order_provider(*, tick: int, state: MatchState) -> OrderBatch:
        accepted = OrderBatch()
        rejections: list[RejectedOrder] = []

        for envelope in scenario.orders_by_tick.get(tick, []):
            validation = validate_order_envelope(envelope, state, scenario.map_definition)
            accepted.movements.extend(validation.accepted.movements)
            accepted.recruitment.extend(validation.accepted.recruitment)
            accepted.upgrades.extend(validation.accepted.upgrades)
            accepted.transfers.extend(validation.accepted.transfers)
            rejections.extend(validation.rejected)

        if rejections:
            rejected_orders_by_tick[tick] = rejections

        return accepted

    simulation = simulate_ticks(
        scenario.initial_state,
        ticks=ticks,
        order_provider=order_provider,
        map_definition=scenario.map_definition,
    )
    return SmokeScenarioRun(
        simulation=simulation,
        rejected_orders_by_tick=rejected_orders_by_tick,
    )


def _stationed_troops(snapshot: MatchState, *, owner: str, city: str) -> int | None:
    for army in snapshot.armies:
        if army.owner == owner and army.location == city and army.destination is None:
            return army.troops
    return None


def _moving_army(snapshot: MatchState, *, owner: str, destination: str) -> ArmyState | None:
    for army in snapshot.armies:
        if army.owner == owner and army.destination == destination:
            return army
    return None


def _scenario_outcome_digest(run: SmokeScenarioRun) -> dict[str, object]:
    return {
        "rejected_orders_by_tick": {
            tick: [
                {
                    "order_type": rejection.order_type,
                    "reason_code": rejection.reason_code.value,
                    "message": rejection.message,
                }
                for rejection in rejections
            ]
            for tick, rejections in sorted(run.rejected_orders_by_tick.items())
        },
        "ticks": [
            {
                "tick": simulated_tick.tick,
                "events": [event.model_dump(mode="json") for event in simulated_tick.events],
                "city_owners": {
                    city_id: city_state.owner
                    for city_id, city_state in sorted(simulated_tick.snapshot.cities.items())
                },
                "fortifications": {
                    city_id: city_state.upgrades.fortification
                    for city_id, city_state in sorted(simulated_tick.snapshot.cities.items())
                },
                "building_queues": {
                    city_id: [
                        BuildingQueueItem.model_validate(queue_item).model_dump(mode="json")
                        for queue_item in city_state.building_queue
                    ]
                    for city_id, city_state in sorted(simulated_tick.snapshot.cities.items())
                    if city_state.building_queue
                },
                "stationed_armies": sorted(
                    (army.owner, army.location, army.troops)
                    for army in simulated_tick.snapshot.armies
                    if army.location is not None and army.destination is None
                ),
                "moving_armies": sorted(
                    (army.owner, army.destination, army.ticks_remaining)
                    for army in simulated_tick.snapshot.armies
                    if army.destination is not None
                ),
                "victory": simulated_tick.snapshot.victory.model_dump(mode="json"),
            }
            for simulated_tick in run.simulation.ticks
        ],
    }


def _normalized_rejections(
    rejected_orders_by_tick: dict[int, list[RejectedOrder]],
) -> dict[int, list[tuple[str, ValidationReasonCode, str]]]:
    return {
        tick: [
            (rejection.order_type, rejection.reason_code, rejection.message)
            for rejection in rejections
        ]
        for tick, rejections in sorted(rejected_orders_by_tick.items())
    }


def _assert_frontier_campaign_outcomes(run: SmokeScenarioRun) -> None:
    tick_11, tick_12, tick_13, tick_14, tick_15, tick_16 = [
        simulated_tick.snapshot for simulated_tick in run.simulation.ticks
    ]

    in_transit_to_bravo = _moving_army(tick_11, owner="player_1", destination="bravo")
    assert in_transit_to_bravo is not None
    assert _stationed_troops(tick_11, owner="player_1", city="charlie") == 6
    assert tick_11.cities["bravo"].upgrades.fortification == 1
    assert tick_11.cities["charlie"].building_queue == [
        BuildingQueueItem(
            type=UpgradeTrack.FORTIFICATION,
            tier=FortificationTier.TRENCHES,
            ticks_remaining=1,
        )
    ]

    assert tick_12.cities["charlie"].building_queue == []
    assert tick_12.cities["bravo"].owner == "player_2"
    assert tick_12.cities["bravo"].upgrades.fortification == 0
    assert _stationed_troops(tick_12, owner="player_1", city="bravo") is not None
    assert _stationed_troops(tick_12, owner="player_2", city="bravo") is not None

    player_1_troops_on_arrival = _stationed_troops(tick_12, owner="player_1", city="bravo")
    player_1_troops_after_pressure = _stationed_troops(tick_13, owner="player_1", city="bravo")
    player_2_troops_on_arrival = _stationed_troops(tick_12, owner="player_2", city="bravo")
    player_2_troops_after_pressure = _stationed_troops(tick_13, owner="player_2", city="bravo")
    assert player_1_troops_on_arrival is not None
    assert player_1_troops_after_pressure is not None
    assert player_2_troops_on_arrival is not None
    assert player_2_troops_after_pressure is not None
    assert player_1_troops_after_pressure < player_1_troops_on_arrival
    assert player_2_troops_after_pressure < player_2_troops_on_arrival
    assert tick_14.cities["bravo"].owner == "player_2"
    assert _stationed_troops(tick_14, owner="player_2", city="bravo") is None

    assert tick_15.cities["bravo"].owner == "player_1"
    assert tick_15.victory.model_dump(mode="json") == {
        "leading_alliance": "player_1",
        "cities_held": 3,
        "threshold": 3,
        "countdown_ticks_remaining": 3,
    }
    assert tick_16.victory.countdown_ticks_remaining == 2


SMOKE_SCENARIO_BUILDERS = (_frontier_campaign_smoke_scenario,)
SMOKE_SCENARIOS = [builder() for builder in SMOKE_SCENARIO_BUILDERS]


@pytest.mark.parametrize("scenario", SMOKE_SCENARIOS, ids=lambda scenario: scenario.name)
def test_simulation_smoke_scenarios_cover_representative_gameplay_flows(
    scenario: SmokeScenario,
) -> None:
    run = _run_smoke_scenario(scenario, ticks=scenario.ticks)

    assert (
        _normalized_rejections(run.rejected_orders_by_tick) == scenario.expected_rejections_by_tick
    )
    scenario.assert_outcomes(run)


@pytest.mark.parametrize("scenario", SMOKE_SCENARIOS, ids=lambda scenario: scenario.name)
def test_simulation_smoke_scenarios_are_deterministic_for_externally_visible_outcomes(
    scenario: SmokeScenario,
) -> None:
    first_run = _run_smoke_scenario(scenario, ticks=scenario.ticks)
    repeated_run = _run_smoke_scenario(scenario, ticks=scenario.ticks)

    assert _scenario_outcome_digest(first_run) == _scenario_outcome_digest(repeated_run)
