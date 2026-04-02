# Story: 38.1 Extract public browse and roster assembly helpers out of `server/db/public_reads.py`

Status: drafted

## Story

As a server maintainer,
I want the public match browse/detail metadata and roster assembly logic grouped behind focused helpers,
So that `server/db/public_reads.py` can keep top-level query orchestration visible without one file continuing to own every public browse/detail payload-building detail.

## Acceptance Criteria

1. The inline browse/detail payload-building responsibilities in `server/db/public_reads.py` (at minimum the `MatchSummary` / `PublicMatchDetailResponse` assembly paths and public roster-row construction) move behind a focused compatibility-safe helper surface while preserving stable caller behavior from `server.db.public_reads` and `server.db.registry`.
2. Canonical player-id mapping, compact roster ordering, open-slot calculations, public match visibility filtering, and public browse/detail response payloads remain unchanged at the registry, route, and test boundary.
3. `server/db/public_reads.py` keeps explicit top-level DB query orchestration and does not gain a framework/service abstraction.
4. Focused DB public-read / registry regression coverage passes, along with the strongest practical repo-managed verification for the touched seam.
5. The final structure is simpler than the current starting point: fewer mixed responsibilities in `server/db/public_reads.py`, clearer ownership for payload assembly helpers, and no abstraction added only for test convenience.

## Tasks / Subtasks

- [ ] Audit the browse/detail payload-building seams in `server/db/public_reads.py` and identify the tightest extraction that preserves current behavior. (AC: 1, 5)
- [ ] Extract focused helper(s) or a compatibility-safe helper module for public match browse/detail payload assembly and roster row construction. (AC: 1, 2, 3, 5)
- [ ] Keep `server.db.public_reads` and `server.db.registry` import behavior stable for current callers. (AC: 1, 2)
- [ ] Add or tighten focused regression coverage around public browse/detail payload assembly and canonical player-id mapping behavior. (AC: 2, 4)
- [ ] Run focused verification plus the strongest practical repo-managed checks. (AC: 4, 5)

## Dev Notes

- This is the next pragmatic follow-on after Epic 37 reduced concentration in `server/db/hydration.py`.
- Treat this as refactor-only work; do not broaden into new public routes, API shape changes, DB schema changes, or UI work.
- Prefer plain functions and explicit inputs over classes, registries, or generalized read-service frameworks.
- Preserve the public-match detail roster ordering and canonical player-id mapping behavior exactly.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the next post-Epic-37 refactor slice after completing Story 37.2.

### Completion Notes

- Pending.

### File List

- `_bmad-output/implementation-artifacts/38-1-extract-public-browse-and-roster-assembly-helpers-out-of-server-db-public_reads-py.md`

### Change Log

- 2026-04-02: Drafted Story 38.1 to continue DB surface decomposition by splitting focused browse/detail payload assembly helpers out of `server/db/public_reads.py`.
