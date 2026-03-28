from __future__ import annotations

import builtins
from copy import deepcopy

import pytest
from server import PHASE_ORDER, TickPhaseEvent, TickPhaseMetadata, simulate_ticks
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

    monkeypatch.setattr(builtins, "__import__", import_guard)

    simulation = simulate_ticks(_match_state(), ticks=1, orders=OrderBatch())

    assert simulation.final_state.tick == 6
    assert attempted_imports == []
