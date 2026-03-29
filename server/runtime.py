from __future__ import annotations

import asyncio
from collections.abc import Callable

from server.agent_registry import AdvancedMatchTick, InMemoryMatchRegistry
from server.models.domain import MatchStatus


class MatchRuntime:
    def __init__(
        self,
        registry: InMemoryMatchRegistry,
        *,
        tick_persistence: Callable[[AdvancedMatchTick], None] | None = None,
    ) -> None:
        self._registry = registry
        self._tick_persistence = tick_persistence
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def start(self) -> None:
        for match in self._registry.list_matches():
            if match.status != MatchStatus.ACTIVE:
                continue
            self._tasks[match.match_id] = asyncio.create_task(
                self._run_match_loop(match.match_id),
                name=f"match-runtime:{match.match_id}",
            )

    async def stop(self) -> None:
        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_match_loop(self, match_id: str) -> None:
        try:
            while True:
                match = self._registry.get_match(match_id)
                if match is None or match.status != MatchStatus.ACTIVE:
                    return
                await asyncio.sleep(match.tick_interval_seconds)
                match_snapshot = (
                    self._registry.snapshot_match(match_id)
                    if self._tick_persistence is not None
                    else None
                )
                advanced_tick = self._registry.advance_match_tick(match_id)
                if self._tick_persistence is not None:
                    try:
                        self._tick_persistence(advanced_tick)
                    except Exception:
                        if match_snapshot is not None:
                            self._registry.restore_match(match_id, match_snapshot)
                        raise
        except asyncio.CancelledError:
            raise
