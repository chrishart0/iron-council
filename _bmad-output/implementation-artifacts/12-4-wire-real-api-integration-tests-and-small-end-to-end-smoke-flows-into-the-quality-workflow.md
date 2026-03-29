# Story 12.4: Wire real API integration tests and small end-to-end smoke flows into the quality workflow

Status: drafted

## Story

As a delivery lead,
I want real API integration tests and a small set of high-value end-to-end smoke flows to become part of the normal quality bar,
So that we stop shipping large amounts of unvalidated code that has never run against a real database-backed environment.

## Acceptance Criteria

1. Given the local support-services stack, migration workflow, and seed/reset tooling, when integration and end-to-end suites run, then they execute against the real running app and database boundaries instead of only in-memory stand-ins.
2. Given user-facing stories, when they are completed, then each story adds or updates appropriate real-API coverage and contributes to a small smoke-level set of high-value end-to-end user flows rather than an excessive e2e suite.
3. Given developers and autonomous workers running checks in parallel, when the quality workflow executes per worktree, then each lane can run the relevant DB-backed tests without shared-state interference.
4. Given the repository quality workflow and CI configuration, when the new test layers are introduced, then the project has clear command targets and an enforceable quality gate for real-API validation plus a maintainable smoke-level e2e suite.
5. Given Story 11.4 already introduced in-process FastAPI journey coverage, when this story is implemented, then it extends validation to a real running process and real database-backed state rather than duplicating the same ASGITransport-only coverage.
6. Given the repository is still backend-first today, when the first smoke suite is defined, then it may remain API-driven or minimal-browser in shape as long as it validates real user-facing outcomes through the running app boundary.

## Tasks / Subtasks

- [ ] Define the real-API integration test boundary and the smoke-level e2e scope. (AC: 1, 2, 4, 5, 6)
  - [ ] Distinguish clearly between existing in-process API coverage and the new real-process validation layer.
  - [ ] Keep the e2e layer intentionally small and focused on critical user flows.
  - [ ] Tie smoke flows back to user-facing acceptance behavior in readable scenario language.
- [ ] Implement DB-backed integration test execution against the running app. (AC: 1, 3, 4, 5)
  - [ ] Boot the app as a real process for the relevant tests.
  - [ ] Ensure tests hit real HTTP endpoints rather than only ASGI in-process transports where full-stack validation is needed.
  - [ ] Ensure each worktree can run the suite without colliding with siblings.
- [ ] Add and maintain a small smoke suite for critical user journeys. (AC: 2, 4, 6)
  - [ ] Cover enough high-value flows to give real confidence, but do not explode into a brittle suite.
  - [ ] Validate visible outcomes meaningful to API consumers and eventual human players.
  - [ ] Defer heavyweight browser coverage unless a real frontend surface exists that justifies it.
- [ ] Wire the new layer into local and CI quality workflows. (AC: 3, 4)
  - [ ] Add stable command targets for real-API checks and smoke checks.
  - [ ] Make the expected local prerequisite flow explicit.
  - [ ] Re-run the repository quality gate after the new test layers land.

## Dev Notes

- This story is about validating the app actually works when running, not merely proving helpers behave in isolation.
- Favor real API validation first, then a very small smoke layer for the most important journeys.
- Keep the smoke suite lean, durable, and tied to user-facing value.
- Story 11.4 already delivered valuable in-process API journey tests using the FastAPI app boundary. Do not throw that work away; build on it by adding the missing running-process and real-DB layer.
- Because the repo currently has no full Next.js client checked in, the first smoke flows do not need to be browser-heavy. A process-level HTTP journey suite is acceptable if it exercises real app startup, real DB-backed state, and meaningful end-user outcomes.
- This story depends on Story 12.3 for per-worktree DB isolation if we want autonomous parallel execution without collisions.

### Candidate Implementation Surface

- `tests/api/` for process-level HTTP integration suites
- `tests/` or `tests/e2e/` for smoke scenarios
- `tests/conftest.py` for running-app fixtures and DB-backed setup helpers
- `Makefile` for stable real-API/smoke commands
- `.github/workflows/quality.yml` for enforceable CI wiring
- `README.md` for the real local validation workflow

### References

- `_bmad-output/planning-artifacts/epics.md` Story 12.4 acceptance criteria.
- `_bmad-output/implementation-artifacts/11-4-add-critical-api-end-to-end-tests-for-agent-gameplay-journeys.md`
- `_bmad-output/implementation-artifacts/12-3-add-deterministic-seed-reset-tooling-and-per-worktree-isolated-test-databases.md`
- `AGENTS.md` guidance favoring real API coverage plus a small high-value smoke suite.

## Dev Agent Record

### Agent Model Used

_TBD_

### Debug Log References

- 2026-03-29: Local environment review confirmed the machine can now run Docker-backed Postgres and migrations, but the quality gate still relies on in-process API tests and does not boot the app as a real service.
- 2026-03-29: Review conclusion: Story 12.4 remains necessary even though Story 11.4 is done, because the missing layer is real-process, real-DB validation.

### Completion Notes List

- _TBD_

### File List

- _TBD_

### Change Log

- 2026-03-28 14:57 UTC: Drafted Story 12.4 for real-API integration testing and a small smoke-level e2e suite.
- 2026-03-29 05:55 UTC: Expanded Story 12.4 to clarify the distinction from Story 11.4 and to target real running-app, real-DB validation in the quality workflow.
