# Story 54.2: Extract authenticated client write and account-management helpers out of `client/src/lib/api.ts`

Status: done

## Story

As a client maintainer,
I want the authenticated lobby, match-write, guided-agent, and account/session helpers separated into route-family modules,
So that `client/src/lib/api.ts` becomes a thin compatibility facade instead of a generic authenticated catch-all.

## Acceptance Criteria

1. The authenticated helper surface moves behind focused modules under `client/src/lib/api/` while `client/src/lib/api.ts` continues to expose the same `./api` exports for existing callers.
2. The resulting module structure is clearly route-family based: lobby lifecycle, match write/messaging/diplomacy, guided-agent controls, and account/session helpers remain scoped to their route families.
3. Authenticated request/response behavior remains unchanged at the browser-contract boundary, including bearer-token headers, API-base resolution, deterministic error mapping, websocket URL helpers, and guided-agent write/read semantics.
4. The story stays client-only and does not change server contracts, page routes, or caller import sites outside the `client/src/lib` API boundary.
5. Focused client verification passes, along with the repo-managed `make quality` gate.
6. The resulting structure is simpler than the pre-story baseline: `client/src/lib/api.ts` stays a thin facade and the remaining authenticated surface no longer lives in one generic module.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Audit the authenticated seam in `client/src/lib/api.ts` and group helpers by route family. (AC: 1, 2, 6)
- [x] Extract lobby lifecycle helpers into `client/src/lib/api/lobby-lifecycle.ts`. (AC: 1, 2, 3)
- [x] Extract match write/messaging/diplomacy helpers into `client/src/lib/api/match-writes.ts`. (AC: 1, 2, 3)
- [x] Extract guided-agent helpers into `client/src/lib/api/guided-agents.ts`. (AC: 1, 2, 3)
- [x] Keep account API-key plus websocket/session helpers scoped in `client/src/lib/api/account-session.ts`. (AC: 2, 3)
- [x] Keep `client/src/lib/api.ts` as the compatibility facade for current callers. (AC: 1, 4, 6)
- [x] Tighten the seam regression in `client/src/lib/api.test.ts` to assert the facade aligns with the route-family modules. (AC: 1, 3, 5)
- [x] Run the required focused verification and full repo quality gate. (AC: 5, 6)

## Dev Notes

- Follow the Epic 54 plan in `docs/plans/2026-04-04-epic-54-client-api-boundary-decomposition.md`.
- Keep the extraction boring: plain exported functions, plain error classes, explicit re-exports.
- Preserve all existing `./api` exports and current caller contracts exactly.
- Avoid changing component imports outside the `client/src/lib` seam.

### References

- `docs/plans/2026-04-04-epic-54-client-api-boundary-decomposition.md`
- `client/src/lib/api.ts`
- `client/src/lib/api.test.ts`
- `_bmad-output/implementation-artifacts/54-1-extract-client-public-read-and-live-parse-helpers-out-of-client-src-lib-api-ts.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-04: Drafted Story 54.2 as the second Epic 54 slice to finish decomposing the client API boundary after the public-contract extraction.
- 2026-04-04: Completed Story 54.2 by replacing the generic authenticated write bucket with route-family modules for lobby lifecycle, match writes, and guided-agent controls while preserving the `./api` facade.

## Debug Log References

- `cd client && npm test -- --run src/lib/api.test.ts`
  - Passed in worker and controller repos: `1` file, `91` tests, `0` failures.
- `source .venv/bin/activate && make quality`
  - Worker passed after one transient Vitest unhandled-error flake on the first rerun; immediate rerun was green.
  - Controller repo gate passed: Ruff format check, Ruff lint, mypy strict, `491` Python tests with `95.20%` coverage, client typecheck, full Vitest (`22` files, `206` tests), and Next production build.

## Completion Notes

- Replaced the generic authenticated helper bucket with route-family modules: `lobby-lifecycle.ts`, `match-writes.ts`, and `guided-agents.ts`.
- Kept `account-session.ts` as the scoped account/session + websocket helper module and left `client/src/lib/api.ts` as a thin compatibility re-export facade.
- Added `authenticated-contracts.ts` so the route-family files can stay boring without duplicating contract guards.
- Tightened `client/src/lib/api.test.ts` to assert the facade still re-exports the route-family modules plus the shared account/session helpers.
- Explicitly preserved the previously exported `./api` helper surface for `buildAuthenticatedHeaders`, `buildAuthenticatedJsonHeaders`, `isApiErrorEnvelope`, `isRecord`, and `resolveApiBaseUrl`.
- Kept `client/src/lib/api.ts` thin at `59` lines after the final split.

## File List

- `_bmad-output/implementation-artifacts/54-2-extract-authenticated-client-write-and-account-management-helpers-out-of-client-src-lib-api-ts.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `client/src/lib/api.ts`
- `client/src/lib/api.test.ts`
- `client/src/lib/api/account-session.ts`
- `client/src/lib/api/authenticated-contracts.ts`
- `client/src/lib/api/guided-agents.ts`
- `client/src/lib/api/lobby-lifecycle.ts`
- `client/src/lib/api/match-writes.ts`
