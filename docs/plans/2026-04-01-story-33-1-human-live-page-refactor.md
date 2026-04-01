# Story 33.1 Human Live Page Refactor Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Split the oversized authenticated human live match page into smaller UI and state slices without changing the shipped browser/API/WebSocket contract.

**Architecture:** Keep `HumanMatchLivePage` as the public entrypoint for the Next.js route, but move fetch/websocket/session state and the major UI surfaces into focused modules under `client/src/components/matches/human-live/`. Preserve the current behavior-first tests and add regression coverage that proves the route still renders the same major sections and still submits through the existing client API helpers.

**Tech Stack:** Next.js 16, React 19 client components/hooks, TypeScript, Vitest, Testing Library.

---

### Parallelism / sequencing

- **Sequential only for implementation.** The current page and its giant test file both concentrate the same feature surface, so parallel Codex workers would collide heavily.
- **Safe parallel support work:** lightweight review tasks can run after implementation because they are read-only.
- **Primary risk:** accidental browser-contract drift while extracting helpers/components. Guard with contract-level tests first.

### Task 1: Pin the current page contract with focused regression coverage

**Objective:** Lock the current human live page behavior at the browser boundary before extracting code.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.test.tsx`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Write failing tests**

Add or tighten tests that prove:
- the top-level page still renders the hero/status shell and the key sections (`Map selection inspector`, `Live messaging`, `Live diplomacy`, `Order Drafts`)
- at least one messaging, diplomacy, and order-submission happy path still calls the existing API helper layer through the current user journey
- offline / not-live state still preserves last confirmed snapshot copy when the socket closes after an update

**Step 2: Run the focused test file to verify the red/green baseline**

Run:

```bash
cd client && npm test -- human-match-live-page.test.tsx
```

Expected: either green on the tightened assertions or red on the newly added contract cases.

**Step 3: Keep only contract-level assertions**

Prefer assertions on visible section headings, feedback copy, and outgoing browser actions. Avoid asserting internal component names or hook state.

**Step 4: Re-run the same focused test**

Run:

```bash
cd client && npm test -- human-match-live-page.test.tsx
```

Expected: PASS before structural refactoring starts.

**Step 5: Commit**

```bash
git add client/src/components/matches/human-match-live-page.test.tsx
git commit -m "test: pin human live page contract"
```

### Task 2: Extract the page shell and live-state hook

**Objective:** Move session/fetch/websocket lifecycle logic out of the monolithic page component while keeping `HumanMatchLivePage` as the route-facing entrypoint.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.tsx`
- Create: `client/src/components/matches/human-live/use-human-match-live-state.ts`
- Create: `client/src/components/matches/human-live/human-match-live-shell.tsx`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Extract the pure state boundary**

Create a focused hook that owns:
- public match detail loading
- websocket connect/reconnect-close state
- returned `matchState` / `liveState`
- the exact same error and not-live copy currently shown by the page

**Step 2: Move the hero/loading/error shell into a dedicated component**

`HumanMatchLiveShell` should render the existing hero, loading, and not-live wrappers and accept the already-derived state as props.

**Step 3: Keep the route-facing component boring**

`HumanMatchLivePage` should mostly:
- read the session
- call the extracted hook
- render the shell
- pass the live envelope into the snapshot surface when available

**Step 4: Run focused tests**

Run:

```bash
cd client && npm test -- human-match-live-page.test.tsx
cd client && npm run lint
```

Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/components/matches/human-match-live-page.tsx client/src/components/matches/human-live/use-human-match-live-state.ts client/src/components/matches/human-live/human-match-live-shell.tsx client/src/components/matches/human-match-live-page.test.tsx
git commit -m "refactor: extract human live page shell state"
```

### Task 3: Extract read-only snapshot panels and selection helpers

**Objective:** Break the giant snapshot render tree into stable read-only components before touching the write forms.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.tsx`
- Create: `client/src/components/matches/human-live/human-match-live-snapshot.tsx`
- Create: `client/src/components/matches/human-live/human-match-live-summary-panels.tsx`
- Create: `client/src/components/matches/human-live/human-match-live-selection-panel.tsx`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Extract the snapshot component**

