# Story 24.3 Client Session Bootstrap Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a tiny reusable client-side session shell that remembers the browser's API/auth context and clearly separates public pages from authenticated-only navigation.

**Architecture:** Keep the browser bootstrap layer intentionally small and client-only. Add a lightweight session provider/state seam around the existing Next.js app that persists a user-configurable API base URL and optional human bearer token, exposes derived auth status, and powers a simple protected-route wrapper plus navigation affordances for future human stories. Reuse this shell in public pages without requiring auth today.

**Tech Stack:** Next.js App Router, React context/hooks, TypeScript, localStorage/browser persistence, existing Vitest + Testing Library client harness.

---

## Parallelism / Sequencing

- **Implementation should stay sequential:** provider, storage contract, navigation, guard UI, and docs all touch the same client shell.
- **Do not widen scope:** no Supabase SDK, no login/signup form, no server mutation work, no middleware-heavy routing.
- **This story should enable later work:** Story 25.1 can consume the session shell immediately, while Story 25.3 can later attach real authenticated lobby mutations to the same seam.
- **Refinement pass required:** prefer the smallest boring context/provider rather than over-abstracted auth frameworks.

## Task 1: Add a tiny persisted client session model

**Objective:** Introduce one reusable client-side source of truth for API base URL and optional auth token.

**Files:**
- Modify: `client/src/app/layout.tsx`
- Create: `client/src/components/session/session-provider.tsx`
- Create: `client/src/components/session/session-context.ts`
- Create: `client/src/lib/session-storage.ts`
- Test: `client/src/components/session/session-provider.test.tsx`

**Step 1: Write failing tests**

Add behavior-first tests that prove:
- default session values load when storage is empty
- a saved API base URL and bearer token rehydrate on mount
- updating the session persists the new values

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --runInBand
```

Expected: FAIL because the session provider/storage seam does not exist yet.

**Step 3: Write minimal implementation**

Implement the smallest coherent session model:
- `apiBaseUrl`
- `bearerToken`
- derived `isAuthenticated`
- optional `displayLabel`/status string if useful for the nav only

Persist it through one `localStorage` key with a stable JSON shape. Avoid introducing reducers or external state libraries unless truly necessary.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --runInBand
```

Expected: PASS.

## Task 2: Add public/authenticated navigation and a protected-route shell

**Objective:** Make the app clearly distinguish public pages from authenticated-only pages without duplicating bootstrap logic.

**Files:**
- Modify: `client/src/app/layout.tsx`
- Modify: `client/src/app/page.tsx`
- Modify: `client/src/app/matches/page.tsx`
- Create: `client/src/app/(authed)/layout.tsx` or equivalent route-group shell
- Create: `client/src/app/(authed)/lobby/page.tsx` (placeholder/future-facing authenticated route)
- Create: `client/src/components/navigation/app-shell.tsx`
- Create: `client/src/components/navigation/protected-route.tsx`
- Test: `client/src/components/navigation/protected-route.test.tsx`

**Step 1: Write failing tests**

Add tests that prove:
- public navigation remains available without auth
- the authenticated placeholder route shows a clear sign-in/configuration requirement when no token exists
- the authenticated placeholder route renders when a token exists

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --runInBand
```

Expected: FAIL because the protected-route/nav shell does not exist yet.

**Step 3: Write minimal implementation**

Use the session provider from Task 1 to render a small global shell with:
- links to existing public pages
- a clearly labeled authenticated area link
- current API base URL/auth status summary
- a deterministic protected-route message instead of complex redirect logic

Keep `/` and `/matches` public. The authenticated route can be a placeholder for future lobby flows, but it must visibly use the shared session seam.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --runInBand
cd client && npm run build
```

Expected: PASS.

## Task 3: Add a simple runtime configuration panel and document the workflow

**Objective:** Let the user configure the stored API base URL/token intentionally and make the workflow obvious in docs.

**Files:**
- Create: `client/src/components/session/session-config-panel.tsx`
- Modify: `client/src/app/page.tsx`
- Modify: `client/src/app/matches/page.tsx`
- Modify: `README.md`
- Modify: `client/.env.example` if a documented default/env note needs clarification
- Test: `client/src/components/session/session-config-panel.test.tsx`
- Test: `tests/test_local_dev_docs.py`

**Step 1: Write failing tests**

Add tests that prove:
- editing/submitting the configuration panel updates persisted session values
- the panel does not expose stack traces/raw transport details
- docs mention the new client-side bootstrap flow accurately

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --runInBand
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_local_dev_docs.py
```

Expected: FAIL until the panel/docs are wired.

**Step 3: Write minimal implementation**

Add a small form for:
- API base URL
- optional bearer token

Show clear explanatory copy that:
- public pages do not require auth
- authenticated pages will reuse this stored token later
- the default local server remains `http://127.0.0.1:8000`

Update README with the exact browser flow after `npm run dev`.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --runInBand
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_local_dev_docs.py
cd client && npm run build
```

Expected: PASS.

## Task 4: Final verification and simplification pass

**Objective:** Ensure the session shell is the simplest coherent foundation for the next human stories.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/24-3-add-client-side-auth-session-bootstrap-for-future-human-flows.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `README.md` if verification finds doc drift

**Step 1: Review against the acceptance criteria**

Check explicitly:
- one shared session/bootstrap layer exists
- public vs authenticated areas are obvious
- protected routes do not duplicate config/bootstrap logic
- docs tell the truth about local setup and browser workflow
- no full auth product scope leaked into the story

**Step 2: Run final verification**

```bash
make client-lint
make client-test
make client-build
make quality
```

Expected: PASS.

**Step 3: Complete BMAD closeout**

- mark Story 24.3 done only after verification passes
- fill in the story artifact completion notes/debug log/file list
- leave Story 25.1 ready to build on the new shell immediately

## Final review checklist

- [ ] session state persists the small intended contract only
- [ ] public routes remain public and working
- [ ] authenticated placeholder routes reuse the shared session shell
- [ ] docs and tests cover the bootstrap flow
- [ ] no unnecessary auth abstraction or third-party client dependency was added
- [ ] BMAD artifacts reflect the shipped state
