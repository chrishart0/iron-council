# Story 6.1: Apply starvation attrition and elimination checks during the attrition phase

Status: done

## Story

As a game engine developer,
I want the attrition phase to shrink starving armies and flag defeated players,
so that resource shortages and lost territory create deterministic consequences in headless simulations.

## Acceptance Criteria

1. Given players whose food stockpile is zero after the resource phase, when the attrition phase runs, then each of their armies loses deterministic starvation casualties and any army reduced to zero is removed from the next state.
2. Given players with no owned cities and no surviving armies after attrition resolution, when the attrition phase completes, then those players are marked eliminated while players that still have territory or armies remain active.
3. Given identical starting states with the same starvation conditions, when attrition resolves repeatedly, then the casualty and elimination outcomes are identical and the caller-owned `MatchState` remains unchanged.

## Tasks / Subtasks

- [x] Add behavior-first attrition coverage before implementation. (AC: 1, 2, 3)
  - [x] Cover starvation casualties only for players at zero food.
  - [x] Cover removal of armies reduced to zero troops.
  - [x] Cover elimination status updates after attrition settles.
- [x] Implement deterministic attrition-phase starvation logic. (AC: 1, 2, 3)
  - [x] Keep the resolver pure by mutating only the copied next-state.
  - [x] Use a small fixed starvation casualty rule and document the scope in code/story notes.
  - [x] Preserve the stable `phase.attrition.completed` event contract.
- [x] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [x] Re-run focused resolver and simulation coverage.
  - [x] Re-run the repository quality gate.

## Dev Notes

- Keep this story intentionally narrow: starvation attrition only, without fortification decay or siege interaction.
- Prefer tests at the resolver/simulation boundary instead of helper-only unit tests.
- Use canonical city ownership as the elimination source of truth; `PlayerState.cities_owned` remains derivative metadata for now.

### References

- `core-plan.md` section 4.3 for starvation consequences.
- `core-architecture.md` sections 4.1 and 4.2 for attrition-phase responsibilities and deterministic resolution order.
- `_bmad-output/planning-artifacts/epics.md` Story 6.1 acceptance criteria.

## Dev Agent Record

### Agent Model Used

OpenAI Codex CLI (`codex --yolo exec` in a dedicated git worktree)

### Debug Log References

- RED evidence: `source .venv/bin/activate && pytest tests/test_resolver.py -q -o addopts='' -k 'starvation_attrition or eliminated'`
- Focused green verification: `source .venv/bin/activate && pytest tests/test_resolver.py -q -o addopts='' -k 'starvation_attrition or eliminated or advances_transit or clamps_food or adds_owned_city'`
- Focused refinement verification: `source .venv/bin/activate && pytest tests/test_resolver.py -q -o addopts='' -k 'starvation_attrition or updates_elimination or city_remains'`
- Focused regression coverage: `source .venv/bin/activate && pytest tests/test_resolver.py tests/test_simulation.py -q -o addopts=''`
- Quality gate: `source .venv/bin/activate && make quality`

### Completion Notes List

- Added resolver-boundary regression coverage for starvation attrition, zero-troop army removal, retained-city survival, and elimination state changes after attrition.
- Implemented deterministic starvation attrition in `server.resolver` only for players whose copied post-resource state is at zero food.
- Removed armies reduced to zero or below troops before the resolved state is returned, preserving valid army contracts.
- Marked players eliminated only when canonical city ownership is empty and no surviving armies remain after attrition resolution; otherwise kept them active.
- Preserved resolver purity and the existing `phase.attrition.completed` metadata and event contract.

### File List

- `_bmad-output/implementation-artifacts/6-1-apply-starvation-attrition-and-elimination-checks-during-the-attrition-phase.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/resolver.py`
- `tests/test_resolver.py`

### Change Log

- 2026-03-28 10:25 UTC: Drafted Story 6.1 for starvation attrition and elimination checks.
- 2026-03-28 10:36 UTC: Implemented deterministic starvation attrition and elimination checks in the resolver attrition phase, added resolver regression coverage, and marked the story complete.
