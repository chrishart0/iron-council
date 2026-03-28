# Story 8.2: Process accepted recruitment orders during the build phase

Status: drafted

## Story

As a game engine developer,
I want the build phase to convert accepted recruitment orders into stationed armies,
so that validated troop purchases actually create military presence for later movement, combat, and attrition phases.

## Acceptance Criteria

1. Given accepted recruitment orders for player-owned cities, when the build phase runs, then each order deducts the documented food and production cost and creates or reinforces a stationed army for that player in the ordered city.
2. Given multiple accepted recruitment orders for the same player across different cities in one tick, when the build phase runs, then all accepted orders resolve deterministically without depending on list order side effects beyond the already-validated order set.
3. Given repeated runs from the same starting state and accepted recruitment orders, when the build phase resolves, then the resulting armies, city occupants, player resources, and the caller-owned `MatchState` remain deterministic and unmutated.

## Tasks / Subtasks

- [ ] Add behavior-first resolver coverage before implementation. (AC: 1, 2, 3)
  - [ ] Cover new stationed armies appearing for cities without a current army.
  - [ ] Cover deterministic reinforcement or co-location behavior for cities that already contain a friendly stationed army.
  - [ ] Cover repeated runs and input-state immutability.
- [ ] Implement narrow build-phase recruitment resolution. (AC: 1, 2, 3)
  - [ ] Keep scope to accepted recruitment orders only; do not add recruitment-capacity tuning, combat, or transfer-order behavior in this story.
  - [ ] Reuse the documented recruitment cost table rather than duplicating food/production pricing logic.
  - [ ] Keep army creation deterministic and compatible with the existing pure-function resolver contract.
- [ ] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [ ] Re-run focused resolver coverage.
  - [ ] Re-run the repository quality gate.

## Dev Notes

- Sequence after Story 8.1 so build-phase queue work remains stable before adding more state mutation to the same phase.
- Prefer resolver-boundary tests over helper-only tests.
- Preserve the existing `phase.build.completed` event contract.

### References

- `core-plan.md` sections 4.2, 5.1, and 6.1 for recruitment and army-state context.
- `core-architecture.md` sections 4.1, 4.2, and 4.3 for build-phase ordering and deterministic simultaneous resolution.
- `_bmad-output/planning-artifacts/epics.md` Story 8.2 acceptance criteria.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Pending.

### Completion Notes List

- Pending.

### File List

- `_bmad-output/implementation-artifacts/8-2-process-accepted-recruitment-orders-during-the-build-phase.md`

### Change Log

- 2026-03-28 12:24 UTC: Drafted Story 8.2 for deterministic build-phase recruitment execution.
