# Story 4.2: Provide a headless simulation harness for smoke testing ticks

Status: backlog

## Story

As a game engine developer,
I want a headless tick runner,
so that CI can execute basic match progression without web or database infrastructure.

## Acceptance Criteria

1. Given a minimal match fixture, when the headless simulation runner advances N ticks, then it returns deterministic state snapshots and ordered event logs for each tick.
2. Given identical initial state and order inputs, when the simulation is run repeatedly, then the resulting snapshots and logs are identical.
3. Given the resolver skeleton is still placeholder-driven, when the harness executes, then it depends only on pure in-process engine contracts and not on API, websocket, or database infrastructure.

## Tasks / Subtasks

- [ ] Add a public simulation entrypoint under `server/`. (AC: 1, 2, 3)
  - [ ] Introduce a `simulate_ticks(...)` surface that accepts an initial `MatchState` plus validated orders or an order provider.
  - [ ] Return a stable result object that includes per-tick state snapshots and ordered phase/event logs.
- [ ] Reuse the Story 4.1 resolver boundary instead of duplicating orchestration logic. (AC: 1, 2, 3)
  - [ ] Call `resolve_tick(...)` once per simulated tick.
  - [ ] Preserve deterministic ordering in all accumulated outputs.
- [ ] Keep the simulation harness headless and side-effect free. (AC: 1, 2, 3)
  - [ ] Avoid FastAPI app state, websockets, persistence, or timers.
  - [ ] Keep the harness usable directly from tests and future bot simulations.
- [ ] Add behavior-first tests for deterministic multi-tick simulation. (AC: 1, 2, 3)
  - [ ] Cover exact tick counts and ordered outputs.
  - [ ] Cover deterministic repeated runs.
  - [ ] Cover the absence of external infrastructure requirements.

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

Pending

### Debug Log References

- Pending

### Completion Notes List

- Pending

### File List

- `_bmad-output/implementation-artifacts/4-2-provide-a-headless-simulation-harness-for-smoke-testing-ticks.md`

### Change Log

- Created Story 4.2 implementation artifact.
