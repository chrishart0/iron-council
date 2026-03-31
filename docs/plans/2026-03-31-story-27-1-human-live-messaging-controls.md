# Story 27.1 Human Live Messaging Controls Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add text-first authenticated world/direct/group message sending to the browser live-match page using the already-shipped message HTTP routes while keeping the websocket as the source of truth.

**Architecture:** Reuse the existing `/matches/[matchId]/play` live page, websocket snapshot, and session bootstrap. Extend the client API/types with the smallest typed surface needed for authenticated world/direct/group message submissions, then add a deterministic message composer on the live page that chooses an existing route based on channel type, submits against the current websocket tick, preserves drafts on failure, and shows only server-confirmed acceptance metadata on success.

**Tech Stack:** Next.js App Router, React, TypeScript, existing client API/helpers/types, existing Vitest + Testing Library client harness, repository `make quality` gate.

---

## Parallelism / Sequencing

- **Sequential only:** this work touches the same live-page, API, and type surface as Stories 26.1 and 26.2, so parallel implementation would create unnecessary merge risk.
- **No backend expansion:** consume only the shipped `/api/v1/matches/{id}/messages` and `/api/v1/matches/{id}/group-chats/{group_chat_id}/messages` routes.
- **Messaging only:** do not add treaty/alliance controls, group-chat creation, or extra background polling in this story.

## Task 1: Extend the typed client API with authenticated messaging helpers

**Objective:** Add the smallest typed request/response surface needed for human live-page message submission through the shipped HTTP routes.

**Files:**
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing tests**

Add tests that prove:
- world/direct message payloads serialize to the existing `/messages` request shape
- group-chat message payloads serialize to the existing `/group-chats/{id}/messages` request shape
- helpers post with bearer auth and the current live tick
- structured API error envelopes become deterministic typed client errors with code/status
- accepted responses parse into typed acceptance metadata

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run src/lib/api.test.ts
```

Expected: FAIL because the messaging helpers/types do not exist yet.

**Step 3: Write minimal implementation**

Add only the already-shipped surface:
- typed request/response models for match messages and group-chat messages
- one small structured error class for message submission failures
- thin helpers that select the route by message target rather than introducing a generic future abstraction

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run src/lib/api.test.ts
```

Expected: PASS.

## Task 2: Build the live-page message composer and deterministic submit flow

**Objective:** Let an authenticated human send text-first world/direct/group messages from the live page without optimistic timeline mutations.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.tsx`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Write failing tests**

Add tests that prove:
- the live page renders a message composer once a live player snapshot is available
- a player can choose world, direct, or group-chat targets from currently visible websocket data
- submit uses the current live tick and the correct shipped route for the chosen target
- accepted responses show deterministic confirmation and clear only the accepted draft
- structured errors preserve the current draft and show server message/code/status

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx
```

Expected: FAIL because the composer and submit path do not exist yet.

**Step 3: Write minimal implementation**

Keep the UI boring and text-first:
- a small “Live messaging” section under the existing chat/diplomacy summaries
- a simple channel selector (`world`, `direct`, `group`)
- target selectors populated from the websocket snapshot for direct/group targets
- one text area for message content
- submit button disabled when no authenticated live snapshot is available or a submit is in flight
- success banner uses accepted tick/player/message metadata only
- failure banner preserves the current draft exactly as entered

Prefer straightforward local component state over reusable form frameworks.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx src/lib/api.test.ts
cd client && npm run build
```

Expected: PASS.

## Task 3: Close docs/BMAD gaps and run the real quality gate

**Objective:** Keep docs and story artifacts aligned with the new live messaging behavior.

**Files:**
- Modify: `README.md`
- Modify: `_bmad-output/implementation-artifacts/27-1-add-authenticated-human-live-messaging-controls-in-the-web-client.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Test: `make quality`

**Step 1: Review against the acceptance criteria**

Check explicitly:
- browser posts only the existing message routes
- payloads use the current live tick
- failures preserve drafts and show structured errors
- success does not fake timeline updates before the websocket broadcasts them

**Step 2: Run final verification**

```bash
make client-lint
make client-test
make client-build
make quality
```

Expected: PASS.

**Step 3: Complete BMAD closeout**

- mark Story 27.1 done only after verification passes
- fill in debug logs, completion notes, and file list
- move `next_story` to Story 27.2 and keep the artifact queue warm for treaty/alliance controls

## Final review checklist

- [ ] messaging helpers mirror only the shipped backend request/response contracts
- [ ] live-page message composer stays text-first and deterministic
- [ ] successful submit shows acceptance metadata but relies on websocket state as source of truth
- [ ] failure handling preserves drafts and surfaces structured errors
- [ ] docs and BMAD artifacts match the shipped routes and behavior
