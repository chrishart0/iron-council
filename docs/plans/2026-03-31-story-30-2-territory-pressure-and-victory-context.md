# Story 30.2 Territory Pressure and Victory Context Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make the spectator live page explain who currently controls territory and whether a coalition is threatening victory, using only the shipped public roster plus spectator websocket payload.

**Architecture:** Keep the feature client-only and text-first. Aggregate city ownership directly from the spectator websocket snapshot, resolve visible player labels from the already-fetched public roster, optionally fold visible players under alliance names from the same websocket update, and render a compact pressure board plus victory-context copy without inventing a new server route. Prefer deterministic ordering and explicit empty states over speculative rankings.

**Tech Stack:** Next.js App Router, React client components, TypeScript, Vitest + Testing Library, existing spectator websocket/public match detail client helpers, repo `make quality` gate.

---

## Parallelism / Sequencing

- **Sequential:** this story touches the existing spectator live view and its focused tests, so one worktree should own it end-to-end.
- **No backend expansion:** reuse only the shipped spectator websocket payload and the public match-detail roster already fetched by the page.
- **Keep scope tight:** no SVG overlays, no new API, no replay changes, no authenticated controls.

### Task 1: Add failing client tests for territory pressure and victory context

**Objective:** Pin the spectator-facing browser behavior before implementation.

**Files:**
- Modify: `client/src/components/matches/match-live-view.test.tsx`
- Modify: `client/src/components/matches/public-match-live-page.test.tsx`
- Modify: `client/src/components/matches/match-live-view.tsx`

**Step 1: Write failing tests**

Add tests that prove:
- the live view renders a compact territory summary grouped by visible alliance/player labels from the current websocket snapshot
- the summary uses deterministic ordering (owned-city count desc, then label asc)
- active victory countdowns render concrete context copy with the leading alliance/player label, cities held, threshold, and countdown ticks remaining
- inactive or sparse territory states render explanatory empty-state copy instead of fake rankings

**Step 2: Run test to verify failure**

Run:
```bash
cd client && npm test -- --run src/components/matches/match-live-view.test.tsx src/components/matches/public-match-live-page.test.tsx
```

Expected: FAIL because the territory-pressure and victory-context panels do not exist yet.

**Step 3: Write minimal implementation**

Implement only the smallest coherent UI:
- derive city-control counts from `envelope.data.state.cities`
- resolve player labels from `roster`
- if a player belongs to an alliance present in `envelope.data.alliances`, group them under the alliance name; otherwise show the player label
- keep deterministic fallback to raw IDs when a roster/alliance label is unavailable
- render text-first territory and victory panels only from shipped data already in the spectator payload

**Step 4: Run test to verify pass**

Run:
```bash
cd client && npm test -- --run src/components/matches/match-live-view.test.tsx src/components/matches/public-match-live-page.test.tsx
```

Expected: PASS.

### Task 2: Refine copy and edge-case handling for spectator clarity

**Objective:** Keep the pressure board honest, simple, and aligned with the product vision.

**Files:**
- Modify: `client/src/components/matches/match-live-view.tsx`
- Modify: `client/src/components/matches/match-live-view.test.tsx`

**Step 1: Add/extend failing edge-case tests**

Add tests for:
- no owned cities visible
- a leading alliance ID that lacks a visible alliance record
- a live snapshot with city control but no active victory countdown

**Step 2: Run test to verify failure**

Run:
```bash
cd client && npm test -- --run src/components/matches/match-live-view.test.tsx
```

Expected: FAIL until the explanatory copy and fallback handling are implemented.

**Step 3: Write minimal refinement**

Add deterministic copy such as:
- no owned cities visible yet
- no coalition is currently on a victory countdown
- leading coalition label falls back to raw ID when not resolvable

Do not add extra abstractions unless repeated logic truly demands it.

**Step 4: Run test/build to verify pass**

Run:
```bash
cd client && npm test -- --run src/components/matches/match-live-view.test.tsx src/components/matches/public-match-live-page.test.tsx
cd client && npm run build
```

Expected: PASS.

### Task 3: Close docs/BMAD artifacts and run the full gate

**Objective:** Leave Story 30.2 documented, signed off, and ready to close Epic 30.

**Files:**
- Modify: `README.md`
- Modify: `core-architecture.md`
- Modify: `_bmad-output/implementation-artifacts/30-2-add-territory-pressure-and-victory-context-to-the-spectator-live-page.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Update docs/BMAD artifacts**

Document the enriched spectator live surface, fix any architecture drift around the already-shipped public roster fields if needed, mark Story 30.2 complete, and close Epic 30 in sprint tracking.

**Step 2: Run focused verification**

Run:
```bash
cd client && npm test -- --run src/components/matches/match-live-view.test.tsx src/components/matches/public-match-live-page.test.tsx
cd client && npm run build
```

Expected: PASS.

**Step 3: Run the repo gate**

Run:
```bash
make quality
```

Expected: PASS.

---

## Verification Checklist

- `cd client && npm test -- --run src/components/matches/match-live-view.test.tsx src/components/matches/public-match-live-page.test.tsx`
- `cd client && npm run build`
- `make quality`
