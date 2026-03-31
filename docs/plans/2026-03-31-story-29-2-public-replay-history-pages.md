# Story 29.2 Public Replay/History Pages Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Ship a boring, read-only completed-match replay inspector in the Next.js client that loads deterministic tick history metadata plus one persisted replay snapshot at a time from the existing public history APIs.

**Architecture:** Extend the existing public-browser client pattern instead of inventing a new replay system. Add narrow TypeScript types plus `lib/api.ts` helpers for `GET /api/v1/matches/{id}/history` and `GET /api/v1/matches/{id}/history/{tick}`, then replace the current placeholder `/matches/[matchId]/history` page with a client-side inspector that waits for session hydration, fetches the history list, selects a tick, and renders the authoritative persisted snapshot/orders/events response. Keep the UI text-first and read-only, with deterministic loading and error states plus stable links back to `/matches/completed`, `/leaderboard`, and `/`.

**Tech Stack:** Next.js App Router, React client components, TypeScript, Vitest + Testing Library, existing session-provider helpers, shipped FastAPI public history routes, repo `make quality` gate.

---

### Task 1: Add failing API helper tests for public history and replay reads

**Objective:** Pin the shipped browser/API contract for completed-match history metadata and one-tick replay reads before touching production code.

**Files:**
- Modify: `client/src/lib/api.test.ts`
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`

**Step 1: Write failing tests**

Add tests that expect:
- `fetchMatchHistory(matchId)` to GET `/api/v1/matches/{matchId}/history`
- `fetchMatchReplayTick(matchId, tick)` to GET `/api/v1/matches/{matchId}/history/{tick}`
- explicit `apiBaseUrl` override support for both helpers
- `match_not_found`, `tick_not_found`, and generic unavailable paths to raise typed read-only errors
- malformed payloads to raise the same deterministic typed errors instead of leaking server details

**Step 2: Run tests to verify failure**

Run:
```bash
cd client && npm test -- --run src/lib/api.test.ts
```
Expected: FAIL with missing helper/type exports and/or missing error classes.

**Step 3: Write minimal implementation**

Add narrow response types and boring helper functions in:
- `client/src/lib/types.ts`
- `client/src/lib/api.ts`

Required response shapes:
```ts
export type MatchHistoryEntry = {
  tick: number;
};

export type MatchHistoryResponse = {
  match_id: string;
  status: string;
  current_tick: number;
  tick_interval_seconds: number;
  history: MatchHistoryEntry[];
};

export type MatchReplayTickResponse = {
  match_id: string;
  tick: number;
  state_snapshot: Record<string, unknown>;
  orders: Record<string, unknown>;
  events: Record<string, unknown> | Array<Record<string, unknown>>;
};
```

Add typed errors with explicit `kind` values, for example:
```ts
export class MatchHistoryError extends Error {
  constructor(
    message = "Unable to load match history right now.",
    readonly kind: "not_found" | "unavailable" = "unavailable"
  ) {
    super(message);
    this.name = "MatchHistoryError";
  }
}

export class MatchReplayTickError extends Error {
  constructor(
    message = "Unable to load the selected replay tick right now.",
    readonly kind: "match_not_found" | "tick_not_found" | "unavailable" = "unavailable"
  ) {
    super(message);
    this.name = "MatchReplayTickError";
  }
}
```

Use the existing read-only fetch helper style:
- `cache: "no-store"`
- `accept: "application/json"`
- `resolveApiBaseUrl(...)`
- structured 404 handling via API error-envelope parsing

**Step 4: Run tests to verify pass**

Run:
```bash
cd client && npm test -- --run src/lib/api.test.ts
```
Expected: PASS for the new public history/replay helper coverage.

**Step 5: Commit**

```bash
git add client/src/lib/api.ts client/src/lib/api.test.ts client/src/lib/types.ts
git commit -m "feat: add public replay history client helpers"
```

### Task 2: Add failing browser-boundary tests for the replay inspector page

**Objective:** Drive the real shipped `/matches/[matchId]/history` page from the browser boundary rather than from internal helper-only assertions.

**Files:**
- Modify: `client/src/app/matches/[matchId]/history/page.tsx`
- Modify: `client/src/app/matches/[matchId]/history/page.test.tsx`
- Create: `client/src/components/public/match-history-page.tsx`
- Create: `client/src/components/public/match-history-page.test.tsx`

**Step 1: Write failing tests**

Add browser-facing tests that assert:
- the page renders a loading state before the first fetch resolves
- on success, the history list is shown with deterministic tick metadata from `GET /history`
- the selected tick snapshot panel renders the returned `state_snapshot`, `orders`, and `events` from `GET /history/{tick}`
- selecting another tick triggers a new replay fetch for that exact tick
- not-found and unavailable states render stable read-only copy and preserve navigation links back to completed matches/home/leaderboard
- no websocket-specific copy or placeholder “future story” copy remains

Use a text-first rendering contract. A simple display such as this is acceptable and easy to test:
```tsx
<section className="panel panel-section">
  <h3>Selected tick</h3>
  <p>{`Tick ${selectedTick}`}</p>
  <pre>{JSON.stringify(replay.state_snapshot, null, 2)}</pre>
  <pre>{JSON.stringify(replay.orders, null, 2)}</pre>
  <pre>{JSON.stringify(replay.events, null, 2)}</pre>
