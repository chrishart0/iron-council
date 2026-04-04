# Guided Live Owned-Agent Resolution Fix Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Repair the shipped guided live browser flow so the client can deterministically discover the authenticated human's joined owned agent from real server contracts instead of impossible test fixtures.

**Architecture:** Keep the fix additive and contract-first. Expose stable agent identity where the live client can honestly use it, then resolve the guided agent on the page by intersecting authenticated owned-agent data with the current match roster rather than assuming the human websocket `player_id` equals the agent player slot.

**Tech Stack:** FastAPI/Pydantic server models, DB-backed identity/public read helpers, Next.js/React client, TypeScript API validators, pytest, Vitest.

---

### Task 1: Add the missing identity fields to the real API contracts

**Objective:** Make the server return enough stable identity metadata for the live client to resolve joined owned agents honestly.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/db/public_read_assembly.py`
- Modify: `server/main.py`
- Modify: `server/db/api_key_lifecycle.py`
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`
- Test: `tests/api/test_agent_api.py`
- Test: `tests/e2e/test_api_smoke.py`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing tests**
- Add/adjust server tests so public match detail roster rows expose identity fields consistently with competitor kind.
- Add/adjust owned API key lifecycle tests so list/create/revoke responses expose stable `agent_id`.
- Add/adjust client API validator tests so they reject stale contract assumptions and accept the additive identity fields.

**Step 2: Run test to verify failure**
Run: `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py --no-cov -q -k 'public_match_detail or owned_api_key'`
Run: `source .venv/bin/activate && python -m pytest tests/e2e/test_api_smoke.py --no-cov -q -k 'public_match_detail or api_key'`
Run: `cd client && npm test -- --run src/lib/api.test.ts`
Expected: FAIL before implementation because the contract shape is incomplete or mismatched.

**Step 3: Write minimal implementation**
- Extend `PublicMatchRosterRow` with additive `agent_id` / `human_id` fields plus competitor-kind validation.
- Populate those fields in both DB-backed and in-memory fallback public match detail builders.
- Extend `OwnedApiKeySummary` with `agent_id` and keep lifecycle responses additive/backward compatible.
- Align client types/validators with the real server contract.

**Step 4: Run test to verify pass**
Run the same focused commands from Step 2.
Expected: PASS.

**Step 5: Commit**
```bash
git add server/models/api.py server/db/public_read_assembly.py server/main.py server/db/api_key_lifecycle.py client/src/lib/types.ts client/src/lib/api.ts tests/api/test_agent_api.py tests/e2e/test_api_smoke.py client/src/lib/api.test.ts
git commit -m "fix: expose guided live identity seams"
```

### Task 2: Resolve the guided agent on the live page from real authenticated data

**Objective:** Replace the fake `player_id == agent slot` assumption with deterministic owned-agent resolution based on the shipped authenticated session and roster contracts.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.tsx`
- Modify: `client/src/components/matches/human-live/human-match-live-types.ts`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Write failing tests**
- Add page tests proving the guided panel loads when the bearer-authenticated user owns an agent whose `agent_id` appears in the real roster shape.
- Add a regression showing the page no longer requires the impossible `player websocket id == agent player id` fixture.
- Keep failure/session-change behavior deterministic.

**Step 2: Run test to verify failure**
Run: `cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx`
Expected: FAIL before implementation because the page still resolves the guided agent incorrectly.

**Step 3: Write minimal implementation**
- Fetch owned API keys only when the page has a bearer token and the public match detail is ready.
- Resolve the guided agent by intersecting active owned `agent_id`s with roster `agent_id`s.
- Use the resolved `agent_id` for guided-session reads and preserve existing refresh/error semantics.
- If no owned joined agent is present, keep the guided panel hidden/idle rather than faking a match.

**Step 4: Run test to verify pass**
Run: `cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx`
Expected: PASS.

**Step 5: Commit**
```bash
git add client/src/components/matches/human-match-live-page.tsx client/src/components/matches/human-live/human-match-live-types.ts client/src/components/matches/human-match-live-page.test.tsx
git commit -m "fix: resolve guided live agent from owned keys"
```

### Task 3: Re-verify story 49.4 end-to-end and close out BMAD artifacts

**Objective:** Prove the guided live flow now matches the real contracts and update story artifacts accordingly.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/49-4-add-guided-agent-controls-to-the-live-web-client.md`
- Test: `tests/api/test_agent_api.py`
- Test: `tests/e2e/test_api_smoke.py`
- Test: `client/src/lib/api.test.ts`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Run focused verification**
Run: `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py --no-cov -q -k 'public_match_detail or owned_api_key or guided'`
Run: `source .venv/bin/activate && python -m pytest tests/e2e/test_api_smoke.py --no-cov -q -k 'public_match_detail or api_key'`
Run: `cd client && npm test -- --run src/lib/api.test.ts src/components/matches/human-match-live-page.test.tsx`

**Step 2: Run repo gate**
Run: `source .venv/bin/activate && make quality`
Expected: PASS.

**Step 3: Update BMAD artifact**
Record the real follow-up fix, verification commands, and final completion notes in Story 49.4.

**Step 4: Commit**
```bash
git add _bmad-output/implementation-artifacts/49-4-add-guided-agent-controls-to-the-live-web-client.md docs/plans/2026-04-04-guided-live-owned-agent-resolution-fix.md
git commit -m "docs: close guided live contract fix"
```
