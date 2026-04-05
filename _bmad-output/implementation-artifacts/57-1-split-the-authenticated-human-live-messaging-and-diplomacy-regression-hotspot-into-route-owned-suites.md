# Story 57.1: Split the authenticated human live messaging and diplomacy regression hotspot into route-owned suites

Status: done

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

- [x] Identify the stable authenticated seams in the current messaging/diplomacy monolith before moving code.
- [x] Split shared harness/setup from bulky fixtures only where it materially reduces file size and review surface.
- [x] Replace the monolithic regression file with smaller behavior-first suites aligned to the shipped UI seams.
- [x] Re-run the browser smoke, focused authenticated live verification, `make client-test`, and `make quality`.

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

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-05: Drafted Story 57.1 as the first Epic 57 maintainability slice after Epic 56 completed.
- 2026-04-05: Split the authenticated messaging/diplomacy monolith into route-owned message, group-chat, and diplomacy suites, and extracted shared live-page fixtures into a dedicated module while keeping the browser/runtime contract green.

## Debug Log References

- `cd client && npm test -- --run src/components/matches/human-match-live-page.messages.test.tsx src/components/matches/human-match-live-page.group-chats.test.tsx src/components/matches/human-match-live-page.diplomacy.test.tsx`
- `cd client && npm test -- --run src/components/matches/human-match-live-page.connection.test.tsx src/components/matches/human-match-live-page.orders-selection.test.tsx src/components/matches/human-match-live-page.guided.test.tsx src/components/matches/human-match-live-page.messages.test.tsx src/components/matches/human-match-live-page.group-chats.test.tsx src/components/matches/human-match-live-page.diplomacy.test.tsx`
- `make browser-smoke`
- `make client-test`
- `make install`
- `make quality`

## Completion Notes

- Replaced the giant authenticated messaging/diplomacy regression file with three focused suites aligned to message, group-chat, and diplomacy/alliance seams.
- Extracted envelope/response fixture builders into `human-match-live-page-fixtures.ts` so the remaining helper file now owns only the shared websocket/render/session/fetch harness responsibilities.
- Verified the refactor through focused live-page Vitest slices, the browser smoke, `make client-test`, and the full `make quality` gate after bootstrapping the fresh worktree with `make install`.

## File List

- `_bmad-output/implementation-artifacts/57-1-split-the-authenticated-human-live-messaging-and-diplomacy-regression-hotspot-into-route-owned-suites.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `client/src/components/matches/human-match-live-page-fixtures.ts`
- `client/src/components/matches/human-match-live-page-test-helpers.tsx`
- `client/src/components/matches/human-match-live-page.messages.test.tsx`
- `client/src/components/matches/human-match-live-page.group-chats.test.tsx`
- `client/src/components/matches/human-match-live-page.diplomacy.test.tsx`
- `client/src/components/matches/human-match-live-page.connection.test.tsx`
- `client/src/components/matches/human-match-live-page.orders-selection.test.tsx`
- `client/src/components/matches/human-match-live-page.guided.test.tsx`
- `docs/plans/2026-04-05-epic-57-live-browser-regression-sharding.md`
