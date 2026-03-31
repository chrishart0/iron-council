# Story 26.1 Human Live Match Page Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add an authenticated browser live-match page that consumes the shipped player websocket contract and lets a joined human observe fog-filtered state plus messaging/diplomacy summaries during an active match.

**Architecture:** Reuse the session bootstrap shell, public match-detail fetch, and existing spectator live-page patterns, but extend the client API/types with a dedicated player websocket URL/parser and player-safe envelope types. Build a new authenticated route under `/matches/[matchId]/play` that first validates the current match is active, then opens the existing player websocket with the stored bearer token, renders concise player-facing summaries, and preserves the last confirmed snapshot when the socket drops.

**Tech Stack:** Next.js App Router, React, TypeScript, existing client API helpers/types, existing Vitest + Testing Library client harness, repository `make quality` gate.

---

## Parallelism / Sequencing

- **Sequential only:** this work touches the same client websocket/types/live-view surface as the spectator page and authenticated session flow, so parallel implementation would create unnecessary merge risk.
- **No backend expansion:** consume the existing player websocket contract exactly as shipped.
- **No gameplay controls yet:** do not add order submission, message posting, map rendering, or new server routes in this story.

## Task 1: Extend the typed client API with player websocket helpers

**Objective:** Add the smallest typed client surface needed to open and parse authenticated player websocket updates.

**Files:**
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing tests**

Add tests that prove:
- a player websocket URL is built from the configured API base URL plus match id and bearer token
- valid player websocket payloads parse successfully
- malformed player websocket payloads fail deterministically

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run src/lib/api.test.ts
```

Expected: FAIL because the player websocket helpers/types do not exist yet.

**Step 3: Write minimal implementation**

Add only the contract already shipped by the backend:
- `viewer_role: "player"`
- `player_id: string`
- fog-filtered state with visible-city metadata and visible-army collection
- world/direct/group/treaty/alliance collections

Follow the same boring helper pattern used by the spectator live-page code where possible.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run src/lib/api.test.ts
```

Expected: PASS.

## Task 2: Build the authenticated `/matches/[matchId]/play` route and live view

**Objective:** Render a text-first authenticated live page that connects to the shipped player websocket and summarizes the player-safe envelope.

**Files:**
- Create: `client/src/app/matches/[matchId]/play/page.tsx`
- Create or modify: `client/src/components/matches/human-match-live-page.tsx`
- Modify: `client/src/components/matches/match-live-view.tsx` or create a player-specific sibling if keeping contracts simpler
- Modify: `client/src/components/matches/match-detail.tsx`
- Modify: `client/src/components/navigation/app-shell.tsx` only if a global nav/link is truly needed
- Test: `client/src/components/matches/human-match-live-page.test.tsx`
- Test: `client/src/components/matches/match-detail.test.tsx`

**Step 1: Write failing tests**

Add tests that prove:
- an authenticated active match opens the player websocket and renders the player id plus fog-filtered summary data
- the page preserves the last good snapshot if the websocket closes after one valid update
- the public match detail page exposes the next-step link only when that action makes sense for an authenticated player

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx src/components/matches/match-detail.test.tsx
```

Expected: FAIL because the route/component/link behavior does not exist yet.

**Step 3: Write minimal implementation**

Keep the page boring and text-first:
- hero/header with match id and authenticated-player context
- clear auth guard if no bearer token is configured
- active-match gate before opening the websocket
- concise sections for visible state summary, latest world/direct/group message counts, treaty/alliance counts, and current visible armies
- deterministic reconnect/unavailable messaging without optimistic state

Prefer simple semantic HTML over a broad reusable abstraction if a union live-view component becomes awkward.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx src/components/matches/match-detail.test.tsx
cd client && npm run build
```

Expected: PASS.

## Task 3: Add deterministic auth/join/inactive handling and docs touch-ups

**Objective:** Make failure states explicit and keep the local dev docs aligned with the new authenticated route.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.tsx`
- Modify: `README.md`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`
- Test: `tests/test_local_dev_docs.py`

**Step 1: Write failing tests**

Add tests that prove:
- no stored bearer token produces a deterministic auth-required state without opening a websocket
- non-active matches render a clear inactive-state message without opening a websocket
- malformed payload / socket error path preserves the last confirmed snapshot and shows a reconnect/unavailable banner
- README mentions how to reach the authenticated live page from the local client flow

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_local_dev_docs.py
```

Expected: FAIL until the guards and docs are complete.

**Step 3: Write minimal implementation**

Reflect the existing contract and session reality only. Do not invent background retry loops, optimistic fake data, or hidden fallback auth behavior.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_local_dev_docs.py
cd client && npm run build
```

Expected: PASS.

## Task 4: Final verification and simplification pass

**Objective:** Close the story in the smallest coherent shippable state and keep BMAD artifacts honest.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/26-1-add-an-authenticated-human-live-match-page-over-the-player-websocket.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `README.md` if verification finds drift

**Step 1: Review against the acceptance criteria**

Check explicitly:
- the page uses the existing player websocket path with the stored bearer token
- only player-safe/fog-filtered contract data renders
- auth/inactive/disconnect states are deterministic
- no gameplay-control scope leaked into the story

**Step 2: Run final verification**

```bash
make client-lint
make client-test
make client-build
make quality
```

Expected: PASS.

**Step 3: Complete BMAD closeout**

- mark Story 26.1 done only after verification passes
- fill in the story artifact completion notes/debug log/file list
- leave the next follow-on centered on gameplay controls rather than broad UI expansion

## Final review checklist

- [ ] typed player websocket contract mirrors the shipped backend envelope only
- [ ] `/matches/[matchId]/play` stays authenticated and player-focused
- [ ] live summaries remain text-first and deterministic
- [ ] disconnect/error handling preserves the last confirmed snapshot
- [ ] docs and BMAD artifacts match the shipped route and behavior
