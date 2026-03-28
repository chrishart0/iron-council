# Story 12.2: Introduce a proper database migration service and migration-driven schema lifecycle

Status: drafted

## Story

As a server developer,
I want all schema changes to flow through a real migration system,
So that local environments, test databases, and future deployments share one deterministic schema history.

## Acceptance Criteria

1. Given a fresh database, when the migration workflow runs, then it can create the full current schema from scratch without manual SQL hand-edits.
2. Given future schema evolution, when developers add or modify persistence structures, then those changes are represented through versioned migrations rather than ad hoc runtime table creation.
3. Given the migration service in local and test workflows, when integration or end-to-end tests prepare a database, then they apply migrations to head before tests execute.

## Tasks / Subtasks

- [ ] Select and wire the migration approach for the Python/FastAPI stack. (AC: 1, 2, 3)
  - [ ] Add the migration tooling and any persistence dependencies required for real schema management.
  - [ ] Keep the setup conventional and by the book for this stack.
  - [ ] Avoid custom migration machinery unless clearly justified.
- [ ] Establish the initial schema and migration workflow. (AC: 1, 2)
  - [ ] Ensure a fresh database can be migrated from empty to head using a stable documented command.
  - [ ] Ensure the migration history is versioned in the repository.
  - [ ] Ensure schema lifecycle does not depend on app startup side effects.
- [ ] Integrate migrations into test and local workflows. (AC: 1, 3)
  - [ ] Apply migrations before DB-backed integration/e2e runs.
  - [ ] Expose stable command targets for migration-upgrade and reset flows.
  - [ ] Re-run the repository quality workflow after migration support lands.

## Dev Notes

- This story is foundational: if we get it wrong, every later DB-backed workflow gets painful.
- Prefer a boring, standard migration setup over a clever one.
- Schema evolution should be explicit, reviewable, and reproducible.

### References

- `_bmad-output/planning-artifacts/epics.md` Story 12.2 acceptance criteria.
- Existing architecture docs calling for a real database and migration-managed schema.

## Dev Agent Record

### Agent Model Used

_TBD_

### Debug Log References

- _TBD_

### Completion Notes List

- _TBD_

### File List

- _TBD_

### Change Log

- 2026-03-28 14:50 UTC: Drafted Story 12.2 for real migration-managed schema lifecycle support.
