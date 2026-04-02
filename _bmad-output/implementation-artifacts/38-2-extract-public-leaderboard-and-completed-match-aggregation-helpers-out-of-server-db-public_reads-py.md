# Story: 38.2 Extract public leaderboard and completed-match aggregation helpers out of `server/db/public_reads.py`

Status: drafted

## Story

As a server maintainer,
I want the leaderboard aggregation and completed-match browse payload assembly logic grouped behind focused helpers,
So that `server/db/public_reads.py` can keep top-level public-read query orchestration visible without one file continuing to own every completed-match and ranking aggregation detail.

## Acceptance Criteria

1. The inline leaderboard/completed-match aggregation responsibilities in `server/db/public_reads.py` (at minimum the competitor identity grouping, completed-match browse payload construction, and winner-name assembly paths) move behind a focused compatibility-safe helper surface while preserving stable caller behavior from `server.db.public_reads` and `server.db.registry`.
2. Public leaderboard ranking order, same-user multi-agent separation, completed-match browse payloads, winner alliance/player naming, and UTC/timestamp ordering behavior remain unchanged at the registry, route, and test boundary.
3. `server/db/public_reads.py` keeps explicit top-level DB query orchestration and does not gain a framework/service abstraction.
4. Focused DB public-read / registry regression coverage passes, along with the strongest practical repo-managed verification for the touched seam.
5. The final structure is simpler than the post-38.1 starting point: fewer mixed responsibilities in `server/db/public_reads.py`, clearer ownership for completed-match/leaderboard aggregation helpers, and no abstraction added only for test convenience.

## Tasks / Subtasks

- [ ] Audit the remaining leaderboard/completed-match aggregation seams in `server/db/public_reads.py` and identify the tightest extraction that preserves current behavior. (AC: 1, 5)
- [ ] Extract focused helper(s) or a compatibility-safe helper module for leaderboard and completed-match payload assembly. (AC: 1, 2, 3, 5)
- [ ] Keep `server.db.public_reads` and `server.db.registry` import behavior stable for current callers. (AC: 1, 2)
- [ ] Add or tighten focused regression coverage around public leaderboard identity grouping and completed-match winner/browse behavior. (AC: 2, 4)
- [ ] Run focused verification plus the strongest practical repo-managed checks. (AC: 4, 5)

## Dev Notes

- This is the next pragmatic Epic 38 slice after Story 38.1 moved active-match browse/detail assembly into `server/db/public_read_assembly.py`.
- Treat this as refactor-only work; do not broaden into new public routes, API shape changes, DB schema changes, or UI work.
- Prefer plain functions and explicit inputs over classes, registries, or generalized read-service frameworks.
- Preserve the current leaderboard tiebreakers, same-user multi-agent separation, and completed-match winner-display behavior exactly.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the next Epic 38 slice after completing Story 38.1.

### Completion Notes

- Pending.

### File List

- `_bmad-output/implementation-artifacts/38-2-extract-public-leaderboard-and-completed-match-aggregation-helpers-out-of-server-db-public_reads-py.md`

### Change Log

- 2026-04-02: Drafted Story 38.2 to continue decomposing `server/db/public_reads.py` by extracting leaderboard and completed-match aggregation helpers.
