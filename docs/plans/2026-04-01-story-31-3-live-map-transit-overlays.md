# Story 31.3 Live Map Transit Overlays Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add visibility-safe transit overlays to the shared live Britain map so spectators and human players can understand which armies are marching, where visible marches are headed, and how long they have left without changing the live transport contract.

**Architecture:** Keep this as a narrow extension of the existing shared `MatchLiveMap` surface. Reuse the already-shipped Britain map layout plus the existing websocket payload fields (`location`, `destination`, `path`, `ticks_remaining`, `visibility`) to derive read-only marching overlays in the client. Spectators may see full route/ETA detail from the public payload, while the human page must mask route information whenever the current player snapshot marks the army as partially visible or omits path/destination detail.

**Tech Stack:** Next.js App Router, React client components, TypeScript, Vitest + Testing Library, existing live page shells, repo `make quality` gate.

---

## Parallelism / Sequencing

- **Sequential:** this story touches one shared map component plus both live page test surfaces; keep it in one worktree.
- **No API changes:** reuse only the shipped spectator/player websocket envelopes and current public-match preload.
- **Read-only scope:** no new gameplay controls, no drag-to-move implementation, no animation runtime beyond simple deterministic SVG overlays/copy.

### Task 1: Add failing browser-boundary tests for marching overlays

**Objective:** Pin the externally visible transit behavior before implementation.

**Files:**
- Modify: `client/src/components/matches/match-live-map.test.tsx`
- Modify: `client/src/components/matches/public-match-live-page.test.tsx`
- Modify: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Write failing tests**

Add tests that prove:
- the shared map renders a visible transit overlay/summary for armies whose websocket payload includes a visible destination/path and remaining ticks
- the spectator live page exposes deterministic route/ETA copy for in-transit armies from the existing public payload
- the human live page masks route specifics when the army is only partially visible or the payload omits destination/path detail, while still showing a safe marching/ETA indicator
- empty-state copy appears when no visible transit overlays exist

**Step 2: Run test to verify failure**

Run:
```bash
cd client && npm test -- --run src/components/matches/match-live-map.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/human-match-live-page.test.tsx
```

Expected: FAIL because the shared map does not yet render marching overlays or visibility-safe transit summaries.

**Step 3: Write minimal implementation**

Implement the smallest coherent test-passing surface:
- extend the shared `MatchLiveMap` component with deterministic transit overlay rendering and readable marching summaries
- feed it only existing army fields already present in the page adapters
- keep the player surface visibility-safe by hiding route geometry/copy whenever the current payload does not expose enough data

**Step 4: Run tests to verify pass**

Run:
```bash
cd client && npm test -- --run src/components/matches/match-live-map.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/human-match-live-page.test.tsx
```

Expected: PASS.

### Task 2: Keep the shared map overlay logic simple, deterministic, and visibility-safe

**Objective:** Add route/ETA rendering without introducing browser-only game rules or leaky fog behavior.

**Files:**
- Modify: `client/src/components/matches/match-live-map.tsx`
- Modify: `client/src/components/matches/match-live-view.tsx`
- Modify: `client/src/components/matches/human-match-live-page.tsx`

**Step 1: Derive overlay data from existing contracts**

Implement a tiny adapter layer that passes only the route fields the map already needs:
- current city id
- destination city id when visible
- visible path segments when available
- ticks remaining
- visibility mode

Do not infer hidden destinations, reconstruct unknown paths, or add client-side routefinding.

**Step 2: Verify the real client build path**

Run:
```bash
cd client && npm run build
```

Expected: PASS, proving the shared overlay code works in the real Next build.

### Task 3: Close docs/BMAD artifacts and run the repo gate

**Objective:** Leave the story aligned with README/BMAD tracking and the full quality harness.

**Files:**
- Modify: `README.md`
- Modify: `_bmad-output/planning-artifacts/epics.md`
- Modify: `_bmad-output/implementation-artifacts/31-3-add-visibility-safe-live-map-transit-overlays.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Update docs/BMAD artifacts**

Document the new transit overlays, mark Story 31.3 complete, and advance sprint tracking to the next chosen increment.

**Step 2: Run focused verification**

Run:
```bash
cd client && npm test -- --run src/components/matches/match-live-map.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/human-match-live-page.test.tsx
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

- `cd client && npm test -- --run src/components/matches/match-live-map.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/human-match-live-page.test.tsx`
- `cd client && npm run build`
- `make quality`
