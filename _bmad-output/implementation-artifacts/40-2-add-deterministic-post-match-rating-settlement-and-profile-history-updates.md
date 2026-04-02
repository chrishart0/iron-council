# Story: 40.2 Add deterministic post-match rating settlement and profile history updates

Status: drafted

## Story

As a platform maintainer,
I want completed matches to settle durable rating and history outcomes exactly once,
So that public leaderboard and agent-profile reads reflect real post-match results instead of perpetual provisional snapshots.

## Acceptance Criteria

1. Completed matches with a persisted `winner_alliance` settle deterministic win/loss/draw history updates and durable rating adjustments for every participating human/agent identity.
2. Settlement is idempotent: retries or duplicate triggers for the same completed match do not double-apply rating/history changes.
3. Leaderboard and agent-profile data sources can consume the finalized settlement results without changing unrelated auth, lobby, or replay contracts.
4. Focused DB/API/e2e regressions pass, plus the strongest practical repo-managed verification for the touched seam.

## Tasks / Subtasks

- [ ] Define the smallest durable settlement record/guard that prevents double-application. (AC: 1, 2)
- [ ] Add failing tests for deterministic rating settlement and idempotent retry behavior. (AC: 1, 2)
- [ ] Implement settlement writes and profile-history updates against the persisted completion path. (AC: 1, 2, 3)
- [ ] Tighten leaderboard/profile regressions to assert finalized outcomes instead of perpetual provisional snapshots. (AC: 3, 4)
- [ ] Run focused verification plus the strongest practical repo-managed checks. (AC: 4)

## Dev Notes

- This story depends on 40.1 providing authoritative completed-match state and a persisted `winner_alliance`.
- Keep settlement logic explicit and idempotent; do not bury it behind a generic ranking framework.
- Re-check `core-plan.md` section 8.2 for intended weighting rules before implementing the actual formula.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the direct follow-on to Story 40.1.

### Completion Notes

- Pending.

### File List

- `_bmad-output/implementation-artifacts/40-2-add-deterministic-post-match-rating-settlement-and-profile-history-updates.md`

### Change Log

- 2026-04-02: Drafted Story 40.2 to convert completed matches into durable rating and profile history outcomes.
