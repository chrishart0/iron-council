# Story 47.2 Public read edge-contract hardening Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Harden DB-backed public read-model assembly around user-backed agent identities and completed-match winner fallback paths so public leaderboard/history/completed-match responses stay correct at the public boundary.

**Architecture:** Keep the implementation narrow and behavior-first. Add focused DB-backed regression tests around `get_public_leaderboard`, `get_completed_match_summaries`, and `get_match_history`, using the real persisted assembly path rather than internal helper-only assertions. Only change `server/db/public_read_assembly.py` if the new public-boundary tests expose a genuine contract bug; otherwise ship this as edge-case coverage and simplification of the existing seam.

**Tech Stack:** Python 3.12, pytest, SQLAlchemy/sqlite test DBs, Iron Council DB-backed public read helpers.

---

### Task 1: Pin the user-backed agent public identity contract in DB-backed read tests

**Objective:** Prove the public read surfaces handle non-seeded user-backed agents with stable public identities.

**Files:**
- Modify: `tests/test_db_registry.py`
- Optionally modify: `tests/support/*` only if one tiny persisted fixture helper makes the test clearer

**Step 1: Write failing test**

Add one focused DB-backed regression that creates or seeds a completed match where an agent player has `api_key_id=None` and a real `user_id`, then assert the public surfaces expose the expected durable public identity (`agent-user-...`) and competitor metadata through the real registry/read path.

The assertions should hit behavior close to the boundary, e.g.:
- `get_public_leaderboard(...)`
- `get_completed_match_summaries(...)`
- `get_match_history(...)`

**Step 2: Run test to verify failure**

Run:

```bash
source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'user_backed_agent or leaderboard or completed_match or match_history'
```

Expected: FAIL if the public read path mishandles the identity, or PASS only after the coverage gap is properly filled.

**Step 3: Write minimal implementation**

Prefer adding/adjusting the narrowest fixture + assertion surface first. Only modify production code if the new public-boundary behavior is actually wrong.

**Step 4: Run test to verify pass**

Re-run the same focused command and confirm the public contract is correct.

**Step 5: Commit**

```bash
git add tests/test_db_registry.py tests/support
git commit -m "test: cover user-backed agent public read contracts"
```

### Task 2: Pin completed-match winner fallback behavior

**Objective:** Cover the fallback winner branches that can be missed when a completed match points at a solo winner or a missing alliance row.

**Files:**
- Modify: `tests/test_db_registry.py`
- Modify only if needed: `server/db/public_read_assembly.py`

**Step 1: Write failing test**

Add focused regressions for at least these cases:
- completed match where `winner_alliance` resolves directly to a solo player rather than an alliance row
- completed match where the winner-alliance lookup is absent and the public surface should degrade honestly instead of inventing winners

Assert the behavior at the public read boundary:
- leaderboard win/loss/draw tallies remain correct
- completed-match winner names / winner competitor summaries stay honest
- history competitor summaries remain stable

**Step 2: Run test to verify failure**

Run:

```bash
source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'solo_winner or completed_match or leaderboard or history'
```

Expected: FAIL if a real edge-case bug exists, otherwise this becomes the red/green coverage pin for the branch.

**Step 3: Write minimal implementation**

If production code needs adjustment, keep it inside `server/db/public_read_assembly.py` and preserve existing public shapes. No new abstractions unless a tiny helper materially clarifies duplicated fallback logic.

**Step 4: Run focused verification**

Run:

```bash
source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'leaderboard or completed_match or match_history or solo_winner'
```

Expected: PASS.

**Step 5: Commit**

```bash
git add server/db/public_read_assembly.py tests/test_db_registry.py
git commit -m "fix: harden public read-model winner fallbacks"
```

### Task 3: Run broader verification and simplification pass

**Objective:** Confirm the public read surfaces still behave correctly in the real repo harness and finish in the simplest coherent state.

**Files:**
- Optionally modify: `tests/api/test_agent_api.py` only if one route-level assertion is needed after a real bugfix
- Modify: `_bmad-output/implementation-artifacts/47-2-harden-db-backed-public-read-edge-contracts.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run focused verification**

```bash
source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'leaderboard or completed_match or match_history or user_backed_agent or solo_winner'
```

**Step 2: Run one public-boundary integration slice if production code changed**

```bash
source .venv/bin/activate && uv run pytest --no-cov tests/api/test_agent_api.py -k 'leaderboard or completed or history' -q
```

**Step 3: Run the repo gate after merge**

```bash
source .venv/bin/activate && make quality
```

**Step 4: Review and simplify**

Check:
- `git diff --stat`
- no unnecessary helper layer was added for a small edge-case fix
- assertions stay public-boundary oriented rather than white-box helper tests

**Step 5: Commit**

```bash
git add -A
git commit -m "test: harden DB-backed public read edge contracts"
```
