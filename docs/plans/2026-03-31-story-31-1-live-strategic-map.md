# Story 31.1 Live Strategic Map Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Render the canonical Britain board as a shared read-only SVG map on the spectator and authenticated human live pages using only the shipped live payloads plus the canonical checked-in map definition.

**Architecture:** Keep the implementation boring and shared. Introduce one reusable client map component plus a tiny map-data adapter around the canonical Britain map artifact already committed in the repo, then feed that component with the existing spectator and player websocket envelopes. The spectator view can render full ownership/garrison context from the public payload, while the human view must strictly mask unknown details using the existing `visibility` fields rather than inventing any extra API or client-side game logic.

**Tech Stack:** Next.js App Router, React client components, TypeScript, Vitest + Testing Library, existing websocket page shells, repo `make quality` gate.

---

## Parallelism / Sequencing

- **Sequential:** this story touches one shared map component, shared client config/data wiring, and both live page shells. Keep it in one worktree.
- **No new live API:** reuse only the existing public match-detail preload plus the shipped spectator/player websocket envelopes.
- **Read-only scope:** no clickable map controls, no order drafting from the map, no animation engine, no new server endpoints.

### Task 1: Add failing tests for the shared live map contract

**Objective:** Pin the browser-visible strategic map behavior before implementation.

**Files:**
- Create: `client/src/components/matches/match-live-map.test.tsx`
- Modify: `client/src/components/matches/match-live-view.test.tsx`
- Modify: `client/src/components/matches/public-match-live-page.test.tsx`
- Modify: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Write failing tests**

Add tests that prove:
- the spectator live surface renders a `Britain strategic map` section with deterministic SVG city labels/markers
- spectator map nodes show readable ownership plus visible army/garrison context from the shipped public payload
- the human live surface renders the same shared map but masks unknown values for `partial` visibility instead of leaking spectator details
- not-live / disconnected states show explicit read-only explanatory copy instead of a blank or stale map

**Step 2: Run test to verify failure**

Run:
```bash
cd client && npm test -- --run src/components/matches/match-live-map.test.tsx src/components/matches/match-live-view.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/human-match-live-page.test.tsx
```

Expected: FAIL because the shared map component and page wiring do not exist yet.

**Step 3: Write minimal implementation**

Implement the smallest coherent test-passing surface:
- one shared map-data adapter for deterministic city positions/edges from the canonical Britain map artifact
- one shared read-only `MatchLiveMap` component that renders the SVG and visibility-safe overlays
- narrow page wiring that inserts the map panel into the spectator and human live surfaces without changing the websocket transport contract

**Step 4: Run tests to verify pass**

Run:
```bash
cd client && npm test -- --run src/components/matches/match-live-map.test.tsx src/components/matches/match-live-view.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/human-match-live-page.test.tsx
```

Expected: PASS.

### Task 2: Keep the shared map artifact/build path minimal and deterministic

**Objective:** Safely reuse the canonical Britain map definition from the repo without introducing hidden client-only duplication or a fragile build path.

**Files:**
- Create or modify: `client/src/lib/britain-map.ts`
- Modify (if required): `client/next.config.ts`
- Modify (if required): `client/tsconfig.json`

**Step 1: Add a minimal adapter**

Create a tiny typed adapter that exposes only what the live SVG needs:
- ordered city list with stable IDs, names, and coordinates
- edge list with stable city references and traversal mode metadata if needed for styling

Do not duplicate gameplay logic or create a second source of truth for city positions.

**Step 2: Verify the real build path**

Run:
```bash
cd client && npm run build
```

Expected: PASS, proving the map artifact path works in the real Next build, not just in Vitest.

### Task 3: Close docs/BMAD artifacts and run the repo gate

**Objective:** Leave the story aligned with README/BMAD tracking and the full quality harness.

**Files:**
- Modify: `README.md`
- Modify: `_bmad-output/implementation-artifacts/31-1-add-a-shared-read-only-strategic-svg-map-to-the-live-web-client.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Update docs/BMAD artifacts**

Document the new shared live map surface, mark Story 31.1 complete, and advance sprint tracking to Story 31.2.

**Step 2: Run focused verification**

Run:
```bash
cd client && npm test -- --run src/components/matches/match-live-map.test.tsx src/components/matches/match-live-view.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/human-match-live-page.test.tsx
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

- `cd client && npm test -- --run src/components/matches/match-live-map.test.tsx src/components/matches/match-live-view.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/human-match-live-page.test.tsx`
- `cd client && npm run build`
- `make quality`
