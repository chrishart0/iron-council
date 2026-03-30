# Story 25.3 Human Lobby Flows Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Let an authenticated human create, join, and start a lobby from the web client using the existing public server routes, while surfacing structured server errors without optimistic drift.

**Architecture:** Reuse the existing browser session shell and add a tiny typed lobby-lifecycle client seam that sends the stored Bearer token to the already-shipped match routes. Because review found a real contract gap — DB-backed lobby create/start currently require API keys even though the architecture says human Bearer auth is the browser contract — add the smallest server extension needed so the same `/api/v1/matches`, `/api/v1/matches/{match_id}/join`, and `/api/v1/matches/{match_id}/start` routes accept valid human JWTs in addition to existing agent API-key flows. Keep the UI boring: submit, wait for the server response, refresh local state from that response, and render structured errors verbatim-safe via the repo’s existing API error envelope.

**Tech Stack:** FastAPI, existing server DB registry/auth seams, Next.js App Router, React, TypeScript, Vitest + Testing Library, pytest API/e2e coverage, existing `make client-*` and `make quality` gates.

---

## Parallelism / Sequencing

- **Sequential:** server contract gap and client lobby flows share the same public contract, auth assumptions, and error codes. Do not split them across parallel workers.
- **No new backend namespace:** use the existing match routes only.
- **Keep scope tight:** no full login UX, no gameplay order UI, no optimistic local lobby state, no extra transport layer.

## Task 1: Close the human-auth contract gap on the existing lobby lifecycle routes

**Objective:** Make the existing DB-backed create/join/start routes work for authenticated human Bearer tokens without breaking agent API-key behavior.

**Files:**
- Modify: `server/main.py`
- Modify: `server/db/registry.py`
- Test: `tests/api/test_agent_api.py`
- Test: `tests/e2e/test_api_smoke.py`
- Modify: `core-architecture.md` only if the shipped contract wording needs a tiny clarification

**Step 1: Write failing tests**

Add API-boundary tests that prove:
- a valid human Bearer token can create a lobby through `POST /api/v1/matches`
- a valid human Bearer token can join a lobby through `POST /api/v1/matches/{match_id}/join`
- a creator human Bearer token can start a ready lobby through `POST /api/v1/matches/{match_id}/start`
- invalid/missing human auth still fails with structured auth errors
- non-creator or not-ready human starts still surface the existing structured domain errors
- a small real-process smoke path proves browser-style Bearer auth works against the running app boundary

**Step 2: Run tests to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'human and (lobby or start or join)'
uv run pytest --no-cov tests/e2e/test_api_smoke.py -k 'human and lobby'
```

Expected: FAIL because create/start DB-backed lobby routes still require API keys and the real-process smoke path does not yet prove human browser flows.

**Step 3: Write minimal implementation**

Implementation constraints:
- keep the same route paths and response models
- preserve X-API-Key support for agent clients
- resolve human ownership on the exact user/player boundary promised by the existing auth architecture
- do not invent optional legacy request fields or a second route family
- keep DB registry helpers small and explicit; prefer adding a narrow “resolve by human user id” path over broad auth abstraction

**Step 4: Run tests to verify pass**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'human and (lobby or start or join)'
uv run pytest --no-cov tests/e2e/test_api_smoke.py -k 'human and lobby'
```

Expected: PASS.

## Task 2: Add typed client lobby lifecycle helpers with deterministic structured errors

**Objective:** Extend the client API layer so the browser can call the shipped lobby lifecycle routes with the stored Bearer token and parse the existing response/error contracts.

**Files:**
- Modify: `client/src/lib/api.ts`
- Modify: `client/src/lib/types.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing tests**

Add tests that prove:
- create/join/start helpers call the existing routes with `Authorization: Bearer ...`
- success payloads parse into narrow typed contracts
- structured API errors like invalid auth, match not found, not joinable, not ready, and forbidden start surface as deterministic client-safe errors
- malformed payloads still fail closed

**Step 2: Run tests to verify failure**

```bash
cd client && npm test -- --run src/lib/api.test.ts
```

Expected: FAIL because the helpers/types/error parsing do not exist yet.

**Step 3: Write minimal implementation**

Use one small request helper pattern if it reduces duplication, but keep it boring. Capture only the currently shipped fields from the existing server responses. Preserve `fetchPublicMatches(...)` and public-detail helpers unchanged.

**Step 4: Run tests to verify pass**

```bash
cd client && npm test -- --run src/lib/api.test.ts
```

Expected: PASS.

## Task 3: Replace the authenticated placeholder with real human lobby actions

**Objective:** Turn `/lobby` into a simple authenticated page for create, join, and start flows driven entirely by server responses.

**Files:**
- Modify: `client/src/app/lobby/page.tsx`
- Create: `client/src/components/lobby/human-lobby-page.tsx`
- Create: `client/src/components/lobby/human-lobby-page.test.tsx`
- Modify: `client/src/app/globals.css` only if a tiny shared style touch is needed

**Step 1: Write failing tests**

Add behavior-first client tests that prove:
- an authenticated user can create a lobby and the returned lobby summary renders
- an authenticated user can join an existing lobby by match id
- the creator can start a ready lobby
- server errors render clearly and do not leave fake local state behind
- unauthenticated users still see the guarded route shell from `ProtectedRoute`

**Step 2: Run tests to verify failure**

```bash
cd client && npm test -- --run src/components/lobby/human-lobby-page.test.tsx src/components/navigation/protected-route.test.tsx
```

Expected: FAIL because the placeholder page and real action UI do not exist yet.

**Step 3: Write minimal implementation**

UI constraints:
- keep the page form-driven and explicit
- no optimistic updates; only show lobby state returned by the server
- show one current result panel that reflects the last successful server response
- render structured error messages in a stable status panel
- include obvious next actions (create, join by id, creator-only start) without overbuilding navigation

**Step 4: Run tests to verify pass**

```bash
cd client && npm test -- --run src/components/lobby/human-lobby-page.test.tsx src/components/navigation/protected-route.test.tsx
cd client && npm run build
```

Expected: PASS.

## Task 4: Sync docs, close BMAD artifacts, and run final verification

**Objective:** Leave the repo in the smallest coherent shippable state with docs and tracking aligned.

**Files:**
- Modify: `README.md`
- Modify: `_bmad-output/implementation-artifacts/25-3-add-authenticated-human-lobby-create-join-start-flows-in-the-web-client.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `_bmad-output/planning-artifacts/epics.md` only if acceptance text or sequencing notes need a tiny sync update

**Step 1: Review against the acceptance criteria**

Check explicitly:
- the client uses the existing match routes
- the browser sends Bearer auth from the shared session shell
- structured errors are surfaced without optimistic drift
- the shipped server contract supports the human browser story through the same route family

**Step 2: Run final verification**

```bash
make client-lint
make client-test
make client-build
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'human and (lobby or start or join)'
uv run pytest --no-cov tests/e2e/test_api_smoke.py -k 'human and lobby'
make quality
```

Expected: PASS.

**Step 3: Complete BMAD closeout**

- mark Story 25.3 done only after verification passes
- fill in the story artifact debug log, completion notes, and file list
- advance `sprint-status.yaml` to the next sensible planning state
- update the README `/lobby` section so it no longer describes the route as a placeholder

## Final review checklist

- [ ] human Bearer auth works for the existing create/join/start route family
- [ ] X-API-Key agent behavior remains intact
- [ ] client helpers parse only the shipped public payloads and error envelopes
- [ ] `/lobby` is simple, deterministic, and free of optimistic drift
- [ ] docs and BMAD artifacts match the shipped browser flow
