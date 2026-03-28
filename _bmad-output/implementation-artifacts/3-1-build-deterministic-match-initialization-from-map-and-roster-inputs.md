# Story 3.1: Build deterministic match initialization from map and roster inputs

Status: done

## Story

As a game server,
I want to create a canonical starting match state,
so that every new match begins from validated map and player inputs.

## Acceptance Criteria

1. Given a match config and player roster, when initialization runs, then players receive legal spawn cities, starting resources, and empty movement queues.
2. Given neutral Ireland is excluded from spawning, when starting cities are assigned, then no player begins in Belfast, Dublin, Cork, or Galway.
3. Given the same config and roster inputs, when initialization runs repeatedly, then the resulting canonical match state is deterministic.
4. Given malformed roster or impossible spawn requirements, when initialization runs, then it fails with clear validation errors instead of producing partial state.

## Tasks / Subtasks

- [x] Add public match-initialization inputs and output surface. (AC: 1, 3, 4)
  - [x] Introduce config/roster models for deterministic initialization.
  - [x] Expose a public initializer function under `server/` that returns a canonical `MatchState`.
- [x] Assign legal mainland spawn cities deterministically. (AC: 1, 2, 3, 4)
  - [x] Exclude Irish no-spawn cities.
  - [x] Enforce the non-adjacent starting-city rule from `core-plan.md`.
  - [x] Make repeated runs with the same ordered inputs produce the same city assignments.
- [x] Populate canonical starting state. (AC: 1, 3)
  - [x] Create city state entries for the entire map.
  - [x] Initialize player resources, owned-city lists, and empty movement-ready army state.
  - [x] Initialize victory state from the configured threshold.
- [x] Add behavior-first tests for successful and failing initialization. (AC: 1, 2, 3, 4)
  - [x] Cover deterministic repeated initialization.
  - [x] Cover Ireland exclusion and non-adjacent player spawns.
  - [x] Cover impossible spawn layouts or invalid player counts with structured failures.

## Dev Notes

- Keep scope tight: this story is about initialization only, not order validation or tick resolution.
- Prefer a pure function that consumes explicit config/roster inputs plus the canonical map loader.
- Preserve behavior-first tests at the public initializer boundary.
- Keep army movement queues empty at start; do not invent resolver behavior.

### References

- `core-plan.md` section 10.2 for spawn rules.
- `core-plan.md` section 8.1 for configurable victory threshold context.
- `core-architecture.md` section 3.2 for canonical `MatchState` shape.
- `_bmad-output/planning-artifacts/epics.md` Story 3.1 acceptance criteria.

## Dev Agent Record

### Agent Model Used

OpenAI Codex CLI (`codex --yolo exec` recommended in this environment)

### Debug Log References

- RED: `uv run pytest tests/test_match_initialization.py -q` -> failed with `ModuleNotFoundError: No module named 'server.match_initialization'`
- RED (correction): `uv run pytest tests/test_match_initialization.py -q` -> failed because `MatchConfig` still required `victory_countdown_ticks` and `MatchRosterEntry` still required caller-supplied `starting_city_ids`
- Targeted verification: `uv run pytest tests/test_match_initialization.py tests/test_map_data.py tests/test_state.py tests/api/test_health.py tests/api/test_metadata.py -q`
- Quality gate: `make format`
- Quality gate: `make lint`
- Quality gate: `make test`
- Quality gate: `make quality`
- PM review follow-up: tightened roster validation for blank/whitespace-padded player IDs, enforced the mainland-only rule for explicit spawn overrides, then reran `make quality`

### Completion Notes List

- Corrected the public initialization contract so the canonical path is `MatchConfig + ordered roster -> initialize_match_state(...)`, with `starting_cities_per_player` in config and optional explicit spawn overrides on roster entries.
- Initializer-owned spawn assignment now deterministically chooses legal mainland cities, excludes Ireland, preserves cross-player non-adjacency, and fails clearly when no valid assignment exists.
- Starting state still populates the full canonical map, seeds player resources from config, leaves `armies` empty, and initializes `VictoryState` from the configured threshold without introducing order validation or tick resolution.
- Removed the unused `victory_countdown_ticks` field from the public Story 3.1 config surface so initialization stays behavior-first and aligned with the canonical `VictoryState` contract (`countdown_ticks_remaining = null` at start).
- Tightened malformed-input handling by rejecting blank or whitespace-padded player IDs and by enforcing the mainland-only spawn rule even for explicit starting-city overrides supplied with a custom map.

### File List

- `_bmad-output/implementation-artifacts/3-1-build-deterministic-match-initialization-from-map-and-roster-inputs.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/match_initialization.py`
- `tests/test_match_initialization.py`

### Change Log

- Created Story 3.1 implementation artifact for deterministic match initialization.
- Implemented deterministic assigned-spawn match initialization and behavior-first coverage for Story 3.1.
- Corrected Story 3.1 to make spawn assignment initializer-owned, config-driven, and spec-compliant at the public boundary.
