# Epic 57 Live Browser Regression Sharding Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Reduce the remaining live-client regression hotspots by splitting the largest authenticated and spectator browser-facing suites into smaller route-owned seams without changing shipped behavior.

**Architecture:** Keep Epic 57 client-only and maintainability-focused. Story 57.1 should decompose the oversized authenticated human live messaging/diplomacy regression surface plus its helper bulk into smaller harness modules and behavior-first suites aligned to shipped interaction seams. Story 57.2 should then apply the same treatment to the spectator/public live page regression monolith so both live surfaces have smaller review and failure boundaries while preserving the existing browser/API contract.

**Tech Stack:** Next.js client, Vitest, Testing Library, existing Story 56 browser smoke, `make client-test`, focused `npm test -- --run ...` slices, `make quality`.

---

## Parallelism and dependency notes

- **Prefer sequential story execution for this epic.** Story 57.1 and Story 57.2 both touch `client/src/components/matches/`, shared live-page fixture patterns, and the same repo client quality gate. Running them in parallel would create unnecessary merge/conflict risk for low-value maintainability work.
- **Within a story, keep one focused Codex worker.** These are bounded refactor/test-sharding tasks that should one-shot cleanly with tight prompts.
- **Controller rule:** no new product features, no route/API contract changes, and no generic abstraction framework. This is regression-surface reduction only.

## Epic sequencing

1. **Story 57.1:** split the authenticated human live messaging/diplomacy regression hotspot into smaller suites and helper modules.
2. **Story 57.2:** split the spectator live page regression hotspot into focused suites and helper modules.

## Story breakdown

### Story 57.1: Split the authenticated human live messaging and diplomacy regression hotspot into route-owned suites

**Objective:** Replace the largest remaining authenticated live-page test hotspot with smaller suite boundaries and lighter-weight test support while keeping the rendered behavior contract unchanged.

**Files:**
- Modify: `client/src/components/matches/human-match-live-page.messaging-diplomacy.test.tsx`
- Modify: `client/src/components/matches/human-match-live-page-test-helpers.tsx`
- Create: additional focused authenticated live-page suites and/or helper modules under `client/src/components/matches/`
- Test: focused Vitest slices for the new files, `make browser-smoke`, `make client-test`, `make quality`
- Story: `_bmad-output/implementation-artifacts/57-1-split-the-authenticated-human-live-messaging-and-diplomacy-regression-hotspot-into-route-owned-suites.md`

**Bite-sized tasks:**
1. Identify the stable behavior seams inside the current monolith (messaging composer rendering, direct/group targeting, group-chat create flow, treaty/alliance controls, structured error handling).
2. Split shared harness/setup from bulky envelope/fixture builders only where it materially shrinks the regression file.
3. Move one seam at a time into focused suites with names that match the shipped UI surface.
4. Keep assertions browser-boundary oriented (`fetch` URL/method/body, rendered headings/forms/status text, websocket-driven refresh behavior) rather than helper spies.
5. Re-run the Story 56 browser smoke, the focused authenticated live-page suites, `make client-test`, and the repo quality gate.

**Guardrails:**
- Do not change production browser behavior or copy except where a test name/file move requires no user-visible change.
- Do not collapse multiple seams into a new generic helper library.
- Prefer deleting dead support code over preserving compatibility wrappers.

### Story 57.2: Split the spectator live page regression hotspot into focused suites and helper modules

**Objective:** Reduce the blast radius of spectator live-page changes by sharding the oversized public live regression surface into smaller behavior-first suites with lighter support code.

**Files:**
- Modify: `client/src/components/matches/public-match-live-page.test.tsx`
- Create/modify: focused spectator live-page suites and any narrow support modules under `client/src/components/matches/`
- Test: focused Vitest slices for the new spectator files, `make browser-smoke`, `make client-test`, `make quality`
- Story: `_bmad-output/implementation-artifacts/57-2-split-the-spectator-live-page-regression-hotspot-into-focused-suites-and-helper-modules.md`

**Bite-sized tasks:**
1. Identify stable spectator seams (connection lifecycle, summary/live state rendering, pressure/victory context, map rendering/links, auth/session-independent behavior).
2. Extract only the minimum support builders needed to keep each focused suite readable.
3. Replace the monolithic spectator file with several suite files that each own one user-visible seam.
4. Re-run the Story 56 browser smoke, the focused spectator suites, `make client-test`, and the repo quality gate.

**Guardrails:**
- No backend/API contract changes.
- No visual snapshot tests or brittle DOM-wide assertions.
- Keep the public live page in the simplest coherent state after the refactor.

## Expected deliverables

- A smaller authenticated live regression surface with clearer file ownership.
- A smaller spectator live regression surface with clearer file ownership.
- Unchanged shipped browser behavior, protected by the existing runtime browser smoke and the repo quality harness.

## Out of scope

- New gameplay features.
- New browser smoke scenarios beyond the existing Story 56 path.
- Generic test frameworks or cross-cutting live-page service layers.
