# Story 5.2: Advance army transit and accepted movement orders during the movement phase

Status: drafted

## Story

As a game engine developer,
I want the movement phase to progress in-transit armies and start accepted new marches,
so that headless simulations can model travel time and arrivals across the map graph.

## Acceptance Criteria

1. Given armies already in transit, when the movement phase runs, then `ticks_remaining` decrements deterministically and armies arrive into their destination city when the counter reaches zero.
2. Given accepted movement orders for armies that are currently stationed in cities, when the movement phase runs, then each army begins a one-edge march using the canonical edge distance for that route and leaves its current location until arrival.
3. Given identical starting state and accepted orders, when the movement phase runs repeatedly, then the resulting army positions and transit counters are identical and the original input state remains unchanged.

## Tasks / Subtasks

- [ ] Add focused movement-phase behavior coverage before implementation. (AC: 1, 2, 3)
  - [ ] Cover decremented transit counters and arrival state transitions.
  - [ ] Cover starting new marches from accepted `OrderBatch.movements`.
  - [ ] Cover deterministic repeated resolution from identical inputs.
- [ ] Implement movement progression in the resolver pipeline. (AC: 1, 2, 3)
  - [ ] Reuse the canonical UK 1900 map data to derive edge distances.
  - [ ] Start only one-edge marches consistent with current order-validation rules.
  - [ ] Preserve the stable movement-phase event contract after applying state changes.
- [ ] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [ ] Re-run focused resolver and simulation coverage.
  - [ ] Re-run the repository quality gate.

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

_OpenAI Codex CLI (`codex --yolo exec` recommended in this environment)_

### Debug Log References

- _To be filled during implementation._

### Completion Notes List

- _To be filled during implementation._

### File List

- `_bmad-output/implementation-artifacts/5-2-advance-army-transit-and-accepted-movement-orders-during-the-movement-phase.md`

### Change Log

- Created Story 5.2 implementation artifact.
