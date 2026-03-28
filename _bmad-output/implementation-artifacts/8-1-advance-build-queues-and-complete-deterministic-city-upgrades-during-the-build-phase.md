# Story 8.1: Advance build queues and complete deterministic city upgrades during the build phase

Status: done

## Story

As a game engine developer,
I want the build phase to progress queued upgrades and finish them deterministically,
so that economy, military, and fortification investments persist across ticks instead of remaining inert validated orders.

## Acceptance Criteria

1. Given a city with an in-progress building queue item, when the build phase runs, then `ticks_remaining` decrements deterministically and completed items apply their target upgrade tier to the copied next state.
2. Given accepted upgrade orders for player-owned cities with no conflicting queue on the same track, when the build phase runs, then each accepted order starts a deterministic queue item and deducts the documented production cost exactly once from the copied next state.
3. Given identical starting states and accepted upgrade orders, when the build phase resolves repeatedly, then queue progression, completed upgrade tiers, player resources, and the caller-owned `MatchState` remain deterministic and unmutated.

## Tasks / Subtasks

- [x] Add behavior-first resolver coverage before implementation. (AC: 1, 2, 3)
  - [x] Cover in-progress queue decrement and deterministic completion into the city upgrade state.
  - [x] Cover accepted upgrade orders creating queue items and deducting production exactly once.
  - [x] Cover repeated runs and input-state immutability.
- [x] Implement narrow build-phase queue progression. (AC: 1, 2, 3)
  - [x] Keep scope to upgrade queues only; do not add recruitment, transfers, siege, or diplomacy rules in this story.
  - [x] Reuse the documented upgrade cost table rather than duplicating production pricing logic.
  - [x] Keep queue progression deterministic and compatible with the existing pure-function resolver contract.
- [x] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [x] Re-run focused resolver coverage.
  - [x] Re-run the repository quality gate.

## Dev Notes

- Prefer resolver-boundary tests over helper-only tests.
- Keep build durations simple and explicit in code; avoid speculative production-speed mechanics that are not yet specified in the core docs.
- Preserve the existing `phase.build.completed` event contract.

### References

- `core-plan.md` sections 5.1 and 5.2 for upgrade-track behavior.
- `core-architecture.md` sections 4.1, 4.2, and 4.3 for build-phase ordering and deterministic resolution.
- `_bmad-output/planning-artifacts/epics.md` Story 8.1 acceptance criteria.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- RED: `uv run pytest tests/test_resolver.py -k 'build_phase' -q` -> failed on the new build-phase assertions before resolver implementation.
- RED (env): `uv run pytest tests/test_resolver.py -k 'build_phase' -q` -> failed before collection until dev dependencies were synced because `pytest-cov` from repo `addopts` was not yet installed in `.venv`.
- Setup: `uv sync --extra dev --frozen`
- GREEN (focused TDD): `uv run pytest tests/test_resolver.py -k 'build_phase' --override-ini addopts='-q --strict-config --strict-markers'`
- Targeted verification: `uv run pytest tests/test_resolver.py --override-ini addopts='-q --strict-config --strict-markers'`
- Quality gate: `make quality`

### Completion Notes List

- Added resolver-boundary coverage for build-phase queue decrement/completion, accepted upgrade queue creation with one-time production spending, and deterministic purity against repeated runs.
- Implemented build-phase upgrade queue progression only: existing queue items decrement each tick, completed items apply their tier onto the copied city upgrade state, and accepted upgrade orders start deterministic queue items.
- Reused `server.order_validation.UPGRADE_COSTS` for production deductions instead of duplicating pricing logic.
- Kept build durations explicit and simple as tier-based tick counts for this story, without adding speculative production-speed or parallel-system behavior.
- Preserved resolver purity and the existing `phase.build.completed` event contract.

### File List

- `_bmad-output/implementation-artifacts/8-1-advance-build-queues-and-complete-deterministic-city-upgrades-during-the-build-phase.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/resolver.py`
- `tests/test_resolver.py`

### Change Log

- 2026-03-28 12:24 UTC: Drafted Story 8.1 for deterministic build-queue progression and city-upgrade completion.
- 2026-03-28 12:24 UTC: Implemented deterministic build-phase upgrade queue progression/completion, added resolver-boundary coverage, and verified with `make quality`.
