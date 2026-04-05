# Story 57.2: Split the spectator live page regression hotspot into focused suites and helper modules

Status: done

## Story

As a client maintainer,
I want the oversized spectator live regression file split into smaller focused suites,
So that public live-page changes can be reviewed and debugged without wading through one giant mixed-responsibility spec.

## Acceptance Criteria

1. `client/src/components/matches/public-match-live-page.test.tsx` is replaced by smaller focused suites/modules aligned to stable spectator live seams without changing shipped behavior.
2. The Story 56 browser smoke, focused spectator live suites, `make client-test`, and `make quality` all stay green.
3. The story stays client-only, avoids snapshot-heavy or generic abstractions, and leaves the spectator live regression surface in the simplest coherent state possible.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Identify stable spectator seams (connection lifecycle, summary/live state, pressure/victory context, map-facing behavior).
- [x] Extract only the minimum support builders needed to keep each focused suite readable.
- [x] Replace the monolithic spectator regression file with smaller behavior-first suites.
- [x] Re-run the browser smoke, focused spectator verification, `make client-test`, and `make quality`.

## Dev Notes

- Keep this story client-only and do not widen it into new spectator functionality.
- Prefer stable rendered-output assertions over brittle page-wide list scans.
- This story should start only after Story 57.1 is completed and the authenticated sharding pattern is settled.

### References

- `client/src/components/matches/public-match-live-page.test.tsx`
- `docs/plans/2026-04-05-epic-57-live-browser-regression-sharding.md`
- `_bmad-output/implementation-artifacts/57-1-split-the-authenticated-human-live-messaging-and-diplomacy-regression-hotspot-into-route-owned-suites.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-05: Drafted Story 57.2 as the follow-on Epic 57 spectator regression-sharding slice.
- 2026-04-05: Replaced the monolithic spectator live regression with focused connection, summary, pressure, and transit suites plus narrow local fixture/helper modules.

## Debug Log References

- `cd client && npm test -- --run src/components/matches/public-match-live-page*.test.tsx`
- `make browser-smoke`
- `make client-test`
- `make quality`

## Completion Notes

- Split the old `public-match-live-page.test.tsx` hotspot into route-owned connection, summary, pressure, and transit suites without changing the shipped spectator browser contract.
- Extracted a narrow spectator fixture module and websocket/render helper module so the new suites share only the minimum common setup.
- Verified the spectator shard through focused Vitest coverage, the Story 56 browser smoke, `make client-test`, and the full `make quality` gate.

## File List

- `_bmad-output/implementation-artifacts/57-2-split-the-spectator-live-page-regression-hotspot-into-focused-suites-and-helper-modules.md`
- `client/src/components/matches/public-match-live-page-fixtures.ts`
- `client/src/components/matches/public-match-live-page-test-helpers.tsx`
- `client/src/components/matches/public-match-live-page.connection.test.tsx`
- `client/src/components/matches/public-match-live-page.summary.test.tsx`
- `client/src/components/matches/public-match-live-page.pressure.test.tsx`
- `client/src/components/matches/public-match-live-page.transit.test.tsx`
