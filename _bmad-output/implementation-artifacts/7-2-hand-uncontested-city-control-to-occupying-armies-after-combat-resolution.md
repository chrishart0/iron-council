# Story 7.2: Hand uncontested city control to occupying armies after combat resolution

Status: drafted

## Story

As a game engine developer,
I want the resolver to update city ownership when exactly one surviving force occupies a city after movement and combat,
so that match state, economy, and victory tracking reflect territorial gains without waiting for later API work.

## Acceptance Criteria

1. Given a neutral or enemy-owned city containing armies from exactly one surviving player after combat resolution, when the tick finishes the combat phase, then the city owner changes to that occupying player in the copied next state.
2. Given a contested city that still contains surviving armies from multiple players, when the combat phase completes, then ownership does not change until only one force remains.
3. Given repeated runs from the same starting state and occupying armies, when the ownership handoff resolves, then the resulting city owners are deterministic and the caller-owned `MatchState` remains unchanged.

## Tasks / Subtasks

- [ ] Add behavior-first occupancy and ownership-handoff coverage before implementation. (AC: 1, 2, 3)
  - [ ] Cover neutral-city occupation by a single survivor.
  - [ ] Cover enemy-city occupation after defenders are gone.
  - [ ] Cover contested survivors leaving ownership unchanged.
- [ ] Implement narrow post-combat ownership updates. (AC: 1, 2, 3)
  - [ ] Limit scope to cities with exactly one surviving occupying player.
  - [ ] Avoid expanding capture timers, loyalty mechanics, or siege markers.
  - [ ] Preserve resolver purity and existing phase event contracts.
- [ ] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [ ] Re-run focused resolver and simulation coverage.
  - [ ] Re-run the repository quality gate.

## Dev Notes

- Sequence after Story 7.1 so combat has already reduced contested stacks before ownership changes.
- Keep scope intentionally narrow: no morale, fog, diplomacy, or delayed capture rules yet.
- Prefer resolver/simulation boundary tests over helper-only tests.

### References

- `core-plan.md` sections 3.1, 3.2, and 6.2 for territorial control and city occupation context.
- `core-architecture.md` sections 3.2 and 4.2 for canonical city ownership state and tick resolution ordering.
- `_bmad-output/planning-artifacts/epics.md` Story 7.2 acceptance criteria.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Pending implementation.

### Completion Notes List

- Pending implementation.

### File List

- `_bmad-output/implementation-artifacts/7-2-hand-uncontested-city-control-to-occupying-armies-after-combat-resolution.md`

### Change Log

- 2026-03-28 11:22 UTC: Drafted Story 7.2 for deterministic post-combat city ownership handoff.