</section>
```

**Step 2: Run tests to verify failure**

Run:
```bash
cd client && npm test -- --run src/components/public/match-history-page.test.tsx src/app/matches/[matchId]/history/page.test.tsx
```
Expected: FAIL because the placeholder route does not fetch/render replay data.

**Step 3: Write minimal implementation**

Implement a `MatchHistoryPage` client component that:
- reads `apiBaseUrl` and `hasHydrated` from `SessionProvider`
- fetches history once after hydration
- defaults to the newest available tick (last entry in ascending `history`) when the history payload arrives
- fetches one selected replay snapshot at a time from the shipped `/history/{tick}` route
- renders loading / error / empty / ready states without hiding navigation
- keeps the surface read-only and text-first
- uses buttons or an explicit list for tick selection; one request per selection is enough
- shows structured copy for:
  - missing match
  - missing tick
  - unavailable DB-backed history API

Suggested state shape:
```ts
type ReplayInspectorState = {
  historyStatus: "loading" | "ready" | "error";
  replayStatus: "idle" | "loading" | "ready" | "error";
  history: MatchHistoryResponse | null;
  replay: MatchReplayTickResponse | null;
  selectedTick: number | null;
  errorMessage: string | null;
};
```

Keep the route file thin:
```tsx
export default async function MatchHistoryRoute({ params }: MatchHistoryPageProps) {
  const { matchId } = await params;
  return <MatchHistoryPage matchId={matchId} />;
}
```

**Step 4: Run tests to verify pass**

Run:
```bash
cd client && npm test -- --run src/components/public/match-history-page.test.tsx src/app/matches/[matchId]/history/page.test.tsx
```
Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/app/matches/[matchId]/history/page.tsx client/src/app/matches/[matchId]/history/page.test.tsx client/src/components/public/match-history-page.tsx client/src/components/public/match-history-page.test.tsx
git commit -m "feat: add completed match replay inspector page"
```

### Task 3: Update docs/BMAD artifacts and run the real quality gate

**Objective:** Verify the finished story through the real repo command path and close the planning artifacts.

**Files:**
- Modify: `README.md`
- Modify: `_bmad-output/implementation-artifacts/29-2-add-public-completed-match-history-and-replay-inspection-pages-in-the-web-client.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run focused client verification**

Run:
```bash
cd client && npm test -- --run src/lib/api.test.ts src/components/public/match-history-page.test.tsx src/app/matches/[matchId]/history/page.test.tsx src/components/public/completed-matches-page.test.tsx
cd client && npm run build
```
Expected: PASS.

**Step 2: Run the repo quality gate**

Run:
```bash
make quality
```
Expected: PASS.

**Step 3: Update docs and BMAD closeout**

Document that:
- `/matches/<match_id>/history` now ships as a real read-only replay inspector page
- the client uses the shipped `GET /api/v1/matches/{id}/history` and `GET /api/v1/matches/{id}/history/{tick}` routes only
- Story 29.2 is done, with completion notes and final file list
- `sprint-status.yaml` advances Epic 29 appropriately

**Step 4: Run simplification pass**

Review the final change set for:
- no invented replay websocket API
- no unnecessary abstraction layer for view-model transformation
- no over-engineered pretty-printing beyond simple text-first inspection
- browser/API boundary tests still centered on public behavior

**Step 5: Commit**

```bash
git add README.md _bmad-output/implementation-artifacts/29-2-add-public-completed-match-history-and-replay-inspection-pages-in-the-web-client.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "docs: close story 29.2 public replay inspector"
```

---

## Verification Checklist

- `cd client && npm test -- --run src/lib/api.test.ts`
- `cd client && npm test -- --run src/components/public/match-history-page.test.tsx src/app/matches/[matchId]/history/page.test.tsx`
- `cd client && npm test -- --run src/components/public/completed-matches-page.test.tsx`
- `cd client && npm run build`
- `make quality`

## Parallelism / Execution Notes

- Story 29.2 should stay sequential in a single worker worktree because it touches the shared public client route, `lib/api.ts`, `lib/types.ts`, README route docs, and BMAD closeout artifacts.
- There is no safe high-value parallel feature story in this run because Epic 29 currently exposes only this drafted next story and its public route contract overlaps with the just-finished Story 29.1 navigation surface.
- Review order remains: implementation -> spec compliance review -> code-quality/KISS review -> simplification pass -> main-repo verification.
