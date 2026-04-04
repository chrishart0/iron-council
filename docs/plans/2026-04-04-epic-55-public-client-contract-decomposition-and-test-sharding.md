# Epic 55 Public Client Contract Decomposition and Test Sharding Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Reduce the blast radius of future client contract work by decomposing the oversized public contract module and its monolithic regression suite without changing any shipped browser behavior.

**Architecture:** Keep both `client/src/lib/api.ts` and `client/src/lib/api/public-contract.ts` as compatibility facades while moving public helpers behind route-family modules under `client/src/lib/api/`. Then shard the tests along the same route families so the seam regressions stay explicit but each browser-contract family can evolve in a smaller file. This is refactor-only work: no caller import churn outside the lib boundary, no request/response shape changes, and no new generic client abstraction.

**Tech Stack:** Next.js/React TypeScript client, Vitest, existing `client/src/lib/types.ts` browser contracts, repo `make quality` gate.

---

## Parallelism and dependency notes

- **Execution should stay sequential.** Story 55.2 depends on the final module layout established by Story 55.1, and both stories touch the shared seam around `client/src/lib/api/public-contract.ts`.
- **Safe parallelism inside a worker:** small mechanical moves across newly created modules are fine, but only one worker should own the public-contract seam at a time.
- **Verification order matters:** run focused Vitest checks after each story, then rerun the repo `make quality` gate after Story 55.2.

## Story sequencing

1. **Story 55.1:** split `client/src/lib/api/public-contract.ts` into route-family modules and leave a tiny compatibility facade.
2. **Story 55.2:** split `client/src/lib/api.test.ts` into focused suites aligned with the new modules while preserving seam regressions and behavior coverage.

## Story 55.1: Extract public client route families out of `client/src/lib/api/public-contract.ts`

**Objective:** Move public browse/detail/profile/history/replay/live-envelope helpers into boring route-family modules while keeping `client/src/lib/api/public-contract.ts` as the compatibility entrypoint.

**Files:**
- Create: `client/src/lib/api/public-browse.ts`
- Create: `client/src/lib/api/public-profiles.ts`
- Create: `client/src/lib/api/public-history.ts`
- Create: `client/src/lib/api/live-envelope.ts`
- Modify: `client/src/lib/api/public-contract.ts`
- Modify: `client/src/lib/api.ts`
- Test: `client/src/lib/api.test.ts` (or a focused seam subset before Story 55.2)
- Story: `_bmad-output/implementation-artifacts/55-1-extract-public-client-route-families-out-of-client-src-lib-api-public-contract-ts.md`

### Task 55.1.1: Pin the seam before moving code

**Objective:** Prove the future route-family modules still re-export through both `./api/public-contract` and `./api`.

**Step 1: Write failing seam tests**

Add focused seam assertions that expect the future modules to exist and to export the same functions/classes as the current facades.

**Step 2: Run the focused seam tests to verify failure**

Run: `cd client && npm test -- --run src/lib/api.test.ts -t "public api extraction seam|authenticated api extraction seam"`
Expected: FAIL because the new public route-family modules do not exist yet.

**Step 3: Create the minimal module shells**

Add the new files with placeholder re-exports so the seam can compile before the real move.

**Step 4: Run the same focused seam tests**

Expected: PASS after the shells and compatibility exports exist.

**Step 5: Commit**

```bash
git add client/src/lib/api.ts client/src/lib/api/public-contract.ts client/src/lib/api/*.ts client/src/lib/api.test.ts
git commit -m "test: pin public client api extraction seam"
```

### Task 55.1.2: Move public browse/detail helpers into `public-browse.ts`

**Objective:** Extract match browse/detail + completed browse helpers and their validators into one route-family module.

