from __future__ import annotations

import builtins
import importlib
import sys
from copy import deepcopy

import pytest
from server import PHASE_ORDER, TickPhaseEvent, TickPhaseMetadata, simulate_ticks
from server.data.maps import CityCoordinates, CityDefinition, MapDefinition, MapEdge
from server.models.domain import ResourceType
from server.models.orders import MovementOrder, OrderBatch, OrderEnvelope
from server.models.state import (
    ArmyState,
    CityState,
    CityUpgradeState,
    MatchState,
    PlayerState,
    ResourceState,
    VictoryState,
)
from server.order_validation import validate_order_envelope


def _match_state() -> MatchState:
    return MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_2"),
        },
        armies=[
            ArmyState(
                id="army_1",
                owner="player_1",
                troops=8,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            )
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=30, production=20, money=30),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=20, production=7, money=6),
                cities_owned=["bravo"],
                alliance_id="alliance_blue",
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


def _city_state(*, owner: str | None) -> CityState:
    return CityState(
        owner=owner,
        population=1,
        resources=ResourceState(food=1, production=1, money=1),
        upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
        garrison=5,
        building_queue=[],
    )


def _custom_city_definition(primary_resource: ResourceType) -> CityDefinition:
    return CityDefinition(
        name=f"{primary_resource.value}-city",
        region="Custom",
        primary_resource=primary_resource,
        notes="",
        position=CityCoordinates(x=1, y=1),
    )


def _custom_simulation_map() -> MapDefinition:
    return MapDefinition(
        map_id="simulation_custom_map",
        name="Simulation Custom Map",
        cities={
            "mesa": _custom_city_definition(ResourceType.FOOD),
            "oasis": _custom_city_definition(ResourceType.PRODUCTION),
        },
        edges=[MapEdge(city_a="mesa", city_b="oasis", distance_ticks=1)],
    )


def _movement_order_envelope() -> OrderEnvelope:
    return OrderEnvelope.model_validate(
        {
            "match_id": "simulation_match",
            "player_id": "player_1",
            "tick": 5,
            "orders": {
                "movements": [{"army_id": "army_custom", "destination": "oasis"}],
                "recruitment": [],
                "upgrades": [],
                "transfers": [],
            },
        }
    )


def test_simulate_ticks_returns_ordered_per_tick_snapshots_and_logs() -> None:
    starting_state = _match_state()
    original_dump = deepcopy(starting_state.model_dump(mode="json"))

    simulation = simulate_ticks(
        starting_state,
        ticks=3,
        orders=OrderBatch(),
    )

    assert starting_state.model_dump(mode="json") == original_dump
    assert simulation.final_state is not starting_state
    assert len(simulation.ticks) == 3
    assert [tick_snapshot.tick for tick_snapshot in simulation.ticks] == [6, 7, 8]
    assert [tick_snapshot.snapshot.tick for tick_snapshot in simulation.ticks] == [6, 7, 8]
    assert simulation.final_state.tick == 8
    assert simulation.final_state.model_dump(mode="json") == simulation.ticks[
        -1
    ].snapshot.model_dump(mode="json")
    assert simulation.ticks[0].phases == [
        TickPhaseMetadata(phase=phase, event=f"phase.{phase}.completed") for phase in PHASE_ORDER
    ]
    assert simulation.ticks[0].events == [
        TickPhaseEvent(phase=phase, event=f"phase.{phase}.completed") for phase in PHASE_ORDER
    ]


def test_simulate_ticks_is_deterministic_for_static_orders() -> None:
    state = _match_state()
    orders = OrderBatch()

    result = simulate_ticks(state, ticks=2, orders=orders)
    repeated_result = simulate_ticks(state, ticks=2, orders=orders)

    assert result.model_dump(mode="json") == repeated_result.model_dump(mode="json")


def test_simulate_ticks_accepts_per_tick_order_provider() -> None:
    provided_states: list[int] = []

    def order_provider(*, tick: int, state: MatchState) -> OrderBatch:
        provided_states.append(state.tick)
        return OrderBatch()

    simulation = simulate_ticks(
        _match_state(),
        ticks=2,
        order_provider=order_provider,
    )

    assert provided_states == [5, 6]
    assert [tick_snapshot.tick for tick_snapshot in simulation.ticks] == [6, 7]


def test_simulate_ticks_rejects_negative_tick_counts() -> None:
    with pytest.raises(ValueError, match="ticks must be non-negative"):
        simulate_ticks(_match_state(), ticks=-1, orders=OrderBatch())


def test_simulate_ticks_rejects_orders_and_order_provider_together() -> None:
    def order_provider(*, tick: int, state: MatchState) -> OrderBatch:
        return OrderBatch()

    with pytest.raises(
        ValueError,
        match="pass either static orders or an order provider, not both",
    ):
        simulate_ticks(
            _match_state(),
            ticks=1,
            orders=OrderBatch(),
            order_provider=order_provider,
        )


