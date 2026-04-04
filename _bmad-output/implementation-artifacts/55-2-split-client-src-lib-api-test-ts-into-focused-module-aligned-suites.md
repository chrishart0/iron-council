# Story 55.2: Split `client/src/lib/api.test.ts` into focused module-aligned suites

Status: done

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

- [x] Isolate seam assertions into a dedicated compatibility regression file. (AC: 2, 6)
- [x] Split public browse/detail/completed tests into a focused route-family suite. (AC: 1, 3)
- [x] Split public profile tests into a focused route-family suite. (AC: 1, 3)
- [x] Split public history/replay and live-envelope tests into focused route-family suites. (AC: 1, 3)
- [x] Split authenticated helper tests into account/session, lobby lifecycle, match writes, and guided-agent suites. (AC: 1, 3)
- [x] Remove or reduce the giant original `client/src/lib/api.test.ts` after the new suite is green. (AC: 1, 6)
- [x] Run the required focused verification and full repo quality gate. (AC: 5, 6)

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

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-04: Drafted Story 55.2 as the follow-on test-sharding slice after the public contract module decomposition.
- 2026-04-04: Completed Story 55.2 by replacing the monolithic `client/src/lib/api.test.ts` with focused module-aligned Vitest suites while preserving the shipped client contract seam.

## Debug Log References

- `cd client && npm test -- --run src/lib/api/account-session.test.ts`
  - Passed after moving websocket URL + close-message coverage into the account/session suite: `12 tests`.
- `cd client && npm test -- --run src/lib/api/live-envelope.test.ts`
  - Passed with the live-envelope suite narrowed to parser/error coverage: `5 tests`.
- `cd client && npx vitest run src/lib/api/*.test.ts`
  - Passed in worker and controller repos: `9` files, `107` tests.
- `source .venv/bin/activate && make quality`
  - Worker bootstrap required `make client-install` plus `uv sync --all-extras --dev` in the fresh worktree before the full gate could run.
  - Full repo gate passed after bootstrap: Ruff format check, Ruff lint, mypy strict, `491` Python tests with `95.20%` coverage, client typecheck, full Vitest (`30` files, `222` tests), and Next production build.
- `git show --stat --oneline dc0af3f`
  - Verified the merged controller commit only contains the intended client API test-sharding files.

## Completion Notes

- Replaced `client/src/lib/api.test.ts` with dedicated route-family suites for public browse, profiles, history, live envelopes, account/session helpers, lobby lifecycle, match writes, guided-agent helpers, and a standalone seam regression.
- Preserved explicit compatibility checks proving both `client/src/lib/api.ts` and `client/src/lib/api/public-contract.ts` continue to re-export the intended helpers.
- Kept the sharded suites behavior-first by preserving request URL/header/body assertions, deterministic error normalization, and websocket/public payload parsing checks instead of introducing helper spies or a generic harness.
- Moved websocket URL-builder and player close-message checks into `account-session.test.ts` during the refinement pass so each suite aligns more cleanly to its production module boundary.

## File List

- `_bmad-output/implementation-artifacts/55-2-split-client-src-lib-api-test-ts-into-focused-module-aligned-suites.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/plans/2026-04-04-epic-55-public-client-contract-decomposition-and-test-sharding.md`
- `client/src/lib/api.test.ts`
- `client/src/lib/api/account-session.test.ts`
- `client/src/lib/api/guided-agents.test.ts`
- `client/src/lib/api/live-envelope.test.ts`
- `client/src/lib/api/lobby-lifecycle.test.ts`
- `client/src/lib/api/match-writes.test.ts`
- `client/src/lib/api/public-browse.test.ts`
- `client/src/lib/api/public-history.test.ts`
- `client/src/lib/api/public-profiles.test.ts`
- `client/src/lib/api/seam.test.ts`
