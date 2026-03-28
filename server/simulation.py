from __future__ import annotations

from typing import Protocol

from server.models.domain import StrictModel
from server.models.orders import OrderBatch
from server.models.state import MatchState
from server.resolver import TickPhaseEvent, TickPhaseMetadata, resolve_tick


class OrderProvider(Protocol):
    def __call__(self, *, tick: int, state: MatchState) -> OrderBatch: ...


class SimulatedTick(StrictModel):
    tick: int
    snapshot: MatchState
    phases: list[TickPhaseMetadata]
    events: list[TickPhaseEvent]


class SimulationResult(StrictModel):
    ticks: list[SimulatedTick]
    final_state: MatchState


def simulate_ticks(
    initial_state: MatchState,
    *,
    ticks: int,
    orders: OrderBatch | None = None,
    order_provider: OrderProvider | None = None,
) -> SimulationResult:
    if ticks < 0:
        raise ValueError("ticks must be non-negative")
    if orders is not None and order_provider is not None:
        raise ValueError("pass either static orders or an order provider, not both")

    current_state = initial_state.model_copy(deep=True)
    simulated_ticks: list[SimulatedTick] = []
    static_orders = orders.model_copy(deep=True) if orders is not None else OrderBatch()

    for _ in range(ticks):
        tick_orders = (
            order_provider(
                tick=current_state.tick,
                state=current_state.model_copy(deep=True),
            ).model_copy(deep=True)
            if order_provider is not None
            else static_orders.model_copy(deep=True)
        )
        resolution = resolve_tick(current_state, tick_orders)
        next_state = resolution.next_state.model_copy(update={"tick": current_state.tick + 1})
        simulated_ticks.append(
            SimulatedTick(
                tick=next_state.tick,
                snapshot=next_state.model_copy(deep=True),
                phases=list(resolution.phases),
                events=list(resolution.events),
            )
        )
        current_state = next_state

    return SimulationResult(ticks=simulated_ticks, final_state=current_state)
