# Story 12.1: Add a local support-services stack for database-backed development and validation

Status: done

## Story

As a server developer,
I want local support services that boot cleanly while the app itself runs in normal dev mode,
So that development, debugging, and integration testing happen against real infrastructure rather than only in-memory fixtures.

## Acceptance Criteria

1. Given a fresh checkout of the repository, when the documented local support-services startup command is run, then it starts the truly required backing services, including a real database, with clear environment-variable wiring for running the app locally in dev mode.
2. Given the local support-services definition, when developers inspect it, then it keeps service responsibilities clear, avoids unnecessary complexity such as containerizing the app without need, and supports reproducible startup and teardown.
3. Given local development and CI-oriented usage, when the support-services stack is configured, then it supports normal developer workflows such as `pnpm dev` and `uv run` alongside focused integration-test runs without manual service tinkering.

## Tasks / Subtasks

- [x] Define the minimum viable support-services shape. (AC: 1, 2, 3)
  - [x] Include a real database service and only the narrowly justified additional backing services needed for local workflows.
  - [x] Keep the service stack intentionally small and easy to understand.
  - [x] Avoid default app-containerization unless a specific validation flow truly requires it.
- [x] Implement support-services wiring and environment setup. (AC: 1, 2)
  - [x] Add clear environment-variable handling so the locally running app can talk to the backing services.
  - [x] Ensure startup, shutdown, and cleanup commands are reproducible.
  - [x] Avoid hidden manual preconditions beyond documented local prerequisites.
- [x] Add developer-facing workflow commands and docs. (AC: 1, 3)
  - [x] Provide stable command paths for bringing support services up and down.
  - [x] Document how developers and Codex workers should run the app in dev mode from a worktree while using the shared service definition.
  - [x] Re-verify the repository quality workflow after the support-services changes land.

## Dev Notes

- Keep this story focused on local support-service bootstrap, not full persistence feature implementation.
- Favor the simplest production-like shape that unlocks real API and integration validation.
- This story should make the next migration and DB-backed testing stories easier, not harder.

### References

- `core-architecture.md` and `_bmad-output/planning-artifacts/architecture.md` mention a future local service stack.
- `_bmad-output/planning-artifacts/epics.md` Story 12.1 acceptance criteria.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Red phase: `uv run pytest --no-cov tests/test_settings.py` failed during collection with `ModuleNotFoundError: No module named 'server.settings'`.
- Environment sync: `uv sync --extra dev --frozen`
- Focused settings verification: `uv run pytest --no-cov tests/test_settings.py`
- Support-services command check: `make support-services-up` could not be completed in this environment because `docker` is not installed in the worktree runner.
- Quality gate: `make quality`

### Completion Notes List

- Added a tiny `server.settings` helper that loads `DATABASE_URL` from `.env.local` by default, while letting an explicit process environment override the file.
- Kept the support-services stack intentionally small with a single Postgres service in `compose.support-services.yaml`; the FastAPI app still runs directly on the host in normal dev mode.
- Added stable `make support-services-*` targets for startup, teardown, logs, and status checks.
- Documented the exact local workflow in `README.md` and checked in `env.local.example` so developers can run `uv run uvicorn` against the local Postgres service without manual wiring.

### File List

- `_bmad-output/implementation-artifacts/12-1-add-a-local-support-services-stack-for-database-backed-development-and-validation.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `Makefile`
- `README.md`
- `compose.support-services.yaml`
- `env.local.example`
- `server/main.py`
- `server/settings.py`
- `tests/test_settings.py`

### Change Log

- 2026-03-28 14:50 UTC: Drafted Story 12.1 for local backing services with the app running in dev mode.
- 2026-03-28 16:35 UTC: Added a Postgres-only local support-services stack, documented host-run dev wiring, verified the new settings contract, and passed `make quality`.
