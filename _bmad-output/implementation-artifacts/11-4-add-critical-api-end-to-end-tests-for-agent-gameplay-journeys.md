# Story 11.4: Add critical API end-to-end tests for agent gameplay journeys

Status: drafted

## Story

As an AI agent developer,
I want true API-level end-to-end tests,
So that the first agent workflows are validated through the actual FastAPI boundary instead of only lower-level helpers.

## Acceptance Criteria

1. Given seeded in-memory matches and the agent-facing endpoints, when end-to-end tests exercise match listing, fog-filtered state polling, order submission, and follow-up state reads, then the tests validate the critical happy-path agent journey through the real API surface.
2. Given invalid or mismatched requests, when the end-to-end suite submits them through the API, then it verifies structured rejection behavior without corrupting stored match or order state.
3. Given multiple players interacting with the same seeded match, when the end-to-end tests fetch visible state, then they verify that fog-of-war boundaries are preserved and one player cannot observe information forbidden by the visibility contract.

## Tasks / Subtasks

- [ ] Define the minimum critical API journeys. (AC: 1, 2, 3)
  - [ ] Cover list -> state poll -> order submit -> follow-up read as the core happy path.
  - [ ] Cover unknown match/player IDs and mismatched order-envelope cases.
  - [ ] Cover at least one multi-player visibility boundary check.
- [ ] Implement end-to-end tests against the real FastAPI app boundary. (AC: 1, 2, 3)
  - [ ] Seed the in-memory registry/reset state in a test-safe way with no cross-test leakage.
  - [ ] Prefer API-contract assertions on status codes and JSON payloads over handler internals.
  - [ ] Keep test flows deterministic and easy to read.
- [ ] Wire the suite into normal verification. (AC: 1, 2, 3)
  - [ ] Ensure the e2e tests can be run as a focused target and as part of broader quality checks.
  - [ ] Verify the suite remains lightweight enough for regular development use.
  - [ ] Re-run the repository quality gate after the e2e suite lands.

## Dev Notes

- This repo currently appears to have only basic API contract coverage, so keep the first e2e suite intentionally narrow and high value.
- Favor realistic agent workflows over exhaustive endpoint permutation testing.
- Reuse Story 10.1 fog projection and Story 10.2 in-memory registry behavior rather than building parallel test-only abstractions.

### References

- `tests/api/test_health.py` and `tests/api/test_metadata.py` for current FastAPI boundary testing style.
- `_bmad-output/implementation-artifacts/10-1-project-fog-filtered-agent-state-from-canonical-match-data.md`.
- `_bmad-output/implementation-artifacts/10-2-expose-in-memory-agent-match-listing-state-polling-and-order-submission-endpoints.md`.
- `_bmad-output/planning-artifacts/epics.md` Story 11.4 acceptance criteria.

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

- 2026-03-28 14:40 UTC: Drafted Story 11.4 for critical API end-to-end gameplay journeys.
