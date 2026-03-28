# Story 5.2: Advance army transit and accepted movement orders during the movement phase

Status: done

## Story

As a game engine developer,
I want the movement phase to progress in-transit armies and start accepted new marches,
so that headless simulations can model travel time and arrivals across the map graph.

## Acceptance Criteria

1. Given armies already in transit, when the movement phase runs, then `ticks_remaining` decrements deterministically and armies arrive into their destination city when the counter reaches zero.
2. Given accepted movement orders for armies that are currently stationed in cities, when the movement phase runs, then each army begins a one-edge march using the canonical edge distance for that route and leaves its current location until arrival.
3. Given identical starting state and accepted orders, when the movement phase runs repeatedly, then the resulting army positions and transit counters are identical and the original input state remains unchanged.

## Tasks / Subtasks

- [x] Add focused movement-phase behavior coverage before implementation. (AC: 1, 2, 3)
  - [x] Cover decremented transit counters and arrival state transitions.
  - [x] Cover starting new marches from accepted `OrderBatch.movements`.
  - [x] Cover deterministic repeated resolution from identical inputs.
- [x] Implement movement progression in the resolver pipeline. (AC: 1, 2, 3)
  - [x] Reuse the canonical UK 1900 map data to derive edge distances.
  - [x] Start only one-edge marches consistent with current order-validation rules.
  - [x] Preserve the stable movement-phase event contract after applying state changes.
- [x] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [x] Re-run focused resolver and simulation coverage.
  - [x] Re-run the repository quality gate.

## Dev Notes

- Current order validation already constrains moves to directly adjacent destinations, so this story only needs one-edge path handling.
- Arrival should restore a stationed army shape (`location` set, `destination/path` cleared, `ticks_remaining = 0`).
- Keep scope intentionally narrow: do not implement contested-arrival combat or ownership transfer here.

### References

- `core-plan.md` sections 3.3 and 6.1 for edge-based travel time and army transit visibility.
- `core-architecture.md` section 4.1 for movement-phase responsibilities.
- `_bmad-output/planning-artifacts/epics.md` Story 5.2 acceptance criteria.

## Dev Agent Record

### Agent Model Used

OpenAI Codex CLI (`codex --yolo exec` in a dedicated git worktree)

### Debug Log References

- RED evidence: `source ../iron-counsil-story-5-1/.venv/bin/activate && python -m pytest --no-cov tests/test_resolver.py -q -k 'advances_transit'`
- RED evidence: `source ../iron-counsil-story-5-1/.venv/bin/activate && python -m pytest --no-cov tests/test_simulation.py -q -k 'movement_transit_progression'`
- Focused green verification: `source .venv/bin/activate && pytest --no-cov tests/test_resolver.py tests/test_simulation.py -q`
- Full suite: `source .venv/bin/activate && pytest tests/ -q`
- Quality gate: `source .venv/bin/activate && make quality`

### Completion Notes List

- Added behavior-first movement-phase regression coverage at the resolver boundary for in-transit decrementing, arrival normalization, and one-edge move startup from accepted movement orders.
- Added simulation coverage proving repeated runs from identical starting state and movement orders remain deterministic while leaving the caller-owned `MatchState` unchanged.
- Implemented narrow movement-phase logic in `server.resolver` that first advances existing transit armies, then starts new one-edge marches using canonical UK 1900 edge distances.
- Preserved the existing `phase.movement.completed` event contract and intentionally left contested arrival, combat, ownership transfer, and multi-edge pathfinding out of scope.
- Synced the local `.venv` with `uv sync --extra dev --frozen` after the first `make quality` run exposed missing dev tools in this worktree, then re-ran the required checks successfully.

### File List

- `_bmad-output/implementation-artifacts/5-2-advance-army-transit-and-accepted-movement-orders-during-the-movement-phase.md`
- `server/resolver.py`
- `tests/test_resolver.py`
- `tests/test_simulation.py`

### Change Log

- Created Story 5.2 implementation artifact.
- 2026-03-28 09:35 UTC: Implemented deterministic movement-phase transit progression and one-edge march startup, added resolver/simulation regression coverage, and marked Story 5.2 complete.
