# Story 8.2: Process accepted recruitment orders during the build phase

Status: done

## Story

As a game engine developer,
I want the build phase to convert accepted recruitment orders into stationed armies,
so that validated troop purchases actually create military presence for later movement, combat, and attrition phases.

## Acceptance Criteria

1. Given accepted recruitment orders for player-owned cities, when the build phase runs, then each order deducts the documented food and production cost and creates or reinforces a stationed army for that player in the ordered city.
2. Given multiple accepted recruitment orders for the same player across different cities in one tick, when the build phase runs, then all accepted orders resolve deterministically without depending on list order side effects beyond the already-validated order set.
3. Given repeated runs from the same starting state and accepted recruitment orders, when the build phase resolves, then the resulting armies, city occupants, player resources, and the caller-owned `MatchState` remain deterministic and unmutated.

## Tasks / Subtasks

- [x] Add behavior-first resolver coverage before implementation. (AC: 1, 2, 3)
  - [x] Cover new stationed armies appearing for cities without a current army.
  - [x] Cover deterministic reinforcement or co-location behavior for cities that already contain a friendly stationed army.
  - [x] Cover repeated runs and input-state immutability.
- [x] Implement narrow build-phase recruitment resolution. (AC: 1, 2, 3)
  - [x] Keep scope to accepted recruitment orders only; do not add recruitment-capacity tuning, combat, or transfer-order behavior in this story.
  - [x] Reuse the documented recruitment cost table rather than duplicating food/production pricing logic.
  - [x] Keep army creation deterministic and compatible with the existing pure-function resolver contract.
- [x] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [x] Re-run focused resolver coverage.
  - [x] Re-run the repository quality gate.

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

- RED (env): `uv run pytest tests/test_resolver.py -k 'build_phase and recruitment' --override-ini addopts='-q --strict-config --strict-markers'` failed during collection with `ModuleNotFoundError: No module named 'server'` before the local dev environment was synced.
- RED: `.venv/bin/pytest tests/test_resolver.py -k 'build_phase and recruitment' -o addopts=''` failed on the new resolver-boundary assertions because build-phase recruitment did not yet reinforce armies or spend recruitment costs.
- RED (follow-up): `.venv/bin/pytest tests/test_resolver.py -k 'permutation_invariant or creates_deterministic_stationed_armies' -o addopts=''` failed because equivalent multi-city recruitment batches produced different `next_state.armies` ordering based on incoming order permutation.
- GREEN (follow-up focused recruitment): `.venv/bin/pytest tests/test_resolver.py -k 'recruitment or build_phase' -o addopts=''`
- GREEN (focused): `.venv/bin/pytest tests/test_resolver.py -k 'build_phase' -o addopts=''`
- GREEN (focused full resolver): `.venv/bin/pytest tests/test_resolver.py -o addopts=''`
- GREEN (quality gate): `make quality`

### Completion Notes List

- Added resolver-boundary tests for accepted build-phase recruitment covering reinforcement into an existing friendly stationed army, deterministic stationed-army creation when none exists, repeated-run determinism, and caller-state immutability.
- Added a follow-up resolver-boundary regression asserting that two equivalent accepted recruitment batches with different order permutations resolve to the same `next_state`.
- Implemented narrow build-phase recruitment resolution in `server.resolver` by reusing `RECRUITMENT_COST_PER_TROOP`, spending only documented food and production costs, and leaving transfer, siege, diplomacy, and recruitment-capacity behavior unchanged.
- Deterministic army creation now uses collision-safe ids shaped as `recruitment:{owner}:{city}:{n}` and reinforces the lexicographically earliest friendly stationed army already in the ordered city.
- Follow-up fix canonicalizes recruitment processing by `(owner, city, troops)` before applying accepted orders so multi-city stationed-army creation no longer depends on incoming batch permutation.
- Verified the change with focused resolver coverage and the full repository quality gate; no extra speculative resolver behavior was added.

### File List

- `_bmad-output/implementation-artifacts/8-2-process-accepted-recruitment-orders-during-the-build-phase.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/resolver.py`
- `tests/test_resolver.py`

### Change Log

- 2026-03-28 12:24 UTC: Drafted Story 8.2 for deterministic build-phase recruitment execution.
- 2026-03-28 12:40 UTC: Added resolver-boundary recruitment coverage, implemented deterministic build-phase recruitment resolution, and passed `make quality`.
- 2026-03-28 12:43 UTC: Added a permutation-invariance regression, canonicalized recruitment processing order for multi-city stationed-army creation, and re-passed `make quality`.
