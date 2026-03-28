# Story 9.2: Degrade besieged fortifications when hostile control seals every adjacent route

Status: done

## Story

As a game engine developer,
I want the siege phase to recognize fully surrounded fortified cities and wear down their defenses,
so that entrenched defenders become vulnerable when attackers isolate every adjacent approach.

## Acceptance Criteria

1. Given a fortified city whose owner is different from the owner of every adjacent city on the map, when the siege phase runs, then the city's fortification tier drops by exactly one level in the copied next state.
2. Given a fortified city that still has at least one adjacent city owned by its controller or by an allied coalition member, when the siege phase runs, then the fortification tier does not degrade from siege pressure.
3. Given repeated runs from the same starting state and adjacency ownership layout, when the siege phase resolves, then the resulting fortification tiers are deterministic and the caller-owned `MatchState` remains unchanged.

## Tasks / Subtasks

- [x] Add behavior-first resolver coverage before implementation. (AC: 1, 2, 3)
  - [x] Cover deterministic siege degradation for a fully surrounded fortified city.
  - [x] Cover the non-besieged case when a friendly or allied adjacent city keeps a route open.
  - [x] Cover repeated runs and input-state immutability.
- [x] Implement narrow siege-phase encirclement handling. (AC: 1, 2, 3)
  - [x] Keep scope to fortification wear from encirclement only; do not add food-transfer blocking, fog changes, or diplomatic side effects in this story.
  - [x] Reuse canonical map adjacency and current alliance membership from match state.
  - [x] Keep siege checks deterministic and independent of dictionary insertion order.
- [x] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [x] Re-run focused resolver coverage.
  - [x] Re-run the repository quality gate.

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

- `pytest -o addopts='-q --strict-config --strict-markers' tests/test_resolver.py -k 'surrounded_city or route_open_when_adjacent_city_is_allied or keeps_siege_degradation_deterministic'` (red phase via `PYTHONPATH=.` before `uv sync`, then green via `uv run`)
- `uv sync --extra dev --frozen`
- `uv run pytest -o addopts='-q --strict-config --strict-markers' tests/test_resolver.py`
- `make format`
- `make quality`
- `uv run pytest -o addopts='' tests/test_resolver.py -k 'caps_fortification_wear_at_one_tier_when_city_is_besieged_and_unpaid'` (red: fortification dropped from tier 2 to tier 0 in one tick before the corrective fix)
- `uv run pytest -o addopts='' tests/test_resolver.py -k 'fortification_upkeep or unpaid_fortifications or fortification_upkeep_and_decay or surrounded_city or route_open_when_adjacent_city_is_allied or keeps_siege_degradation_deterministic or caps_fortification_wear_at_one_tier_when_city_is_besieged_and_unpaid'`
- `make quality`

### Completion Notes List

- Added resolver-boundary siege regression coverage for full encirclement, allied-route exemption, and repeated-run/input-immutability behavior using canonical map city IDs.
- Implemented siege-phase fortification degradation only, driven by canonical UK 1900 adjacency and current coalition membership from `MatchState`, with sorted iteration to preserve deterministic behavior independent of dict insertion order.
- Verified the full quality gate after formatting; `make quality` passed with 92 tests passing and 97.17% total coverage.
- Added a corrective resolver-boundary regression for the overlap case where the same city is both besieged and unpaid in one tick, pinning Story 9.2's requirement that the returned `next_state` drops by exactly one fortification tier.
- Narrowed the fix to per-tick fortification wear tracking inside `ResolverPhaseState`, preserving Story 9.1's deterministic unpaid upkeep ordering while preventing attrition from applying a second downgrade after siege already wore the city once.
- Re-verified the repository after the follow-up; `make quality` passed with 93 tests passing and 97.19% total coverage.

### File List

- `server/resolver.py`
- `tests/test_resolver.py`
- `_bmad-output/implementation-artifacts/9-2-degrade-besieged-fortifications-when-hostile-control-seals-every-adjacent-route.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-28 13:35 UTC: Drafted Story 9.2 for deterministic siege-phase fortification degradation.
- 2026-03-28 14:05 UTC: Added failing resolver-boundary siege tests for surrounded, allied-route-open, and deterministic repeated-run behavior.
- 2026-03-28 14:12 UTC: Implemented deterministic siege-phase fortification degradation from canonical adjacency and coalition ownership, then passed `make quality`.
- 2026-03-28 13:45 UTC: Added corrective overlap regression coverage and capped per-city fortification wear at one tier per tick so besieged unpaid cities only degrade once in the returned `next_state`.
