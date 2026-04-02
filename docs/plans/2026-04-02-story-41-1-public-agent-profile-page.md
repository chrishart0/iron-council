# Story 41.1 Public Agent Profile Page Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Ship a read-only public `/agents/{agentId}` web route backed by the existing `/api/v1/agents/{agent_id}/profile` API, and wire leaderboard agent rows to it without inventing human profile destinations.

**Architecture:** Extend the existing public leaderboard contract with an explicit optional `agent_id`, keep the server as the source of truth for whether a row is linkable, then add a small client fetcher + typed validator + read-only page component for public agent profiles. Verification should cover the API contract, client boundary, page behavior, and the repo-managed quality gate.

**Tech Stack:** FastAPI/Pydantic server, Next.js 16 client, TypeScript, Vitest, pytest, uv, make.

---

### Task 1: Extend the public leaderboard contract with an explicit durable agent id

**Objective:** Make the leaderboard response tell the client which rows can honestly link to an agent profile.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/db/public_read_assembly.py`
- Modify: `server/db/public_reads.py`
- Test: `tests/api/test_agent_api.py`
- Test: `tests/e2e/test_api_smoke.py`
- Test: `tests/test_db_registry.py`

**Step 1: Write failing server/API tests**

Add assertions that:
- agent leaderboard rows include `agent_id`
- human leaderboard rows include `agent_id: null`
- DB-backed smoke/regression fixtures preserve the contract

**Step 2: Run focused tests to verify failure**

Run:
```bash
uv run pytest -o addopts='' tests/api/test_agent_api.py -k "public_leaderboard or openapi_declares_public_read_contracts"
```
Expected: FAIL because `agent_id` is missing from the current response model/assembly.

**Step 3: Write the minimal implementation**

Update `LeaderboardEntry` to include `agent_id: str | None`, then compute it in `build_public_leaderboard()` only for honest agent identities.

**Step 4: Run focused server verification**

Run:
```bash
uv run pytest -o addopts='' tests/api/test_agent_api.py -k "public_leaderboard or agent_profile_routes_return_finalized_settlement_results or openapi_declares_public_read_contracts"
uv run pytest -o addopts='' tests/test_db_registry.py -k "solo_terminal_winner_coherent_across_public_reads or ranked_competitors_with_stable_tiebreakers"
uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k "public_leaderboard_and_completed_match_smoke_flow_runs_through_real_process or completion_to_leaderboard_smoke_flow_runs_through_real_process"
```
Expected: PASS.

**Step 5: Commit**

```bash
git add server/models/api.py server/db/public_read_assembly.py server/db/public_reads.py tests/api/test_agent_api.py tests/test_db_registry.py tests/e2e/test_api_smoke.py
git commit -m "feat: add durable agent ids to public leaderboard rows"
```

### Task 2: Add typed client support for public agent profiles

**Objective:** Create the client-side contract and fetch helper for the existing public agent profile API.

**Files:**
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing client API tests**

Add tests for:
- successful `fetchPublicAgentProfile("agent-player-2")`
- deterministic not-found state mapping
- invalid payload rejection
- leaderboard validator requiring explicit `agent_id` shape

**Step 2: Run focused client tests to verify failure**

Run:
```bash
cd client && npm test -- --run src/lib/api.test.ts
```
Expected: FAIL because the fetch helper/types/validators do not exist yet.

**Step 3: Write the minimal implementation**

Add:
- `PublicAgentProfileResponse`
- `PublicAgentProfileError`
- `fetchPublicAgentProfile()`
- a runtime validator that keeps `agent_id` explicit and type-safe

**Step 4: Run focused client verification**

Run:
```bash
cd client && npm test -- --run src/lib/api.test.ts
```
Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/lib/types.ts client/src/lib/api.ts client/src/lib/api.test.ts
git commit -m "feat: add client public agent profile API support"
```

### Task 3: Ship the read-only `/agents/[agentId]` page and leaderboard links

**Objective:** Render the public profile UI and link only agent leaderboard rows that have durable ids.

**Files:**
- Create: `client/src/app/agents/[agentId]/page.tsx`
- Create: `client/src/app/agents/[agentId]/page.test.tsx`
- Create: `client/src/components/public/public-agent-profile-page.tsx`
- Create: `client/src/components/public/public-agent-profile-page.test.tsx`
- Modify: `client/src/components/public/public-leaderboard-page.tsx`
- Modify: `client/src/components/public/public-leaderboard-page.test.tsx`

**Step 1: Write failing page/component tests**

Add tests that prove:
- `/agents/[agentId]` renders loading → ready → unavailable states
- ready state shows display name, seeded status, rating, and history from the API response
- invalid/unknown ids show deterministic unavailable copy
- agent leaderboard rows link to `/agents/{agentId}`
- human rows remain plain text without profile links

**Step 2: Run focused page/component tests to verify failure**

Run:
```bash
cd client && npm test -- --run src/components/public/public-leaderboard-page.test.tsx src/components/public/public-agent-profile-page.test.tsx src/app/agents/[agentId]/page.test.tsx
```
Expected: FAIL because the page/component/link wiring does not exist yet.

**Step 3: Write the minimal implementation**

Implement a boring read-only UI with stable navigation and no new write paths.

**Step 4: Run focused page/component verification**

Run:
```bash
cd client && npm test -- --run src/components/public/public-leaderboard-page.test.tsx src/components/public/public-agent-profile-page.test.tsx src/app/agents/[agentId]/page.test.tsx
```
Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/app/agents/[agentId]/page.tsx client/src/app/agents/[agentId]/page.test.tsx client/src/components/public/public-agent-profile-page.tsx client/src/components/public/public-agent-profile-page.test.tsx client/src/components/public/public-leaderboard-page.tsx client/src/components/public/public-leaderboard-page.test.tsx
git commit -m "feat: add public agent profile page"
```

### Task 4: Run review-quality verification, BMAD closeout, and shippable cleanup

**Objective:** Prove the story is integrated, simple, and reflected in BMAD tracking.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/41-1-add-public-agent-profile-page-in-the-web-client.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Review: touched server/client/tests files

**Step 1: Remove worker junk and keep only intended repo files**

Delete any prompt scratchpads or Codex-only notes before merge if they are not part of the product story.

**Step 2: Run strongest practical repo-managed verification**

Run:
```bash
source .venv/bin/activate && make quality
```
If the worktree is missing tools, bootstrap first:
```bash
uv sync --extra dev --frozen
make client-install
source .venv/bin/activate && make quality
```
Expected: PASS.

**Step 3: Perform review passes**

Check:
- spec compliance with Story 41.1 acceptance criteria
- code quality and test quality
- no overbuilt profile abstraction
- human rows remain non-clickable

**Step 4: Update BMAD artifacts**

Mark Story 41.1 done, update debug log with real commands/outcomes, and advance `next_story`.

**Step 5: Commit and push**

```bash
git add docs/plans/2026-04-02-story-41-1-public-agent-profile-page.md _bmad-output/implementation-artifacts/41-1-add-public-agent-profile-page-in-the-web-client.md _bmad-output/implementation-artifacts/sprint-status.yaml
git add client/src server tests
git commit -m "feat: add public agent profile page"
git push origin master
```
