# Story 19.1: Expose persisted tick history and replay snapshots

Status: done

## Story

As a spectator client or debugging tool,
I want to list recorded match ticks and fetch one persisted snapshot by tick,
So that replay and audit flows can inspect the authoritative history written by the live runtime.

## Acceptance Criteria

1. Given the DB-backed server has persisted `tick_log` rows for a match, when a client requests the match history route, then the API returns deterministic tick entries for that match in ascending order, together with enough match metadata to drive a replay picker.
2. Given a client requests one specific persisted tick, when the replay snapshot route is called with an existing tick number, then the API returns the persisted state snapshot, accepted orders, and emitted events for that tick.
3. Given replay depends on durable runtime history rather than in-memory state, when the feature ships, then behavior-first tests cover unknown match/tick failures plus a real-process DB-backed smoke proving the running app serves the persisted history contract.

## Tasks / Subtasks

- [x] Add narrow API response models and DB query helpers for persisted tick history and replay snapshots. (AC: 1, 2)
- [x] Expose public GET routes for match history and per-tick replay reads with structured error handling. (AC: 1, 2)
- [x] Add focused DB/API tests plus a real-process smoke that proves the running DB-backed app serves persisted history. (AC: 3)
- [x] Update story/BMAD/source-of-truth docs as needed and run simplification plus the repo quality gate. (AC: 3)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex + Hermes PM review loop

### Debug Log References

- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'tick_history or replay'`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'history or replay'`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'history or replay'`
- `make quality`

### Completion Notes List

- Added narrow replay response models in `server/models/api.py` so the public contract clearly separates match-history summaries from one persisted replay snapshot payload.
- Added one direct DB query seam in `server/db/registry.py` that reads `matches` and `tick_log`, returns deterministic ascending tick summaries, and distinguishes missing-match from missing-tick failures without introducing a new repository/service layer.
- Exposed `GET /api/v1/matches/{match_id}/history` and `GET /api/v1/matches/{match_id}/history/{tick}` in `server/main.py`, with explicit `match_not_found`, `tick_not_found`, and `match_history_unavailable` error responses.
- Added behavior-first DB helper tests, API-boundary tests, and a real-process smoke proving the running DB-backed app serves persisted history from durable `tick_log` rows rather than from in-memory match state.
- Updated the canonical architecture docs and BMAD mirror to include the shipped public replay/history routes.
- Simplification pass: kept the feature read-only and intentionally boring—one helper seam, two GET routes, no caching, and no extra abstraction layer.

### File List

- _bmad-output/implementation-artifacts/19-1-expose-persisted-tick-history-and-replay-snapshots.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- _bmad-output/planning-artifacts/architecture.md
- core-architecture.md
- server/db/registry.py
- server/main.py
- server/models/api.py
- tests/api/test_agent_api.py
- tests/e2e/test_api_smoke.py
- tests/test_db_registry.py

## Dev Notes

- Reuse Story 18.2's `tick_log` persistence as the single source of truth; do not create a second history cache.
- Keep the story read-only and narrowly scoped to replay/history reads.
- Prefer one boring DB query helper plus two GET routes over a new repository/service abstraction.

## Implementation Plan

- Plan file: `docs/plans/2026-03-30-story-19-1-match-history-replay-api.md`
- Parallelism assessment: sequential implementation because the public route contract, DB helper, response models, and tests all share the same API seam; spec and quality reviews can run independently after implementation.
- Verification target: focused DB/API tests, real-process history smoke, then `make quality`.
