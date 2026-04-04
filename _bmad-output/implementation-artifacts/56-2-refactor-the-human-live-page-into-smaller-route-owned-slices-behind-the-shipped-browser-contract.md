# Story 56.2: Refactor the human live page into smaller route-owned slices behind the shipped browser contract

Status: done

## Story

As a client maintainer,
I want the oversized authenticated human live page and its monolithic regression surface split into smaller route-owned modules,
So that future gameplay/UI changes can land with lower regression risk and simpler review boundaries.

## Acceptance Criteria

1. `client/src/components/matches/human-match-live-snapshot.tsx` and the matching giant regression surface are decomposed into smaller modules/tests aligned to stable UI seams without changing shipped behavior.
2. The browser smoke from Story 56.1 stays green alongside the focused client suites and `make quality`.
3. The story avoids generic framework abstractions and leaves the authenticated live client in a simpler coherent state than the pre-story baseline.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Identify the highest-value stable seams in the human live page and its tests before moving code.
- [x] Split presentational and interaction slices into smaller route-owned modules while preserving the public/browser contract.
- [x] Replace the giant regression file with smaller behavior-first suites aligned to the extracted seams.
- [x] Re-run the browser smoke, focused client verification, and the repo quality gate.

## Dev Notes

- Story 56.1 should land first to provide a browser-level regression over the shipped runtime path.
- Keep the refactor client-only unless a narrow compatibility seam change is strictly required.
- Preserve session/websocket/order/diplomacy behavior and prefer public-boundary assertions over helper spies.

### References

- `client/src/components/matches/human-match-live-snapshot.tsx`
- `client/src/components/matches/human-match-live-page.test.tsx`
- `_bmad-output/implementation-artifacts/56-1-add-a-browser-smoke-for-the-public-demo-walkthrough-and-auth-required-route-guardrails.md`
- `docs/plans/2026-04-04-epic-56-browser-launch-confidence-and-human-live-maintainability.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-04: Drafted Story 56.2 as the follow-on maintainability slice after the browser launch-confidence smoke.
- 2026-04-04: Split the authenticated human live snapshot into route-owned hooks/support modules and replaced the monolithic live-page suite with focused seam-aligned specs while keeping the shipped browser contract green.

## Debug Log References

- `npm ci` in `client/` to bootstrap the fresh worktree before running Vitest.
- `npm test -- --run src/components/matches/human-match-live-page.connection.test.tsx src/components/matches/human-match-live-page.messaging-diplomacy.test.tsx src/components/matches/human-match-live-page.orders-selection.test.tsx src/components/matches/human-match-live-page.guided.test.tsx`
- `make browser-smoke`
- `make client-test`
- `uv sync --extra dev --frozen` to install the repo's Python dev dependencies after the first `make quality` run exposed missing fresh-worktree packages for mypy.
- `make quality`

## Completion Notes

- The oversized `human-match-live-snapshot.tsx` controller now composes route-owned hooks for orders, messaging, diplomacy, guided controls, and map selection plus a shared support module for pure live-page derivations.
- The old `human-match-live-page.test.tsx` monolith was replaced with focused connection, messaging/diplomacy, orders/selection, and guided suites backed by a shared page harness while keeping assertions at the rendered page boundary.
- Verification stayed green across the Story 56.1 browser smoke, focused live-page Vitest coverage, `make client-test`, and the full `make quality` gate after bootstrapping the missing fresh-worktree Node and Python dependencies.

## File List

- `_bmad-output/implementation-artifacts/56-2-refactor-the-human-live-page-into-smaller-route-owned-slices-behind-the-shipped-browser-contract.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `client/src/components/matches/human-live/human-match-live-snapshot.tsx`
- `client/src/components/matches/human-live/human-match-live-snapshot-support.ts`
- `client/src/components/matches/human-live/use-human-live-diplomacy.ts`
- `client/src/components/matches/human-live/use-human-live-guided-controls.ts`
- `client/src/components/matches/human-live/use-human-live-map-selection.ts`
- `client/src/components/matches/human-live/use-human-live-messaging.ts`
- `client/src/components/matches/human-live/use-human-live-orders.ts`
- `client/src/components/matches/human-match-live-page-test-helpers.tsx`
- `client/src/components/matches/human-match-live-page.connection.test.tsx`
- `client/src/components/matches/human-match-live-page.guided.test.tsx`
- `client/src/components/matches/human-match-live-page.messaging-diplomacy.test.tsx`
- `client/src/components/matches/human-match-live-page.orders-selection.test.tsx`
- `client/src/components/matches/human-match-live-page.test.tsx`
