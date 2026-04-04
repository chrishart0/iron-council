# Story 49.4 Guided Agent Live Client Controls Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a narrow guided-mode browser surface to the authenticated live match page so the owner can read guided-session context, send private guidance, and submit pre-tick overrides through the shipped contracts.

**Architecture:** Extend the existing authenticated human live page instead of creating a new route family. Add typed client API helpers for guided-session/guidance/override contracts, then layer a small guided panel into the current live snapshot shell that reads guided-session data alongside the websocket snapshot while keeping the websocket plus guided-session read model authoritative after writes.

**Tech Stack:** Next.js client, React state/hooks, TypeScript, Vitest + Testing Library, existing bearer-token session provider, existing REST + websocket contracts.

---

### Task 1: Add typed guided client contract helpers

**Objective:** Teach the client API layer and shared types about guided-session reads and guidance/override writes without widening the backend contract.

**Files:**
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing tests**

Add focused API-helper tests for:
- fetching `GET /api/v1/matches/{matchId}/agents/{agentId}/guided-session`
- posting `POST /api/v1/matches/{matchId}/agents/{agentId}/guidance`
- posting `POST /api/v1/matches/{matchId}/agents/{agentId}/override`
- structured error propagation for guided failures
- strict but additive response validation

**Step 2: Run test to verify failure**

Run: `cd client && npm test -- --run src/lib/api.test.ts`
Expected: FAIL because the guided types/helpers/validators do not exist yet.

**Step 3: Write minimal implementation**

Add types for:
- guided-session response
- guidance create + acceptance response
- override create + acceptance response

Add helpers in `api.ts` for:
- `fetchOwnedAgentGuidedSession(...)`
- `submitOwnedAgentGuidance(...)`
- `submitOwnedAgentOverride(...)`
- a small shared guided-action error mapper

**Step 4: Run test to verify pass**

Run: `cd client && npm test -- --run src/lib/api.test.ts`
Expected: PASS for the new helper coverage.

**Step 5: Commit**

```bash
git add client/src/lib/types.ts client/src/lib/api.ts client/src/lib/api.test.ts
git commit -m "feat: add guided live client api helpers"
```

### Task 2: Add guided read/write state to the live match page

