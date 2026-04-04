# Epic 54 Client API Boundary Decomposition Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Reduce risk on the shipped browser contract by splitting `client/src/lib/api.ts` along stable public-versus-authenticated seams while preserving every current export and runtime behavior.

**Architecture:** Keep `client/src/lib/api.ts` as the compatibility entrypoint for current callers, but move coherent helper families behind narrowly scoped modules under `client/src/lib/api/`. Start with the public read and live-envelope parsing surface because it has clear boundaries, wide reuse, and no auth/write coupling. Follow with authenticated write and account-management families only after the public slice is merged and verified.

**Tech Stack:** Next.js/React TypeScript client, Vitest, existing `client/src/lib/types.ts` contracts, repo `make quality` gate.

---

## Parallelism and dependency notes

- **This run should stay sequential for implementation.** Every near-term decomposition candidate currently starts from `client/src/lib/api.ts`, so parallel Codex workers would collide on the same file and shared test seam.
- **Low-risk first slice:** extract the public read + live-parse family first because it is already behaviorally covered in `client/src/lib/api.test.ts` and consumed by multiple read-only pages.
- **Controller rule:** preserve `./api` imports for all existing callers in this story. No component call sites should need to change yet.

## Epic sequencing

1. **Story 54.1:** extract public read and live parse helpers out of `client/src/lib/api.ts` behind a compatibility-safe module seam.
2. **Story 54.2:** extract authenticated lobby, account API-key, guided-agent, and write helpers so `client/src/lib/api.ts` becomes a thin export facade.

## Story breakdown

### Story 54.1: Extract client public read and live parse helpers out of `client/src/lib/api.ts`

**Objective:** Move the public match/profile/history/replay fetchers plus websocket-envelope parsing into a focused module while keeping the exported `./api` contract unchanged.

**Files:**
- Create: `client/src/lib/api/public-contract.ts`
- Modify: `client/src/lib/api.ts`
- Modify: `client/src/lib/api.test.ts`
- Story: `_bmad-output/implementation-artifacts/54-1-extract-client-public-read-and-live-parse-helpers-out-of-client-src-lib-api-ts.md`

**Bite-sized tasks:**
1. Add a focused seam regression proving the extracted module exports the public-read builders/parsers and that `./api` still re-exports the same public surface.
2. Move public read error classes, fetch helpers, websocket parse helpers, and their tiny private validators into `client/src/lib/api/public-contract.ts`.
3. Leave `client/src/lib/api.ts` as a compatibility facade that re-exports the extracted public helpers while keeping authenticated/write helpers in place for now.
4. Re-run focused `api.test.ts` coverage for the extracted family, then run the strongest repo-managed client/repo gate and record actual outcomes in the story artifact.
5. Inspect the simplification result by checking line counts before/after so the story measurably reduces `client/src/lib/api.ts`.

**Guardrails:**
- No request/response shape changes.
- No caller import churn outside the lib boundary.
- No new class hierarchy or over-abstracted API client object.
- Keep additive modules boring: plain functions, plain error classes, explicit exports.

### Story 54.2: Extract authenticated client write and account-management helpers out of `client/src/lib/api.ts`

**Objective:** Finish the decomposition by splitting the authenticated lobby/write/account/guided-agent helpers into stable modules and trimming `client/src/lib/api.ts` to a thin facade.

**Files:**
- Create: `client/src/lib/api/authenticated-writes.ts`
- Create: `client/src/lib/api/account-session.ts`
- Modify: `client/src/lib/api.ts`
- Modify: `client/src/lib/api.test.ts`

**Bite-sized tasks:**
1. Group exported helpers by stable contract family: lobby lifecycle, messaging/orders/diplomacy, owned API-key lifecycle, guided-agent controls.
2. Extract one or two closely related families at a time into dedicated modules.
3. Keep `./api` as the re-export facade until all callers are ready for any later direct-import cleanup.
4. Re-run focused authenticated client tests, then `make quality`, and measure the final facade size.

**Guardrails:**
- Preserve bearer-token/header semantics exactly.
- Do not combine unrelated auth flows behind a generic client class.
- Prefer future-safe file names that match user-visible route families.

## Expected deliverables

- A materially smaller `client/src/lib/api.ts`.
- Dedicated client lib modules that map to the shipped public and authenticated contract families.
- Focused tests proving the public boundary stays unchanged through the compatibility facade.

## Out of scope

- Backend/API contract changes.
- New pages, routes, or session UX.
- Rewriting all components to import from the new modules directly.
- A generated SDK or generic runtime client abstraction.
