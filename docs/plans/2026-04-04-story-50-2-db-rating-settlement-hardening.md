# Story 50.2 DB Rating Settlement Hardening Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Harden DB-backed rating settlement and identity aggregation semantics with focused persistence-boundary regressions and only the smallest production cleanup required.

**Architecture:** Keep tests close to the SQLite/Postgres-backed persistence seam in `tests/test_db_registry.py`, covering solo winners, alliance winners, draw handling, territory fallback, tenure weighting, aggregate grouping, and latest-human-ELO lookup behavior. If regressions expose drift, patch `server/db/rating_settlement.py` narrowly without adding abstraction layers.

**Tech Stack:** Python 3.12, SQLAlchemy, pytest, uv, SQLite-backed DB fixtures, repository quality gate.

---

### Task 1: Add DB-backed settlement outcome and weighting regressions

**Objective:** Pin deterministic behavior for winner identity resolution, draw handling, tenure weighting, and zero-territory fallback.

**Files:**
- Modify: `tests/test_db_registry.py`
- Verify context in: `server/db/rating_settlement.py`
- Supporting fixtures: `tests/support.py` if a tiny helper is honestly required

**Step 1: Write failing test**

Add focused persistence tests for cases like:
- solo winner matched by persisted player identity, not incidental row order
- alliance winners share gain according to tenure and territory weighting
- zero-territory winner fallback uses `1 / winner_count`
- draws produce zero delta and durable settlement rows

**Step 2: Run test to verify failure**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'settlement or elo or latest_human'`
Expected: FAIL for at least one uncovered edge case.

**Step 3: Write minimal implementation**

If needed, patch only `server/db/rating_settlement.py` with the smallest fix that preserves current public behavior.

**Step 4: Run test to verify pass**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'settlement or elo or latest_human'`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_db_registry.py server/db/rating_settlement.py tests/support.py
git commit -m "test: harden db rating settlement edge contracts"
```

### Task 2: Add identity aggregate and latest-human-ELO regressions

**Objective:** Prove aggregate grouping and latest-human-ELO lookups stay stable across identity and timestamp edge cases.

**Files:**
- Modify: `tests/test_db_registry.py`
- Verify context in: `server/db/rating_settlement.py`, `server/db/identity.py`

**Step 1: Write failing test**

Add narrow tests for cases like:
- `load_settlement_aggregates_by_identity()` groups human rows by `user_id` and agent rows by `api_key_id`
- latest row choice breaks ties deterministically when `settled_at` matches
- `latest_human_settled_elo()` ignores agent rows and returns the latest human settlement only

**Step 2: Run test to verify failure**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'aggregate or latest_human or settled_elo'`
Expected: FAIL if the edge behavior is not already pinned.

**Step 3: Write minimal implementation**

If needed, make the smallest fix in `server/db/rating_settlement.py`.

**Step 4: Run test to verify pass**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'aggregate or latest_human or settled_elo'`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_db_registry.py server/db/rating_settlement.py
git commit -m "test: pin db rating identity aggregation semantics"
```

### Task 3: Run focused verification and repo gate, then close BMAD artifact

**Objective:** Verify the story with focused DB tests plus the full repo gate and update BMAD tracking to reality.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/50-2-harden-db-backed-rating-settlement-identity-and-tenure-edges.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run focused verification**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'settlement or elo or latest_human or aggregate'`
Expected: PASS.

**Step 2: Run full repo gate**

Run: `source .venv/bin/activate && make quality`
Expected: PASS.

**Step 3: Update BMAD closeout**

Mark the story done, record actual verification commands and results, and advance sprint tracking appropriately.

**Step 4: Commit**

```bash
git add _bmad-output/implementation-artifacts/50-2-harden-db-backed-rating-settlement-identity-and-tenure-edges.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "docs: close story 50-2"
```
