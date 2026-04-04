# Story 55.2: Split `client/src/lib/api.test.ts` into focused module-aligned suites

Status: backlog

## Story

As a client maintainer,
I want the client API regression suite grouped by the same route families as the extracted helpers,
So that future public-contract changes can be reviewed and debugged in smaller, more local test files.

## Acceptance Criteria

1. `client/src/lib/api.test.ts` is replaced by focused Vitest files aligned to route families while preserving the same behavioral coverage.
2. There remains an explicit seam regression proving `client/src/lib/api.ts` and `client/src/lib/api/public-contract.ts` continue to re-export the intended helpers.
3. The split suite preserves behavior-first browser-contract assertions instead of replacing them with internal implementation-detail tests.
4. The story stays client-only and does not change production browser behavior or server contracts.
5. Focused Vitest verification passes, along with the repo-managed `make quality` gate.
6. The resulting test layout is simpler than the pre-story baseline and does not introduce a generic test harness abstraction.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [ ] Isolate seam assertions into a dedicated compatibility regression file. (AC: 2, 6)
- [ ] Split public browse/detail/completed tests into a focused route-family suite. (AC: 1, 3)
- [ ] Split public profile tests into a focused route-family suite. (AC: 1, 3)
- [ ] Split public history/replay and live-envelope tests into focused route-family suites. (AC: 1, 3)
- [ ] Split authenticated helper tests into account/session, lobby lifecycle, match writes, and guided-agent suites. (AC: 1, 3)
- [ ] Remove or reduce the giant original `client/src/lib/api.test.ts` after the new suite is green. (AC: 1, 6)
- [ ] Run the required focused verification and full repo quality gate. (AC: 5, 6)

## Dev Notes

- Follow `docs/plans/2026-04-04-epic-55-public-client-contract-decomposition-and-test-sharding.md`.
- Keep tests behavior-first and public-boundary oriented; do not pivot to internal helper spies.
- Preserve explicit seam checks for both `./api` and `./api/public-contract`.
- Prefer one module family per test file; avoid a new giant shared helper layer.

### References

- `docs/plans/2026-04-04-epic-55-public-client-contract-decomposition-and-test-sharding.md`
- `client/src/lib/api.test.ts`
- `client/src/lib/api/`
- `_bmad-output/implementation-artifacts/55-1-extract-public-client-route-families-out-of-client-src-lib-api-public-contract-ts.md`

## Complete Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-04: Drafted Story 55.2 as the follow-on test-sharding slice after the public contract module decomposition.

## Debug Log References

- Pending implementation.

## Completion Notes

- Pending implementation.

## File List

- `_bmad-output/implementation-artifacts/55-2-split-client-src-lib-api-test-ts-into-focused-module-aligned-suites.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/plans/2026-04-04-epic-55-public-client-contract-decomposition-and-test-sharding.md`
