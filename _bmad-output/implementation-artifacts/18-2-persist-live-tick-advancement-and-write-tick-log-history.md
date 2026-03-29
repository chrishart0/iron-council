# Story 18.2: Persist live tick advancement and write tick-log history

Status: done

## Story

As a game server operator,
I want runtime tick advancement to update the database durably,
So that active matches can resume after a restart and expose auditable tick history.

## Acceptance Criteria

1. Given the app runs against the database-backed registry, when an active match advances a tick, then the latest match state and current tick are persisted back to the `matches` table.
2. Given debugging and replay require historical state, when each runtime tick completes, then the server writes a `tick_log` row containing the resolved tick number, state snapshot, accepted orders, and emitted events.
3. Given runtime durability should not break local workflows, when the persistence path is verified, then running-app tests exercise the real service boundary against migrated seeded data and confirm the persisted state survives a registry reload.

## Tasks / Subtasks

- [x] Add a registry tick-advance result contract that exposes the resolved tick, next state, accepted orders, and emitted events without re-running resolution. (AC: 1, 2)
- [x] Add a database persistence helper that updates `matches.current_tick` / `matches.state` and appends one `tick_log` row in a single transaction. (AC: 1, 2)
- [x] Wire the runtime loop to persist completed ticks only for the DB-backed app path while preserving current in-memory behavior. (AC: 1)
- [x] Add focused DB tests plus running-app smoke coverage that proves a persisted tick survives a fresh registry reload. (AC: 2, 3)
- [x] Run simplification/review and refresh BMAD completion notes when the story ships. (AC: 3)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py`
- `uv run pytest --no-cov tests/e2e/test_api_smoke.py -k active_match_ticks_forward_without_manual_advance_endpoint`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py tests/test_db_registry.py`
- `uv run pytest --no-cov tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py`
- `make quality`

### Completion Notes List

- Added `AdvancedMatchTick` so the registry exposes the resolved tick number, next state, accepted orders, and emitted resolver events without re-running resolution.
- Added `persist_advanced_match_tick()` as one explicit transactional DB seam that updates `matches.current_tick`, replaces `matches.state`, and appends one `tick_log` row per completed runtime tick.
- Wired `MatchRuntime` with an optional persistence callback and enabled it only for the default DB-backed app startup path, leaving explicit in-memory `create_app(match_registry=...)` workflows unchanged.
- Added focused registry/DB tests and real-process smoke coverage proving a runtime-advanced DB-backed match persists and survives a fresh registry reload.
- Kept Story 18.2 scoped to durability only; broadcast fanout remains deferred to Story 18.3.

### File List

- _bmad-output/implementation-artifacts/18-2-persist-live-tick-advancement-and-write-tick-log-history.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- server/agent_registry.py
- server/db/registry.py
- server/main.py
- server/runtime.py
- tests/conftest.py
- tests/e2e/test_api_smoke.py
- tests/support.py
- tests/test_agent_registry.py
- tests/test_db_registry.py

### Change Log

- 2026-03-29 22:25 UTC: Drafted Story 18.2 and the live tick persistence implementation plan.
- 2026-03-29 23:14 UTC: Implemented the advanced tick contract, transactional DB persistence seam, DB-backed runtime wiring, focused tests, and running-process reload coverage.

## Dev Notes

- Reuse the existing pure resolver and current runtime loop; do not introduce a second tick-resolution path.
- Keep the persistence seam explicit and boring: one completed tick in memory, one transactional write to `matches` + `tick_log`.
- Preserve local dev ergonomics and DB-backed smoke coverage using the existing migrated/seeded database fixtures.
- Story 18.3 depends on this story’s persisted runtime contract and should remain deferred until 18.2 is complete.

## Implementation Plan

- Plan file: `docs/plans/2026-03-29-story-18-2-live-tick-persistence.md`
- Parallelism assessment: implementation is sequential because the runtime/persistence seam overlaps heavily; spec review and code-quality review can run in parallel after the worker finishes.
- Verification target: focused registry + DB tests, running-app no-cov API/smoke tests, then `make quality`.
