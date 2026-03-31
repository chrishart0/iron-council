# Story 29.1 Public Read Pages Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add boring, read-only web pages for the shipped public leaderboard and completed-match summary APIs, with stable links into a later replay/history page.

**Architecture:** Extend the existing client-side public-browser pattern: add narrow TypeScript types plus `lib/api.ts` fetch helpers for `/api/v1/leaderboard` and `/api/v1/matches/completed`, then render read-only pages/components that load after session hydration and show deterministic error states. Keep the implementation text-first and route-based; completed-match browse cards should link to a future replay page instead of embedding replay payloads.

**Tech Stack:** Next.js App Router, React client components, TypeScript, Vitest + Testing Library, existing session-provider/public-browser helpers, repo `make quality` gate.

---

### Task 1: Add failing API helper tests for leaderboard and completed matches

**Objective:** Pin the public browser/API contract before touching production code.

**Files:**
- Modify: `client/src/lib/api.test.ts`
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`

**Step 1: Write failing test**

Add tests that expect:
- `fetchPublicLeaderboard()` to GET `/api/v1/leaderboard`
- `fetchCompletedMatches()` to GET `/api/v1/matches/completed`
- explicit `apiBaseUrl` override support
- malformed payloads to raise typed read-only errors

**Step 2: Run test to verify failure**

Run: `cd client && npm test -- --run src/lib/api.test.ts`
Expected: FAIL with missing helper/type errors.

**Step 3: Write minimal implementation**

Add the narrow response types and fetch helpers in:
- `client/src/lib/types.ts`
- `client/src/lib/api.ts`

Keep errors boring and specific (for example `PublicLeaderboardError`, `CompletedMatchesError`).

**Step 4: Run test to verify pass**

Run: `cd client && npm test -- --run src/lib/api.test.ts`
Expected: PASS for the new helper coverage.

**Step 5: Commit**

```bash
git add client/src/lib/api.ts client/src/lib/api.test.ts client/src/lib/types.ts
git commit -m "feat: add public read helpers for leaderboard pages"
```

### Task 2: Add failing component tests for the new public pages

**Objective:** Drive the read-only leaderboard/completed-match UI from the browser boundary.

**Files:**
- Create: `client/src/components/public/public-leaderboard-page.tsx`
- Create: `client/src/components/public/completed-matches-page.tsx`
- Create: `client/src/components/public/public-leaderboard-page.test.tsx`
- Create: `client/src/components/public/completed-matches-page.test.tsx`
- Create: `client/src/app/leaderboard/page.tsx`
- Create: `client/src/app/matches/completed/page.tsx`
- Modify: `client/src/app/page.tsx`
- Modify: `client/src/components/matches/match-detail.tsx`

**Step 1: Write failing tests**

Add browser-facing tests that assert:
- loading states render first
- successful leaderboard render shows ordered rank rows and summary stats
- successful completed-match render shows compact metadata plus a link to `/matches/<id>/history`
- failure states show clear read-only copy and stable navigation links
- home page / public match detail include links to the new pages where appropriate

**Step 2: Run tests to verify failure**

Run: `cd client && npm test -- --run src/components/public/public-leaderboard-page.test.tsx src/components/public/completed-matches-page.test.tsx`
Expected: FAIL with missing page/component exports.

**Step 3: Write minimal implementation**

Follow existing public page patterns:
- gate fetches on `hasHydrated`
- use `fetch(..., { cache: "no-store" })` through the typed helpers only
- render text-first sections/panels
- keep completed matches read-only and link-only for replay follow-up

**Step 4: Run tests to verify pass**

Run: `cd client && npm test -- --run src/components/public/public-leaderboard-page.test.tsx src/components/public/completed-matches-page.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/app/page.tsx client/src/app/leaderboard/page.tsx client/src/app/matches/completed/page.tsx client/src/components/public client/src/components/matches/match-detail.tsx
git commit -m "feat: add public leaderboard and completed match pages"
```

### Task 3: Update docs and verification coverage

**Objective:** Align README/BMAD docs and run the real repo gate.

**Files:**
- Modify: `README.md`
- Modify: `_bmad-output/implementation-artifacts/29-1-add-public-leaderboard-and-completed-match-browse-pages-in-the-web-client.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Write/update failing expectations if needed**

If README/browser-route coverage already has tests, extend them first; otherwise rely on the page/component tests from Task 2 plus route wiring assertions.

**Step 2: Run focused verification**

Run:
- `cd client && npm test -- --run src/lib/api.test.ts src/components/public/public-leaderboard-page.test.tsx src/components/public/completed-matches-page.test.tsx`
- `cd client && npm run build`

Expected: PASS.

**Step 3: Run the full repo gate**

Run: `make quality`
Expected: PASS.

**Step 4: Update docs/BMAD artifacts**

Document the new public pages in `README.md`, mark Story 29.1 done with completion notes, and advance `sprint-status.yaml` to Story 29.2 as next.

**Step 5: Commit**

```bash
git add README.md _bmad-output/implementation-artifacts/29-1-add-public-leaderboard-and-completed-match-browse-pages-in-the-web-client.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "docs: close story 29.1 public read pages"
```

---

## Verification Checklist

- `cd client && npm test -- --run src/lib/api.test.ts src/components/public/public-leaderboard-page.test.tsx src/components/public/completed-matches-page.test.tsx`
- `cd client && npm run build`
- `make quality`

## Parallelism / Execution Notes

- Story 29.1 should stay sequential in one worktree because it touches shared public navigation, routes, `lib/types.ts`, and `lib/api.ts`.
- Story 29.2 can follow after Story 29.1 lands; do not run them in parallel.
- Review order remains: spec compliance first, code quality second, then simplification and main-repo verification.
