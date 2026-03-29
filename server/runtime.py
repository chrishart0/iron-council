from __future__ import annotations

import asyncio

from server.agent_registry import InMemoryMatchRegistry
from server.models.domain import MatchStatus


class MatchRuntime:
    def __init__(self, registry: InMemoryMatchRegistry) -> None:
        self._registry = registry
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
                self._registry.advance_match_tick(match_id)
        except asyncio.CancelledError:
            raise
