# Story: 40.4 Add completion-to-leaderboard end-to-end regression coverage

Status: done

## Story

As a maintainer,
I want a real workflow regression that drives a match to completion and verifies the downstream public reads,
So that future runtime or settlement changes cannot silently break completed-match finalization.

## Acceptance Criteria

1. A real-process DB-backed regression drives a live match from active state to completed state through the shipped runtime path rather than inserting a pre-baked completed fixture.
2. The regression proves the completed match disappears from active browse reads and appears in completed-match/history reads with the finalized terminal metadata.
3. The regression proves downstream leaderboard and participant profile reads expose settled non-provisional results for that completed match.
4. Focused smoke/API verification passes, plus the strongest practical repo-managed checks for the touched seam.

## Tasks / Subtasks

- [x] Add the smallest helper/fixture needed to start the seeded DB-backed match one tick away from terminal victory. (AC: 1)
- [x] Add a failing real-process smoke test that waits for runtime completion and asserts completed-match/history/public profile/leaderboard behavior from the public boundary. (AC: 1, 2, 3)
- [x] Keep the supporting test code boring and aligned with existing smoke-test patterns; avoid production abstractions added only for test convenience. (AC: 1, 4)
- [x] Run focused smoke/API verification plus the repo-managed real-process checks. (AC: 4)

## Dev Notes

- Reused the existing seeded real-process smoke harness rather than introducing a new runtime test stack.
- The new coverage adds a live completion regression without replacing the broader completed-fixture browse/read smoke assertions.
- Profile and leaderboard assertions stay at the public boundary so the test proves the shipped runtime + persistence + read-model path end to end.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted to close Epic 40 with a live runtime-to-public-read regression.
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k completion_to_leaderboard`
- `uv run pytest -o addopts='' -q tests/e2e/test_api_smoke.py -k 'completion_to_leaderboard or public_leaderboard_and_completed_match_smoke_flow'`
- `uv run pytest -o addopts='' -q tests/api/test_agent_api.py -k 'completed_terminal_tick or finalized_settlement_results'`
- `make test-smoke`
- `make test-real-api`
- Spec review: PASS
- Code quality review: APPROVED

### Completion Notes

- Added `prepare_seeded_terminal_match()` in test support to mutate the seeded DB-backed primary match into a one-tick-from-terminal-victory scenario with fast runtime ticks.
- Added `running_terminal_fast_tick_app` so the real-process smoke suite can launch a DB-backed live app against that near-terminal seeded scenario without changing production code.
- Added `test_completion_to_leaderboard_smoke_flow_runs_through_real_process()` to poll only shipped HTTP routes until the live runtime completes the match, then assert the match leaves active browse reads, appears in completed/history reads, and updates leaderboard plus public/authenticated agent profile surfaces with settled non-provisional results.
- Kept the implementation entirely in test/support code so Story 40.4 strengthens product safety without widening production scope.

### File List

- `_bmad-output/implementation-artifacts/40-4-add-completion-to-leaderboard-end-to-end-regression-coverage.md`
- `docs/plans/2026-04-02-story-40-4-completion-to-leaderboard-e2e.md`
- `tests/conftest.py`
- `tests/e2e/test_api_smoke.py`
- `tests/support.py`

### Change Log

- 2026-04-02: Drafted Story 40.4 to add live completion-to-leaderboard regression coverage.
- 2026-04-02: Implemented the near-terminal seeded smoke harness and added a real-process runtime-to-leaderboard regression with focused and repo-managed verification.
