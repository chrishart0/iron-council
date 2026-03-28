"""Iron Council server package."""

from server.resolver import (
    PHASE_ORDER,
    TickPhaseEvent,
    TickPhaseMetadata,
    TickResolutionResult,
    resolve_tick,
)
from server.simulation import SimulatedTick, SimulationResult, simulate_ticks

__all__ = [
    "PHASE_ORDER",
    "SimulatedTick",
    "SimulationResult",
    "TickPhaseEvent",
    "TickPhaseMetadata",
    "TickResolutionResult",
    "__version__",
    "resolve_tick",
    "simulate_ticks",
]

__version__ = "0.1.0"
