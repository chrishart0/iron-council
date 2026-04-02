# Story: 40.3 Consume finalized ratings and non-provisional outcomes in leaderboard/profile reads

Status: done

## Story

As a player or spectator,
I want public leaderboard and profile endpoints to expose settled post-match results,
So that the browse surface matches the real competitive state of the platform instead of only match-start snapshots.

## Acceptance Criteria

1. DB-backed leaderboard reads expose finalized non-provisional settled ratings/history rather than provisional match-start snapshots when settlement rows exist.
2. Public and authenticated participant profile reads expose the same finalized settled rating/history outcomes.
3. Existing lobby/auth/history contracts remain unchanged while the finalized read path is adopted.
4. Focused DB/API/e2e verification passes.

## Tasks / Subtasks

- [x] Aggregate finalized settlement rows into DB-backed leaderboard reads. (AC: 1, 3)
- [x] Hydrate public/authenticated profile reads from finalized settlement aggregates when present. (AC: 2, 3)
- [x] Preserve provisional fallback behavior for in-memory/seeded paths without settlements. (AC: 1, 2, 3)
- [x] Verify the finalized read path through focused DB/API/e2e checks. (AC: 4)

## Dev Notes

- This story was functionally implemented as part of Story 40.2 because deterministic settlement persistence and finalized read-model consumption landed together in the same change set.
- The artifact is recorded separately here to keep Epic 40 bookkeeping aligned with the actual shipped scope in `epics.md` and `sprint-status.yaml`.

## Dev Agent Record

### Debug Log

- 2026-04-02: Recorded after-the-fact to reconcile Epic 40 artifact tracking with the already-shipped 40.2 implementation.
- See Story 40.2 debug log for the exact verification command history.

### Completion Notes

- Story 40.2 updated DB-backed leaderboard aggregation to prefer finalized settlement rows and updated public/authenticated agent profile reads to surface the same finalized non-provisional rating/history data.
- No additional production changes were required in this follow-up artifact pass; this file documents the already-implemented scope so Epic 40 can close honestly.

### File List

- `_bmad-output/implementation-artifacts/40-3-consume-finalized-ratings-and-non-provisional-outcomes-in-leaderboard-profile-reads.md`
- `_bmad-output/implementation-artifacts/40-2-add-deterministic-post-match-rating-settlement-and-profile-history-updates.md`

### Change Log

- 2026-04-02: Added the missing Story 40.3 artifact and marked it complete via the already-shipped Story 40.2 implementation.
