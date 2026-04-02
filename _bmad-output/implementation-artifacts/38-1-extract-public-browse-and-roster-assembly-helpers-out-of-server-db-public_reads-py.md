# Story: 38.1 Extract public browse and roster assembly helpers out of `server/db/public_reads.py`

Status: done

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
- 2026-04-02: Implemented the public browse/detail extraction in `/tmp/iron-38-1`, then re-ran focused DB registry/API checks plus `make quality` before integrating onto `master`.

### Completion Notes

- Extracted public match browse/detail payload assembly and roster-row construction into the new focused helper module `server/db/public_read_assembly.py` while keeping `server/db/public_reads.py` as the explicit SQLAlchemy query orchestrator.
- Preserved canonical player-id mapping, visible roster ordering, open-slot calculations, and registry/API compatibility by keeping `build_persisted_player_mapping(...)` in the orchestration layer and routing the final response construction through plain helper functions.
- Added a focused regression that proves browse/detail counts continue to reflect persisted player rows even when unmapped persisted rows are filtered out of the public roster surface, then re-verified the touched seam in both DB-registry and API-route tests.

### File List

- `server/db/public_read_assembly.py`
- `server/db/public_reads.py`
- `tests/test_db_registry.py`
- `_bmad-output/implementation-artifacts/38-1-extract-public-browse-and-roster-assembly-helpers-out-of-server-db-public_reads-py.md`

### Change Log

- 2026-04-02: Drafted Story 38.1 to continue DB surface decomposition by splitting focused browse/detail payload assembly helpers out of `server/db/public_reads.py`.
- 2026-04-02: Completed Story 38.1 by moving public browse/detail assembly into `server/db/public_read_assembly.py`, adding a focused roster/count regression, and re-running focused plus repo-managed verification.
