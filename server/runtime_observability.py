from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from server.agent_registry import InMemoryMatchRegistry
from server.models.api import (
    RuntimeObservabilityFanoutStatus,
    RuntimeObservabilityMatchStatus,
    RuntimeObservabilityResponse,
    RuntimeObservabilityStartupRecovery,
    RuntimeObservabilityTickStatus,
    RuntimeObservabilityWebSocketStatus,
)
from server.models.domain import MatchStatus


@dataclass(slots=True)
class TickObservation:
    resolved_tick: int
    tick_interval_seconds: int
    drift_seconds: float
    processing_seconds: float
    observed_at: datetime


@dataclass(slots=True)
class FanoutObservation:
    attempted_connections: int
    delivered_connections: int
    dropped_connections: int
    observed_at: datetime


class RuntimeObservability:
    def __init__(self, registry: InMemoryMatchRegistry) -> None:
        self._registry = registry
        self._startup_recovery: RuntimeObservabilityStartupRecovery | None = None
        self._tick_observations: dict[str, TickObservation] = {}
        self._fanout_observations: dict[str, FanoutObservation] = {}

    def record_startup_recovery(self) -> None:
        recovered_matches = []
        for match in sorted(self._registry.list_matches(), key=lambda match: match.match_id):
            if match.status != MatchStatus.ACTIVE:
                continue
            recovered_matches.append(
                RuntimeObservabilityMatchStatus(
                    match_id=match.match_id,
                    status=match.status,
                    tick=match.state.tick,
                    tick_interval_seconds=match.tick_interval_seconds,
                    last_tick=None,
                    websocket=RuntimeObservabilityWebSocketStatus(
                        connection_count=0,
                        last_fanout=None,
                    ),
                )
            )

        self._startup_recovery = RuntimeObservabilityStartupRecovery(
            recorded_at=datetime.now(UTC),
            resumed_active_match_count=len(recovered_matches),
            resumed_active_matches=recovered_matches,
        )

    def record_tick(
        self,
        *,
        match_id: str,
        resolved_tick: int,
        tick_interval_seconds: int,
        drift_seconds: float,
        processing_seconds: float,
    ) -> None:
        self._tick_observations[match_id] = TickObservation(
            resolved_tick=resolved_tick,
            tick_interval_seconds=tick_interval_seconds,
            drift_seconds=max(drift_seconds, 0.0),
            processing_seconds=max(processing_seconds, 0.0),
            observed_at=datetime.now(UTC),
        )

    def record_fanout(
        self,
        *,
        match_id: str,
        attempted_connections: int,
        delivered_connections: int,
        dropped_connections: int,
    ) -> None:
        self._fanout_observations[match_id] = FanoutObservation(
            attempted_connections=attempted_connections,
            delivered_connections=delivered_connections,
            dropped_connections=dropped_connections,
            observed_at=datetime.now(UTC),
        )

    def build_response(
        self, *, websocket_connection_counts: dict[str, int]
    ) -> RuntimeObservabilityResponse:
        matches = []
        for match in sorted(self._registry.list_matches(), key=lambda match: match.match_id):
            tick_observation = self._tick_observations.get(match.match_id)
            fanout_observation = self._fanout_observations.get(match.match_id)
            matches.append(
                RuntimeObservabilityMatchStatus(
                    match_id=match.match_id,
                    status=match.status,
                    tick=match.state.tick,
                    tick_interval_seconds=match.tick_interval_seconds,
                    last_tick=(
                        RuntimeObservabilityTickStatus(
                            resolved_tick=tick_observation.resolved_tick,
                            expected_interval_seconds=tick_observation.tick_interval_seconds,
                            drift_seconds=round(tick_observation.drift_seconds, 6),
                            processing_seconds=round(tick_observation.processing_seconds, 6),
                            observed_at=tick_observation.observed_at,
                        )
                        if tick_observation is not None
                        else None
                    ),
                    websocket=RuntimeObservabilityWebSocketStatus(
                        connection_count=websocket_connection_counts.get(match.match_id, 0),
                        last_fanout=(
                            RuntimeObservabilityFanoutStatus(
                                attempted_connections=fanout_observation.attempted_connections,
                                delivered_connections=fanout_observation.delivered_connections,
                                dropped_connections=fanout_observation.dropped_connections,
                                observed_at=fanout_observation.observed_at,
                            )
                            if fanout_observation is not None
                            else None
                        ),
                    ),
                )
            )

        return RuntimeObservabilityResponse(
            status="ok",
            startup_recovery=self._startup_recovery,
            matches=matches,
        )
