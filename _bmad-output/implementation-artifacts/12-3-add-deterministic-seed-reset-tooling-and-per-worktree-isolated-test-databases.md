# Story 12.3: Add deterministic seed/reset tooling and per-worktree isolated test databases

Status: done

## Story

As a delivery lead,
I want every worktree to be able to create a fresh database with fresh test data,
So that integration and end-to-end tests can run in parallel without state collisions or manual cleanup.

## Acceptance Criteria

1. Given multiple git worktrees or parallel test lanes, when each one provisions its integration-test environment, then it receives an isolated database identity, migrated schema, and deterministic seed data without conflicting with sibling worktrees.
2. Given a developer or Codex worker needs a clean starting point, when the reset workflow runs, then it can recreate the database state from migrations plus seed data using a stable documented command.
3. Given repeated setup runs from the same inputs, when the seed/reset workflow executes, then the resulting test data is deterministic and suitable for reproducible debugging.

## Tasks / Subtasks

- [x] Define the isolation strategy for parallel worktrees and test lanes. (AC: 1, 2, 3)
  - [x] Use a deterministic naming or scoping strategy so each worktree gets its own database identity.
  - [x] Ensure the approach also works for parallel CI or local test worker execution.
  - [x] Keep the setup simple enough that Codex workers can use it reliably.
- [x] Implement seed and reset workflows. (AC: 1, 2, 3)
  - [x] Recreate the database from migrations plus deterministic seed data.
  - [x] Keep seed fixtures realistic enough for integration and end-to-end validation.
  - [x] Ensure reruns converge to the same known-good state.
- [x] Expose stable developer commands and docs. (AC: 2, 3)
  - [x] Add command targets for fresh setup and clean reset.
  - [x] Document how worktree-local environment variables map to isolated DB instances.
  - [x] Re-verify the repository quality workflow after the isolation tooling lands.

## Dev Notes

- This story is what makes parallel Codex worker testing practical instead of hand-wavy.
- Favor deterministic, boring setup over clever dynamic orchestration.
- Seed data should support real user-facing flows, not just schema smoke checks.

### References

- `_bmad-output/planning-artifacts/epics.md` Story 12.3 acceptance criteria.
- Existing user requirement that each worktree be able to spin up a fresh DB with fresh data.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run --extra dev pytest --no-cov tests/test_settings.py tests/test_database_migrations.py tests/test_local_dev_docs.py tests/test_db_tooling.py`
- `make quality`

### Completion Notes List

- Added deterministic worktree-scoped Postgres database URL derivation with optional `IRON_COUNCIL_DB_LANE` suffixing so sibling worktrees and parallel workers do not collide.
- Added `server.db.tooling` plus `make db-setup` and `make db-reset` to provision a database, apply migrations, and load deterministic seed data through one stable workflow.
- Seeded a realistic integration baseline across matches, api keys, alliances, players, messages, treaties, and tick log rows, and verified reset converges back to the same seeded snapshot.
- Updated README workflow docs and sprint tracking after `make quality` passed.

### File List

- `Makefile`
- `README.md`
- `server/db/testing.py`
- `server/db/tooling.py`
- `server/settings.py`
- `tests/test_database_migrations.py`
- `tests/test_db_tooling.py`
- `tests/test_local_dev_docs.py`
- `tests/test_settings.py`
- `_bmad-output/implementation-artifacts/12-3-add-deterministic-seed-reset-tooling-and-per-worktree-isolated-test-databases.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-28 14:57 UTC: Drafted Story 12.3 for deterministic seed/reset workflows and per-worktree DB isolation.
- 2026-03-29 00:00 UTC: Implemented worktree-local deterministic database provisioning, seed/reset tooling, docs, and coverage-backed tests.
