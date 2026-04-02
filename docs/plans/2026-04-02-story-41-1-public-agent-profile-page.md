# Story 41.1 Public Agent Profile Page Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a public web-client agent profile page and wire leaderboard agent rows to it using a durable backend `agent_id` contract.

**Architecture:** Keep the story contract-first and boring. Extend the public leaderboard read model with an optional `agent_id` only for agent competitors, add client validators/types for both leaderboard and public agent profiles, then build a read-only `/agents/[agentId]` page that consumes the existing shipped profile route with deterministic loading and unavailable states.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, TypeScript, Next.js App Router, React, Vitest, pytest, uv, npm.

---

### Task 1: Extend the public leaderboard contract with durable agent ids

**Objective:** Let the web client link agent rows to real profile routes without inventing identity heuristics.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/db/public_read_assembly.py`
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing API assertions**

Update the existing leaderboard API tests to expect an `agent_id` field on agent rows and `null` on human rows.

**Step 2: Run test to verify failure**

Run:

```bash
source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'public_leaderboard_and_completed_match_routes_return_compact_db_backed_reads or completion_to_leaderboard_smoke_flow_runs_through_real_process'
```

Expected: FAIL because the current response model does not expose `agent_id`.

**Step 3: Write minimal implementation**

Add an optional `agent_id` field to `LeaderboardEntry` and populate it only for agent competitors from the persisted identity that already backs settlement/profile reads.

**Step 4: Run test to verify pass**

Re-run the same command and expect PASS.

**Step 5: Commit**

```bash
git add server/models/api.py server/db/public_read_assembly.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
git commit -m "feat: expose leaderboard agent profile ids"
```

### Task 2: Add client API/types for public agent profiles

**Objective:** Teach the client to validate and load the shipped public profile route.

**Files:**
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`
- Modify: `client/src/lib/api.test.ts`

**Step 1: Write failing client API tests**

Add behavior-first tests for:
- successful `fetchPublicAgentProfile(agentId)` parsing
- 404 -> deterministic not-found error kind/message
- invalid payload -> unavailable error
- leaderboard validator accepting `agent_id` only when `competitor_kind === 'agent'`

**Step 2: Run test to verify failure**

Run:

```bash
cd client && npm test -- --run src/lib/api.test.ts
```

Expected: FAIL because the helper/types/validators do not exist yet.

**Step 3: Write minimal implementation**

Add typed profile shapes, a `PublicAgentProfileError`, a `fetchPublicAgentProfile` helper, and runtime validators that keep the contract explicit.

**Step 4: Run test to verify pass**

Re-run the same command and expect PASS.

**Step 5: Commit**

```bash
git add client/src/lib/types.ts client/src/lib/api.ts client/src/lib/api.test.ts
git commit -m "feat: add public agent profile client api"
```

### Task 3: Build the read-only `/agents/[agentId]` page and leaderboard links

**Objective:** Surface the public profile in the web client and connect leaderboard agent rows to it.

**Files:**
- Create: `client/src/app/agents/[agentId]/page.tsx`
- Create: `client/src/components/public/public-agent-profile-page.tsx`
- Create: `client/src/components/public/public-agent-profile-page.test.tsx`
- Modify: `client/src/components/public/public-leaderboard-page.tsx`
- Modify: `client/src/components/public/public-leaderboard-page.test.tsx`

**Step 1: Write failing component tests**

Add tests that prove:
- the new page shows loading, ready, and unavailable/not-found states
- the ready state renders display name, seeded status, rating, and history
- leaderboard agent rows link to `/agents/{agentId}`
- human rows stay non-clickable text

**Step 2: Run test to verify failure**

Run:

```bash
cd client && npm test -- --run src/components/public/public-agent-profile-page.test.tsx src/components/public/public-leaderboard-page.test.tsx
```

Expected: FAIL because the page/components/links do not exist yet.

**Step 3: Write minimal implementation**

Follow existing public-page patterns (`match-history-page`, `completed-matches-page`, `public-leaderboard-page`) for session hydration, deterministic errors, and stable navigation.

**Step 4: Run test to verify pass**

Re-run the same command and expect PASS.

**Step 5: Commit**

```bash
git add client/src/app/agents/[agentId]/page.tsx client/src/components/public/public-agent-profile-page.tsx client/src/components/public/public-agent-profile-page.test.tsx client/src/components/public/public-leaderboard-page.tsx client/src/components/public/public-leaderboard-page.test.tsx
git commit -m "feat: add public agent profile page"
```

### Task 4: Run full story verification, review, and BMAD closeout

**Objective:** Prove the story from the public boundary, simplify if needed, and leave the BMAD artifacts honest.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/41-1-add-public-agent-profile-page-in-the-web-client.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run focused verification**

Run:

```bash
source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'public_leaderboard_and_completed_match_routes_return_compact_db_backed_reads or public_and_authenticated_agent_profile_reads_expose_finalized_settlement_results or openapi_declares_public_read_contracts'
source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'public_leaderboard_and_completed_match_smoke_flow_runs_through_real_process or completion_to_leaderboard_smoke_flow_runs_through_real_process'
cd client && npm test -- --run src/lib/api.test.ts src/components/public/public-agent-profile-page.test.tsx src/components/public/public-leaderboard-page.test.tsx src/app/page.test.tsx
```

Expected: PASS.

**Step 2: Run repo-managed quality gate**

Run:

```bash
source .venv/bin/activate && make quality
```

Expected: PASS.

**Step 3: Simplify and review**

Check for over-complexity, unnecessary abstractions, or any client/server contract drift. Keep the solution KISS and aligned with the repo's existing public-page patterns.

**Step 4: Update BMAD artifacts**

Mark Story 41.1 done, record the exact verification commands, and advance `next_story` to `41-2-link-completed-match-and-replay-browse-surfaces-to-durable-public-competitor-identities`.

**Step 5: Commit**

```bash
git add _bmad-output/implementation-artifacts/41-1-add-public-agent-profile-page-in-the-web-client.md _bmad-output/implementation-artifacts/sprint-status.yaml server/models/api.py server/db/public_read_assembly.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py client/src/lib/types.ts client/src/lib/api.ts client/src/lib/api.test.ts client/src/app/agents/[agentId]/page.tsx client/src/components/public/public-agent-profile-page.tsx client/src/components/public/public-agent-profile-page.test.tsx client/src/components/public/public-leaderboard-page.tsx client/src/components/public/public-leaderboard-page.test.tsx
git commit -m "feat: add public agent profile page"
```
