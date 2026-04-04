from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from server.agent_registry import (
    AdvancedMatchTick,
    InMemoryMatchRegistry,
    is_terminal_victory_tick,
)
from server.models.domain import MatchStatus


class MatchRuntime:
    def __init__(
        self,
        registry: InMemoryMatchRegistry,
        *,
        tick_persistence: Callable[[AdvancedMatchTick], None] | None = None,
        tick_broadcast: Callable[[AdvancedMatchTick], Awaitable[None]] | None = None,
        tick_observer: Callable[[str, int, int, float, float], None] | None = None,
    ) -> None:
        self._registry = registry
        self._tick_persistence = tick_persistence
        self._tick_broadcast = tick_broadcast
        self._tick_observer = tick_observer
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def start(self) -> None:
        for match in self._registry.list_matches():
            if match.status != MatchStatus.ACTIVE:
                continue
            self._ensure_match_task(match.match_id)

    async def ensure_match_running(self, match_id: str) -> None:
        match = self._registry.get_match(match_id)
        if match is None or match.status != MatchStatus.ACTIVE:
            return
        self._ensure_match_task(match_id)

    async def stop(self) -> None:
        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _ensure_match_task(self, match_id: str) -> None:
        existing_task = self._tasks.get(match_id)
        if existing_task is not None and not existing_task.done():
            return
        self._tasks[match_id] = asyncio.create_task(
            self._run_match_loop(match_id),
            name=f"match-runtime:{match_id}",
        )

    async def _run_match_loop(self, match_id: str) -> None:
        loop = asyncio.get_running_loop()
        next_tick_scheduled_at: float | None = None
        try:
            while True:
                match = self._registry.get_match(match_id)
                if match is None or match.status != MatchStatus.ACTIVE:
                    return
                if next_tick_scheduled_at is None:
                    next_tick_scheduled_at = loop.time() + match.tick_interval_seconds
                await asyncio.sleep(max(0.0, next_tick_scheduled_at - loop.time()))
                actual_tick_started_at = loop.time()
                tick_drift_seconds = max(0.0, actual_tick_started_at - next_tick_scheduled_at)
                match_snapshot = (
                    self._registry.snapshot_match(match_id)
                    if self._tick_persistence is not None
                    else None
                )
                advanced_tick = self._registry.advance_match_tick(match_id)
                is_terminal = is_terminal_victory_tick(advanced_tick)
                if self._tick_persistence is not None:
                    try:
                        self._tick_persistence(advanced_tick)
                    except Exception:
                        if match_snapshot is not None:
                            self._registry.restore_match(match_id, match_snapshot)
                        raise
                if is_terminal:
                    completed_match = self._registry.get_match(match_id)
                    if completed_match is not None:
                        completed_match.status = MatchStatus.COMPLETED
                if self._tick_broadcast is not None:
                    await self._tick_broadcast(advanced_tick)
                if self._tick_observer is not None:
                    self._tick_observer(
                        advanced_tick.match_id,
                        advanced_tick.resolved_tick,
                        match.tick_interval_seconds,
                        tick_drift_seconds,
                        max(0.0, loop.time() - actual_tick_started_at),
                    )
                if is_terminal:
                    return
                next_tick_scheduled_at += match.tick_interval_seconds
        except asyncio.CancelledError:
            raise
