# Story 19.2: Add public leaderboard and completed-match summary reads

Status: done

## Story

As a human player or spectator,
I want lightweight leaderboard and completed-match summary endpoints,
So that pre-game browsing can show who is strong and what happened in finished matches without requiring private agent credentials.

## Acceptance Criteria

1. Given persisted player and match records in the database, when a client requests the public leaderboard route, then the API returns deterministic agent/player ranking summaries ordered by visible rating fields.
2. Given completed matches exist in the database, when a client requests match-history summaries, then the API returns compact completed-match metadata suitable for browse/list views without dumping full tick snapshots.
3. Given these are public read models, when the story ships, then tests verify stable ordering, minimal response shape, and real-process coverage against the running DB-backed app.

## Tasks / Subtasks

- [x] Add narrow public response models and DB query helpers for leaderboard rows and compact completed-match summaries. (AC: 1, 2)
- [x] Expose public GET routes for leaderboard and completed-match browse reads with structured DB-backed availability handling. (AC: 1, 2)
- [x] Add focused DB/API tests plus a real-process smoke that proves the running app serves the public read models. (AC: 3)
- [x] Update story/BMAD/source-of-truth docs, run review/simplification, and pass the repo quality gate. (AC: 3)

## Dev Notes

- Reuse the existing DB-backed read path from Story 19.1 instead of adding a cache or service abstraction.
- Keep the story read-only and intentionally boring.
- Return compact browse metadata only; replay-sized payloads stay on the dedicated history routes.

## Implementation Plan

- Plan file: `docs/plans/2026-03-30-story-19-2-public-read-models.md`
- Parallelism assessment: sequential implementation because the response models, DB helper queries, routes, tests, and doc updates all share the same public seam; spec and quality reviews can run independently after implementation.
- Verification target: focused DB/API tests, real-process public-read smoke, then `make quality`.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'leaderboard or completed_match'`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'leaderboard or completed_match'`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'leaderboard or completed_match'`
- `make quality`

### Completion Notes List

- Added narrow public response models in `server/models/api.py` for leaderboard rows and compact completed-match browse summaries.
- Added direct DB-backed query helpers in `server/db/registry.py` that aggregate completed-match records into deterministic leaderboard standings and compact finished-match metadata without introducing a repository or service layer.
- Exposed `GET /api/v1/leaderboard` and `GET /api/v1/matches/completed` in `server/main.py` with the same structured DB-backed availability pattern used by Story 19.1.
- Added behavior-first registry tests, API-boundary tests, and a real-process smoke proving the running DB-backed app serves the new public read models directly from persisted rows.
- Updated the canonical architecture docs and BMAD mirror to reflect the shipped public browse endpoints.
- Simplification pass: kept the feature read-only and intentionally boring, with stable tiebreakers and compact match summaries that avoid replay payloads.

### File List

- _bmad-output/implementation-artifacts/19-2-add-public-leaderboard-and-completed-match-summary-reads.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- _bmad-output/planning-artifacts/architecture.md
- core-architecture.md
- server/db/registry.py
- server/main.py
- server/models/api.py
- tests/api/test_agent_api.py
- tests/e2e/test_api_smoke.py
- tests/test_db_registry.py
