"""Iron Council server package."""

from server.resolver import PHASE_ORDER, TickPhaseMetadata, TickResolutionResult, resolve_tick

__all__ = [
    "PHASE_ORDER",
    "TickPhaseMetadata",
    "TickResolutionResult",
    "__version__",
    "resolve_tick",
]

__version__ = "0.1.0"
