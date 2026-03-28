# Story 7.1: Resolve contested-city combat with defender and fortification advantages

Status: in-progress

## Story

As a game engine developer,
I want the combat phase to apply simultaneous deterministic casualties to opposing armies that share a city,
so that headless simulations can model frontline battles before diplomacy and full siege systems land.

## Acceptance Criteria

1. Given armies from different players occupying the same city at the start of the combat phase, when combat resolves, then each side takes deterministic simultaneous casualties derived from the opposing force and armies reduced to zero troops are removed from the next state.
2. Given one side qualifies as the city defender because it owns the contested city, when combat resolves in a fortified city, then the defending side receives the documented base defender bonus plus the city's fortification multiplier while attackers do not.
3. Given identical starting states and contested armies, when the combat phase resolves repeatedly, then the resulting troop counts and surviving armies are identical and the caller-owned `MatchState` remains unchanged.

## Tasks / Subtasks

- [ ] Add behavior-first combat coverage before implementation. (AC: 1, 2, 3)
  - [ ] Cover simultaneous casualties for contested cities with one army per side.
  - [ ] Cover defender bonus plus fortification multiplier on a city-owned defender.
  - [ ] Cover zero-troop removal and deterministic repeated resolution.
- [ ] Implement narrow combat-phase casualty resolution. (AC: 1, 2, 3)
  - [ ] Keep scope to city-level contested armies already co-located after movement.
  - [ ] Apply deterministic integer casualty math with no randomness.
  - [ ] Preserve resolver purity and the stable `phase.combat.completed` event contract.
- [ ] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [ ] Re-run focused resolver coverage.
  - [ ] Re-run the repository quality gate.

## Dev Notes

- Keep this story intentionally narrow: do not add capture, siege, diplomacy, or garrison-combat rules yet.
- Prefer resolver/simulation boundary tests over helper-only tests.
- Use the documented defender advantage (`1.2x`) and fortification tiers from `core-plan.md` section 6.2 and 5.1.

### References

- `core-plan.md` sections 5.1 and 6.2 for fortification and combat rules.
- `core-architecture.md` sections 4.1 and 4.2 for phase ordering and deterministic simultaneous resolution.
- `_bmad-output/planning-artifacts/epics.md` Story 7.1 acceptance criteria.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Pending implementation.

### Completion Notes List

- Pending implementation.

### File List

- `_bmad-output/implementation-artifacts/7-1-resolve-contested-city-combat-with-defender-and-fortification-advantages.md`

### Change Log

- 2026-03-28 11:22 UTC: Drafted Story 7.1 for deterministic contested-city combat resolution.
