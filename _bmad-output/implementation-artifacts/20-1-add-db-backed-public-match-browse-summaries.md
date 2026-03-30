# Story 20.1: Add DB-backed public match browse summaries

Status: done

## Story

As a human player or spectator,
I want the public matches route to return compact browse metadata for joinable and live matches,
So that pre-game browsing can distinguish lobbies, running games, and spectator candidates without relying on private agent APIs.

## Acceptance Criteria

1. Given persisted non-completed matches exist in the database, when a client requests `GET /api/v1/matches`, then the API returns deterministic compact browse summaries ordered by public status and recency rather than replay-sized state payloads.
2. Given match browse needs to support lobby and live entry decisions, when the response is returned, then each summary includes only public metadata needed for browsing, such as match identity, status, map, current tick, tick interval, current player count, max player count, and open slot count.
3. Given completed matches already have a dedicated browse route, when the public matches route is called in DB-backed mode, then completed matches are excluded and behavior-first tests plus a real-process smoke prove the running app serves the DB-backed browse contract.

## Tasks / Subtasks

- [x] Add the narrow public browse response shape and DB-backed query helper for non-completed matches. (AC: 1, 2)
- [x] Expose DB-backed public browse behavior through `GET /api/v1/matches` while preserving the lightweight in-memory fallback for seeded/dev mode. (AC: 1, 2)
- [x] Add focused DB/API/e2e coverage for ordering, compact fields, completed-match exclusion, and real-process browse behavior. (AC: 1, 2, 3)
- [x] Update story/BMAD/source-of-truth docs, run review + simplification, and pass the repo quality gate. (AC: 3)

## Dev Notes

- Reuse the existing DB-backed registry/read-model approach instead of inventing a browse service.
- Keep the response compact and public-only; do not return fogged state, player IDs, join tokens, or replay payloads.
- Preserve the existing in-memory route behavior for local seeded mode unless a DB-backed registry is active.
- Status ordering should favor player decision usefulness: lobby first, then active, then paused; completed belongs on `/api/v1/matches/completed`.

## Implementation Plan

- Plan file: `docs/plans/2026-03-30-story-20-1-public-match-browse-summaries.md`
- Parallelism assessment: sequential implementation because the response model, DB helper, route wiring, and tests all share the same public contract seam; spec and quality reviews can run independently after implementation.
- Verification target: focused DB/API/e2e tests, then `make quality`.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'match_browse or list_matches'`
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'list_matches or match_browse'`
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'match_browse or list_matches'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'match_browse or list_matches'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'list_matches or match_browse'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'match_browse or list_matches'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py tests/api/test_agent_api.py tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py tests/agent_sdk/test_python_client.py -k 'match_browse or list_matches or public_match'`
- GREEN: `make quality`

### Completion Notes List

- `GET /api/v1/matches` now returns compact public browse summaries with map and slot-count metadata instead of replay-sized-style match rows.
- DB-backed public browse reads exclude completed matches and order rows by lobby, active, paused, then recency with a stable id tiebreaker.
- Seeded/in-memory mode still serves deterministic lightweight browse rows for local development without requiring a database-backed read helper.
- Added focused DB, API, and real-process smoke coverage for compact browse shape, completed-match exclusion, and ordering.
- Follow-up fix: the in-memory fallback now derives browse metadata from `MatchRecord` public fields instead of fabricating placeholder values, and the seeded/API/SDK expectations now assert the seeded public match metadata.

### File List

- core-architecture.md
- _bmad-output/planning-artifacts/architecture.md
- _bmad-output/implementation-artifacts/20-1-add-db-backed-public-match-browse-summaries.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- server/agent_registry.py
- server/db/registry.py
- server/main.py
- server/models/api.py
- agent-sdk/python/iron_council_client.py
- tests/agent_sdk/test_python_client.py
- tests/api/test_agent_api.py
- tests/api/test_agent_process_api.py
- tests/e2e/test_api_smoke.py
- tests/test_db_registry.py
