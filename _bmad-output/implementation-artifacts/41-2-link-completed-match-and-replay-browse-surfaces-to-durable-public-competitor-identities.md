# Story: 41.2 Link completed-match and replay browse surfaces to durable public competitor identities

Status: done

## Story

As a spectator,
I want finished-match and replay surfaces to link into durable public competitor identities where the contract can support it honestly,
So that I can move from match outcomes to competitor context without relying on ambiguous display-name matching.

## Acceptance Criteria

1. Completed-match and/or replay browse routes expose durable public competitor identifiers only where the backend can provide them honestly.
2. The web client adds profile navigation only from rows with durable identifiers; no display-name heuristics or invented identity mapping are introduced.
3. Existing completed-match/history/replay behavior remains unchanged aside from the new read-only navigation.
4. Focused verification passes.

## Tasks / Subtasks

- [x] Extend the completed-match and history public response contracts with honest competitor summaries. (AC: 1, 3)
- [x] Load the required persisted `ApiKey` rows during public reads so agent competitor rows expose durable public `agent_id` values when they are honestly available. (AC: 1)
- [x] Preserve legacy winner display-name fields and replay behavior while adding read-only competitor roster metadata. (AC: 2, 3)
- [x] Update the web client types, runtime validators, and public pages to render competitor links only for rows with non-null `agent_id`. (AC: 2, 3)
- [x] Run the required focused DB/API/e2e/client verification suite. (AC: 4)

## Dev Notes

- Story 41.2 builds directly on 41.1 and the DB-backed public replay/completed-match surfaces from epics 19, 29, 38, and 39.
- Keep the contract additive and honest: no display-name matching, no synthetic human IDs, and no replay-route shape breakage.

## Dev Agent Record

### Debug Log

- 2026-04-02: Continued the partial worktree instead of restarting the story from scratch.
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k "completed or history or public_leaderboard_route_exposes_honest_agent_ids_by_competitor_kind"`
- `uv run pytest -o addopts='' tests/test_db_registry.py -k "completed_match or history or ranked_competitors_with_stable_tiebreakers"`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k "public_leaderboard_and_completed_match_smoke_flow_runs_through_real_process or completion_to_leaderboard_smoke_flow_runs_through_real_process"`
- `cd client && npm test -- --run src/lib/api.test.ts src/components/public/completed-matches-page.test.tsx src/components/public/match-history-page.test.tsx`

### Completion Notes

- Finished the server-side completed-match and history contract so both public reads load any needed `ApiKey` rows and derive durable public `agent_id` values through the existing identity resolver instead of display-name heuristics.
- Added additive `winning_competitors` and `competitors` summaries while preserving the legacy `winning_player_display_names` field and replay payload behavior unchanged.
- Updated client runtime validators to accept the new summaries and reject dishonest payloads that assign human competitors an `agent_id`.
- Updated the completed matches and match history pages to render competitor links only when `agent_id` is non-null, leaving human rows as plain text.
- Kept the implementation small and explicit by reusing the existing public roster sort order and identity-loading helpers already present in the DB-backed public read path.

### File List

- `_bmad-output/implementation-artifacts/41-2-link-completed-match-and-replay-browse-surfaces-to-durable-public-competitor-identities.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `client/src/components/public/completed-matches-page.test.tsx`
- `client/src/components/public/completed-matches-page.tsx`
- `client/src/components/public/match-history-page.test.tsx`
- `client/src/components/public/match-history-page.tsx`
- `client/src/lib/api.test.ts`
- `client/src/lib/api.ts`
- `client/src/lib/types.ts`
- `server/db/public_read_assembly.py`
- `server/db/public_reads.py`
- `server/models/api.py`
- `tests/api/test_agent_api.py`
- `tests/e2e/test_api_smoke.py`
- `tests/test_db_registry.py`

### Change Log

- 2026-04-02: Completed Story 41.2 by wiring honest public competitor summaries through the completed-match and history reads, client validators, and public browse UI surfaces.
