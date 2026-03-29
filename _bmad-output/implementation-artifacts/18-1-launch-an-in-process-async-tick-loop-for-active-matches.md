# Story 18.1: Launch an in-process async tick loop for active matches

Status: done

## Story

As a game server operator,
I want active matches to advance on their configured interval without an HTTP trigger,
So that the running service behaves like a real tick-based simulation instead of a static contract mock.

## Acceptance Criteria

1. Given the FastAPI app starts with one or more active matches in the registry, when the server lifespan begins, then it launches one background loop per active match that sleeps by the match tick interval and advances only that match state on schedule.
2. Given agents have already submitted validated orders for the current tick, when the loop advances the match, then it resolves the next tick from the existing pure-function engine, consumes the queued submissions for that tick, increments the canonical match tick, and leaves later ticks' submissions untouched.
3. Given developers need confidence at the public boundary, when the story ships, then behavior-first tests cover lifecycle startup/shutdown plus a small real-process API smoke proving an active match tick advances without any manual endpoint call.

## Tasks / Subtasks

- [x] Add a runtime tick service abstraction that can start and stop per-match background loops from the FastAPI lifespan. (AC: 1)
- [x] Teach the match registry how to snapshot, resolve, and commit one active-match tick from queued submissions while keeping future-tick submissions intact. (AC: 1, 2)
- [x] Wire startup/shutdown lifecycle management in `server.main` without regressing existing API behavior. (AC: 1)
- [x] Add behavior-first unit/API coverage plus one running-process smoke for autonomous tick advancement. (AC: 2, 3)
- [x] Run simplification/review and refresh BMAD completion notes when the story ships. (AC: 3)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py tests/api/test_agent_api.py`
- `uv run pytest --override-ini addopts='' tests/e2e/test_api_smoke.py`
- `make quality`

### Completion Notes List

- Added `server.runtime.MatchRuntime` as a minimal per-active-match asyncio loop manager started and stopped through the FastAPI lifespan.
- Added `InMemoryMatchRegistry.advance_match_tick()` so runtime advancement reuses the existing order-validation and pure resolver path, increments the canonical tick, and consumes only current-tick submissions.
- Combined same-player same-tick submissions before validation so runtime advancement cannot overspend resources by validating envelopes independently against the same starting budget.
- Added lifecycle/API tests plus a real-process smoke that proves an active match advances automatically without any manual tick endpoint.
- Kept this story scoped to in-process runtime advancement only; persistence/tick-log work remains deferred to Story 18.2.

### File List

- _bmad-output/implementation-artifacts/18-1-launch-an-in-process-async-tick-loop-for-active-matches.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- server/agent_registry.py
- server/main.py
- server/runtime.py
- tests/api/test_agent_api.py
- tests/conftest.py
- tests/e2e/test_api_smoke.py
- tests/test_agent_registry.py

### Change Log

- 2026-03-29 22:25 UTC: Drafted Epic 18 and Story 18.1 for the live runtime loop.
- 2026-03-29 22:52 UTC: Implemented the in-process runtime loop, match tick advancement path, lifecycle coverage, and running-app smoke validation.
- 2026-03-29 23:05 UTC: Fixed duplicate same-player submission validation so runtime tick advancement combines same-tick envelopes before validation.

## Dev Notes

- This story intentionally stops at in-process runtime advancement. Durable DB persistence and tick-log history belong to Story 18.2; WebSocket fanout belongs to Story 18.3.
- Reuse the existing pure resolver and order-validation pipeline; do not create a second tick-resolution path for runtime.
- Preserve the current agent polling/write endpoints while the background loop is running.
- Prefer small, explicit lifecycle objects over clever task orchestration. A single-process local-dev-safe implementation is the goal.

## Implementation Plan

### Parallelism assessment

- **Sequential core path:** registry tick-advance semantics, runtime loop, and FastAPI lifespan wiring all touch the same runtime boundary and should stay in one worker.
- **Safe parallel work this run:** review can happen in separate reviewer subagents after the implementation worker finishes. No second coding worker is justified because the core files overlap heavily (`server/main.py`, registry/runtime support, runtime tests).

### File targets

- Modify: `server/agent_registry.py`
- Create: `server/runtime.py`
- Modify: `server/main.py`
- Add/modify tests near the public boundary, likely under `tests/api/` and `tests/e2e/`

### Verification targets

- Focused red/green loop with repo coverage addopts overridden as needed.
- Real command path for the story’s running-app smoke.
- Final repo gate at least `make quality` before merge.
