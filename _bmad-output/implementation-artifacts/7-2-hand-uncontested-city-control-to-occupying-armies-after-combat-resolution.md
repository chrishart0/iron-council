# Story 7.2: Hand uncontested city control to occupying armies after combat resolution

Status: done

## Story

As a game engine developer,
I want the resolver to update city ownership when exactly one surviving force occupies a city after movement and combat,
so that match state, economy, and victory tracking reflect territorial gains without waiting for later API work.

## Acceptance Criteria

1. Given a neutral or enemy-owned city containing armies from exactly one surviving player after combat resolution, when the tick finishes the combat phase, then the city owner changes to that occupying player in the copied next state.
2. Given a contested city that still contains surviving armies from multiple players, when the combat phase completes, then ownership does not change until only one force remains.
3. Given repeated runs from the same starting state and occupying armies, when the ownership handoff resolves, then the resulting city owners are deterministic and the caller-owned `MatchState` remains unchanged.

## Tasks / Subtasks

- [x] Add behavior-first occupancy and ownership-handoff coverage before implementation. (AC: 1, 2, 3)
  - [x] Cover neutral-city occupation by a single survivor.
  - [x] Cover enemy-city occupation after defenders are gone.
  - [x] Cover contested survivors leaving ownership unchanged.
- [x] Implement narrow post-combat ownership updates. (AC: 1, 2, 3)
  - [x] Limit scope to cities with exactly one surviving occupying player.
  - [x] Avoid expanding capture timers, loyalty mechanics, or siege markers.
  - [x] Preserve resolver purity and existing phase event contracts.
- [x] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [x] Re-run focused resolver and simulation coverage.
  - [x] Re-run the repository quality gate.

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

- Red: `uv run --python .venv/bin/python pytest -o addopts= tests/test_resolver.py -q`
- Green: `uv run --python .venv/bin/python pytest -o addopts= tests/test_simulation.py tests/test_resolver.py -q`
- Red (follow-up): `uv run --python .venv/bin/python pytest -o addopts= tests/test_resolver.py -k 'handoff or uncontested or missing_from_players or multiple_survivors' -q`
- Green (follow-up): `uv run --python .venv/bin/python pytest -o addopts= tests/test_resolver.py -k 'handoff or uncontested or missing_from_players or multiple_survivors' -q`
- Quality gate: `make quality`

### Completion Notes List

- Added resolver-boundary tests for neutral capture, enemy capture after combat, and contested survivors retaining the current owner.
- Updated the combat phase to hand city ownership to exactly one surviving occupier after combat while leaving contested cities unchanged.
- Kept the resolver pure by mutating only the copied next state and synchronized `players[*].cities_owned` with `cities[*].owner`.
- Added explicit AC3 follow-up coverage for deterministic ownership handoff outcomes and `cities_owned` synchronization.
- Guarded uncontested city handoff when the occupying owner is absent from `match_state.players` so city ownership and player-owned city lists cannot diverge.

### File List

- `server/resolver.py`
- `tests/test_resolver.py`
- `_bmad-output/implementation-artifacts/7-2-hand-uncontested-city-control-to-occupying-armies-after-combat-resolution.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-28 11:22 UTC: Drafted Story 7.2 for deterministic post-combat city ownership handoff.
- 2026-03-28 11:37 UTC: Implemented uncontested post-combat city ownership handoff with resolver-boundary regression coverage and green quality gate.
- 2026-03-28 11:42 UTC: Tightened Story 7.2 ownership handoff invariants with explicit AC3 determinism coverage and a missing-player guard.
