# Story 48.2 Browser agent-key management Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a small authenticated browser settings surface for listing, creating, and revoking owned agent API keys so BYOA onboarding works from the shipped product without curl.

**Architecture:** Keep the change client-first and narrow. Extend the existing browser session/settings panel and typed client API layer to call the Bearer-authenticated `/api/v1/account/api-keys` routes from Story 48.1. Use browser-boundary component tests plus typed API helper tests to prove list/create/revoke behavior, one-time raw-secret reveal, and deterministic inactive-state updates without introducing billing or occupancy UX.

**Tech Stack:** Next.js 16 app router, React 19 client components, TypeScript, Vitest + Testing Library, existing Bearer-token session storage and typed fetch helpers.

---

### Task 1: Add typed owned-agent-key client contracts and helper coverage

**Objective:** Add the minimal client-side types/helpers for listing, creating, and revoking owned keys through the existing bearer-token session.

**Files:**
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`
- Modify: `client/src/lib/api.test.ts`

**Step 1: Write failing tests**

Add focused tests for:
- `fetchOwnedApiKeys(...)` issuing `GET /api/v1/account/api-keys` with Bearer auth and parsing compact key summaries
- `createOwnedApiKey(...)` issuing `POST /api/v1/account/api-keys`, returning the one-time secret plus summary
- `revokeOwnedApiKey(...)` issuing `DELETE /api/v1/account/api-keys/{key_id}` and returning the inactive summary
- malformed success payloads or structured API errors failing closed deterministically

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run client/src/lib/api.test.ts
```

Expected: FAIL until the new helper/types exist.

**Step 3: Write minimal implementation**

Add narrow `OwnedApiKeySummary`, `OwnedApiKeyListResponse`, and `OwnedApiKeyCreateResponse` types plus helper functions that reuse the existing authenticated header builders and error-envelope parsing.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run client/src/lib/api.test.ts
```

Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/lib/types.ts client/src/lib/api.ts client/src/lib/api.test.ts
git commit -m "feat: add client api-key lifecycle helpers"
```

### Task 2: Add the browser settings surface for owned keys with one-time secret reveal

**Objective:** Extend the existing session/settings panel so authenticated humans can load, create, and revoke owned keys from the browser boundary.

**Files:**
- Modify: `client/src/components/session/session-config-panel.tsx`
- Modify: `client/src/components/session/session-config-panel.test.tsx`
- Optionally create: one tiny presentational helper under `client/src/components/session/` only if it materially simplifies the panel without over-splitting it

**Step 1: Write failing tests**

Add browser-boundary tests covering:
- authenticated sessions loading and displaying owned-key metadata (id, rating, active state, creation time)
- creating a key and showing the raw secret exactly once with explicit copy explaining it will not be shown again
- persistent list view excluding the raw secret after the initial creation reveal is dismissed or after a reload/remount
- revoking a key updating only the relevant row to inactive while preserving the rest of the panel
- unauthenticated sessions staying honest about needing a bearer token rather than inventing a parallel auth flow

**Step 2: Run test to verify failure**

```bash
cd client && npm test -- --run client/src/components/session/session-config-panel.test.tsx
```

Expected: FAIL until the new UI exists.

**Step 3: Write minimal implementation**

Keep the UI in the existing settings panel. Reuse the stored `apiBaseUrl` and `bearerToken` from `useSession()`, load keys only when authenticated, and maintain a tiny state machine for `idle/loading/error`, `create`, and `revoke`. Show the one-time secret in a dedicated success block that is cleared on dismissal and never mixed into the durable list rows.

**Step 4: Run test to verify pass**

```bash
cd client && npm test -- --run client/src/components/session/session-config-panel.test.tsx
```

Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/components/session/session-config-panel.tsx client/src/components/session/session-config-panel.test.tsx
git commit -m "feat: add browser api-key management panel"
```

### Task 3: Verify, simplify, and close out BMAD artifacts

**Objective:** Confirm the BYOA browser path works in the repo harness, then update the story/tracker artifacts with real outcomes.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/48-2-add-a-browser-agent-key-management-surface-for-byoa-onboarding.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Optionally modify: `README.md` or `docs/index.md` only if the shipped product entrypoint needs one honest sentence pointing to the new browser surface

**Step 1: Run focused client verification**

```bash
source .venv/bin/activate && make client-test
source .venv/bin/activate && make client-build
```

**Step 2: Run the repo quality gate**

```bash
source .venv/bin/activate && make quality
```

**Step 3: Review and simplify**

Check:
- `git diff --stat`
- the settings panel stayed small and understandable
- no raw secret survives in the durable list-state path
- no billing/entitlement/occupancy UX slipped into the story

**Step 4: Update BMAD artifacts with real verification results**

Record actual commands/outcomes in the story file, set complete signoff, and advance `sprint-status.yaml` to the next story.

**Step 5: Commit**

```bash
git add docs/plans/2026-04-03-story-48-2-browser-agent-key-management.md _bmad-output/implementation-artifacts/48-2-add-a-browser-agent-key-management-surface-for-byoa-onboarding.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "docs: close out story 48-2"
```
