# Story 56.2: Refactor the human live page into smaller route-owned slices behind the shipped browser contract

Status: ready-for-dev

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

- [ ] Identify the highest-value stable seams in the human live page and its tests before moving code.
- [ ] Split presentational and interaction slices into smaller route-owned modules while preserving the public/browser contract.
- [ ] Replace the giant regression file with smaller behavior-first suites aligned to the extracted seams.
- [ ] Re-run the browser smoke, focused client verification, and the repo quality gate.

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

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-04: Drafted Story 56.2 as the follow-on maintainability slice after the browser launch-confidence smoke.

## Debug Log References

- Pending implementation.

## Completion Notes

- Pending implementation.

## File List

- `_bmad-output/implementation-artifacts/56-2-refactor-the-human-live-page-into-smaller-route-owned-slices-behind-the-shipped-browser-contract.md`
