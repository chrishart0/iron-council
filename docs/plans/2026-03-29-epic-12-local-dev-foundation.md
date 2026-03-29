# Epic 12 Local Dev Foundation Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Finish Epic 12 so Iron Counsil can support parallel worktrees, deterministic local reset-and-seed workflows, and real running-app validation against a real database.

**Architecture:** Keep the app running directly on the host in normal dev mode while Docker provides only the backing Postgres service. Build boring per-worktree isolation inside the shared Postgres server, then layer real process-level API validation and a tiny smoke suite on top. Reuse the existing in-process API tests from Story 11.4 rather than replacing them.

**Tech Stack:** Python 3.12, FastAPI, uv, Alembic, SQLAlchemy, Postgres 16, Docker Compose, pytest, httpx, uvicorn, GitHub Actions.

---

## Story sequencing

1. Story 12.3 first: per-worktree database isolation and deterministic reset/seed flow.
2. Story 12.4 second: real running-app integration tests and small smoke suite.

Story 12.4 should not start in earnest until Story 12.3 provides isolated DB identities for local workers and CI lanes.

---

### Task 1: Lock the worktree database naming contract

**Objective:** Define the simplest deterministic way for each worktree to derive or override its own database identity.

**Files:**
- Modify: `server/settings.py`
- Modify: `README.md`
- Modify: `env.local.example`
- Test: `tests/test_settings.py`
- Modify: `_bmad-output/implementation-artifacts/12-3-add-deterministic-seed-reset-tooling-and-per-worktree-isolated-test-databases.md`

**Step 1: Write failing tests**

Add tests for:
- derived worktree-safe database naming
- explicit env override behavior
- stable fallback behavior in the main worktree

Run:

```bash
uv run pytest --no-cov tests/test_settings.py -q
```

Expected: FAIL because the naming contract does not exist yet.

**Step 2: Implement the minimal settings logic**

Add the smallest config surface needed to derive or override the DB name while preserving the current boring default path.

**Step 3: Verify the focused tests pass**

```bash
uv run pytest --no-cov tests/test_settings.py -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add server/settings.py README.md env.local.example tests/test_settings.py _bmad-output/implementation-artifacts/12-3-add-deterministic-seed-reset-tooling-and-per-worktree-isolated-test-databases.md
git commit -m "feat: add worktree database naming contract"
```

---

### Task 2: Add database create/drop helpers for the shared Postgres server

**Objective:** Provision isolated per-worktree databases inside the existing shared Postgres service.

**Files:**
- Create: `server/db/provisioning.py`
- Modify: `server/db/__init__.py`
- Test: `tests/test_database_migrations.py`
- Modify: `Makefile`
- Modify: `_bmad-output/implementation-artifacts/12-3-add-deterministic-seed-reset-tooling-and-per-worktree-isolated-test-databases.md`

**Step 1: Write failing tests**

Add tests that verify helper commands/entrypoints exist and that the target DB name is explicit and deterministic.

Run:

```bash
uv run pytest --no-cov tests/test_database_migrations.py -q
```

Expected: FAIL because provisioning support is missing.

**Step 2: Implement the minimal provisioning layer**

Support:
- create database if missing
- drop/reset target database when explicitly requested
- connect through an admin database on the same Postgres server

Keep it simple and by the book.

**Step 3: Verify the focused tests pass**

```bash
uv run pytest --no-cov tests/test_database_migrations.py -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add server/db/provisioning.py server/db/__init__.py tests/test_database_migrations.py Makefile _bmad-output/implementation-artifacts/12-3-add-deterministic-seed-reset-tooling-and-per-worktree-isolated-test-databases.md
git commit -m "feat: add per-worktree database provisioning"
```

---

### Task 3: Add deterministic seed fixtures and reset workflow

**Objective:** Rebuild a target worktree DB from migrations plus deterministic seed data useful for API journey validation.

**Files:**
- Create: `server/db/seeds.py`
- Modify: `server/db/testing.py`
- Modify: `tests/conftest.py`
- Create or Modify: `tests/test_seed_workflow.py`
- Modify: `Makefile`
- Modify: `README.md`
- Modify: `_bmad-output/implementation-artifacts/12-3-add-deterministic-seed-reset-tooling-and-per-worktree-isolated-test-databases.md`

**Step 1: Write failing tests**

Add tests for:
- deterministic seeded match/player dataset
- rerunning reset+seed yields the same visible records
- test fixtures can target an isolated DB cleanly

Run:

```bash
uv run pytest --no-cov tests/test_seed_workflow.py -q
```

Expected: FAIL because the seed workflow does not exist yet.

**Step 2: Implement the minimal seed workflow**

