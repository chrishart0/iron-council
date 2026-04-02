# Story: 41.3 Add read-only public player/human profile scaffolding once a stable public identity contract exists

Status: done

## Story

As a player or spectator,
I want the public web client to expose a consistent profile destination for non-agent competitors once the backend defines that identity surface,
So that the public ranking UX does not stop at agents only.

## Acceptance Criteria

1. A stable backend public identity contract exists for non-agent competitors before any client route is introduced.
2. The web client adds read-only public profile navigation only after that contract is explicit and tested.
3. Existing public browse surfaces do not guess or infer non-agent profile identities from display names.
4. Focused verification passes.

## Tasks / Subtasks

- [x] Add a stable public human profile API contract and DB-backed route using durable `human:{user_id}` identities. (AC: 1)
- [x] Extend public leaderboard/completed/history competitor summaries with honest optional `human_id` values while preserving existing `agent_id` behavior. (AC: 1, 3)
- [x] Add client validators/fetch support plus a read-only `/humans/[humanId]` page. (AC: 2)
- [x] Link leaderboard/completed/history human rows only when explicit `human_id` is present. (AC: 2, 3)
- [x] Run focused verification and review passes. (AC: 4)

## Dev Notes

- Reuse persisted human identity `human:{user_id}` as the durable public profile key.
- Keep the implementation explicit and additive: no display-name heuristics, no synthetic merged profile abstraction.
- Human competitors expose `human_id` and keep `agent_id: null`; agent competitors expose `agent_id` and keep `human_id: null`.

## Dev Agent Record

### Debug Log

- 2026-04-02 19:46 UTC: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k "human_profile or public_leaderboard or completed or history or openapi_declares_public_read_contracts" && uv run pytest -o addopts='' tests/api/test_agent_process_api.py -k "non_agent_public_profile" && uv run pytest -o addopts='' tests/test_db_registry.py -k "human_profile or public_leaderboard or completed_match or history or coherent_across_public_reads or settled_elo" && uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k "public_leaderboard_and_completed_match_smoke_flow_runs_through_real_process or completion_to_leaderboard_smoke_flow_runs_through_real_process"` initially failed because the new `human_id` contract had not been propagated through all focused expectations yet.
- 2026-04-02 19:50 UTC: Added the missing `get_human_profile_from_db` compatibility export in `server/db/registry.py` so the DB-focused regression suite could import the new public human profile helper through the existing facade.
- 2026-04-02 19:54 UTC: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k "human_profile or public_leaderboard or completed or history or openapi_declares_public_read_contracts" && uv run pytest -o addopts='' tests/api/test_agent_process_api.py -k "non_agent_public_profile" && uv run pytest -o addopts='' tests/test_db_registry.py -k "human_profile or public_leaderboard or completed_match or history or coherent_across_public_reads or settled_elo" && uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k "public_leaderboard_and_completed_match_smoke_flow_runs_through_real_process or completion_to_leaderboard_smoke_flow_runs_through_real_process" && cd client && npm test -- --run src/lib/api.test.ts src/components/public/public-leaderboard-page.test.tsx src/components/public/completed-matches-page.test.tsx src/components/public/match-history-page.test.tsx src/components/public/public-human-profile-page.test.tsx src/app/humans/[humanId]/page.test.tsx` failed on missing client worktree dependencies (`vitest: not found`).
- 2026-04-02 19:55 UTC: `make client-install` restored the client toolchain in the story worktree.
- 2026-04-02 19:57 UTC: Re-ran the focused server/e2e/client verification command above; server and e2e suites passed, then client page tests exposed an honest Next `Link` href expectation mismatch for `human:` IDs (`/humans/human:...` vs encoded `%3A`).
- 2026-04-02 19:58 UTC: Updated the affected public page tests to assert the real rendered href shape and reran `cd client && npm test -- --run src/lib/api.test.ts src/components/public/public-leaderboard-page.test.tsx src/components/public/completed-matches-page.test.tsx src/components/public/match-history-page.test.tsx src/components/public/public-human-profile-page.test.tsx src/app/humans/[humanId]/page.test.tsx` green.
- 2026-04-02 20:40 UTC: `source .venv/bin/activate && make quality` initially failed in the worktree because `server/db/identity_hydration.py` passed a `Sequence[PlayerMatchSettlement]` into `load_settlement_aggregates_by_identity`, whose signature was typed too narrowly as `list[...]`.
- 2026-04-02 20:42 UTC: Broadened `server/db/rating_settlement.py` to accept `Sequence[PlayerMatchSettlement]`, reran `source .venv/bin/activate && make quality`, and got the full repo quality harness green (Ruff, mypy, pytest, client lint/test/build).
- 2026-04-02 20:48 UTC: Review found two follow-up gaps: the public human profile route returned `503 human_profile_unavailable` without declaring that response in OpenAPI, and the API suite did not pin that unavailable-path contract.
- 2026-04-02 20:50 UTC: Added the missing `503` route schema plus a deterministic unavailable-path API regression, removed the temporary Codex prompt scratch file, reran focused server/client verification, reformatted the touched test, and reran `source .venv/bin/activate && make quality` green.
- 2026-04-02 20:50 UTC: Final spec-compliance and code-quality review passed with `next_story: null` kept intentionally because Epic 41 is fully closed and no Story 42 artifact exists yet.

### Completion Notes

- Added a public DB-backed `GET /api/v1/humans/{human_id}/profile` contract and hydration path that resolves durable public human identities from persisted settlement/user data instead of display-name guesses.
- Extended public leaderboard, completed-match, and replay/history competitor summaries with honest optional `human_id` fields while preserving the additive explicit `agent_id` contract for agent competitors.
- Added client runtime types, validation, and `fetchPublicHumanProfile`, plus a read-only `/humans/[humanId]` route and public human profile page with deterministic loading and unavailable states.
- Updated leaderboard, completed-match, and history pages so human rows link only when explicit `human_id` is present and agent rows continue using `/agents/{agentId}`.
- Declared and regression-tested the DB-unavailable `503 human_profile_unavailable` contract for the public human profile route, then reran the full quality harness green.
- Removed temporary worker scratch prompts before closeout and kept the implementation small, explicit, and by-the-book.

### File List

- `_bmad-output/implementation-artifacts/41-3-add-read-only-public-player-human-profile-scaffolding-once-a-stable-public-identity-contract-exists.md`
- `client/src/app/humans/[humanId]/page.test.tsx`
- `client/src/app/humans/[humanId]/page.tsx`
- `client/src/components/public/completed-matches-page.test.tsx`
- `client/src/components/public/completed-matches-page.tsx`
- `client/src/components/public/match-history-page.test.tsx`
- `client/src/components/public/match-history-page.tsx`
- `client/src/components/public/public-human-profile-page.test.tsx`
- `client/src/components/public/public-human-profile-page.tsx`
- `client/src/components/public/public-leaderboard-page.test.tsx`
- `client/src/components/public/public-leaderboard-page.tsx`
- `client/src/lib/api.test.ts`
- `client/src/lib/api.ts`
- `client/src/lib/types.ts`
- `server/api/authenticated_read_routes.py`
- `server/db/identity.py`
- `server/db/identity_hydration.py`
- `server/db/public_read_assembly.py`
- `server/db/registry.py`
- `server/db/rating_settlement.py`
- `server/models/api.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/e2e/test_api_smoke.py`
- `tests/test_db_registry.py`

### Change Log

- 2026-04-02: Completed Story 41.3 by shipping the public human profile API/client surface, honest `human_id` browse contracts, unavailable-path contract coverage, full quality verification, and BMAD closeout.
