# Story 8.1: Advance build queues and complete deterministic city upgrades during the build phase

Status: drafted

## Story

As a game engine developer,
I want the build phase to progress queued upgrades and finish them deterministically,
so that economy, military, and fortification investments persist across ticks instead of remaining inert validated orders.

## Acceptance Criteria

1. Given a city with an in-progress building queue item, when the build phase runs, then `ticks_remaining` decrements deterministically and completed items apply their target upgrade tier to the copied next state.
2. Given accepted upgrade orders for player-owned cities with no conflicting queue on the same track, when the build phase runs, then each accepted order starts a deterministic queue item and deducts the documented production cost exactly once from the copied next state.
3. Given identical starting states and accepted upgrade orders, when the build phase resolves repeatedly, then queue progression, completed upgrade tiers, player resources, and the caller-owned `MatchState` remain deterministic and unmutated.

## Tasks / Subtasks

- [ ] Add behavior-first resolver coverage before implementation. (AC: 1, 2, 3)
  - [ ] Cover in-progress queue decrement and deterministic completion into the city upgrade state.
  - [ ] Cover accepted upgrade orders creating queue items and deducting production exactly once.
  - [ ] Cover repeated runs and input-state immutability.
- [ ] Implement narrow build-phase queue progression. (AC: 1, 2, 3)
  - [ ] Keep scope to upgrade queues only; do not add recruitment, transfers, siege, or diplomacy rules in this story.
  - [ ] Reuse the documented upgrade cost table rather than duplicating production pricing logic.
  - [ ] Keep queue progression deterministic and compatible with the existing pure-function resolver contract.
- [ ] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [ ] Re-run focused resolver coverage.
  - [ ] Re-run the repository quality gate.

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

- Pending.

### Completion Notes List

- Pending.

### File List

- `_bmad-output/implementation-artifacts/8-1-advance-build-queues-and-complete-deterministic-city-upgrades-during-the-build-phase.md`

### Change Log

- 2026-03-28 12:24 UTC: Drafted Story 8.1 for deterministic build-queue progression and city-upgrade completion.