**Files:**
- Create/modify: `client/src/lib/api/public-browse.ts`
- Modify: `client/src/lib/api/public-contract.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write or tighten failing tests**

Add/adjust tests for:
- `fetchPublicMatches`
- `fetchPublicMatchDetail`
- `fetchCompletedMatches`
- additive competitor/roster parsing regressions

**Step 2: Run the focused tests**

Run: `cd client && npm test -- --run src/lib/api.test.ts -t "fetchPublicMatches|fetchPublicMatchDetail|fetchCompletedMatches"`
Expected: RED if the extraction temporarily breaks re-exports or validators.

**Step 3: Move the minimal code**

Keep only the browse-family fetchers, errors, validators, and tiny shared helpers in `public-browse.ts`. Leave the facade as explicit re-exports.

**Step 4: Re-run focused tests**

Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/lib/api/public-browse.ts client/src/lib/api/public-contract.ts client/src/lib/api.test.ts
git commit -m "refactor: extract public browse client helpers"
```

### Task 55.1.3: Move public profile helpers into `public-profiles.ts`

**Objective:** Extract leaderboard + public agent/human profile fetchers and validators into one module.

**Files:**
- Create/modify: `client/src/lib/api/public-profiles.ts`
- Modify: `client/src/lib/api/public-contract.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Focus the failing tests**

Run: `cd client && npm test -- --run src/lib/api.test.ts -t "fetchPublicLeaderboard|fetchPublicAgentProfile|fetchPublicHumanProfile"`

**Step 2: Move the minimal implementation**

Keep only the profile-family fetchers/errors/validators in `public-profiles.ts`.

**Step 3: Re-run the focused tests**

Expected: PASS.

**Step 4: Commit**

```bash
git add client/src/lib/api/public-profiles.ts client/src/lib/api/public-contract.ts
git commit -m "refactor: extract public profile client helpers"
```

### Task 55.1.4: Move history/replay and websocket envelope helpers into focused modules

**Objective:** Finish the decomposition by separating durable history/replay helpers from websocket envelope parsing.

**Files:**
- Create/modify: `client/src/lib/api/public-history.ts`
- Create/modify: `client/src/lib/api/live-envelope.ts`
- Modify: `client/src/lib/api/public-contract.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Run focused tests for history/replay/live parsing**

Run: `cd client && npm test -- --run src/lib/api.test.ts -t "fetchPublicMatchHistory|fetchMatchReplayTick|parsePlayerMatchEnvelope|parseSpectatorMatchEnvelope|parseWebSocketApiErrorEnvelope"`

**Step 2: Move the minimal implementation**

Keep history/replay fetchers and validators in `public-history.ts`, and websocket envelope parsers/validators in `live-envelope.ts`.

**Step 3: Re-run the focused tests**

Expected: PASS.

**Step 4: Run broader client verification**

Run: `cd client && npm test -- --run src/lib/api.test.ts`
Expected: PASS.

**Step 5: Simplification review**

Check line counts and make sure `client/src/lib/api/public-contract.ts` is now just explicit re-exports.

**Step 6: Commit**

```bash
git add client/src/lib/api/public-contract.ts client/src/lib/api/public-history.ts client/src/lib/api/live-envelope.ts client/src/lib/api.test.ts
git commit -m "refactor: split public client contract helpers"
```

## Story 55.2: Split `client/src/lib/api.test.ts` into focused module-aligned suites

**Objective:** Replace the giant single-file client API regression suite with focused route-family suites while keeping the exported contract and seam coverage explicit.

**Files:**
- Create: `client/src/lib/api/public-browse.test.ts`
- Create: `client/src/lib/api/public-profiles.test.ts`
- Create: `client/src/lib/api/public-history.test.ts`
- Create: `client/src/lib/api/live-envelope.test.ts`
- Create: `client/src/lib/api/account-session.test.ts`
- Create: `client/src/lib/api/lobby-lifecycle.test.ts`
- Create: `client/src/lib/api/match-writes.test.ts`
- Create: `client/src/lib/api/guided-agents.test.ts`
- Create: `client/src/lib/api/seam.test.ts`
- Modify/delete: `client/src/lib/api.test.ts`
- Story: `_bmad-output/implementation-artifacts/55-2-split-client-src-lib-api-test-ts-into-focused-module-aligned-suites.md`

