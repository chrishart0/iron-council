# Story 9.2: Degrade besieged fortifications when hostile control seals every adjacent route

Status: ready

## Story

As a game engine developer,
I want the siege phase to recognize fully surrounded fortified cities and wear down their defenses,
so that entrenched defenders become vulnerable when attackers isolate every adjacent approach.

## Acceptance Criteria

1. Given a fortified city whose owner is different from the owner of every adjacent city on the map, when the siege phase runs, then the city's fortification tier drops by exactly one level in the copied next state.
2. Given a fortified city that still has at least one adjacent city owned by its controller or by an allied coalition member, when the siege phase runs, then the fortification tier does not degrade from siege pressure.
3. Given repeated runs from the same starting state and adjacency ownership layout, when the siege phase resolves, then the resulting fortification tiers are deterministic and the caller-owned `MatchState` remains unchanged.

## Tasks / Subtasks

- [ ] Add behavior-first resolver coverage before implementation. (AC: 1, 2, 3)
  - [ ] Cover deterministic siege degradation for a fully surrounded fortified city.
  - [ ] Cover the non-besieged case when a friendly or allied adjacent city keeps a route open.
  - [ ] Cover repeated runs and input-state immutability.
- [ ] Implement narrow siege-phase encirclement handling. (AC: 1, 2, 3)
  - [ ] Keep scope to fortification wear from encirclement only; do not add food-transfer blocking, fog changes, or diplomatic side effects in this story.
  - [ ] Reuse canonical map adjacency and current alliance membership from match state.
  - [ ] Keep siege checks deterministic and independent of dictionary insertion order.
- [ ] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [ ] Re-run focused resolver coverage.
  - [ ] Re-run the repository quality gate.

## Dev Notes

- Prefer resolver-boundary tests over helper-only tests.
- Treat neutral cities and enemy-controlled cities as hostile blockers for siege purposes unless the city owner also owns them.
- Keep the first siege model intentionally narrow: wear down fortification tiers without introducing persistent siege-status state.

### References

- `core-plan.md` sections 6.3 and 8.1 for siege behavior and endgame pressure.
- `core-architecture.md` section 4.3 for siege-phase responsibilities.
- `_bmad-output/planning-artifacts/epics.md` Story 9.2 acceptance criteria.

## Dev Agent Record

### Agent Model Used

_GPT-5 Codex_

### Debug Log References

- _To be filled during implementation._

### Completion Notes List

- _To be filled during implementation._

### File List

- `_bmad-output/implementation-artifacts/9-2-degrade-besieged-fortifications-when-hostile-control-seals-every-adjacent-route.md`

### Change Log

- 2026-03-28 13:35 UTC: Drafted Story 9.2 for deterministic siege-phase fortification degradation.
