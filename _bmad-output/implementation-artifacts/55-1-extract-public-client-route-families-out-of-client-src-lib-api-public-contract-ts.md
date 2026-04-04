# Story 55.1: Extract public client route families out of `client/src/lib/api/public-contract.ts`

Status: in-progress

## Story

As a client maintainer,
I want the public browse/detail/profile/history/replay/live-parse helpers separated into focused modules,
So that `client/src/lib/api/public-contract.ts` stops acting as a second monolith behind the thin `./api` facade.

## Acceptance Criteria

1. The shipped public read helpers and live-envelope parsers move into focused modules under `client/src/lib/api/` while `client/src/lib/api/public-contract.ts` remains a compatibility re-export entrypoint.
2. The resulting module structure is route-family based: public browse/detail, public profiles, public history/replay, and live websocket envelope parsing each stay scoped to one public contract family.
3. Public browser request/response behavior remains unchanged, including API-base resolution, not-found/unavailable mapping, additive read-model parsing, and websocket envelope parsing.
4. The story stays client-only and does not change server contracts, page routes, or caller import sites outside the `client/src/lib` API boundary.
5. Focused client verification passes, along with the repo-managed `make quality` gate.
6. The resulting structure is simpler than the pre-story baseline: `client/src/lib/api/public-contract.ts` becomes a thin facade and the remaining public contract surface no longer lives in one generic module.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [ ] Audit `client/src/lib/api/public-contract.ts` and group exports by stable public route family. (AC: 1, 2, 6)
- [ ] Extract public browse/detail/completed helpers into `client/src/lib/api/public-browse.ts`. (AC: 1, 2, 3)
- [ ] Extract leaderboard and public profile helpers into `client/src/lib/api/public-profiles.ts`. (AC: 1, 2, 3)
- [ ] Extract public history/replay helpers into `client/src/lib/api/public-history.ts`. (AC: 1, 2, 3)
- [ ] Extract websocket live-envelope parsing into `client/src/lib/api/live-envelope.ts`. (AC: 1, 2, 3)
- [ ] Keep `client/src/lib/api/public-contract.ts` as the compatibility facade for current callers. (AC: 1, 4, 6)
- [ ] Tighten the seam regression so both `./api` and `./api/public-contract` still re-export the route-family modules. (AC: 1, 3, 5)
- [ ] Run the required focused verification and full repo quality gate. (AC: 5, 6)

## Dev Notes

- Follow `docs/plans/2026-04-04-epic-55-public-client-contract-decomposition-and-test-sharding.md`.
- Keep the extraction boring: plain exported functions, plain error classes, explicit re-exports.
- Preserve all existing `./api` and `./api/public-contract` exports exactly.
- Avoid changing component imports outside the `client/src/lib` seam.

### References

- `docs/plans/2026-04-04-epic-55-public-client-contract-decomposition-and-test-sharding.md`
- `client/src/lib/api.ts`
- `client/src/lib/api/public-contract.ts`
- `client/src/lib/api.test.ts`
- `_bmad-output/implementation-artifacts/54-1-extract-client-public-read-and-live-parse-helpers-out-of-client-src-lib-api-ts.md`
- `_bmad-output/implementation-artifacts/54-2-extract-authenticated-client-write-and-account-management-helpers-out-of-client-src-lib-api-ts.md`

## Complete Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-04: Drafted Story 55.1 as the next maintainability slice after Epic 54 to break up the still-oversized public client contract seam.

## Debug Log References

- Pending implementation.

## Completion Notes

- Pending implementation.

## File List

- `_bmad-output/implementation-artifacts/55-1-extract-public-client-route-families-out-of-client-src-lib-api-public-contract-ts.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/plans/2026-04-04-epic-55-public-client-contract-decomposition-and-test-sharding.md`
