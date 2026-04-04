# Story 54.1: Extract client public read and live parse helpers out of `client/src/lib/api.ts`

Status: done

## Story

As a client maintainer,
I want the public read and websocket-envelope parsing helpers separated from the authenticated write surface,
So that `client/src/lib/api.ts` stops concentrating unrelated browser-contract responsibilities in one oversized file.

## Acceptance Criteria

1. The public match/profile/history/replay fetch helpers and websocket-envelope parsing helpers move behind a focused module under `client/src/lib/api/` while `client/src/lib/api.ts` continues to expose the same public exports for existing callers.
2. Public read and live-parse behavior remains unchanged at the Vitest/browser-contract boundary, including API-base resolution, deterministic public error mapping, not-found handling, replay/history parsing, and websocket error parsing.
3. The story stays client-only and does not change any server contracts, page routes, or caller import sites outside the `client/src/lib` API boundary.
4. Focused client verification passes, along with the strongest practical repo-managed gate for the touched seam.
5. The resulting structure is simpler than the pre-story baseline: `client/src/lib/api.ts` materially shrinks, the new module owns one coherent contract family, and no abstraction is introduced only for test convenience.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Audit the public read + live parse seam in `client/src/lib/api.ts` and identify the smallest compatibility-safe extraction. (AC: 1, 5)
- [x] Extract the public fetch/error/parser family into `client/src/lib/api/public-contract.ts`. (AC: 1, 2, 5)
- [x] Keep `client/src/lib/api.ts` as the current compatibility import surface for existing callers. (AC: 1, 3)
- [x] Add or tighten focused seam regressions proving both the extracted module and the facade exports stay available. (AC: 1, 2, 4)
- [x] Run focused verification plus the strongest practical repo-managed client/repo checks. (AC: 4, 5)

## Dev Notes

- This is the first pragmatic Epic 54 slice after the launch-polish epic closed with no next story selected.
- Keep the extraction boring: plain exported functions, plain error classes, explicit helper imports.
- Preserve public contract semantics exactly; this is refactor-only work.
- Do not move authenticated lobby, account, guidance, or write helpers yet.

### References

- `docs/consulting/public-repo-assessment-2026-04-01.md`
- `docs/plans/2026-04-04-epic-54-client-api-boundary-decomposition.md`
- `client/src/lib/api.ts`
- `client/src/lib/api.test.ts`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-04: Drafted Story 54.1 as the next maintainability slice to decompose the oversized client API boundary without changing shipped behavior.
- 2026-04-04: Completed Story 54.1 by extracting the public read/live-parse browser contract into `client/src/lib/api/public-contract.ts` while keeping `client/src/lib/api.ts` as the compatibility facade.

## Debug Log References

- `cd client && npm test -- --run src/lib/api.test.ts`
  - Passed in both worker and controller repos: `87 tests`.
- `source .venv/bin/activate && make quality`
  - Worker initially exposed a fresh-worktree bootstrap issue (`.venv` missing dev dependencies); after `make install`, the full repo gate passed.
  - Controller repo gate passed: Ruff, mypy, full pytest (`491 passed`), client lint/typecheck, full Vitest (`202 passed`), and Next production build.
- `git show --stat --oneline 2221dbd`
  - Verified the merged controller commit only contains the intended client API extraction files.

## Completion Notes

- Extracted the public match/profile/history/replay fetch helpers plus websocket-envelope parsers into `client/src/lib/api/public-contract.ts`.
- Kept `client/src/lib/api.ts` as the stable caller entrypoint by re-exporting the extracted public surface and retaining the authenticated/write helpers in place.
- Added a focused seam regression in `client/src/lib/api.test.ts` proving the compatibility facade still exposes the same public helpers and error classes.
- Ran a simplification follow-up after the first worker pass to remove duplicated dead public-helper code from `client/src/lib/api.ts`, leaving only the shared `isMatchSummary` helper needed by the remaining authenticated surface.
- Reduced `client/src/lib/api.ts` from 2073 lines at planning time to 1517 lines after the extraction while moving the public contract family into a dedicated 1034-line module.

## File List

- `_bmad-output/implementation-artifacts/54-1-extract-client-public-read-and-live-parse-helpers-out-of-client-src-lib-api-ts.md`
- `docs/plans/2026-04-04-epic-54-client-api-boundary-decomposition.md`
- `client/src/lib/api.ts`
- `client/src/lib/api/public-contract.ts`
- `client/src/lib/api.test.ts`
