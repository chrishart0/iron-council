# Story 54.1: Extract client public read and live parse helpers out of `client/src/lib/api.ts`

Status: drafted

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

- [ ] Audit the public read + live parse seam in `client/src/lib/api.ts` and identify the smallest compatibility-safe extraction. (AC: 1, 5)
- [ ] Extract the public fetch/error/parser family into `client/src/lib/api/public-contract.ts`. (AC: 1, 2, 5)
- [ ] Keep `client/src/lib/api.ts` as the current compatibility import surface for existing callers. (AC: 1, 3)
- [ ] Add or tighten focused seam regressions proving both the extracted module and the facade exports stay available. (AC: 1, 2, 4)
- [ ] Run focused verification plus the strongest practical repo-managed client/repo checks. (AC: 4, 5)

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

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-04: Drafted Story 54.1 as the next maintainability slice to decompose the oversized client API boundary without changing shipped behavior.

## Debug Log References

- Pending implementation.

## Completion Notes

- Pending implementation.

## File List

- `_bmad-output/implementation-artifacts/54-1-extract-client-public-read-and-live-parse-helpers-out-of-client-src-lib-api-ts.md`
- `docs/plans/2026-04-04-epic-54-client-api-boundary-decomposition.md`
