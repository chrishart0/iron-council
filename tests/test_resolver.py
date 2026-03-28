from __future__ import annotations

from copy import deepcopy

from server.models.orders import MovementOrder, OrderBatch
from server.models.state import (
    ArmyState,
    CityState,
    CityUpgradeState,
    MatchState,
    PlayerState,
    ResourceState,
    VictoryState,
)
from server.resolver import PHASE_ORDER, TickPhaseEvent, resolve_tick


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


def test_resolve_tick_adds_owned_city_yields_and_food_upkeep_without_mutating_input() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": CityState(
                owner="player_1",
                population=4,
                resources=ResourceState(food=3, production=1, money=1),
                upgrades=CityUpgradeState(economy=3, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            ),
            "bravo": CityState(
                owner="player_1",
                population=2,
                resources=ResourceState(food=1, production=3, money=1),
                upgrades=CityUpgradeState(economy=2, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            ),
            "charlie": CityState(
                owner="player_2",
                population=3,
                resources=ResourceState(food=1, production=1, money=3),
                upgrades=CityUpgradeState(economy=1, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            ),
            "delta": CityState(
                owner=None,
                population=9,
                resources=ResourceState(food=3, production=1, money=1),
                upgrades=CityUpgradeState(economy=3, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            ),
        },
        armies=[
            ArmyState(
                id="army_1",
                owner="player_1",
                troops=5,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_2",
                owner="player_1",
                troops=2,
                location="bravo",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
            ArmyState(
                id="army_3",
                owner="player_2",
                troops=1,
                location="charlie",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=10, production=20, money=30),
                cities_owned=["alpha", "bravo"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=8, production=7, money=6),
                cities_owned=["charlie"],
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
    original_dump = deepcopy(state.model_dump(mode="json"))

    result = resolve_tick(state, OrderBatch())

    assert state.model_dump(mode="json") == original_dump
    assert result.next_state.players["player_1"].resources == ResourceState(
        food=4,
        production=26,
        money=32,
    )
    assert result.next_state.players["player_2"].resources == ResourceState(
        food=5,
        production=8,
        money=10,
    )


def test_resolve_tick_clamps_food_to_zero_when_upkeep_exceeds_available_food() -> None:
    state = MatchState(
        tick=5,
        cities={
            "alpha": CityState(
                owner="player_1",
                population=4,
                resources=ResourceState(food=1, production=1, money=1),
                upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
                garrison=5,
                building_queue=[],
            )
        },
        armies=[
            ArmyState(
                id="army_1",
                owner="player_1",
                troops=3,
                location="alpha",
                destination=None,
                path=None,
                ticks_remaining=0,
            )
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=2, production=10, money=10),
                cities_owned=["alpha"],
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
    original_dump = deepcopy(state.model_dump(mode="json"))

    result = resolve_tick(state, OrderBatch())

    assert state.model_dump(mode="json") == original_dump
    assert result.next_state.players["player_1"].resources == ResourceState(
        food=0,
        production=11,
        money=11,
    )


def test_resolve_tick_returns_copied_state_without_mutating_input() -> None:
    state = _match_state()
    original_dump = deepcopy(state.model_dump(mode="json"))
    orders = OrderBatch()

    result = resolve_tick(state, orders)

    assert result.next_state is not state
    assert state.model_dump(mode="json") == original_dump
    assert result.next_state.tick == state.tick
    assert result.next_state.model_dump(mode="json")["cities"] == original_dump["cities"]
    assert result.next_state.model_dump(mode="json")["armies"] == original_dump["armies"]
    assert result.next_state.model_dump(mode="json")["victory"] == original_dump["victory"]


def test_resolve_tick_emits_phase_metadata_and_typed_events_in_phase_order() -> None:
    result = resolve_tick(_match_state(), OrderBatch())

    assert [phase.phase for phase in result.phases] == list(PHASE_ORDER)
    assert result.events == [
        TickPhaseEvent(phase=phase, event=f"phase.{phase}.completed") for phase in PHASE_ORDER
    ]


def test_resolve_tick_is_deterministic_for_same_state_and_orders() -> None:
    state = _match_state()
    orders = OrderBatch()

    result = resolve_tick(state, orders)
    repeated_result = resolve_tick(state, orders)

    assert result.model_dump(mode="json") == repeated_result.model_dump(mode="json")


def test_resolve_tick_advances_transit_arrivals_and_starts_new_one_edge_marches() -> None:
    state = MatchState(
        tick=5,
        cities={
            "london": _city_state(owner="player_1"),
            "birmingham": _city_state(owner=None),
            "southampton": _city_state(owner="player_1"),
        },
        armies=[
            ArmyState(
                id="marching_army",
                owner="player_1",
                troops=8,
                location=None,
                destination="birmingham",
                path=["birmingham"],
                ticks_remaining=2,
            ),
            ArmyState(
                id="arriving_army",
                owner="player_1",
                troops=4,
                location=None,
                destination="southampton",
                path=["southampton"],
                ticks_remaining=1,
            ),
            ArmyState(
                id="stationed_army",
                owner="player_1",
                troops=6,
                location="london",
                destination=None,
                path=None,
                ticks_remaining=0,
            ),
        ],
        players={
            "player_1": PlayerState(
                resources=ResourceState(food=30, production=20, money=30),
                cities_owned=["london", "southampton"],
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
    original_dump = deepcopy(state.model_dump(mode="json"))
    orders = OrderBatch(
        movements=[MovementOrder(army_id="stationed_army", destination="birmingham")]
    )

    result = resolve_tick(state, orders)

    assert state.model_dump(mode="json") == original_dump
    armies_by_id = {army.id: army for army in result.next_state.armies}

    assert armies_by_id["marching_army"] == ArmyState(
        id="marching_army",
        owner="player_1",
        troops=8,
        location=None,
        destination="birmingham",
        path=["birmingham"],
        ticks_remaining=1,
    )
    assert armies_by_id["arriving_army"] == ArmyState(
        id="arriving_army",
        owner="player_1",
        troops=4,
        location="southampton",
        destination=None,
        path=None,
        ticks_remaining=0,
    )
    assert armies_by_id["stationed_army"] == ArmyState(
        id="stationed_army",
        owner="player_1",
        troops=6,
        location=None,
        destination="birmingham",
        path=["birmingham"],
        ticks_remaining=2,
    )
