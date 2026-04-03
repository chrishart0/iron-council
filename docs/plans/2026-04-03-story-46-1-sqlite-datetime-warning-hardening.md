# Story 46.1 SQLite Datetime Warning Hardening Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Remove the Python 3.12 sqlite datetime adapter deprecation warnings from the Iron Council persistence/test path without regressing Postgres or public API behavior.

**Architecture:** Keep the fix narrow and boring: introduce one explicit DB datetime compatibility seam for SQLAlchemy models instead of sprinkling warning filters or per-call conversions through the codebase. The preferred shape is a shared UTC-aware column type/helper used by the persistence models, plus focused regression tests that prove sqlite round-trips timezone-aware timestamps cleanly and the repo quality gate runs warning-clean for the affected paths.

**Tech Stack:** Python 3.12, SQLAlchemy ORM, Alembic-compatible model metadata, pytest, FastAPI, sqlite and Postgres-backed test paths.

---

### Task 1: Pin the sqlite warning problem in focused DB tests

**Objective:** Add/adjust focused tests so the deprecation-warning contract is explicit before changing the DB layer.

**Files:**
- Modify: `tests/test_database_migrations.py`
- Modify: `tests/test_db_registry.py`
- Modify: `tests/api/test_agent_api.py` or another focused DB-backed API test only if needed

**Step 1: Write failing test**

Add a focused regression that exercises one representative persisted aware timestamp through the sqlite path and asserts no `DeprecationWarning` from the default sqlite datetime adapter is emitted. Prefer `warnings.catch_warnings(record=True)` with the warning filter set to always capture `DeprecationWarning`.

Keep the contract at the behavior boundary:
- write a timezone-aware UTC datetime through the real ORM/session path
- read it back successfully
- assert the captured warnings do not include the Python 3.12 sqlite adapter deprecation text

**Step 2: Run test to verify failure**

Run:

```bash
source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_database_migrations.py -k datetime
```

Expected: FAIL because the current sqlite binding path still emits the adapter deprecation warning.

**Step 3: Write minimal implementation scaffold (if needed for the test seam only)**

If the tests need one small shared helper import path, add that helper stub in the DB metadata/models seam only.

**Step 4: Run test to verify the focused failure is real and isolated**

Re-run the same command and confirm the failure is still the warning/assertion gap, not a broken fixture.

**Step 5: Commit**

```bash
git add tests/test_database_migrations.py tests/test_db_registry.py tests/api/test_agent_api.py
 git commit -m "test: pin sqlite datetime warning regression"
```

### Task 2: Add one shared sqlite-safe UTC datetime persistence seam

**Objective:** Replace the warning-producing sqlite datetime binding path with one explicit shared type/helper.

**Files:**
- Modify: `server/db/metadata.py` and/or `server/db/models.py`
- Possibly modify: any DB helper module that needs explicit normalization on read/write
- Test: reuse the focused tests from Task 1

**Step 1: Write minimal implementation**

Prefer one shared SQLAlchemy type such as a `TypeDecorator` or similarly narrow abstraction that:
- preserves timezone-aware UTC semantics
- avoids the Python stdlib sqlite default adapter path that now warns on 3.12
- stays compatible with the existing model fields and Postgres behavior

A reasonable shape is:

```python
class UTCDateTime(sa.types.TypeDecorator[datetime]):
    impl = sa.DateTime(timezone=True)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        ...

    def process_bind_param(self, value, dialect):
        ...

    def process_result_value(self, value, dialect):
        ...
```

Use it for the ORM timestamp columns currently declared with `sa.DateTime(timezone=True)`.

**Step 2: Run focused tests to verify pass**

Run:

```bash
source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_database_migrations.py -k datetime
source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'tick or settlement or datetime'
```

Expected: PASS.

**Step 3: Add/keep behavior assertions**

Make sure the tests assert actual timestamp round-trip behavior, not just absence of warnings.

**Step 4: Commit**

```bash
git add server/db/metadata.py server/db/models.py tests/test_database_migrations.py tests/test_db_registry.py
 git commit -m "fix: harden sqlite datetime persistence"
```

### Task 3: Verify the public/runtime contract still behaves the same

**Objective:** Prove the warning fix does not silently regress DB-backed API/runtime behavior.

**Files:**
- Modify only if needed: `tests/api/test_agent_api.py`, `tests/e2e/test_api_smoke.py`, `server/db/public_read_assembly.py`

**Step 1: Run focused boundary tests**

Run:

```bash
source .venv/bin/activate && uv run pytest --no-cov tests/api/test_agent_api.py -k 'completed or settlement or history' -q
source .venv/bin/activate && uv run pytest --no-cov tests/e2e/test_api_smoke.py -k 'completed or history or treaty' -q
```

**Step 2: Fix only real regressions**

If timezone/result parsing drifts in public response models, add the smallest normalization needed in the shared DB read seam. Do not add warning filters.

**Step 3: Re-run the same focused commands**

Expected: PASS.

**Step 4: Commit**

```bash
git add tests/api/test_agent_api.py tests/e2e/test_api_smoke.py server/db/public_read_assembly.py
 git commit -m "test: verify datetime compatibility at API boundary"
```

### Task 4: Run the real repo gate and simplification pass

**Objective:** Finish in a warning-clean, low-complexity state.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/46-1-eliminate-python-3-12-sqlite-datetime-adapter-warnings.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run the strongest practical verification**

```bash
source .venv/bin/activate && make quality
```

Goal: the prior sqlite adapter deprecation warnings no longer appear in the affected Python test paths.

**Step 2: Run a simplification review**

Inspect the diff and make sure the fix stayed local to the DB datetime seam plus tests. Avoid a new generic persistence framework.

```bash
git diff --stat HEAD~3..HEAD
```

**Step 3: Update BMAD artifact with real results**

Record the exact commands and outcomes in the story file.

**Step 4: Final commit**

```bash
git add -A
 git commit -m "fix: remove sqlite datetime adapter warnings"
```
