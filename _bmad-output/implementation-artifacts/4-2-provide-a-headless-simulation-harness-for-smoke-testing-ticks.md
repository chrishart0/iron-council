# Story 4.2: Provide a headless simulation harness for smoke testing ticks

Status: done

## Story

As a game engine developer,
I want a headless tick runner,
so that CI can execute basic match progression without web or database infrastructure.

## Acceptance Criteria

1. Given a minimal match fixture, when the headless simulation runner advances N ticks, then it returns deterministic state snapshots and ordered event logs for each tick.
2. Given identical initial state and order inputs, when the simulation is run repeatedly, then the resulting snapshots and logs are identical.
3. Given the resolver skeleton is still placeholder-driven, when the harness executes, then it depends only on pure in-process engine contracts and not on API, websocket, or database infrastructure.

## Tasks / Subtasks

- [x] Add a public simulation entrypoint under `server/`. (AC: 1, 2, 3)
  - [x] Introduce a `simulate_ticks(...)` surface that accepts an initial `MatchState` plus validated orders or an order provider.
  - [x] Return a stable result object that includes per-tick state snapshots and ordered phase/event logs.
- [x] Reuse the Story 4.1 resolver boundary instead of duplicating orchestration logic. (AC: 1, 2, 3)
  - [x] Call `resolve_tick(...)` once per simulated tick.
  - [x] Preserve deterministic ordering in all accumulated outputs.
- [x] Keep the simulation harness headless and side-effect free. (AC: 1, 2, 3)
  - [x] Avoid FastAPI app state, websockets, persistence, or timers.
  - [x] Keep the harness usable directly from tests and future bot simulations.
- [x] Add behavior-first tests for deterministic multi-tick simulation. (AC: 1, 2, 3)
  - [x] Cover exact tick counts and ordered outputs.
  - [x] Cover deterministic repeated runs.
  - [x] Cover the absence of external infrastructure requirements.

## Dev Notes

- Keep scope intentionally narrow: this story is about a smoke-testable runner, not real resource/combat rules.
- Prefer simple list-based snapshot and event-log outputs over speculative replay abstractions.
- Reuse Pydantic models and the pure-function resolver so future simulation and bot layers build on the same contract.

### References

- `core-plan.md` tick-loop overview and agent-per-tick contract sections.
- `core-architecture.md` sections 2.1 and 4.1 to 4.3 for the deterministic game loop and master resolver flow.
- `_bmad-output/planning-artifacts/epics.md` Story 4.2 acceptance criteria.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run --extra dev pytest tests/test_simulation.py -q -o addopts=''`
- `uv run --extra dev pytest tests/test_simulation.py tests/test_resolver.py -q -o addopts=''`
- `make format`
- `uv run ruff check tests/test_simulation.py --select I --fix`
- `make quality`

### Completion Notes List

- Added `server.simulation.simulate_ticks(...)` as a small public headless harness that loops the Story 4.1 resolver and advances `MatchState.tick` one step per simulated tick.
- Returned deterministic `SimulatedTick` snapshots plus ordered phase and event logs for each tick without introducing replay or persistence abstractions.
- Strengthened the contract surface with behavior-first coverage for rejected negative tick counts, mutually exclusive `orders` and `order_provider` inputs, and an explicit in-process-only execution check that guards against web or database imports during simulation.
- Tightened `order_provider` typing to a small named protocol so the callable contract is explicit without broadening the harness surface.
- Supported both static validated `OrderBatch` input and a simple per-tick order provider while keeping the harness side-effect free by copying caller-owned state and orders.
- Captured red-phase evidence with a focused simulation test run; the initial failure was `ImportError: cannot import name 'simulate_ticks' from 'server'`.
- Reverified the strengthened harness contract with a focused resolver/simulation suite and a full `make quality` pass.

### File List

- `server/__init__.py`
- `server/simulation.py`
- `tests/test_simulation.py`
- `_bmad-output/implementation-artifacts/4-2-provide-a-headless-simulation-harness-for-smoke-testing-ticks.md`

### Change Log

- Created Story 4.2 implementation artifact.
- Implemented the headless tick simulation harness, added behavior-first simulation tests, and marked Story 4.2 complete.