**Objective:** Load guided-session data beside the existing websocket-driven live page using the current bearer-token session.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.tsx`
- Modify: `client/src/components/matches/human-live/use-human-match-live-state.ts`
- Modify: `client/src/components/matches/human-live/human-match-live-types.ts`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Write failing tests**

Add page-level tests that prove:
- the page fetches guided-session data once the live page is ready
- missing bearer-token behavior stays deterministic
- the guided-session data is cleared/guarded correctly across failures/session changes

**Step 2: Run test to verify failure**

Run: `cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx`
Expected: FAIL because no guided-session read state exists yet.

**Step 3: Write minimal implementation**

Add a guided-state slice that tracks:
- loading / ready / error status
- latest guided-session payload
- request identity guard against stale responses

Keep websocket state and guided-session state separate so the authoritative live snapshot is still explicit.

**Step 4: Run test to verify pass**

Run: `cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx`
Expected: PASS for the guided-session loading/error coverage.

**Step 5: Commit**

```bash
git add client/src/components/matches/human-match-live-page.tsx client/src/components/matches/human-live/use-human-match-live-state.ts client/src/components/matches/human-live/human-match-live-types.ts client/src/components/matches/human-match-live-page.test.tsx
git commit -m "feat: load guided session state on live page"
```

### Task 3: Render the guided panel and guidance composer

**Objective:** Show current queued orders plus private guidance history/composer on the live page without optimistic state drift.

**Files:**
- Modify: `client/src/components/matches/human-live/human-match-live-snapshot.tsx`
- Create: `client/src/components/matches/human-live/human-live-guided-panel.tsx`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Write failing tests**

Add browser-boundary tests that prove:
- queued orders and guidance history render from guided-session data
- successful guidance submission shows accepted metadata
- structured guidance errors preserve the draft text
- authoritative history/listing still comes from read-model refresh rather than fake optimistic insertion

**Step 2: Run test to verify failure**

Run: `cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx`
Expected: FAIL because the guided panel does not exist.

**Step 3: Write minimal implementation**

Render a small panel that shows:
- current queued order summary from guided-session
- guidance history list
- guidance textarea + submit button
- explicit accepted/error feedback

After guidance submit, refresh guided-session data rather than mutating the history list optimistically.

**Step 4: Run test to verify pass**

Run: `cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx`
Expected: PASS for the guided read/guidance flow coverage.

**Step 5: Commit**

```bash
git add client/src/components/matches/human-live/human-match-live-snapshot.tsx client/src/components/matches/human-live/human-live-guided-panel.tsx client/src/components/matches/human-match-live-page.test.tsx
git commit -m "feat: add guided guidance panel to live page"
```

### Task 4: Add override controls wired to the existing order drafts

**Objective:** Let the owner turn the existing order draft UI into deterministic guided overrides against the shipped override route.

**Files:**
- Modify: `client/src/components/matches/human-live/human-match-live-snapshot.tsx`
- Modify: `client/src/components/matches/human-live/human-live-orders-panel.tsx`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Write failing tests**

Add tests that prove:
- the override path calls only the override route with the current draft payload
- override success shows accepted metadata and preserves websocket authority
- structured override failures preserve the draft rows for correction
- the live page distinguishes normal order submission from guided override intent clearly

**Step 2: Run test to verify failure**

Run: `cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx`
Expected: FAIL because no override control exists.

**Step 3: Write minimal implementation**

Reuse the existing draft builder. Add a separate guided override action/button and feedback path that:
- requires the guided-session agent id
- submits the current draft batch to the override route
- refreshes guided-session after success
- never mutates authoritative live match state optimistically

**Step 4: Run test to verify pass**

Run: `cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx`
Expected: PASS for override success/failure coverage.

**Step 5: Commit**

```bash
git add client/src/components/matches/human-live/human-match-live-snapshot.tsx client/src/components/matches/human-live/human-live-orders-panel.tsx client/src/components/matches/human-match-live-page.test.tsx
git commit -m "feat: add guided override controls to live page"
```

### Task 5: Verify, simplify, and close out BMAD artifacts

**Objective:** Run the real gates, simplify any overbuilt UI/state seams, and update story tracking with actual outcomes.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/49-4-add-guided-agent-controls-to-the-live-web-client.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `docs/plans/2026-04-04-story-49-4-guided-agent-live-client-controls.md`

**Step 1: Run focused client verification**

Run:
- `cd client && npm test -- --run src/lib/api.test.ts src/components/matches/human-match-live-page.test.tsx`
- `cd client && npm run build`

Expected: PASS.

**Step 2: Run repo quality gate**

Run: `source .venv/bin/activate && make quality`
Expected: PASS.

**Step 3: Simplification pass**

Review for:
- duplicated guided-state logic
- unnecessary optimistic state
- unused compatibility seams
- overgrown UI component boundaries

**Step 4: Update BMAD artifacts**

Record the real commands, outcomes, completion notes, and file list. Mark `49-4` done and set the next story appropriately in `sprint-status.yaml`.

**Step 5: Commit**

```bash
git add _bmad-output/implementation-artifacts/49-4-add-guided-agent-controls-to-the-live-web-client.md _bmad-output/implementation-artifacts/sprint-status.yaml docs/plans/2026-04-04-story-49-4-guided-agent-live-client-controls.md
git commit -m "docs: close out story 49.4"
```


## Execution Outcome

- Implemented on 2026-04-04 in `feat: add guided live client controls`.
- Controller verification passed with `uv run pytest --no-cov tests/api/test_agent_api.py -q`, `cd client && npm test -- --run src/lib/api.test.ts src/components/matches/human-match-live-page.test.tsx`, and `make quality`.
- Final review findings required one simplification-quality follow-up: guided-session now refetches on websocket tick changes, and page tests now cover guided browser-boundary error handling plus tick-driven refresh.
