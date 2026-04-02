# Story 40.1 Match Completion Finalization Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Persist terminal match completion from `VictoryState`, stop the runtime loop cleanly, and keep public completed-match/history/replay surfaces consistent with the final tick.

**Architecture:** Extend the existing `AdvancedMatchTick` flow rather than introducing a new subsystem. Add the smallest explicit terminal-match helper(s) needed so the in-memory registry/runtime and DB tick-persistence path can agree on one completion rule: a terminal tick both appends its replay log and finalizes the match row (`status`, `winner_alliance`, `state`, `current_tick`) atomically, while the runtime stops future scheduling after that tick.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, in-memory runtime loop, Pydantic match state models, pytest, real-process smoke tests.

---

### Task 1: Pin the terminal-victory persistence contract in DB tests

**Objective:** Add focused failing tests that prove the terminal tick finalizes the persisted match row atomically with the tick log.

**Files:**
- Modify: `tests/test_db_registry.py`
- Modify: `server/db/tick_persistence.py`

**Step 1: Write failing test**

Add a DB-focused regression near the existing `persist_advanced_match_tick` tests asserting that a terminal `AdvancedMatchTick`:
- sets `matches.status` to `completed`
- stores `winner_alliance`
- stores the terminal `current_tick` and `state`
- appends exactly one matching `TickLog`

Use a helper tick fixture where:

```python
VictoryState(
    leading_alliance="alliance-red",
    cities_held=13,
    threshold=13,
    countdown_ticks_remaining=0,
)
```

**Step 2: Run test to verify failure**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'persist_advanced_match_tick and completed'
```

Expected: FAIL because the current persistence path updates only `current_tick`/`state` and appends a tick log.

**Step 3: Write minimal implementation**

In `server/db/tick_persistence.py`, add the smallest explicit terminal-match helper, for example:

```python
def _is_completed_victory_tick(advanced_tick: AdvancedMatchTick) -> bool:
    victory = advanced_tick.next_state.victory
    return victory.leading_alliance is not None and victory.countdown_ticks_remaining == 0
```

Then, inside the existing transaction:

```python
if _is_completed_victory_tick(advanced_tick):
    match.status = MatchStatus.COMPLETED.value
    match.winner_alliance = advanced_tick.next_state.victory.leading_alliance
```

Keep `current_tick`, `state`, and `TickLog` persistence in the same transaction.

**Step 4: Run test to verify pass**

Run the same focused command again. Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_db_registry.py server/db/tick_persistence.py
git commit -m "feat: persist completed matches on terminal victory"
```

### Task 2: Stop the runtime loop cleanly after the terminal tick

**Objective:** Ensure the in-memory runtime records the final tick exactly once and does not schedule another tick for a completed match.

**Files:**
- Modify: `server/runtime.py`
- Modify: `server/agent_registry.py` or `server/agent_registry_types.py` if a tiny explicit completion seam is needed
- Test: `tests/test_runtime.py` (create if absent)

**Step 1: Write failing runtime test**

Create a focused async test proving that when `advance_match_tick()` returns a terminal victory tick:
- persistence and broadcast still run for that tick
- the in-memory match transitions to `MatchStatus.COMPLETED`
- the runtime loop exits without advancing another tick

If no `tests/test_runtime.py` exists, create it.

**Step 2: Run test to verify failure**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_runtime.py -k completed
```

Expected: FAIL because the current loop continues until it sees a non-active match on the next iteration.

**Step 3: Write minimal implementation**

Keep the solution local and explicit. After `advanced_tick = self._registry.advance_match_tick(match_id)`, detect terminal completion from `advanced_tick.next_state.victory`, transition the match record to `MatchStatus.COMPLETED`, finish persistence/broadcast for that terminal tick, and then return from the loop.

Prefer a tiny helper such as:

```python
def _advanced_tick_completes_match(advanced_tick: AdvancedMatchTick) -> bool:
    victory = advanced_tick.next_state.victory
    return victory.leading_alliance is not None and victory.countdown_ticks_remaining == 0
```

Avoid introducing a new runtime manager/service layer.

**Step 4: Run test to verify pass**

Run the same focused runtime command again. Expected: PASS.

**Step 5: Commit**

```bash
git add server/runtime.py tests/test_runtime.py server/agent_registry.py server/agent_registry_types.py
git commit -m "feat: stop runtime after terminal victory tick"
```

### Task 3: Prove completed-match public behavior stays coherent

**Objective:** Verify public browse/history/replay surfaces behave correctly after a terminal completion tick.

**Files:**
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/e2e/test_api_smoke.py`
- Possibly inspect: `server/api/public_match_routes.py`, `server/db/public_reads.py`

**Step 1: Write or tighten failing contract tests**

Add assertions covering a completed persisted match after terminal victory:
- `/api/v1/matches` excludes it
- `/api/v1/matches/completed` includes it
- `/api/v1/matches/{match_id}/history` and `/history/{tick}` still return the terminal persisted data

Keep assertions at the API boundary, not on internal helpers.

**Step 2: Run focused tests to verify expected failures (if any)**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'completed and (history or replay or matches)'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'completed or history or replay'
```

**Step 3: Implement the smallest fixes if tests reveal gaps**

Prefer preserving existing public route/read surfaces. Only adjust query/visibility logic if terminal completion exposes a real drift.

**Step 4: Run focused tests to verify pass**

Re-run the same commands and confirm GREEN.

**Step 5: Commit**

```bash
git add tests/api/test_agent_api.py tests/e2e/test_api_smoke.py server/api/public_match_routes.py server/db/public_reads.py
git commit -m "test: cover completed-match finalization contract"
```

### Task 4: Verify rollback and repo quality end-to-end

**Objective:** Confirm terminal completion is safe under failure and the repo remains green.

**Files:**
- Modify: `tests/test_db_registry.py`
- Modify: `tests/test_runtime.py`

**Step 1: Add rollback regression if missing**

Prove that if persistence fails during a terminal completion tick, the runtime restores the in-memory match snapshot and the match is not left partially completed.

**Step 2: Run focused failure-path tests**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'persist_advanced_match_tick and completed'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_runtime.py -k 'completed or rollback'
```

**Step 3: Run strongest practical repo-managed verification**

Run:

```bash
source .venv/bin/activate && make quality
```

Expected: PASS.

**Step 4: Inspect simplification outcome**

Run:

```bash
git diff --stat HEAD~3..HEAD
```

Check that the change stayed localized to runtime/persistence/tests and did not introduce unnecessary abstraction.

**Step 5: Final commit / squash as needed**

```bash
git add -A
git commit -m "feat: finalize completed matches from terminal victory"
```

## Parallelism / sequencing note

This story should remain sequential. Runtime stop behavior, terminal persistence, and public completed-match visibility all depend on the same definition of a terminal victory tick and touch overlapping files.

## Validation summary

Primary commands:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'persist_advanced_match_tick and completed'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_runtime.py -k 'completed or rollback'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'completed and (history or replay or matches)'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'completed or history or replay'
source .venv/bin/activate && make quality
```

## Risks / pitfalls

- Do not let the runtime skip persistence/broadcast of the terminal tick while trying to stop the loop.
- Do not mark the match completed in memory but leave the DB row active if persistence fails.
- Keep the terminal-victory rule explicit and derived from the already-shipped `VictoryState`; this story should not redefine gameplay countdown semantics.
- Preserve real public-contract behavior at `/matches`, `/matches/completed`, `/history`, and `/history/{tick}`.
