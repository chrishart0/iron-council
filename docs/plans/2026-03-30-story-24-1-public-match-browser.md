# Story 24.1 Public Match Browser Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Ship the first human-facing product surface by adding a minimal Next.js client that renders the existing public match browse API at a read-only `/matches` page.

**Architecture:** Keep the first client slice intentionally small and consumer-boundary-only. Add a new `client/` Next.js + TypeScript workspace, fetch the already-shipped `GET /api/v1/matches` route through a tiny typed wrapper, and render deterministic loading/empty/error/success states without adding auth, websockets, or map/gameplay complexity. Extend local docs and CI just enough that the client becomes a supported repo runtime instead of a side experiment.

**Tech Stack:** Next.js (App Router), React, TypeScript, Node/npm, existing FastAPI server, existing Python quality gate plus lightweight client lint/build/test commands.

---

## Parallelism / Sequencing

- **Implementation should stay mostly sequential:** scaffolding, fetch contract, page rendering, and repo quality integration all touch the same new client seam.
- **Safe follow-on parallelism after this story:** Story 24.2 (human JWT auth) can proceed in parallel with a later Story 24.3 client auth/bootstrap pass once the client workspace exists.
- **Do not widen scope:** no lobby mutations, no websocket code, no Supabase auth UI, no map SVG, no design system, no global state library.
- **Refinement pass required:** after the page works, simplify any extra abstraction added only for tests or hypothetical future flows.

## Task 1: Scaffold the smallest supported Next.js client workspace

**Objective:** Create a repo-native `client/` app that can build and host a simple public page.

**Files:**
- Create: `client/package.json`
- Create: `client/tsconfig.json`
- Create: `client/next.config.ts`
- Create: `client/.gitignore`
- Create: `client/src/app/layout.tsx`
- Create: `client/src/app/page.tsx`
- Create: `client/src/app/matches/page.tsx`
- Create: `client/src/app/globals.css`
- Create: `client/src/lib/api.ts`
- Create: `client/src/lib/types.ts`

**Step 1: Write failing test/build proof**

Add or configure a minimal client validation command that fails before the scaffold exists. The fastest acceptable RED step is a build or test command that proves the workspace is missing.

**Step 2: Run the RED command**

```bash
cd client && npm run build
```

Expected: FAIL because the client workspace does not exist yet.

**Step 3: Write minimal implementation**

Create the smallest coherent Next.js app-router scaffold:
- a root layout
- a homepage that links to `/matches`
- a public `/matches` page shell
- a tiny `api.ts` wrapper and `types.ts` file for the compact browse contract

Keep the page server-rendered or simple async-rendered if that is the easiest boring path.

**Step 4: Run the GREEN command**

```bash
cd client && npm install && npm run build
```

Expected: PASS.

## Task 2: Render the public match browser against `GET /api/v1/matches`

**Objective:** Show the existing browse contract in a human-facing page with deterministic UX states.

**Files:**
- Modify: `client/src/app/matches/page.tsx`
- Modify: `client/src/lib/api.ts`
- Modify: `client/src/lib/types.ts`
- Create: `client/src/components/matches/match-list.tsx`
- Create: `client/src/components/matches/match-row.tsx`
- Create: `client/src/components/matches/match-list.test.tsx` or equivalent client test file

**Step 1: Write failing tests**

Add tests that prove:
- successful API data renders rows with compact browse fields
- empty responses render a friendly empty state
- request failures render a deterministic error state

Prefer behavior-first UI tests; avoid asserting internal hook structure.

**Step 2: Run the RED command**

```bash
cd client && npm test -- --runInBand
```

Expected: FAIL because the page/components/test harness are incomplete.

**Step 3: Write minimal implementation**

Implement a small `MatchSummary` TypeScript type matching the public API fields already shipped by Story 20.1, fetch via one helper, and render a boring list/table/card layout.

Guardrails:
- no auth headers
- no retry abstraction unless truly needed
- no hidden transformation layer between fetch and component props beyond the minimal typed parse
- no optimistic behavior or local caching strategy in this story

**Step 4: Run the GREEN command**

```bash
cd client && npm test -- --runInBand
cd client && npm run build
```

Expected: PASS.

## Task 3: Integrate the client into repo ergonomics and documentation

**Objective:** Make the new client a first-class repo runtime with obvious local commands.

**Files:**
- Modify: `README.md`
- Modify: `Makefile`
- Modify: `.github/workflows/quality.yml`
- Create: `client/.env.example` (only if a base URL env var is actually needed)

**Step 1: Write failing verification expectation**

Choose or add commands that will become the supported client workflow:
- install
- lint
- test
- build

If the repo quality workflow will call new Make targets, prove they fail before wiring is complete.

**Step 2: Run the RED command**

```bash
make ci
```

Expected: FAIL until the new client commands and CI wiring exist and are valid.

**Step 3: Write minimal implementation**

Add the simplest coherent commands, for example:
- `make client-install`
- `make client-lint`
- `make client-test`
- `make client-build`

Then decide whether `make quality` should include the client immediately or whether `make ci` should run a separate client section. Prefer the smallest stable path.

Update `README.md` with exact local commands to:
- run the server
- run the client
- visit `/matches`

**Step 4: Run the GREEN commands**

```bash
make quality
make ci
```

Expected: PASS.

## Task 4: Final review and simplification pass

**Objective:** Ensure the first client story stays small, clear, and aligned with the BMAD/source docs.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/24-1-scaffold-a-next-js-client-and-public-match-browser.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `_bmad-output/planning-artifacts/architecture.md` only if implementation details drift from the current architecture wording
- Modify: `core-architecture.md` only if the public contract/doc wording drifts

**Step 1: Review against the acceptance criteria**

Check explicitly:
- the page uses the existing public browse route
- the client remains read-only
- fields shown stay compact/public
- empty/error states are deterministic
- docs and repo commands are accurate

**Step 2: Run final verification**

```bash
cd client && npm run build
cd client && npm test -- --runInBand
make quality
make ci
```

Expected: PASS.

**Step 3: Complete BMAD closeout**

- mark Story 24.1 done only after verification passes
- fill in the story artifact debug log/completion notes/file list
- preserve Epic 24 sequencing so Story 24.2 remains ready-for-dev next

## Final review checklist

- [ ] `client/` exists and builds cleanly
- [ ] `/matches` renders only public browse metadata from the existing API
- [ ] empty and error states are intentional and user-safe
- [ ] no auth, websocket, or gameplay scope leaked into this story
- [ ] local run docs are exact and tested
- [ ] repo verification commands cover the new client surface
- [ ] BMAD artifacts reflect the shipped state
