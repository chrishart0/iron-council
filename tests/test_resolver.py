from __future__ import annotations

from copy import deepcopy

from server.models.orders import OrderBatch
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
                resources=ResourceState(food=10, production=20, money=30),
                cities_owned=["alpha"],
                alliance_id="alliance_red",
                is_eliminated=False,
            ),
            "player_2": PlayerState(
                resources=ResourceState(food=8, production=7, money=6),
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
        population=10,
        resources=ResourceState(food=1, production=1, money=1),
        upgrades=CityUpgradeState(economy=0, military=0, fortification=0),
        garrison=5,
        building_queue=[],
    )


def test_resolve_tick_returns_copied_state_without_mutating_input() -> None:
    state = _match_state()
    original_dump = deepcopy(state.model_dump(mode="json"))
    orders = OrderBatch()

    result = resolve_tick(state, orders)

    assert result.next_state is not state
    assert state.model_dump(mode="json") == original_dump
    assert result.next_state.model_dump(mode="json") == original_dump


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