Add:
- one realistic seeded match fixture
- one stable reset+seed command path
- helper reuse for later API integration tests

**Step 3: Verify the focused tests pass**

```bash
uv run pytest --no-cov tests/test_seed_workflow.py -q
```

Expected: PASS.

**Step 4: Run quality**

```bash
make quality
```

Expected: PASS.

**Step 5: Commit**

```bash
git add server/db/seeds.py server/db/testing.py tests/conftest.py tests/test_seed_workflow.py Makefile README.md _bmad-output/implementation-artifacts/12-3-add-deterministic-seed-reset-tooling-and-per-worktree-isolated-test-databases.md
git commit -m "feat: add deterministic database seed workflow"
```

---

### Task 4: Add a real running-app API integration fixture

**Objective:** Boot the FastAPI app as a real process and hit it over HTTP against a seeded isolated database.

**Files:**
- Create or Modify: `tests/api/test_real_api.py`
- Modify: `tests/conftest.py`
- Modify: `Makefile`
- Modify: `README.md`
- Modify: `_bmad-output/implementation-artifacts/12-4-wire-real-api-integration-tests-and-small-end-to-end-smoke-flows-into-the-quality-workflow.md`

**Step 1: Write failing tests**

Add one narrow end-to-end journey that:
- prepares an isolated seeded DB
- starts uvicorn as a subprocess
- calls the real HTTP endpoint(s)
- verifies meaningful JSON outcomes

Run:

```bash
uv run pytest --no-cov tests/api/test_real_api.py -q
```

Expected: FAIL because the real running-app fixture is missing.

**Step 2: Implement the running-app fixture**

Start the app with:
- explicit env wiring to the isolated DB
- deterministic port selection or ephemeral port handling
- clean startup/shutdown behavior

**Step 3: Verify the focused tests pass**

```bash
uv run pytest --no-cov tests/api/test_real_api.py -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add tests/api/test_real_api.py tests/conftest.py Makefile README.md _bmad-output/implementation-artifacts/12-4-wire-real-api-integration-tests-and-small-end-to-end-smoke-flows-into-the-quality-workflow.md
git commit -m "test: add real running-app API integration coverage"
```

---

### Task 5: Add the smallest valuable smoke suite

**Objective:** Add a tiny smoke layer that validates critical running-app journeys without building a brittle mega-suite.

**Files:**
- Create: `tests/e2e/test_smoke_journeys.py` or similar
- Modify: `Makefile`
- Modify: `.github/workflows/quality.yml`
- Modify: `README.md`
- Modify: `_bmad-output/implementation-artifacts/12-4-wire-real-api-integration-tests-and-small-end-to-end-smoke-flows-into-the-quality-workflow.md`

**Step 1: Write failing smoke tests**

Cover only the highest-value journeys available in the current backend-first repo.

Suggested first flow:
- list matches
- fetch fog-filtered state for a seeded player
- submit an order envelope
- confirm follow-up visible outcome or stored acceptance state through the running app boundary

**Step 2: Implement the minimal smoke harness**

Reuse the process-level fixture and seeded DB helpers from previous tasks.

**Step 3: Verify the focused smoke tests pass**

```bash
uv run pytest --no-cov tests/e2e/test_smoke_journeys.py -q
```

Expected: PASS.

**Step 4: Wire stable commands and CI entrypoints**

Add explicit `make` targets and keep CI practical.

**Step 5: Commit**

```bash
git add tests/e2e/test_smoke_journeys.py Makefile .github/workflows/quality.yml README.md _bmad-output/implementation-artifacts/12-4-wire-real-api-integration-tests-and-small-end-to-end-smoke-flows-into-the-quality-workflow.md
git commit -m "test: add smoke journeys to real quality workflow"
```

---

### Task 6: Final artifact updates and simplification review

**Objective:** Close the loop on Epic 12 with green quality, updated story artifacts, and a simplicity pass.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/12-3-add-deterministic-seed-reset-tooling-and-per-worktree-isolated-test-databases.md`
- Modify: `_bmad-output/implementation-artifacts/12-4-wire-real-api-integration-tests-and-small-end-to-end-smoke-flows-into-the-quality-workflow.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run the final gate**

```bash
make quality
```

And run any new explicit real-API/smoke targets.

**Step 2: Review for overcomplexity**

Confirm:
- no unnecessary containerization of the app
- no over-engineered database orchestration
- no explosion of smoke tests
- no duplication of 11.4’s in-process coverage

**Step 3: Update BMAD artifacts**

Record:
- red-phase evidence
- completion notes
- file list
- sprint status changes

**Step 4: Final commit if needed**

```bash
git add -A
git commit -m "docs: close epic 12 local dev foundation"
```

Only if the review changed files.
