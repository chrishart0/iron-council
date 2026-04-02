# Story: 41.1 Add a public agent profile page in the web client

Status: done

## Story

As a player or spectator,
I want to open a public agent profile page from the leaderboard,
So that I can inspect an agent's settled rating and match history instead of only seeing a one-line leaderboard row.

## Acceptance Criteria

1. The web client ships a public `/agents/{agentId}` route that loads the existing `/api/v1/agents/{agent_id}/profile` contract and renders display name, seeded status, rating, and history in a stable read-only UI.
2. Public leaderboard rows for agents expose a durable link target into `/agents/{agentId}`; human rows remain plain text with no invented profile route.
3. The leaderboard/public profile contract stays explicit and type-safe: the client receives a durable `agent_id` only where the backend can provide one honestly, and invalid/unknown agent ids render a deterministic unavailable state.
4. Focused server/client verification passes, followed by the strongest practical repo-managed quality checks for the touched seam.

## Tasks / Subtasks

- [x] Add the smallest public leaderboard contract extension needed to carry durable agent profile ids without inventing human-profile destinations. (AC: 2, 3)
- [x] Add client API/types for the public agent profile route and a read-only `/agents/{agentId}` page. (AC: 1, 3)
- [x] Wire leaderboard agent rows to the new profile route and keep human rows non-clickable. (AC: 2)
- [x] Add focused API/client tests plus repo-managed verification. (AC: 4)

## Dev Notes

- Reuse the already-shipped `/api/v1/agents/{agent_id}/profile` route; do not build a parallel client-only profile abstraction.
- Keep this story agent-only. Public human profile pages are out of scope until the backend defines a stable public identity contract for them.
- Prefer optional `agent_id` on leaderboard rows over any display-name heuristics.
- Keep the UI boring and read-only; no social features, follow actions, or new write paths.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the first Epic 41 slice after Epic 40 finalized rating/profile reads server-side but the public web client still lacked a profile destination.
- 2026-04-02 16:29 UTC: `cd client && npm test -- --run src/lib/api.test.ts src/components/public/public-leaderboard-page.test.tsx src/components/public/public-agent-profile-page.test.tsx src/app/agents/[agentId]/page.test.tsx` failed first on duplicated `fetchPublicAgentProfile`/validator declarations plus malformed leaderboard JSX; fixed the client API/module cleanup and reran green.
- 2026-04-02 16:32 UTC: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k "public_leaderboard or agent_profile_routes_return_finalized_settlement_results or public_and_authenticated_agent_profile_routes_return_stable_shapes or openapi_declares_public_read_contracts"` passed.
- 2026-04-02 16:32 UTC: `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k "public_leaderboard_and_completed_match_smoke_flow_runs_through_real_process or completion_to_leaderboard_smoke_flow_runs_through_real_process or agent_join_and_profile_smoke_flow_runs_through_real_process"` passed.
- 2026-04-02 16:37 UTC: `source .venv/bin/activate && make quality` initially failed on formatting in `server/db/public_reads.py`; ran `uv run ruff format server/db/public_reads.py`.
- 2026-04-02 16:38 UTC: `source .venv/bin/activate && make quality` then failed because `uv run mypy` could not spawn `mypy`; ran `uv sync --extra dev --frozen` to restore the locked dev toolchain.
- 2026-04-02 16:36 UTC: The first full-quality pytest pass exposed stale DB-backed leaderboard assertions in `tests/test_db_registry.py`; updated them for the new optional `agent_id` contract and confirmed with `uv run pytest -o addopts='' tests/test_db_registry.py -k "solo_terminal_winner_coherent_across_public_reads or ranked_competitors_with_stable_tiebreakers"`.
- 2026-04-02 16:40 UTC: Final `source .venv/bin/activate && make quality` passed, including Ruff, mypy, full pytest, client typecheck/test, and Next build.

### Completion Notes

- Added client-side public agent profile types, validators, and `fetchPublicAgentProfile`, and tightened leaderboard validation so human rows must keep `agent_id: null`.
- Added the read-only Next.js route `/agents/[agentId]` with deterministic loading, ready, and unavailable states backed directly by `/api/v1/agents/{agent_id}/profile`.
- Updated leaderboard rendering so agent rows link to `/agents/{agentId}` only when the backend supplies a durable `agent_id`; human rows remain plain text.
- Extended client coverage for the new route/page/API surface and updated server/e2e/DB-backed assertions to the explicit optional `agent_id` leaderboard contract.
- Full repo quality gate passed after syncing the locked dev environment and formatting the touched server read module.

### File List

- `_bmad-output/implementation-artifacts/41-1-add-public-agent-profile-page-in-the-web-client.md`
- `CODEX_41_1_CLIENT_FINISH.md`
- `CODEX_41_1_PROMPT.md`
- `client/src/app/agents/[agentId]/page.test.tsx`
- `client/src/app/agents/[agentId]/page.tsx`
- `client/src/components/public/public-agent-profile-page.test.tsx`
- `client/src/components/public/public-agent-profile-page.tsx`
- `client/src/components/public/public-leaderboard-page.test.tsx`
- `client/src/components/public/public-leaderboard-page.tsx`
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

- 2026-04-02: Drafted Story 41.1 for public agent profile surfacing in the web client.
- 2026-04-02: Added the client public agent profile contract, read-only `/agents/[agentId]` route, leaderboard profile links for agent rows, and verification/artifact updates to complete Story 41.1.
