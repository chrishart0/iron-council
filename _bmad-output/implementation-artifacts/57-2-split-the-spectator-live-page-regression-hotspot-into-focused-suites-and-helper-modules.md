# Story 57.2: Split the spectator live page regression hotspot into focused suites and helper modules

Status: drafted

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

- [ ] Identify stable spectator seams (connection lifecycle, summary/live state, pressure/victory context, map-facing behavior).
- [ ] Extract only the minimum support builders needed to keep each focused suite readable.
- [ ] Replace the monolithic spectator regression file with smaller behavior-first suites.
- [ ] Re-run the browser smoke, focused spectator verification, `make client-test`, and `make quality`.

## Dev Notes

- Keep this story client-only and do not widen it into new spectator functionality.
- Prefer stable rendered-output assertions over brittle page-wide list scans.
- This story should start only after Story 57.1 is completed and the authenticated sharding pattern is settled.

### References

- `client/src/components/matches/public-match-live-page.test.tsx`
- `docs/plans/2026-04-05-epic-57-live-browser-regression-sharding.md`
- `_bmad-output/implementation-artifacts/57-1-split-the-authenticated-human-live-messaging-and-diplomacy-regression-hotspot-into-route-owned-suites.md`

## Complete Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-05: Drafted Story 57.2 as the follow-on Epic 57 spectator regression-sharding slice.

## Debug Log References

- Pending implementation.

## Completion Notes

- Pending implementation.

## File List

- `_bmad-output/implementation-artifacts/57-2-split-the-spectator-live-page-regression-hotspot-into-focused-suites-and-helper-modules.md`
- `docs/plans/2026-04-05-epic-57-live-browser-regression-sharding.md`
