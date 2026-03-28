# Story 12.3: Add deterministic seed/reset tooling and per-worktree isolated test databases

Status: drafted

## Story

As a delivery lead,
I want every worktree to be able to create a fresh database with fresh test data,
So that integration and end-to-end tests can run in parallel without state collisions or manual cleanup.

## Acceptance Criteria

1. Given multiple git worktrees or parallel test lanes, when each one provisions its integration-test environment, then it receives an isolated database identity, migrated schema, and deterministic seed data without conflicting with sibling worktrees.
2. Given a developer or Codex worker needs a clean starting point, when the reset workflow runs, then it can recreate the database state from migrations plus seed data using a stable documented command.
3. Given repeated setup runs from the same inputs, when the seed/reset workflow executes, then the resulting test data is deterministic and suitable for reproducible debugging.

## Tasks / Subtasks

- [ ] Define the isolation strategy for parallel worktrees and test lanes. (AC: 1, 2, 3)
  - [ ] Use a deterministic naming or scoping strategy so each worktree gets its own database identity.
  - [ ] Ensure the approach also works for parallel CI or local test worker execution.
  - [ ] Keep the setup simple enough that Codex workers can use it reliably.
- [ ] Implement seed and reset workflows. (AC: 1, 2, 3)
  - [ ] Recreate the database from migrations plus deterministic seed data.
  - [ ] Keep seed fixtures realistic enough for integration and end-to-end validation.
  - [ ] Ensure reruns converge to the same known-good state.
- [ ] Expose stable developer commands and docs. (AC: 2, 3)
  - [ ] Add command targets for fresh setup and clean reset.
  - [ ] Document how worktree-local environment variables map to isolated DB instances.
  - [ ] Re-verify the repository quality workflow after the isolation tooling lands.

## Dev Notes

- This story is what makes parallel Codex worker testing practical instead of hand-wavy.
- Favor deterministic, boring setup over clever dynamic orchestration.
- Seed data should support real user-facing flows, not just schema smoke checks.

### References

- `_bmad-output/planning-artifacts/epics.md` Story 12.3 acceptance criteria.
- Existing user requirement that each worktree be able to spin up a fresh DB with fresh data.

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

- 2026-03-28 14:57 UTC: Drafted Story 12.3 for deterministic seed/reset workflows and per-worktree DB isolation.
