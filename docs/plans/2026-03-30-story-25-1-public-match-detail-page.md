# Story 25.1 Public Match Detail Page Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a public web page for one match that consumes the existing match-detail API contract and helps users decide whether to spectate or later join.

**Architecture:** Reuse the existing client runtime and session shell, but keep this page fully public and read-only. Extend the small typed client API layer with the already-shipped `GET /api/v1/matches/{match_id}` contract, add a route under `/matches/[matchId]`, and render only public metadata plus roster rows. Handle unknown/completed match IDs deterministically by reflecting the public API behavior rather than inventing hidden fallback state.

**Tech Stack:** Next.js App Router, React, TypeScript, existing client API helpers/types, existing Vitest + Testing Library client harness.

---

## Parallelism / Sequencing

- **Sequential after Story 24.3:** this page should sit on top of the newly-added session/bootstrap shell, but it remains public.
- **Do not widen scope:** no WebSocket live state, no map rendering, no join/start actions, no private player state.
- **Prepare the next step:** the detail page should make Story 25.2 spectator live entry obvious without implementing it yet.

## Task 1: Extend the typed client API for public match detail

**Objective:** Add one small fetch helper and TypeScript contract for `GET /api/v1/matches/{match_id}`.

**Files:**
- Modify: `client/src/lib/api.ts`
- Modify: `client/src/lib/types.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing tests**

Add tests that prove:
- valid match-detail payloads parse successfully
- malformed payloads fail deterministically
- not-found/error responses surface a client-safe detail error

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --runInBand
```

Expected: FAIL because the detail fetch/types do not exist yet.

**Step 3: Write minimal implementation**

Mirror only the public fields already exposed by the server:
- match id
- status
- map
- tick
- tick interval
- player/open-slot counts
- roster rows with `display_name` and `competitor_kind`

Use the same boring parsing/error pattern as the existing match-list helper where possible.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --runInBand
```

Expected: PASS.

## Task 2: Build the `/matches/[matchId]` page and link into it from the browser

**Objective:** Render the public detail view and make it discoverable from the existing match list.

**Files:**
- Create: `client/src/app/matches/[matchId]/page.tsx`
- Modify: `client/src/app/matches/page.tsx`
- Modify: `client/src/components/matches/match-browser.tsx`
- Create: `client/src/components/matches/match-detail.tsx`
- Test: `client/src/components/matches/match-detail.test.tsx`
- Test: `client/src/components/matches/match-browser.test.tsx`

**Step 1: Write failing tests**

Add tests that prove:
- a valid detail response renders public metadata and roster rows
- the match browser links to the detail page
- the page stays read-only and does not leak private state fields

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --runInBand
```

Expected: FAIL because the new route/component/link behavior does not exist yet.

**Step 3: Write minimal implementation**

Render a boring detail view with:
- hero/header section
- key public match metadata
- visible roster list with human/agent labels
- optional next-step affordance text such as “spectator live view coming next” only if it is clearly non-interactive

Prefer plain semantic HTML over a large presentational abstraction.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --runInBand
cd client && npm run build
```

Expected: PASS.

## Task 3: Add deterministic not-found/error handling and docs touch-ups

**Objective:** Ensure unknown/completed matches fail in an intentional, user-safe way.

**Files:**
- Modify: `client/src/app/matches/[matchId]/page.tsx`
- Modify: `README.md`
- Test: `client/src/components/matches/match-detail.test.tsx`
- Test: `tests/test_local_dev_docs.py`

**Step 1: Write failing tests**

Add tests that prove:
- a not-found API result renders a deterministic missing/unsupported message
- generic transport errors render a safe fallback message
- docs mention how to navigate from `/matches` to a detail page in local dev

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --runInBand
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_local_dev_docs.py
```

Expected: FAIL until the route/docs are complete.

**Step 3: Write minimal implementation**

Treat unknown and completed matches according to the server's public contract. Keep the message deterministic and concise; do not leak raw HTTP payloads or stack traces.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --runInBand
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_local_dev_docs.py
cd client && npm run build
```

Expected: PASS.

## Task 4: Final verification and simplification pass

**Objective:** Close the story in the smallest coherent state and keep BMAD artifacts honest.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/25-1-add-a-public-match-detail-page-in-the-web-client.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `README.md` if verification finds drift

**Step 1: Review against the acceptance criteria**

Check explicitly:
- the client uses the existing public match-detail route
- only public metadata and roster info render
- unknown/completed ids handle deterministically
- the route remains public and read-only

**Step 2: Run final verification**

```bash
make client-lint
make client-test
make client-build
make quality
```

Expected: PASS.

**Step 3: Complete BMAD closeout**

- mark Story 25.1 done only after verification passes
- fill in the story artifact completion notes/debug log/file list
- leave Story 25.2 as the next obvious follow-on

## Final review checklist

- [ ] typed API contract mirrors only the shipped public fields
- [ ] `/matches/[matchId]` is public, read-only, and linked from the browser page
- [ ] not-found/error handling is deterministic and safe
- [ ] no websocket or authenticated lobby scope leaked into the story
- [ ] docs and BMAD artifacts match the shipped behavior