Move the main snapshot surface out of `human-match-live-page.tsx` and keep props explicit instead of introducing context or generic component registries.

**Step 2: Split read-only rendering seams**

Create small components for:
- map selection inspector
- live summary/resources/fog-filtered movement panels
- chat/diplomacy summary list

Keep utility helpers near the extracted snapshot modules if they are only used there.

**Step 3: Preserve labels and accessibility hooks**

Do not rename the visible section headings or aria labels that the tests and user flows depend on.

**Step 4: Run focused tests**

Run:

```bash
cd client && npm test -- human-match-live-page.test.tsx
cd client && npm run lint
```

Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/components/matches/human-match-live-page.tsx client/src/components/matches/human-live/human-match-live-snapshot.tsx client/src/components/matches/human-live/human-match-live-summary-panels.tsx client/src/components/matches/human-live/human-match-live-selection-panel.tsx client/src/components/matches/human-match-live-page.test.tsx
git commit -m "refactor: split human live snapshot panels"
```

### Task 4: Extract write surfaces for messaging, diplomacy, and orders

**Objective:** Isolate the three highest-change interactive surfaces behind focused components while keeping the existing API helper contract and success/error copy intact.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.tsx`
- Create: `client/src/components/matches/human-live/human-live-messaging-panel.tsx`
- Create: `client/src/components/matches/human-live/human-live-diplomacy-panel.tsx`
- Create: `client/src/components/matches/human-live/human-live-orders-panel.tsx`
- Test: `client/src/components/matches/human-match-live-page.test.tsx`

**Step 1: Move one form family at a time**

Extract messaging first, then diplomacy, then order drafts. Keep prop names concrete and pass the submit helpers or callbacks explicitly.

**Step 2: Preserve acceptance feedback semantics**

Success/error states must still render the same public text and must still rely on the accepted response payloads already returned by the API helper layer.

**Step 3: Delete dead local helpers**

After extraction, remove any unused state, utility functions, or duplicated literals from `human-match-live-page.tsx`.

**Step 4: Run focused client verification**

Run:

```bash
cd client && npm test -- human-match-live-page.test.tsx
cd client && npm test -- public-match-live-page.test.tsx match-live-map.test.tsx
cd client && npm run lint
```

Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/components/matches/human-match-live-page.tsx client/src/components/matches/human-live/human-live-messaging-panel.tsx client/src/components/matches/human-live/human-live-diplomacy-panel.tsx client/src/components/matches/human-live/human-live-orders-panel.tsx client/src/components/matches/human-match-live-page.test.tsx
git commit -m "refactor: extract human live interactive panels"
```

### Task 5: Simplify, run the real quality gate, and update BMAD artifacts

**Objective:** Finish in the simplest coherent shippable state and document the story completion.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.tsx`
- Modify: `_bmad-output/implementation-artifacts/33-1-refactor-human-live-page-into-smaller-ui-and-state-slices.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run a simplification pass**

Check for:
- props that can be narrowed
- utilities that should stay local instead of becoming shared
- avoidable abstraction introduced only for tests
- opportunities to keep `human-match-live-page.tsx` as a thin export/composition file

**Step 2: Run the repo-managed verification commands**

Run:

```bash
make client-test
make client-build
make quality
```

Expected: PASS.

**Step 3: Update story bookkeeping**

Mark the BMAD story done, record the verification commands actually run, and update sprint tracking to the next state.

**Step 4: Review before merge**

Do a spec-compliance review first, then a code-quality / KISS review.

**Step 5: Commit**

```bash
git add client/src/components/matches/human-match-live-page.tsx client/src/components/matches/human-live _bmad-output/implementation-artifacts/33-1-refactor-human-live-page-into-smaller-ui-and-state-slices.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "refactor: split human live page into focused client modules"
```
