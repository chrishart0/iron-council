# Story 6.2: Track coalition city control and victory countdown during the victory phase

Status: done

## Story

As a game engine developer,
I want the victory phase to count coalition-controlled cities and manage a countdown,
so that simulations can expose an explicit endgame race before combat, siege, and diplomacy are fully implemented.

## Acceptance Criteria

1. Given city ownership and player alliance membership in the canonical match state, when the victory phase runs, then it groups owned cities by alliance-or-solo coalition, sets `VictoryState.leading_alliance`, and records the leading coalition's controlled city count.
2. Given a coalition meeting or exceeding the configured city threshold, when the victory phase runs on consecutive ticks, then `countdown_ticks_remaining` starts, decreases deterministically while the coalition stays above threshold, and clears if control drops below threshold or the leader changes.
3. Given repeated runs from the same starting state and coalition ownership layout, when the victory phase resolves, then the resulting victory metadata is deterministic and the caller-owned `MatchState` remains unchanged.

## Tasks / Subtasks

- [x] Add behavior-first victory coverage before implementation. (AC: 1, 2, 3)
  - [x] Cover coalition grouping for allied and solo players.
  - [x] Cover countdown start, continuation, and reset cases.
  - [x] Cover deterministic repeated resolution from the same starting state.
- [x] Implement deterministic victory-phase coalition counting. (AC: 1, 2, 3)
  - [x] Reuse canonical player alliance IDs without introducing new alliance models yet.
  - [x] Keep countdown semantics explicit and easy to test.
  - [x] Preserve the stable `phase.victory.completed` event contract.
- [x] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [x] Re-run focused resolver and simulation coverage.
  - [x] Re-run the repository quality gate.

## Dev Notes

- Treat players without an alliance as their own solo coalition keyed by player ID.
- Keep scope intentionally narrow: update victory metadata only; do not add match-complete status or chat/broadcast side effects yet.
- Prefer resolver/simulation boundary tests over helper-only tests.

### References

- `core-plan.md` section 8.1 for coalition victory and countdown behavior.
- `core-architecture.md` sections 3.2 and 4.1 for canonical victory state shape and phase responsibilities.
- `_bmad-output/planning-artifacts/epics.md` Story 6.2 acceptance criteria.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Red phase: `uv run pytest --no-cov tests/test_resolver.py -k 'victory_metadata or top_city_control'`
- Red phase: `uv run pytest --no-cov tests/test_simulation.py -k 'victory_countdown_for_same_coalition'`
- Red phase (follow-up): `uv run pytest --no-cov tests/test_resolver.py -k 'leading_coalition_changes or drops_below_threshold'`
- Red phase (collision follow-up): `uv run pytest --no-cov tests/test_resolver.py -k 'keeps_solo_and_alliance_coalitions_distinct_when_ids_collide'`
- Focused verification: `uv run pytest --no-cov tests/test_resolver.py tests/test_simulation.py`
- Focused verification (follow-up): `uv run pytest --no-cov tests/test_resolver.py -k 'victory or leading_coalition_changes or drops_below_threshold'`
- Focused verification (collision follow-up): `uv run pytest --no-cov tests/test_resolver.py::test_resolve_tick_groups_allied_and_solo_city_control_for_victory_metadata tests/test_resolver.py::test_resolve_tick_keeps_solo_and_alliance_coalitions_distinct_when_ids_collide tests/test_resolver.py::test_resolve_tick_clears_victory_countdown_when_top_city_control_is_tied tests/test_resolver.py::test_resolve_tick_clears_victory_countdown_when_leading_coalition_changes tests/test_resolver.py::test_resolve_tick_clears_victory_countdown_when_control_drops_below_threshold tests/test_simulation.py::test_simulate_ticks_starts_and_continues_victory_countdown_for_same_coalition`
- Quality gate: `make quality`

### Completion Notes List

- Implemented deterministic coalition city counting from owned cities using `players[*].alliance_id`, with unallied players treated as solo coalitions keyed by player id.
- Updated victory resolution to set `VictoryState.leading_alliance` and `VictoryState.cities_held` from coalition control counts while keeping resolver purity and the existing `phase.victory.completed` event contract unchanged.
- Applied deterministic tie handling so tied top coalitions clear `leading_alliance` and any active countdown while still recording the top controlled city count.
- Used `VictoryState.threshold` as both the city-control threshold and temporary initial countdown duration for this narrow story because the schema has no dedicated countdown-duration field yet.
- Verified countdown behavior across resolver and simulation boundaries: start on first qualifying tick, decrement on later ticks while the same coalition stays above threshold, and clear on ties or leader loss.
- Follow-up fix: when the leader changes from one coalition to another, the resolver now clears the countdown on that tick instead of restarting it immediately.
- Added behavior-first regression coverage for both missing reset paths: coalition handoff clears the countdown, and loss of threshold control clears it.
- Follow-up fix: coalition counting now uses an internal namespaced coalition key so solo player IDs cannot collide with alliance IDs while `VictoryState.leading_alliance` still exposes the existing alliance-or-solo identifier semantics.
- Added behavior-first regression coverage for the collision case where an alliance ID equals a solo player ID, preventing those distinct coalitions from merging during victory counting.

### File List

- `_bmad-output/implementation-artifacts/6-2-track-coalition-city-control-and-victory-countdown-during-the-victory-phase.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/resolver.py`
- `tests/test_resolver.py`
- `tests/test_simulation.py`

### Change Log

- 2026-03-28 10:25 UTC: Drafted Story 6.2 for coalition control and victory countdown tracking.
- 2026-03-28 10:33 UTC: Added resolver and simulation coverage for coalition counting, deterministic ties, and countdown progression before implementing the victory-phase logic.
- 2026-03-28 10:33 UTC: Implemented narrow victory-phase coalition counting and countdown updates without expanding the canonical schema.
- 2026-03-28 10:33 UTC: Passed focused resolver/simulation verification and the full `make quality` gate.
- 2026-03-28 10:45 UTC: Fixed the countdown reset gap so coalition handoffs clear for one tick before any restart, and added regression coverage for leader-change and below-threshold resets.
- 2026-03-28 10:56 UTC: Fixed coalition-count key collisions between solo player IDs and alliance IDs by namespacing internal victory coalitions, and added regression coverage for the collision case.
