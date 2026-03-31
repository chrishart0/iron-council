# Story 27.2 Human Live Treaty and Alliance Controls Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add text-first authenticated treaty and alliance actions to the browser live-match page using only the shipped authenticated diplomacy routes while keeping the websocket snapshot as the source of truth.

**Architecture:** Reuse the existing `/matches/[matchId]/play` live page, live websocket snapshot, and session bootstrap. Extend the client type/API surface with thin typed helpers for treaty and alliance submissions, then add a deterministic diplomacy control section that derives selectable players and alliances from the current websocket snapshot, submits against the current live tick, preserves drafts on failure, and shows only accepted metadata while waiting for websocket refresh to reflect the real diplomacy state.

**Tech Stack:** Next.js App Router, React, TypeScript, existing client API/helpers/types, Vitest + Testing Library, repo `make quality` gate.

---

## Parallelism / Sequencing

- **Sequential only for implementation:** Story 27.2 touches the same `client/src/lib/api.ts`, `client/src/lib/types.ts`, and `client/src/components/matches/human-match-live-page.tsx` surfaces as Stories 26.2 and 27.1, so implementation should stay in one isolated worktree.
- **Parallel review is safe:** after the implementation branch is ready, spec review and code-quality review can run as separate fresh reviewer passes.
- **No backend expansion:** consume only the shipped authenticated `/api/v1/matches/{id}/treaties` and `/api/v1/matches/{id}/alliances` routes. Do not invent polling endpoints, browser-only mutation APIs, or optimistic shadow state.
- **Text-first diplomacy only:** no map widgets, no drag-and-drop relationship UI, no group-chat creation, and no lobby-management expansion in this story.

## Task 1: Extend the typed client API with treaty and alliance helpers

**Objective:** Add the smallest typed request/response and error-handling surface needed for authenticated human treaty/alliance submissions.

**Files:**
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing tests**

Add tests that prove:
- treaty actions post to `/api/v1/matches/{id}/treaties` with bearer auth and the shipped `{ match_id, counterparty_id, action, treaty_type }` payload
- alliance create/join/leave actions post to `/api/v1/matches/{id}/alliances` with bearer auth and the shipped `{ match_id, action, alliance_id?, name? }` payload
- accepted treaty/alliance responses parse into typed acceptance metadata
- structured API error envelopes become deterministic typed client errors with `message`, `code`, and `statusCode`

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run src/lib/api.test.ts
```

Expected: FAIL because the treaty/alliance helper surface does not exist yet.

**Step 3: Write minimal implementation**

Add only the already-shipped diplomacy surface:
- treaty/alliance request and acceptance response types that mirror the server contracts
- one small structured diplomacy submission error class (or the smallest extension of the existing submission-error pattern)
- thin `submitTreatyAction()` and `submitAllianceAction()` helpers that post directly to the real routes and reuse the shared authenticated-header helpers

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run src/lib/api.test.ts
```

Expected: PASS.

## Task 2: Add deterministic live-page treaty controls

**Objective:** Let an authenticated human propose, accept, or withdraw treaties from the live page without fabricating diplomatic state.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.tsx`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Write failing tests**

Add tests that prove:
- the live page renders treaty controls once a live player snapshot is available
- direct treaty counterparties are derived from visible websocket player IDs and exclude the current player
- submit uses the current websocket tick and the correct shipped treaty route
- successful treaty submission shows deterministic accepted metadata but relies on later websocket updates for the treaty list
- structured treaty errors preserve the selected counterparty/type/action state and show server `message`, `code`, and `status`

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx
```

Expected: FAIL because the treaty controls do not exist yet.

**Step 3: Write minimal implementation**

Keep the UI boring and explicit:
- add a `Live diplomacy` section adjacent to the existing live messaging section
- include a treaty action selector (`propose`, `accept`, `withdraw`)
- include a treaty type selector (`non_aggression`, `defensive`, `trade`)
- include a visible-player selector populated from the live snapshot, excluding the current player
- disable submit when the live snapshot is unavailable or the submit is already in flight
- success banner should use accepted treaty metadata only
- failure banner should preserve the entire treaty draft exactly as entered

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx src/lib/api.test.ts
```

Expected: PASS.

## Task 3: Add deterministic live-page alliance controls

**Objective:** Let an authenticated human create, join, or leave alliances from the live page using only the shipped route contract.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.tsx`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Write failing tests**

Add tests that prove:
- alliance create shows a name field and does not send `alliance_id`
- alliance join uses a selectable alliance from the websocket snapshot and does not send `name`
- alliance leave sends only `{ match_id, action: "leave" }`
- success banners show accepted metadata while the websocket remains authoritative for alliance membership/listing state
- structured alliance failures preserve the relevant draft state for correction

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx
```

Expected: FAIL because alliance controls do not exist yet.

**Step 3: Write minimal implementation**

Prefer simple local state over generalized form abstractions:
- one alliance action selector (`create`, `join`, `leave`)
- conditionally render a name input for create and an alliance selector for join
- derive candidate alliances from the websocket snapshot
- show current alliance/leader context from the live snapshot to make the text-first UX understandable
- success feedback should report accepted create/join/leave metadata only
- error feedback should preserve draft inputs exactly

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx src/lib/api.test.ts
cd client && npm run build
```

Expected: PASS.

## Task 4: Close docs/BMAD gaps and run the real quality gate

**Objective:** Keep docs and story artifacts aligned with the shipped live diplomacy behavior.

**Files:**
- Modify: `README.md`
- Modify: `_bmad-output/implementation-artifacts/27-2-add-authenticated-human-treaty-and-alliance-controls-in-the-live-web-client.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Test: `make quality`

**Step 1: Review against the acceptance criteria**

Check explicitly:
- browser posts only the existing treaty/alliance routes
- payloads use the current live tick where required by the shipped contract
- failures preserve selections/drafts and show structured errors
- success does not fake treaty or alliance state before websocket refresh updates the snapshot

**Step 2: Run final verification**

```bash
make client-lint
make client-test
make client-build
make quality
```

Expected: PASS.

**Step 3: Complete BMAD closeout**

- mark Story 27.2 done only after verification passes
- fill in debug logs, completion notes, and file list
- advance `sprint-status.yaml` to the next sensible story/epic

## Final review checklist

- [ ] treaty/alliance helpers mirror only the shipped backend contracts
- [ ] live-page diplomacy controls remain text-first and deterministic
- [ ] successful submits show acceptance metadata but rely on websocket state as source of truth
- [ ] failure handling preserves draft state and surfaces structured errors
- [ ] docs and BMAD artifacts match the shipped treaty/alliance routes and behavior
