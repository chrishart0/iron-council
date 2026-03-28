# Story 4.1: Add a pure-function tick resolver skeleton with phase ordering

Status: done

## Story

As a game engine developer,
I want a resolver shell that advances the match through documented phases,
so that later resource, movement, combat, and victory logic plugs into a deterministic pipeline.

## Acceptance Criteria

1. Given a current state and validated order payload, when the resolver runs, then it returns a new state object and phase/event metadata without mutating the input state.
2. Given the documented phase order, when the resolver is instrumented, then resource, build, movement, combat, siege, attrition, diplomacy, and victory phases execute in the expected sequence.
3. Given placeholder phase handlers, when the resolver runs before full gameplay logic exists, then the skeleton still emits deterministic phase/event metadata suitable for future engine expansion.

## Tasks / Subtasks

- [x] Add a public pure resolver entrypoint under `server/`. (AC: 1, 2, 3)
  - [x] Introduce a `resolve_tick(...)` surface that accepts the current `MatchState` and validated orders.
  - [x] Return a result object with next-state and ordered phase/event metadata.
- [x] Define canonical phase ordering and metadata contracts. (AC: 1, 2, 3)
  - [x] Encode the phase order: resource -> build -> movement -> combat -> siege -> attrition -> diplomacy -> victory.
  - [x] Emit stable phase/event names that later engines can extend without changing the skeleton boundary.
- [x] Keep the resolver pure while gameplay logic is still stubbed. (AC: 1, 3)
  - [x] Copy the input state instead of mutating it in place.
  - [x] Use no-op placeholder handlers that preserve determinism.
- [x] Add behavior-first tests for resolver ordering and purity. (AC: 1, 2, 3)
  - [x] Cover non-mutation of the input state.
  - [x] Cover exact phase ordering in emitted metadata.
  - [x] Cover deterministic repeated runs with the same state + orders.

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

GPT-5 Codex

### Debug Log References

- `uv run --extra dev pytest tests/test_resolver.py -q -o addopts=''`
- `make format`
- `uv run --extra dev pytest tests/test_resolver.py tests/test_order_validation.py -q -o addopts=''`
- `make quality`

### Completion Notes List

- Added `server.resolver.resolve_tick(...)` as the public pure-function tick resolver boundary using validated `OrderBatch` input from Story 3.2.
- Refactored the resolver to execute a deterministic ordered list of no-op placeholder phase handlers for resource, build, movement, combat, siege, attrition, diplomacy, and victory.
- Replaced the weakly typed `list[dict[str, str]]` event payloads with a typed `TickPhaseEvent` model while preserving the small resolver contract.
- Preserved input purity by deep-copying `MatchState` and returning a distinct next-state object without mutating the caller-owned state.
- Captured red-phase evidence with a focused resolver test run after adding the contract test; the first failure was `ModuleNotFoundError: No module named 'server.resolver'`.
- Captured follow-up red-phase evidence for the review refactor with a focused resolver test run; the first failure was `ImportError: cannot import name 'TickPhaseEvent' from 'server.resolver'`.
- Used `-o addopts=''` for focused pytest commands because the repo-level pytest config expects `pytest-cov`, which is only available when running with dev extras.
- Split the resolver contract coverage into focused behavior tests for purity, ordered typed phase events, and deterministic repeated runs while removing unnecessary order payload noise.

### File List

- `server/__init__.py`
- `server/resolver.py`
- `tests/test_resolver.py`
- `_bmad-output/implementation-artifacts/4-1-add-a-pure-function-tick-resolver-skeleton-with-phase-ordering.md`

### Change Log

- Created Story 4.1 implementation artifact.
- Implemented the pure tick resolver skeleton, added behavior-first resolver tests, and marked Story 4.1 complete.
- Refactored the resolver pipeline to use ordered placeholder handlers and typed phase events in response to Story 4.1 review feedback.
