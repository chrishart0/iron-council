# Epic 56 Browser Launch Confidence and Human Live Maintainability Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add one real-browser smoke over the documented local demo/runtime path, then use that protection to decompose the largest remaining authenticated live-client hotspot.

**Architecture:** Keep Epic 56 narrow and launch-focused. Story 56.1 should add the smallest honest browser automation layer possible around the existing packaged runtime, seeded DB flow, and shipped public/auth-required client routes. Story 56.2 should stay client-only and treat the new smoke as a guardrail while splitting the oversized human live surface into smaller route-owned modules/tests without changing browser-visible behavior.

**Tech Stack:** Python pytest e2e helpers, existing `scripts/runtime-control.sh` server/client entrypoints, seeded DB tooling, Next.js client, Playwright for browser automation, Vitest + Testing Library, `make launch-readiness-smoke`, `make client-test`, `make client-build`, `make quality`.

---

## Parallelism and dependency notes

- **Must stay sequential at the story level:** Story 56.1 should land before Story 56.2 so the repo has browser-level runtime protection before the human-live refactor starts.
- **Within Story 56.1:** a Codex worker can usually implement the smoke end-to-end in one slice because the likely changes overlap on test harness/bootstrap files (`tests/e2e/`, `client/package.json`, `Makefile`, docs if needed).
- **Within Story 56.2:** future decomposition can be split into presentational vs test-sharding follow-ups only after Story 56.1 is green.
- **Controller rule:** do not widen this epic into login automation, payment flows, or new backend endpoints. The value is launch confidence plus maintainability over already shipped surfaces.

## Epic sequencing

1. **Story 56.1:** add a browser smoke for the public demo walkthrough and auth-required route guardrails.
2. **Story 56.2:** refactor the human live page into smaller route-owned slices behind the shipped browser contract.

## Story breakdown

### Story 56.1: Add a browser smoke for the public demo walkthrough and auth-required route guardrails

**Objective:** Prove the documented browser walkthrough against the real packaged runtime and seeded demo data with one small high-value smoke.

**Files:**
- Modify: `client/package.json`
- Create: `client/playwright.config.ts` (or the smallest equivalent config)
- Create: `client/tests/e2e/public-demo-smoke.spec.ts`
- Create or modify: `client/tests/e2e/helpers/*` only if needed to keep the spec small and honest
- Modify: `Makefile`
- Modify: `tests/e2e/test_launch_readiness_smoke.py` only if a tiny shared runtime helper extraction makes the browser smoke simpler
- Modify: `_bmad-output/implementation-artifacts/56-1-add-a-browser-smoke-for-the-public-demo-walkthrough-and-auth-required-route-guardrails.md`
- Test: `make launch-readiness-smoke`, the new browser smoke command, `make client-test`, `make client-build`, `make quality`

**Bite-sized tasks:**
1. Write the failing browser smoke first so the desired walkthrough is explicit: public matches -> match detail -> history -> live spectator -> auth-required `/lobby` and `/matches/<match_id>/play` -> persisted API base URL.
2. Add the smallest Playwright/bootstrap config needed to run against the real local runtime instead of mocked component fixtures.
3. Reuse the existing seeded DB/runtime-control flow so the smoke brings up the packaged server and client with deterministic demo data.
4. Make the smoke assertions coarse and contract-shaped: stable headings/links/guardrail copy/session-field values, not brittle layout snapshots.
5. Add a simple repo command path (for example `make browser-smoke`) and keep bootstrap honest (`npm ci`, Playwright browser install if required).
6. Re-run the focused smoke commands, then the full repo gate, and record the exact outcomes in the story artifact.

**Guardrails:**
- Do not automate bearer-token acquisition; assert the existing auth-required state without a token.
- Do not add a second runtime/bootstrap path when `runtime-control.sh` plus seeded DB setup can be reused.
- Keep websocket assertions minimal and deterministic; proving the live page renders/connects is enough.
- Prefer a single high-value end-to-end spec over a large flaky suite.

### Story 56.2: Refactor the human live page into smaller route-owned slices behind the shipped browser contract

**Objective:** Reduce the regression blast radius of the authenticated live client by splitting the largest remaining module/test hotspot behind stable browser-visible seams.

**Files:**
- Modify: `client/src/components/matches/human-match-live-snapshot.tsx`
- Modify/create: smaller modules under `client/src/components/matches/human-live/`
- Modify: `client/src/components/matches/human-match-live-page.test.tsx`
- Create: additional focused test files under `client/src/components/matches/` or `client/src/components/matches/human-live/`
- Test: Story 56.1 browser smoke, focused Vitest slices, `make client-test`, `make quality`
- Story: `_bmad-output/implementation-artifacts/56-2-refactor-the-human-live-page-into-smaller-route-owned-slices-behind-the-shipped-browser-contract.md`

**Bite-sized tasks:**
1. Write seam-preserving failing tests or identify existing suites that lock the live-page contract before moving code.
2. Extract one stable slice at a time (read-only panels, draft actions, messaging/diplomacy, guided-agent controls) into smaller modules.
3. Replace the giant regression file with smaller route-owned suites as each slice moves.
4. Keep the Story 56.1 browser smoke green after each meaningful refactor chunk.
5. Re-run focused client verification, then the real repo gate, and record the outcomes in the story artifact.

**Guardrails:**
- No new product scope.
- No generic framework or service abstraction layer.
- Keep behavior-first tests at the browser/API boundary where feasible; avoid internal helper-spy rewrites.

## Expected deliverables

- One checked-in real-browser smoke over the documented local demo path.
- One simple repo command for that smoke and honest bootstrap instructions.
- A future-ready follow-on story for decomposing the human live hotspot behind the new browser protection.

## Out of scope

- Hosted demo environments or cloud deployment automation.
- Human login/token issuance automation.
- Payments, billing, or entitlement expansion.
- Large browser test matrixes or visual snapshot suites.
