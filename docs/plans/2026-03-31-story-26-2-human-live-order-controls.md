# Story 26.2 Human Live Order Controls Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add text-first authenticated order drafting and submission controls to the browser live-match page using the already-shipped authenticated command envelope.

**Architecture:** Reuse the existing `/matches/[matchId]/play` live page and session bootstrap, but extend the client API/types with the smallest typed command-envelope surface needed for order-only submissions. Keep the UI boring: a deterministic draft composer on the live page that builds movement, recruitment, upgrade, and transfer rows, submits them through the existing `/api/v1/matches/{id}/commands` route for the current websocket tick, preserves drafts on error, and shows only server-confirmed acceptance metadata on success.

**Tech Stack:** Next.js App Router, React, TypeScript, existing client API/helpers/types, existing Vitest + Testing Library client harness, repository `make quality` gate.

---

## Parallelism / Sequencing

- **Sequential only:** this work touches the same client live-page, API, and type surface as Story 26.1, so parallel implementation would create unnecessary merge risk.
- **No backend expansion:** consume only the shipped `/api/v1/matches/{id}/commands` route and existing order payload contracts.
- **Text-first scope only:** do not add map interactions, drag-to-path controls, message sending, treaty writing, or alliance UI in this story.

## Task 1: Extend the typed client API with authenticated order-command helpers

**Objective:** Add the smallest typed request/response surface needed for human order submission through the existing command envelope.

**Files:**
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing tests**

Add tests that prove:
- order-command payloads serialize to the existing command-envelope shape
- the helper posts to `/api/v1/matches/{matchId}/commands` with bearer auth and the current tick
- structured API error envelopes become a deterministic client error with code/status
- accepted responses parse into typed acceptance metadata

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run src/lib/api.test.ts
```

Expected: FAIL because the command helper/types do not exist yet.

**Step 3: Write minimal implementation**

Add only the already-shipped surface:
- movement/recruitment/upgrade/transfer order rows inside the existing command envelope
- accepted response metadata already returned by the backend
- a small `CommandActionError`-style class for structured command failures

Do not add abstractions for future message/treaty/alliance writes yet.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run src/lib/api.test.ts
```

Expected: PASS.

## Task 2: Build the live-page order composer and deterministic submit flow

**Objective:** Let an authenticated human draft and submit text-first orders from the live page without inventing optimistic state.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.tsx`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Write failing tests**

Add tests that prove:
- the live page renders order draft controls once a live player snapshot is available
- a player can add draft rows for movement, recruitment, upgrade, and transfer orders
- submit uses the current live tick and shows accepted-for-tick confirmation on success
- structured errors keep the draft rows intact and show the server message/code

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx
```

Expected: FAIL because the composer and submit path do not exist yet.

**Step 3: Write minimal implementation**

Keep the UI boring and text-first:
- small section under the live summaries titled “Order Drafts”
- one simple row editor per supported order type
- explicit add/remove buttons
- submit button disabled when no authenticated live snapshot is available or a submit is in flight
- success banner uses accepted tick/player metadata only
- failure banner preserves the current draft rows exactly as entered

Prefer straightforward local component state over a reusable form framework.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx
cd client && npm run build
```

Expected: PASS.

## Task 3: Close docs/BMAD gaps and run the real quality gate

**Objective:** Keep the shipped docs and story artifacts aligned with the new authenticated order-control behavior.

**Files:**
- Modify: `README.md`
- Modify: `_bmad-output/implementation-artifacts/26-2-add-authenticated-human-order-submission-controls-in-the-live-web-client.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Test: `tests/test_local_dev_docs.py` if docs wording changes warrant it

**Step 1: Review against the acceptance criteria**

Check explicitly:
- the browser posts only the existing command route
- the payload uses the current live tick
- failures preserve drafts and show structured errors
- success does not fake a live state update before the websocket broadcasts it

**Step 2: Run final verification**

```bash
make client-lint
make client-test
make client-build
make quality
```

Expected: PASS.

**Step 3: Complete BMAD closeout**

- mark Story 26.2 done only after verification passes
- fill in debug logs, completion notes, and file list
- set the next story to browser-side messaging/diplomacy writes rather than broad UI expansion

## Final review checklist

- [ ] command helper mirrors the shipped backend envelope only
- [ ] live-page order composer stays text-first and deterministic
- [ ] successful submit shows acceptance metadata but relies on websocket state as source of truth
- [ ] failure handling preserves draft rows and surfaces structured errors
- [ ] docs and BMAD artifacts match the shipped route and behavior
