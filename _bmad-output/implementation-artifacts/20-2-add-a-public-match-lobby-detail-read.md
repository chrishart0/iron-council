# Story 20.2: Add a public match lobby detail read

Status: done

## Story

As a human player or spectator,
I want a compact public detail route for one browseable match,
So that I can inspect one lobby or live match's public metadata and visible roster without relying on private agent APIs or replay surfaces.

## Acceptance Criteria

1. Given a lobby, paused, or active match exists, when a client requests the public match-detail route, return compact public metadata for that one match, including configuration and a visible roster summary, without exposing fog-filtered state or private agent credentials.
2. Given a completed match or unknown match is requested, when the public detail route is called, return a structured response aligned with the browse-surface contract and do not leak replay/history payloads through this endpoint.
3. Add tests for route success, structured not-found handling, stable ordering of visible roster rows, and real-process coverage against the DB-backed app.

## Tasks / Subtasks

- [x] Add compact public match-detail response models and a DB-backed public detail helper that reuse the existing browse read-model style. (AC: 1, 2)
- [x] Expose `GET /api/v1/matches/{match_id}` with DB-backed source-of-truth behavior and a lightweight in-memory seeded/dev fallback. (AC: 1, 2)
- [x] Add focused DB/API/e2e tests for success, structured not-found handling, stable roster ordering, and no replay/history leakage from the detail surface. (AC: 1, 2, 3)
- [x] Update architecture/BMAD artifacts, run the quality gate, and mark sprint tracking complete. (AC: 3)

## Dev Notes

- Reuse the existing DB-backed public read-model style from Stories 19.1, 19.2, and 20.1 instead of adding a new service abstraction.
- Keep the detail payload compact and public-only. Do not return fog-filtered state, player IDs, join tokens, replay/history payloads, auth details, or API keys.
- Completed matches intentionally do not resolve through this route; they belong on the completed-match browse/history surfaces instead.
- Preserve a lightweight in-memory fallback for seeded/dev mode using public match metadata already held in the registry.

## Implementation Plan

- Plan file: `docs/plans/2026-03-30-story-20-2-public-match-lobby-detail-read.md`
- Parallelism assessment: sequential implementation because the models, DB helper, route, tests, and contract docs all share one public seam; verification fans out after the core route is in place.
- Verification target: focused RED/GREEN DB/API/e2e commands, then `make quality`.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'public_match_detail'`
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'public_match_detail'`
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'public_match_detail'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'public_match_detail or match_browse or leaderboard or completed_match'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'public_match_detail or match_browse or leaderboard or completed_match or list_matches'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'public_match_detail or match_browse or leaderboard or completed_match or list_matches'`
- GREEN: `make quality`

### Completion Notes List

- Added a compact public detail contract in `server/models/api.py` with browse-sized top-level fields plus public roster rows containing only `display_name` and `competitor_kind`.
- Added `get_public_match_detail` in `server/db/registry.py` to read one non-completed persisted match directly from the database, derive compact browse metadata, and return a deterministically sorted public roster.
- Exposed `GET /api/v1/matches/{match_id}` in `server/main.py` using DB-backed source-of-truth reads in persisted mode while preserving a seeded in-memory fallback that derives public roster rows without exposing private state.
- Completed and unknown matches now return the existing structured `match_not_found` response on this public detail surface, and the endpoint never returns history/replay payloads.
- Added focused registry, API, and real-process smoke coverage for route success, structured not-found handling, stable roster ordering, and public-only payload shape.
- Updated the canonical architecture docs and BMAD mirror to explicitly mention the compact public detail route and its non-leakage contract.

### File List

- _bmad-output/implementation-artifacts/20-2-add-a-public-match-lobby-detail-read.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- _bmad-output/planning-artifacts/architecture.md
- core-architecture.md
- docs/plans/2026-03-30-story-20-2-public-match-lobby-detail-read.md
- server/db/registry.py
- server/main.py
- server/models/api.py
- tests/api/test_agent_api.py
- tests/e2e/test_api_smoke.py
- tests/test_db_registry.py
