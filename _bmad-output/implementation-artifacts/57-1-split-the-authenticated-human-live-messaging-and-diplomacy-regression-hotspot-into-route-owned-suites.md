# Story 57.1: Split the authenticated human live messaging and diplomacy regression hotspot into route-owned suites

Status: in-progress

## Story

As a client maintainer,
I want the oversized authenticated human live messaging/diplomacy regression file and helper bulk split into smaller route-owned suites,
So that future messaging, treaty, alliance, and group-chat changes can land with lower regression risk and clearer ownership.

## Acceptance Criteria

1. `client/src/components/matches/human-match-live-page.messaging-diplomacy.test.tsx` and the matching bulky support surface are replaced by smaller focused suites/modules aligned to stable authenticated live interaction seams without changing shipped behavior.
2. The Story 56 browser smoke, focused authenticated live suites, `make client-test`, and `make quality` all stay green.
3. The story avoids generic test-framework abstractions and leaves the authenticated live test surface in a simpler coherent state than the pre-story baseline.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [ ] Identify the stable authenticated seams in the current messaging/diplomacy monolith before moving code.
- [ ] Split shared harness/setup from bulky fixtures only where it materially reduces file size and review surface.
- [ ] Replace the monolithic regression file with smaller behavior-first suites aligned to the shipped UI seams.
- [ ] Re-run the browser smoke, focused authenticated live verification, `make client-test`, and `make quality`.

## Dev Notes

- Keep this story client-only and do not widen it into new messaging or diplomacy features.
- Prefer rendered/browser-boundary assertions over internal helper spies.
- Story 56.1 must remain green throughout the refactor.

### References

- `client/src/components/matches/human-match-live-page.messaging-diplomacy.test.tsx`
- `client/src/components/matches/human-match-live-page-test-helpers.tsx`
- `docs/plans/2026-04-05-epic-57-live-browser-regression-sharding.md`
- `_bmad-output/implementation-artifacts/56-2-refactor-the-human-live-page-into-smaller-route-owned-slices-behind-the-shipped-browser-contract.md`

## Complete Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-05: Drafted Story 57.1 as the first Epic 57 maintainability slice after Epic 56 completed.

## Debug Log References

- Pending implementation.

## Completion Notes

- Pending implementation.

## File List

- `_bmad-output/implementation-artifacts/57-1-split-the-authenticated-human-live-messaging-and-diplomacy-regression-hotspot-into-route-owned-suites.md`
- `docs/plans/2026-04-05-epic-57-live-browser-regression-sharding.md`
