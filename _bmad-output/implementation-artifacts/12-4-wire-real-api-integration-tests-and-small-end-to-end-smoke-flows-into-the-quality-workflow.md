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

## Tasks / Subtasks

- [ ] Define the real-API integration test boundary and the smoke-level e2e scope. (AC: 1, 2, 4)
  - [ ] Require new user-facing stories to add or update real-API tests.
  - [ ] Keep the e2e layer intentionally small and focused on critical user flows.
  - [ ] Tie smoke flows back to user-facing acceptance behavior, ideally in clear scenario/gherkin-style language.
- [ ] Implement DB-backed integration test execution against the running app. (AC: 1, 3, 4)
  - [ ] Ensure the tests hit real running APIs, not just app-in-process stand-ins where full-stack validation is needed.
  - [ ] Ensure each worktree can run the suite without colliding with siblings.
  - [ ] Keep runtime practical enough for frequent use.
- [ ] Add and maintain a small e2e smoke suite for critical user journeys. (AC: 2, 4)
  - [ ] Cover enough high-value user flows to give real confidence, but do not explode into hundreds of brittle tests.
  - [ ] Ensure smoke flows validate visible outcomes meaningful to users.
  - [ ] Re-run the repository quality gate after the new test layers land.

## Dev Notes

- This story is about validating the app actually works when running, not merely proving helpers behave in isolation.
- Favor real API validation first, then a small e2e smoke layer for the most important journeys.
- Keep the e2e suite lean, durable, and tied to user-facing value.

### References

- `_bmad-output/planning-artifacts/epics.md` Story 12.4 acceptance criteria.
- Existing tests show good in-memory and app-boundary coverage, but not enough real running-API validation.

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

- 2026-03-28 14:57 UTC: Drafted Story 12.4 for real-API integration testing and a small smoke-level e2e suite.
