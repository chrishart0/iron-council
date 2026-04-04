# Story 55.1: Extract public client route families out of `client/src/lib/api/public-contract.ts`

Status: done

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

- [x] Audit `client/src/lib/api/public-contract.ts` and group exports by stable public route family. (AC: 1, 2, 6)
- [x] Extract public browse/detail/completed helpers into `client/src/lib/api/public-browse.ts`. (AC: 1, 2, 3)
- [x] Extract leaderboard and public profile helpers into `client/src/lib/api/public-profiles.ts`. (AC: 1, 2, 3)
- [x] Extract public history/replay helpers into `client/src/lib/api/public-history.ts`. (AC: 1, 2, 3)
- [x] Extract websocket live-envelope parsing into `client/src/lib/api/live-envelope.ts`. (AC: 1, 2, 3)
- [x] Keep `client/src/lib/api/public-contract.ts` as the compatibility facade for current callers. (AC: 1, 4, 6)
- [x] Tighten the seam regression so both `./api` and `./api/public-contract` still re-export the route-family modules. (AC: 1, 3, 5)
- [x] Run the required focused verification and full repo quality gate. (AC: 5, 6)

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

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-04: Drafted Story 55.1 as the next maintainability slice after Epic 54 to break up the still-oversized public client contract seam.
- 2026-04-04: Completed Story 55.1 by splitting the public client contract into route-family modules and hardening deterministic public error normalization for the extracted fetch helpers.

## Debug Log References

- `cd client && npm test -- src/lib/api.test.ts`
  - Passed in worker and controller repos: `1` file, `107` tests, `0` failures.
- `source .venv/bin/activate && make quality`
  - Worker/controller gate passed after the review-driven follow-up: Ruff format check, Ruff lint, mypy strict, `491` Python tests with `95.20%` coverage, client typecheck, full Vitest (`22` files, `222` tests), and Next production build.
- Review loop
  - Spec review passed.
  - Initial quality review requested deterministic normalization for transport / malformed-JSON failures in the new public fetch modules.
  - Follow-up fix landed and re-review approved the final story state.

## Completion Notes

- Split the public client contract into focused route-family modules: `public-browse.ts`, `public-profiles.ts`, `public-history.ts`, and `live-envelope.ts`.
- Kept `client/src/lib/api/public-contract.ts` as a thin compatibility facade and factored shared API-base/error helpers into `public-contract-shared.ts`.
- Preserved additive read-model parsing for completed-match competitors and match-history competitors while leaving caller import sites outside `client/src/lib` unchanged.
- Tightened the seam regression so both `./api` and `./api/public-contract` continue re-exporting the extracted route-family helpers.
- Added review-driven failure-normalization coverage proving all public fetch helpers return deterministic exported errors on transport failures and malformed success JSON.

## File List

- `_bmad-output/implementation-artifacts/55-1-extract-public-client-route-families-out-of-client-src-lib-api-public-contract-ts.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/plans/2026-04-04-epic-55-public-client-contract-decomposition-and-test-sharding.md`
- `client/src/lib/api.test.ts`
- `client/src/lib/api/live-envelope.ts`
- `client/src/lib/api/public-browse.ts`
- `client/src/lib/api/public-contract-shared.ts`
- `client/src/lib/api/public-contract.ts`
- `client/src/lib/api/public-history.ts`
- `client/src/lib/api/public-profiles.ts`