### Task 55.2.1: Create a dedicated seam test file

**Objective:** Preserve the compatibility-facade regression separately from functional tests.

**Step 1: Move only the seam assertions into `client/src/lib/api/seam.test.ts`**

Keep explicit checks for:
- `client/src/lib/api.ts` re-exports
- `client/src/lib/api/public-contract.ts` re-exports
- route-family module identity

**Step 2: Run the seam file**

Run: `cd client && npm test -- --run src/lib/api/seam.test.ts`
Expected: PASS.

**Step 3: Commit**

```bash
git add client/src/lib/api/seam.test.ts client/src/lib/api.test.ts
git commit -m "test: isolate client api seam regression"
```

### Task 55.2.2: Move public-contract tests into route-family files

**Objective:** Split browse, profiles, history/replay, and live-envelope tests into the same module families as the production code.

**Step 1: Move one family at a time**

Suggested mapping:
- browse/detail/completed -> `public-browse.test.ts`
- leaderboard/agent/human profiles -> `public-profiles.test.ts`
- history/replay -> `public-history.test.ts`
- websocket envelope parsing -> `live-envelope.test.ts`

**Step 2: After each move, run only the new file**

Examples:
- `cd client && npm test -- --run src/lib/api/public-browse.test.ts`
- `cd client && npm test -- --run src/lib/api/public-profiles.test.ts`
- `cd client && npm test -- --run src/lib/api/public-history.test.ts`
- `cd client && npm test -- --run src/lib/api/live-envelope.test.ts`

**Step 3: Keep tests behavior-first**

Do not replace public-boundary assertions with internal helper spying. Preserve the existing fetch URL/body/header and parsing behavior checks.

### Task 55.2.3: Move authenticated helper tests into module-aligned files

**Objective:** Finish the test sharding so each authenticated helper family owns its own file.

**Step 1: Split tests into**
- `account-session.test.ts`
- `lobby-lifecycle.test.ts`
- `match-writes.test.ts`
- `guided-agents.test.ts`

**Step 2: Run each new file after moving its tests**

Examples:
- `cd client && npm test -- --run src/lib/api/account-session.test.ts`
- `cd client && npm test -- --run src/lib/api/lobby-lifecycle.test.ts`
- `cd client && npm test -- --run src/lib/api/match-writes.test.ts`
- `cd client && npm test -- --run src/lib/api/guided-agents.test.ts`

**Step 3: Remove the giant original file once coverage has moved**

Delete or reduce `client/src/lib/api.test.ts` only after the new files are green and no tests are lost.

### Task 55.2.4: Final verification and quality gate

**Objective:** Prove the sharded suite still protects the shipped boundary and leaves the repo simpler.

**Step 1: Run the whole client API test slice**

Run: `cd client && npm test -- --run src/lib/api/*.test.ts`
Expected: PASS.

**Step 2: Run the repo gate**

Run: `source .venv/bin/activate && make quality`
Expected: PASS.

**Step 3: Simplification review**

Confirm:
- no new generic test utilities hide the public boundary
- each test file aligns to one module family
- no coverage was silently dropped

**Step 4: Commit**

```bash
git add client/src/lib/api/*.test.ts client/src/lib/api.test.ts
git commit -m "test: shard client api contract suites"
```

## Final integration review checklist

- `client/src/lib/api.ts` remains a thin compatibility facade.
- `client/src/lib/api/public-contract.ts` remains a thin compatibility facade.
- Public route-family modules are boring plain-function files.
- Public browser request/response semantics are unchanged.
- Seam regressions still prove the exported surface.
- `make quality` passes from the controller repo.

## Out of scope

- Changing any server route or response contract.
- Rewriting component call sites to import the new modules directly.
- Adding a shared client class or runtime abstraction.
- Any new page or UX behavior.
