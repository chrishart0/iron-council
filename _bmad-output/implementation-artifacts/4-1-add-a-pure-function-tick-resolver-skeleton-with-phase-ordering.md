# Story 4.1: Add a pure-function tick resolver skeleton with phase ordering

Status: backlog

## Story

As a game engine developer,
I want a resolver shell that advances the match through documented phases,
so that later resource, movement, combat, and victory logic plugs into a deterministic pipeline.

## Acceptance Criteria

1. Given a current state and validated order payload, when the resolver runs, then it returns a new state object and phase/event metadata without mutating the input state.
2. Given the documented phase order, when the resolver is instrumented, then resource, build, movement, combat, siege, attrition, diplomacy, and victory phases execute in the expected sequence.
3. Given placeholder phase handlers, when the resolver runs before full gameplay logic exists, then the skeleton still emits deterministic phase/event metadata suitable for future engine expansion.

## Tasks / Subtasks

- [ ] Add a public pure resolver entrypoint under `server/`. (AC: 1, 2, 3)
  - [ ] Introduce a `resolve_tick(...)` surface that accepts the current `MatchState` and validated orders.
  - [ ] Return a result object with next-state and ordered phase/event metadata.
- [ ] Define canonical phase ordering and metadata contracts. (AC: 1, 2, 3)
  - [ ] Encode the phase order: resource -> build -> movement -> combat -> siege -> attrition -> diplomacy -> victory.
  - [ ] Emit stable phase/event names that later engines can extend without changing the skeleton boundary.
- [ ] Keep the resolver pure while gameplay logic is still stubbed. (AC: 1, 3)
  - [ ] Copy the input state instead of mutating it in place.
  - [ ] Use no-op placeholder handlers that preserve determinism.
- [ ] Add behavior-first tests for resolver ordering and purity. (AC: 1, 2, 3)
  - [ ] Cover non-mutation of the input state.
  - [ ] Cover exact phase ordering in emitted metadata.
  - [ ] Cover deterministic repeated runs with the same state + orders.

## Dev Notes

- Keep scope intentionally narrow: build the orchestration shell, not the real resource/build/movement/combat engines.
- Reuse Story 3.2 order-validation output as the incoming validated-order boundary rather than revalidating inside the resolver.
- Prefer small public contracts that are easy to extend with richer event payloads in Story 4.2 and later engine stories.
- Avoid speculative abstractions; a simple ordered list of phase handlers is enough for the first skeleton.

### References

- `core-architecture.md` sections 4.1 to 4.3 for order collection and deterministic resolution sequencing.
- `core-architecture.md` phase diagram around the master resolver flow.
- `_bmad-output/planning-artifacts/epics.md` Story 4.1 acceptance criteria.

## Dev Agent Record

### Agent Model Used

Pending

### Debug Log References

- Pending

### Completion Notes List

- Pending

### File List

- `_bmad-output/implementation-artifacts/4-1-add-a-pure-function-tick-resolver-skeleton-with-phase-ordering.md`

### Change Log

- Created Story 4.1 implementation artifact.
