# Story 28.1 Human Live Group-Chat Creation Controls Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add text-first authenticated human group-chat creation controls to the browser live-match page using only the shipped group-chat creation route while keeping the websocket snapshot as the source of truth.

**Architecture:** Reuse the existing `/matches/[matchId]/play` live page, websocket snapshot, and session bootstrap. Extend the client type/API surface with one thin typed helper for group-chat creation, then add a deterministic live-page form that derives invite candidates from the current websocket snapshot, excludes the current player, submits against the current live tick, preserves the drafted name and invitees on failure, and shows only accepted metadata while waiting for websocket refresh to reflect the authoritative visible group-chat list.

**Tech Stack:** Next.js App Router, React, TypeScript, existing client API/helpers/types, Vitest + Testing Library, repo `make quality` gate.

---

## Parallelism / Sequencing

- **Sequential only for implementation:** Story 28.1 touches the same `client/src/lib/api.ts`, `client/src/lib/types.ts`, and `client/src/components/matches/human-match-live-page.tsx` surfaces as Stories 27.1 and 27.2, so implementation should stay in one isolated worktree.
- **Parallel review is safe:** after the implementation branch is ready, spec review and code-quality review can run as separate fresh reviewer passes.
- **No backend expansion:** consume only the shipped authenticated `/api/v1/matches/{id}/group-chats` route. Do not invent polling endpoints, browser-only mutation APIs, or auxiliary discovery routes.
- **Text-first creation only:** no group-chat membership editing, no player-profile drawer, no unread counters, and no map-integrated chat affordances in this story.

## Task 1: Extend the typed client API with group-chat creation support

**Objective:** Add the smallest typed request/response and error-handling surface needed for authenticated human group-chat creation submissions.

**Files:**
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing tests**

Add tests that prove:
- group-chat creation posts to `/api/v1/matches/{id}/group-chats` with bearer auth and the shipped `{ match_id, tick, name, member_ids }` payload
- accepted responses parse into typed acceptance metadata containing the returned `group_chat`
- structured API error envelopes become deterministic typed client errors with `message`, `code`, and `statusCode`
- invalid response shapes fail closed instead of being treated as success

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run src/lib/api.test.ts
```

Expected: FAIL because the group-chat creation helper surface does not exist yet.

**Step 3: Write minimal implementation**

Add only the already-shipped group-chat creation surface:
- request and acceptance response types that mirror the server contract
- reuse the smallest existing submission-error pattern that fits messaging-like writes
- add one thin `submitGroupChatCreate()` helper that posts directly to the real route using the shared authenticated JSON header helper

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run src/lib/api.test.ts
```

Expected: PASS.

## Task 2: Add deterministic live-page group-chat creation controls

**Objective:** Let an authenticated human create new group chats from the live page without fabricating visible chat state.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.tsx`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Write failing tests**

Add tests that prove:
- the live page renders a group-chat creation form once a live player snapshot is available
- invite candidates are derived from visible websocket player IDs and exclude the current player
- submit uses the current websocket tick and the correct shipped group-chat creation route
- successful creation shows deterministic accepted metadata but relies on later websocket updates for the visible group-chat list and message target selector
- structured creation errors preserve the drafted name and selected invitees and show server `message`, `code`, and `status`
- the form shows a deterministic guard when there are no other visible players to invite

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx
```

Expected: FAIL because the group-chat creation controls do not exist yet.

**Step 3: Write minimal implementation**

Keep the UI boring and explicit:
- add a `Create group chat` subsection inside the existing live messaging area
- include a name input and a simple checkbox list (or equivalent text-first multi-select) for inviteable visible players
- derive inviteable players from the websocket snapshot and exclude the current player id
- disable submit when the live snapshot is unavailable, no inviteable players are available, no invitees are selected, or a submission is already in flight
- success feedback should use accepted `group_chat` metadata only
- failure feedback should preserve the entire creation draft exactly as entered
- do not append the new group chat to visible chat choices until the websocket snapshot actually includes it

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx src/lib/api.test.ts
```

Expected: PASS.

## Task 3: Close docs/BMAD gaps and run the real quality gate

**Objective:** Keep docs and story artifacts aligned with the shipped live group-chat creation behavior.

**Files:**
- Modify: `README.md`
- Modify: `_bmad-output/implementation-artifacts/28-1-add-authenticated-human-live-group-chat-creation-controls-in-the-web-client.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Test: `make quality`

**Step 1: Review against the acceptance criteria**

Check explicitly:
- browser posts only the existing group-chat creation route
- payload uses the current live tick and the shipped request shape
- failures preserve the drafted name and invitees and show structured errors
- success does not fake visible group-chat state before websocket refresh updates the snapshot
- the message-composer group-chat selector continues to rely on websocket-visible chats only

**Step 2: Run final verification**

```bash
make client-lint
make client-test
make client-build
make quality
```

Expected: PASS.

**Step 3: Complete BMAD closeout**

- mark Story 28.1 done only after verification passes
- fill in debug logs, completion notes, and file list
- advance `sprint-status.yaml` to the next sensible story/epic

## Final review checklist

- [ ] group-chat creation helper mirrors only the shipped backend contract
- [ ] live-page creation controls remain text-first and deterministic
- [ ] successful submits show acceptance metadata but rely on websocket state as source of truth
- [ ] failure handling preserves drafted name/invitees and surfaces structured errors
- [ ] docs and BMAD artifacts match the shipped route and behavior
