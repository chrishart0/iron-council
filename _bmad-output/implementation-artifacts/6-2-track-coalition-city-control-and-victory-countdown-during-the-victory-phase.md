# Story 6.2: Track coalition city control and victory countdown during the victory phase

Status: drafted

## Story

As a game engine developer,
I want the victory phase to count coalition-controlled cities and manage a countdown,
so that simulations can expose an explicit endgame race before combat, siege, and diplomacy are fully implemented.

## Acceptance Criteria

1. Given city ownership and player alliance membership in the canonical match state, when the victory phase runs, then it groups owned cities by alliance-or-solo coalition, sets `VictoryState.leading_alliance`, and records the leading coalition's controlled city count.
2. Given a coalition meeting or exceeding the configured city threshold, when the victory phase runs on consecutive ticks, then `countdown_ticks_remaining` starts, decreases deterministically while the coalition stays above threshold, and clears if control drops below threshold or the leader changes.
3. Given repeated runs from the same starting state and coalition ownership layout, when the victory phase resolves, then the resulting victory metadata is deterministic and the caller-owned `MatchState` remains unchanged.

## Tasks / Subtasks

- [ ] Add behavior-first victory coverage before implementation. (AC: 1, 2, 3)
  - [ ] Cover coalition grouping for allied and solo players.
  - [ ] Cover countdown start, continuation, and reset cases.
  - [ ] Cover deterministic repeated resolution from the same starting state.
- [ ] Implement deterministic victory-phase coalition counting. (AC: 1, 2, 3)
  - [ ] Reuse canonical player alliance IDs without introducing new alliance models yet.
  - [ ] Keep countdown semantics explicit and easy to test.
  - [ ] Preserve the stable `phase.victory.completed` event contract.
- [ ] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [ ] Re-run focused resolver and simulation coverage.
  - [ ] Re-run the repository quality gate.

## Dev Notes

- Treat players without an alliance as their own solo coalition keyed by player ID.
- Keep scope intentionally narrow: update victory metadata only; do not add match-complete status or chat/broadcast side effects yet.
- Prefer resolver/simulation boundary tests over helper-only tests.

### References

- `core-plan.md` section 8.1 for coalition victory and countdown behavior.
- `core-architecture.md` sections 3.2 and 4.1 for canonical victory state shape and phase responsibilities.
- `_bmad-output/planning-artifacts/epics.md` Story 6.2 acceptance criteria.

## Dev Agent Record

### Agent Model Used

_Not started yet._

### Debug Log References

- _Pending implementation._

### Completion Notes List

- _Pending implementation._

### File List

- `_bmad-output/implementation-artifacts/6-2-track-coalition-city-control-and-victory-countdown-during-the-victory-phase.md`

### Change Log

- 2026-03-28 10:25 UTC: Drafted Story 6.2 for coalition control and victory countdown tracking.