def test_simulate_ticks_runs_without_importing_external_infrastructure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__
    blocked_modules = {"fastapi", "sqlalchemy", "asyncpg", "psycopg", "websockets"}
    attempted_imports: list[str] = []

    def import_guard(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        root_module = name.split(".", 1)[0]
        if root_module in blocked_modules:
            attempted_imports.append(name)
            raise AssertionError(f"simulate_ticks should not import external module: {name}")
        return real_import(name, globals, locals, fromlist, level)

    server_modules = [
        name for name in sys.modules if name == "server" or name.startswith("server.")
    ]
    for module_name in server_modules:
        monkeypatch.delitem(sys.modules, module_name, raising=False)

    monkeypatch.setattr(builtins, "__import__", import_guard)
    importlib.invalidate_caches()

    simulation_module = importlib.import_module("server.simulation")
    orders_module = importlib.import_module("server.models.orders")
    state_module = importlib.import_module("server.models.state")
    state = state_module.MatchState.model_validate(_match_state().model_dump(mode="json"))
    simulation = simulation_module.simulate_ticks(state, ticks=1, orders=orders_module.OrderBatch())

    assert simulation.final_state.tick == 6
    assert attempted_imports == []


def test_simulate_ticks_is_deterministic_for_movement_transit_progression() -> None:
    starting_state = MatchState(
        tick=5,
        cities={
            "london": _city_state(owner="player_1"),
            "birmingham": _city_state(owner=None),
        },
        armies=[
            ArmyState(
                id="army_1",
                owner="player_1",
                troops=8,
                location="london",
                destination=None,
                path=None,
                ticks_remaining=0,
            )
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=30, production=20, money=30),
                cities_owned=["london"],
                alliance_id="alliance_red",
                is_eliminated=False,
            )
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=2,
            countdown_ticks_remaining=None,
        ),
    )
    original_dump = deepcopy(starting_state.model_dump(mode="json"))
    orders = OrderBatch(movements=[MovementOrder(army_id="army_1", destination="birmingham")])

    simulation = simulate_ticks(starting_state, ticks=3, orders=orders)
    repeated_simulation = simulate_ticks(starting_state, ticks=3, orders=orders)

    assert starting_state.model_dump(mode="json") == original_dump
    assert simulation.model_dump(mode="json") == repeated_simulation.model_dump(mode="json")
    assert [tick.snapshot.armies[0].ticks_remaining for tick in simulation.ticks] == [2, 1, 0]
    assert [tick.snapshot.armies[0].location for tick in simulation.ticks] == [
        None,
        None,
        "birmingham",
    ]
    assert [tick.snapshot.armies[0].destination for tick in simulation.ticks] == [
        "birmingham",
        "birmingham",
        None,
    ]


def test_simulate_ticks_uses_explicit_custom_map_for_validated_movement_orders() -> None:
    custom_map = _custom_simulation_map()
    starting_state = MatchState(
        tick=5,
        cities={
            "mesa": _city_state(owner="player_1"),
            "oasis": _city_state(owner=None),
        },
        armies=[
            ArmyState(
                id="army_custom",
                owner="player_1",
                troops=8,
                location="mesa",
                destination=None,
                path=None,
                ticks_remaining=0,
            )
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["mesa"],
                alliance_id="alliance_red",
                is_eliminated=False,
            )
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            threshold=2,
            countdown_ticks_remaining=None,
        ),
    )

    validation = validate_order_envelope(_movement_order_envelope(), starting_state, custom_map)
    simulation = simulate_ticks(
        starting_state,
        ticks=2,
        orders=validation.accepted,
        map_definition=custom_map,
    )

    assert validation.rejected == []
    assert [tick.snapshot.armies[0].location for tick in simulation.ticks] == [None, "oasis"]
    assert [tick.snapshot.armies[0].ticks_remaining for tick in simulation.ticks] == [1, 0]
    assert [tick.snapshot.armies[0].destination for tick in simulation.ticks] == ["oasis", None]


def test_simulate_ticks_starts_and_continues_victory_countdown_for_same_coalition() -> None:
    starting_state = MatchState(
        tick=5,
        cities={
            "alpha": _city_state(owner="player_1"),
            "bravo": _city_state(owner="player_2"),
            "charlie": _city_state(owner="player_2"),
        },
        armies=[],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=10, production=10, money=10),
                cities_owned=["bravo", "charlie"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
        },
        victory=VictoryState(
            leading_alliance=None,
            cities_held=0,
            # Temporary narrow story choice: threshold also seeds countdown duration.
            threshold=3,
            countdown_ticks_remaining=None,
        ),
    )
    original_dump = deepcopy(starting_state.model_dump(mode="json"))

    simulation = simulate_ticks(starting_state, ticks=3, orders=OrderBatch())

    assert starting_state.model_dump(mode="json") == original_dump
    assert [tick.snapshot.victory.leading_alliance for tick in simulation.ticks] == [
        "alliance_red",
        "alliance_red",
        "alliance_red",
    ]
    assert [tick.snapshot.victory.cities_held for tick in simulation.ticks] == [3, 3, 3]
    assert [tick.snapshot.victory.countdown_ticks_remaining for tick in simulation.ticks] == [
        3,
        2,
        1,
    ]
