# Story 12.1: Add a local support-services stack for database-backed development and validation

Status: drafted

## Story

As a server developer,
I want local support services that boot cleanly while the app itself runs in normal dev mode,
So that development, debugging, and integration testing happen against real infrastructure rather than only in-memory fixtures.

## Acceptance Criteria

1. Given a fresh checkout of the repository, when the documented local support-services startup command is run, then it starts the truly required backing services, including a real database, with clear environment-variable wiring for running the app locally in dev mode.
2. Given the local support-services definition, when developers inspect it, then it keeps service responsibilities clear, avoids unnecessary complexity such as containerizing the app without need, and supports reproducible startup and teardown.
3. Given local development and CI-oriented usage, when the support-services stack is configured, then it supports normal developer workflows such as `pnpm dev` and `uv run` alongside focused integration-test runs without manual service tinkering.

## Tasks / Subtasks

- [ ] Define the minimum viable support-services shape. (AC: 1, 2, 3)
  - [ ] Include a real database service and only the narrowly justified additional backing services needed for local workflows.
  - [ ] Keep the service stack intentionally small and easy to understand.
  - [ ] Avoid default app-containerization unless a specific validation flow truly requires it.
- [ ] Implement support-services wiring and environment setup. (AC: 1, 2)
  - [ ] Add clear environment-variable handling so the locally running app can talk to the backing services.
  - [ ] Ensure startup, shutdown, and cleanup commands are reproducible.
  - [ ] Avoid hidden manual preconditions beyond documented local prerequisites.
- [ ] Add developer-facing workflow commands and docs. (AC: 1, 3)
  - [ ] Provide stable command paths for bringing support services up and down.
  - [ ] Document how developers and Codex workers should run the app in dev mode from a worktree while using the shared service definition.
  - [ ] Re-verify the repository quality workflow after the support-services changes land.

## Dev Notes

- Keep this story focused on local support-service bootstrap, not full persistence feature implementation.
- Favor the simplest production-like shape that unlocks real API and integration validation.
- This story should make the next migration and DB-backed testing stories easier, not harder.

### References

- `core-architecture.md` and `_bmad-output/planning-artifacts/architecture.md` mention a future local service stack.
- `_bmad-output/planning-artifacts/epics.md` Story 12.1 acceptance criteria.

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

- 2026-03-28 14:50 UTC: Drafted Story 12.1 for local backing services with the app running in dev mode.
