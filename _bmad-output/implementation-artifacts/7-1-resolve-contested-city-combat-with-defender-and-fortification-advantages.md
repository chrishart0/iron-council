# Story 7.1: Resolve contested-city combat with defender and fortification advantages

Status: done

## Story

As a game engine developer,
I want the combat phase to apply simultaneous deterministic casualties to opposing armies that share a city,
so that headless simulations can model frontline battles before diplomacy and full siege systems land.

## Acceptance Criteria

1. Given armies from different players occupying the same city at the start of the combat phase, when combat resolves, then each side takes deterministic simultaneous casualties derived from the opposing force and armies reduced to zero troops are removed from the next state.
2. Given one side qualifies as the city defender because it owns the contested city, when combat resolves in a fortified city, then the defending side receives the documented base defender bonus plus the city's fortification multiplier while attackers do not.
3. Given identical starting states and contested armies, when the combat phase resolves repeatedly, then the resulting troop counts and surviving armies are identical and the caller-owned `MatchState` remains unchanged.

## Tasks / Subtasks

- [x] Add behavior-first combat coverage before implementation. (AC: 1, 2, 3)
  - [x] Cover simultaneous casualties for contested cities with one army per side.
  - [x] Cover defender bonus plus fortification multiplier on a city-owned defender.
  - [x] Cover zero-troop removal and deterministic repeated resolution.
- [x] Implement narrow combat-phase casualty resolution. (AC: 1, 2, 3)
  - [x] Keep scope to city-level contested armies already co-located after movement.
  - [x] Apply deterministic integer casualty math with no randomness.
  - [x] Preserve resolver purity and the stable `phase.combat.completed` event contract.
- [x] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [x] Re-run focused resolver coverage.
  - [x] Re-run the repository quality gate.

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

- `uv run pytest --no-cov tests/test_resolver.py -k combat` failed because `pytest --no-cov` still inherited repo `--cov` addopts before the dev extras were synced into `.venv`.
- `uv sync --extra dev`
- `.venv/bin/pytest -o addopts='' tests/test_resolver.py`
- `.venv/bin/pytest -o addopts='' tests/test_resolver.py -k 'minimum_one_casualty or same_owner_stack or applies_simultaneous_casualties_to_contested_city_armies or applies_defender_and_fortification_advantage_only_to_city_owner or combat_is_deterministic'`
- `.venv/bin/pytest -o addopts='' tests/test_resolver.py -k 'combat or contested'`
- `make format`
- `make quality`

### Completion Notes List

- Added behavior-first resolver tests for contested-city simultaneous casualties, defender plus fortification advantage, and deterministic zero-troop cleanup without mutating the caller-owned `MatchState`.
- Implemented narrow combat-phase resolution for co-located city armies only, using deterministic integer effective-strength math with a 1.2x defender bonus and documented fortification multipliers.
- Removed the undocumented minimum-one casualty floor so owner losses now use the simplest proportional integer rule: `opposing_effective_strength // 10`, clamped only by troops remaining.
- Replaced same-owner loss assignment by army-id order with deterministic troop-proportional allocation, using largest-remainder tie-breaking on army id so stacked losses stay stable across runs.
- Preserved existing phase order and the `phase.combat.completed` event contract; did not add capture, siege, diplomacy, garrison combat, timers, randomness, or schema changes.

### File List

- `_bmad-output/implementation-artifacts/7-1-resolve-contested-city-combat-with-defender-and-fortification-advantages.md`
- `server/resolver.py`
- `tests/test_resolver.py`

### Change Log

- 2026-03-28 11:22 UTC: Drafted Story 7.1 for deterministic contested-city combat resolution.
- 2026-03-28 11:25 UTC: Added contested-city combat resolver coverage, implemented deterministic defender-aware combat resolution, and passed `make quality`.
- 2026-03-28 11:32 UTC: Removed the undocumented minimum casualty floor, added troop-proportional same-owner casualty allocation, refreshed combat expectations, and re-passed `make quality`.
