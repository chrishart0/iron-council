# Story: 47.2 Harden DB-backed public read edge contracts

## Status
Draft

## Story
**As a** maintainer of Iron Council's public read models,
**I want** the DB-backed public leaderboard/history/completed-match assembly path to stay correct for user-backed agent identities and winner fallback edge cases,
**so that** public read surfaces remain trustworthy even when persisted data is not limited to the happiest seeded-path shape.

## Acceptance Criteria
1. Focused DB-backed regressions prove public read surfaces handle agent competitors with no `api_key_id` by exposing the expected durable public identity and competitor metadata.
2. Focused DB-backed regressions prove completed-match winner fallback paths remain honest for solo-winner and missing-alliance-row cases.
3. If a production fix is needed, it stays local to the public read assembly seam without changing the public response contract shape.
4. Focused verification passes, any needed public-boundary integration slice still passes, and the repo remains in a simple coherent state.

## Tasks / Subtasks
- [ ] Add focused DB-backed regressions for user-backed agent identities across leaderboard/completed/history surfaces. (AC: 1)
- [ ] Add focused DB-backed regressions for solo-winner / missing-alliance-row fallback behavior. (AC: 2)
- [ ] Apply the smallest production fix only if the new public-boundary tests expose a real bug. (AC: 3)
- [ ] Re-run focused verification and any needed API slice after the fix. (AC: 4)
- [ ] Update this story artifact and sprint status with real outcomes. (AC: 4)

## Dev Notes
- Treat `tests/test_db_registry.py` plus the real DB-backed read helpers as the primary red/green loop.
- Prefer behavior-first assertions at the public read boundary over helper-only unit tests.
- Prior review identified `server/db/public_read_assembly.py` as the weakest current public-read seam and found no existing tests asserting `agent-user-*` public identities in leaderboard/history/completed-match responses.

## Testing
- `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'leaderboard or completed_match or match_history or user_backed_agent or solo_winner'`
- `source .venv/bin/activate && uv run pytest --no-cov tests/api/test_agent_api.py -k 'leaderboard or completed or history' -q`
- `source .venv/bin/activate && make quality`

## Change Log
- 2026-04-03: Drafted Story 47.2 after post-46 review found uncovered/high-risk DB-backed public read edge branches around user-backed agent identities and winner fallback handling.
