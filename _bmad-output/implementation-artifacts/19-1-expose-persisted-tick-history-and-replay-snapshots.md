# Story 19.1: Expose persisted tick history and replay snapshots

Status: in-progress

## Story

As a spectator client or debugging tool,
I want to list recorded match ticks and fetch one persisted snapshot by tick,
So that replay and audit flows can inspect the authoritative history written by the live runtime.

## Acceptance Criteria

1. Given the DB-backed server has persisted `tick_log` rows for a match, when a client requests the match history route, then the API returns deterministic tick entries for that match in ascending order, together with enough match metadata to drive a replay picker.
2. Given a client requests one specific persisted tick, when the replay snapshot route is called with an existing tick number, then the API returns the persisted state snapshot, accepted orders, and emitted events for that tick.
3. Given replay depends on durable runtime history rather than in-memory state, when the feature ships, then behavior-first tests cover unknown match/tick failures plus a real-process DB-backed smoke proving the running app serves the persisted history contract.

## Tasks / Subtasks

- [ ] Add narrow API response models and DB query helpers for persisted tick history and replay snapshots. (AC: 1, 2)
- [ ] Expose public GET routes for match history and per-tick replay reads with structured error handling. (AC: 1, 2)
- [ ] Add focused DB/API tests plus a real-process smoke that proves the running DB-backed app serves persisted history. (AC: 3)
- [ ] Update story/BMAD/source-of-truth docs as needed and run simplification plus the repo quality gate. (AC: 3)

## Dev Notes

- Reuse Story 18.2's `tick_log` persistence as the single source of truth; do not create a second history cache.
- Keep the story read-only and narrowly scoped to replay/history reads.
- Prefer one boring DB query helper plus two GET routes over a new repository/service abstraction.

## Implementation Plan

- Plan file: `docs/plans/2026-03-30-story-19-1-match-history-replay-api.md`
- Parallelism assessment: sequential implementation because the public route contract, DB helper, response models, and tests all share the same API seam; spec and quality reviews can run independently after implementation.
- Verification target: focused DB/API tests, real-process history smoke, then `make quality`.
