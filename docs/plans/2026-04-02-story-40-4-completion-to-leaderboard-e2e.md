# Story 40.4 Completion-to-Leaderboard E2E Regression Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a real DB-backed smoke regression that drives a live match to completion and proves the downstream completed-match, leaderboard, and profile reads update from the finished runtime path.

**Architecture:** Reuse the existing real-process smoke harness instead of inventing a new test stack. Add the smallest helper needed to put the seeded DB-backed match one tick away from terminal victory, run the live app with fast ticks, wait for the real runtime to complete the match, then assert the public/authenticated reads reflect the finalized persisted outcome.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pytest, uvicorn real-process smoke fixtures, uv, make.

---

### Task 1: Add a near-terminal real-process fixture helper

**Objective:** Make the existing smoke harness able to start one seeded match one runtime tick away from completion.

**Files:**
- Modify: `tests/support.py`
- Modify: `tests/conftest.py`
- Test: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing smoke setup usage**

Add or update a smoke test so it expects a fast-tick running app fixture whose primary match completes from the live runtime without manually inserting a completed-match fixture.

**Step 2: Run test to verify failure**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k completion_to_leaderboard
```

Expected: FAIL because no such fixture/helper exists yet.

**Step 3: Write minimal implementation**

Add a helper that updates the seeded DB match into a near-terminal state and a `running_terminal_fast_tick_app` fixture that launches the existing DB-backed real process with `turn_seconds=1`.

**Step 4: Re-run the focused test**

Use the same command; expected to move past fixture/setup failure.

**Step 5: Commit**

```bash
git add tests/support.py tests/conftest.py tests/e2e/test_api_smoke.py
git commit -m "test: add terminal completion smoke fixture"
```

### Task 2: Add the completion-to-leaderboard smoke regression

**Objective:** Prove the real runtime path settles a completed match and updates public/authenticated reads.

**Files:**
- Modify: `tests/e2e/test_api_smoke.py`
- Possibly modify: `tests/support.py`

**Step 1: Write the failing behavior-first smoke test**

Add one real-process smoke flow that:
- starts from the near-terminal fixture
- waits for `/api/v1/matches/{id}` or `/api/v1/matches` to stop showing the match as active
- asserts `/api/v1/matches/completed` now includes the match with the terminal tick and winning alliance/player names
- asserts `/api/v1/leaderboard` reflects finalized non-provisional results for the participating competitors
- asserts `/api/v1/agents/{agent_id}/profile` and `/api/v1/agent/profile` reflect the settled history/rating for a participant
- optionally asserts persisted history/replay now reports `status=completed`

Prefer polling the public boundary over direct internal route-order/state assertions.

**Step 2: Run focused red test**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k completion_to_leaderboard
```

Expected: FAIL until the runtime and assertions line up.

**Step 3: Implement the smallest supporting helper changes**

Keep support code boring. Do not add new production abstractions for test convenience.

**Step 4: Run focused green test**

Re-run the same command and expect PASS.

**Step 5: Commit**

```bash
git add tests/e2e/test_api_smoke.py tests/support.py tests/conftest.py
git commit -m "test: cover match completion to leaderboard workflow"
```

### Task 3: Run the strongest practical verification and reconcile BMAD artifacts

**Objective:** Verify the touched seam, simplify if needed, and leave the BMAD story artifacts honest.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/40-4-add-completion-to-leaderboard-end-to-end-regression-coverage.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run focused verification**

Run:

```bash
uv run pytest -o addopts='' -q tests/e2e/test_api_smoke.py -k 'completion_to_leaderboard or public_leaderboard_and_completed_match_smoke_flow'
uv run pytest -o addopts='' -q tests/api/test_agent_api.py -k 'completed_terminal_tick or finalized_settlement_results'
```

Expected: PASS.

**Step 2: Run repo-managed gate for the touched seam**

Run:

```bash
make test-smoke
make test-real-api
```

Expected: PASS.

**Step 3: Simplify and review**

Trim any helper/test complexity that is only there for convenience. Keep the solution KISS and aligned with existing smoke-test patterns.

**Step 4: Update BMAD artifacts**

Mark Story 40.4 done, record exact verification commands, and point `next_story` to the next planned increment or `null` if Epic 40 is fully closed.

**Step 5: Commit**

```bash
git add tests/e2e/test_api_smoke.py tests/support.py tests/conftest.py _bmad-output/implementation-artifacts/40-4-add-completion-to-leaderboard-end-to-end-regression-coverage.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "test: add completion-to-leaderboard smoke regression"
```
