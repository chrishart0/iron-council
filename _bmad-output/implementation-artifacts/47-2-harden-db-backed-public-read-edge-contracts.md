# Story: 47.2 Harden DB-backed public read edge contracts

## Status
Done

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
- [x] Add focused DB-backed regressions for user-backed agent identities across leaderboard/completed/history surfaces. (AC: 1)
- [x] Add focused DB-backed regressions for solo-winner / missing-alliance-row fallback behavior. (AC: 2)
- [x] Apply the smallest production fix only if the new public-boundary tests expose a real bug. (AC: 3)
- [x] Re-run focused verification and any needed API slice after the fix. (AC: 4)
- [x] Update this story artifact and sprint status with real outcomes. (AC: 4)

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
- 2026-04-03: Added focused DB-backed public-read regressions for `agent-user-*` identity propagation and honest winner fallback metadata; no production code change was needed.

## Debug Log References
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'leaderboard or completed_match or match_history or user_backed_agent or solo_winner or winner_fallback'`
  Outcome: initial red phase exposed an incorrect new test expectation for empty match history on a completed fixture without `tick_log` rows; after correcting the assertion, the slice passed with `12 passed, 51 deselected`.
- `uv sync --extra dev --frozen`
  Outcome: installed the locked dev tools, including `mypy`, so the repo quality gate could run.
- `make quality`
  Outcome: format, Ruff, mypy, and the repo test suite ran, but the gate failed on unrelated existing client smoke coverage in `tests/test_client_dev_smoke.py::test_next_dev_uses_client_workspace_without_warning_or_generated_type_drift`.
- `uv run pytest --no-cov tests/test_client_dev_smoke.py -k next_dev_uses_client_workspace_without_warning_or_generated_type_drift -q`
  Outcome: reproduced the unrelated failure (`ProcessLookupError` during `npm run dev` teardown), confirming it was not introduced by Story 47.2.

## Completion Notes
- Added two behavior-first DB-backed regressions in `tests/test_db_registry.py` to pin:
  - user-backed agent public identities across `get_public_leaderboard`, `get_completed_match_summaries`, and `get_match_history`
  - honest solo-winner and missing-alliance-row winner fallback behavior at the public read boundary
- The new coverage did not reveal a contract bug, so `server/db/public_read_assembly.py` was left unchanged.
- Sprint tracking was updated for Story 47.2 only on the `feat/47-2-public-read-hardening` branch.

## File List
- `tests/test_db_registry.py`
- `_bmad-output/implementation-artifacts/47-2-harden-db-backed-public-read-edge-contracts.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## QA Results
- Story-focused DB-backed verification: pass
- Repo quality gate: partial pass; blocked by unrelated existing failure in `tests/test_client_dev_smoke.py::test_next_dev_uses_client_workspace_without_warning_or_generated_type_drift`
