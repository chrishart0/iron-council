# Story 41.2 Competitor Identity Links Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extend the completed-match and replay read models with honest durable competitor identity fields, then wire the public client to add profile navigation only for rows that already expose a stable agent identity.

**Architecture:** Reuse the existing public agent identity resolution on the server to add a small shared public competitor summary shape to completed-match summaries and match-history metadata. Keep human competitors read-only with `agent_id: null`, preserve existing browse/replay behavior, and add only lightweight client-side rendering/link logic on the completed-matches and history pages.

**Tech Stack:** FastAPI/Pydantic server, SQLAlchemy, Next.js 16, TypeScript, Vitest, pytest, uv, make.

---

### Task 1: Extend completed-match and history read models with explicit public competitor summaries

**Objective:** Make the backend expose durable competitor identifiers only where it can do so honestly.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/db/public_read_assembly.py`
- Modify: `server/db/public_reads.py`
- Test: `tests/api/test_public_routes.py`
- Test: `tests/test_db_registry.py`
- Test: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing server/API tests**

Add assertions that:
- completed-match summaries include a structured winner list with `display_name`, `competitor_kind`, and `agent_id`
- agent winners expose non-null durable `agent_id`
- human winners keep `agent_id: null`
- match history metadata includes a stable competitor roster with the same explicit contract
- existing display-name fields and replay tick behavior still work

**Step 2: Run focused tests to verify failure**

Run:
```bash
uv run pytest -o addopts='' tests/api/test_public_routes.py -k "completed or history"
uv run pytest -o addopts='' tests/test_db_registry.py -k "completed_match or history or leaderboard"
```
Expected: FAIL because the current completed-match and history contracts do not carry structured competitor identities.

**Step 3: Write the minimal implementation**

Add a shared public competitor summary model and populate it from persisted `Player` rows using the existing honest agent identity resolver. Keep human rows explicit with `agent_id=None`, preserve the legacy display-name list for completed matches, and add the competitor roster to match-history metadata without changing replay tick semantics.

**Step 4: Run focused server verification**

Run:
```bash
uv run pytest -o addopts='' tests/api/test_public_routes.py -k "completed or history"
uv run pytest -o addopts='' tests/test_db_registry.py -k "completed_match or history or leaderboard"
uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k "public_leaderboard_and_completed_match_smoke_flow_runs_through_real_process or completion_to_leaderboard_smoke_flow_runs_through_real_process"
```
Expected: PASS.

**Step 5: Commit**

```bash
git add server/models/api.py server/db/public_read_assembly.py server/db/public_reads.py tests/api/test_public_routes.py tests/test_db_registry.py tests/e2e/test_api_smoke.py
git commit -m "feat: expose public competitor identities in history reads"
```

### Task 2: Add typed client support for structured competitor summaries

**Objective:** Keep the client contract explicit and runtime-validated before wiring any new links.

**Files:**
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing client API/validator tests**

Add tests proving that:
- completed-match responses require the new structured winner list shape
- match-history responses require the new competitor roster shape
- agent rows may carry a string `agent_id`
- human rows must keep `agent_id: null`
- invalid shapes are rejected deterministically

**Step 2: Run focused client tests to verify failure**

Run:
```bash
cd client && npm test -- --run src/lib/api.test.ts
```
Expected: FAIL because the current validators/types do not know the structured competitor fields.

**Step 3: Write the minimal implementation**

Add a shared `PublicCompetitorSummary` type, extend the completed-match and match-history types, and tighten the runtime validators so only honest agent rows can carry linkable ids.

**Step 4: Run focused client verification**

Run:
```bash
cd client && npm test -- --run src/lib/api.test.ts
```
Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/lib/types.ts client/src/lib/api.ts client/src/lib/api.test.ts
git commit -m "feat: add client public competitor identity contract"
```

### Task 3: Wire completed-match and replay pages to the new public identity contract

**Objective:** Add read-only profile navigation only where the backend now exposes durable agent identities.

**Files:**
- Modify: `client/src/components/public/completed-matches-page.tsx`
- Modify: `client/src/components/public/completed-matches-page.test.tsx`
- Modify: `client/src/components/public/match-history-page.tsx`
- Modify: `client/src/components/public/match-history-page.test.tsx`

**Step 1: Write failing page/component tests**

Add assertions that:
- completed-match cards render linked winner names for agent winners with `agent_id`
- human winners remain plain text, not links
- the replay/history page shows a read-only competitor roster section using the shipped history metadata
- only agent competitors with durable ids link to `/agents/{agentId}`
- existing replay links, tick picker, and error states still work

**Step 2: Run focused page/component tests to verify failure**

Run:
```bash
cd client && npm test -- --run src/components/public/completed-matches-page.test.tsx src/components/public/match-history-page.test.tsx
```
Expected: FAIL because the pages do not render the new competitor-summary data yet.

**Step 3: Write the minimal implementation**

Render a compact list of competitors/winners using the explicit contract. Use `Link` only for rows with non-null `agent_id`, and keep everything else as static read-only text.

**Step 4: Run focused page/component verification**

Run:
```bash
cd client && npm test -- --run src/components/public/completed-matches-page.test.tsx src/components/public/match-history-page.test.tsx
```
Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/components/public/completed-matches-page.tsx client/src/components/public/completed-matches-page.test.tsx client/src/components/public/match-history-page.tsx client/src/components/public/match-history-page.test.tsx
git commit -m "feat: link public replay surfaces to agent profiles"
```

### Task 4: Run review-quality verification, BMAD closeout, and simplification

**Objective:** Prove Story 41.2 is integrated, simple, and correctly tracked.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/41-2-link-completed-match-and-replay-browse-surfaces-to-durable-public-competitor-identities.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `docs/plans/2026-04-02-story-41-2-competitor-identity-links.md`

**Step 1: Remove worker junk and keep only intended repo files**

Delete any prompt scratchpads, coverage artifacts, or worktree-only notes before merge.

**Step 2: Run strongest practical repo-managed verification**

Run:
```bash
source .venv/bin/activate && make quality
```
If the worktree needs bootstrap first:
```bash
uv sync --extra dev --frozen
make client-install
source .venv/bin/activate && make quality
```
Expected: PASS.

**Step 3: Perform review passes**

Check:
- Story 41.2 acceptance criteria and honest-contract scope
- no display-name heuristics or invented human profile destinations
- code/test quality and overcomplexity
- KISS / repo-convention compliance

**Step 4: Update BMAD artifacts**

Mark Story 41.2 done, advance `next_story` to 41.3, and record the real verification commands/outcomes in the story debug log.

**Step 5: Commit and push**

```bash
git add docs/plans/2026-04-02-story-41-2-competitor-identity-links.md _bmad-output/implementation-artifacts/41-2-link-completed-match-and-replay-browse-surfaces-to-durable-public-competitor-identities.md _bmad-output/implementation-artifacts/sprint-status.yaml
git add client/src server tests
git commit -m "feat: add competitor profile links to replay surfaces"
git push origin master
```
