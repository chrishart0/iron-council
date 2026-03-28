# Story 12.2: Introduce a proper database migration service and migration-driven schema lifecycle

Status: done

## Story

As a server developer,
I want all schema changes to flow through a real migration system,
So that local environments, test databases, and future deployments share one deterministic schema history.

## Acceptance Criteria

1. Given a fresh database, when the migration workflow runs, then it can create the full current schema from scratch without manual SQL hand-edits.
2. Given future schema evolution, when developers add or modify persistence structures, then those changes are represented through versioned migrations rather than ad hoc runtime table creation.
3. Given the migration service in local and test workflows, when integration or end-to-end tests prepare a database, then they apply migrations to head before tests execute.

## Tasks / Subtasks

- [x] Select and wire the migration approach for the Python/FastAPI stack. (AC: 1, 2, 3)
  - [x] Add the migration tooling and any persistence dependencies required for real schema management.
  - [x] Keep the setup conventional and by the book for this stack.
  - [x] Avoid custom migration machinery unless clearly justified.
- [x] Establish the initial schema and migration workflow. (AC: 1, 2)
  - [x] Ensure a fresh database can be migrated from empty to head using a stable documented command.
  - [x] Ensure the migration history is versioned in the repository.
  - [x] Ensure schema lifecycle does not depend on app startup side effects.
- [x] Integrate migrations into test and local workflows. (AC: 1, 3)
  - [x] Apply migrations before DB-backed integration/e2e runs.
  - [x] Expose stable command targets for migration-upgrade and reset flows.
  - [x] Re-run the repository quality workflow after migration support lands.

## Dev Notes

- This story is foundational: if we get it wrong, every later DB-backed workflow gets painful.
- Prefer a boring, standard migration setup over a clever one.
- Schema evolution should be explicit, reviewable, and reproducible.

### References

- `_bmad-output/planning-artifacts/epics.md` Story 12.2 acceptance criteria.
- Existing architecture docs calling for a real database and migration-managed schema.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex + Hermes review loop

### Debug Log References

- 2026-03-28 17:19 UTC: Added Alembic/SQLAlchemy dependencies, migration metadata/models, and the initial versioned schema migration.
- 2026-03-28 17:24 UTC: Added migration lifecycle tests plus a shared `prepare_test_database(...)` helper and pytest fixture for DB-backed test setup.
- 2026-03-28 17:31 UTC: Reworked Alembic URL resolution to pull from app settings by default while preserving explicit test overrides; re-ran focused tests and `make quality`.
- 2026-03-28 17:33 UTC: Verified direct Alembic upgrade/downgrade commands against a temporary SQLite database in addition to the repo quality gate.

### Completion Notes List

- Added a conventional Alembic + SQLAlchemy migration workflow with repository-owned migration history and an initial schema covering the documented persistence tables.
- Exposed stable `make db-upgrade` and `make db-reset` commands and documented the migration-managed local workflow alongside the existing support-services stack.
- Added reusable migration test helpers so DB-backed integration/e2e setup can upgrade a target database to Alembic `head` before tests run.
- Kept schema lifecycle out of app startup side effects; migrations now resolve the default database URL from the same settings path used by the app.
- Verified the change set with focused migration/settings tests, direct Alembic upgrade/downgrade smoke checks on SQLite, and the full `make quality` gate.

### File List

- `Makefile`
- `README.md`
- `pyproject.toml`
- `uv.lock`
- `alembic.ini`
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/20260328_1700_initial_schema.py`
- `server/db/__init__.py`
- `server/db/config.py`
- `server/db/metadata.py`
- `server/db/migrations.py`
- `server/db/models.py`
- `server/db/testing.py`
- `tests/conftest.py`
- `tests/test_database_migrations.py`
- `_bmad-output/implementation-artifacts/12-2-introduce-a-proper-database-migration-service-and-migration-driven-schema-lifecycle.md`

### Change Log

- 2026-03-28 14:50 UTC: Drafted Story 12.2 for real migration-managed schema lifecycle support.
- 2026-03-28 17:33 UTC: Added Alembic-driven schema management, migration-aware test helpers, stable DB reset/upgrade commands, and passing migration/quality verification.
