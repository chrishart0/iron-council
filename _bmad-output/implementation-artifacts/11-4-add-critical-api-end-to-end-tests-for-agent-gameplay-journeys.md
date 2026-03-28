# Story 11.4: Add critical API end-to-end tests for agent gameplay journeys

Status: done

## Story

As an AI agent developer,
I want true API-level end-to-end tests,
So that the first agent workflows are validated through the actual FastAPI boundary instead of only lower-level helpers.

## Acceptance Criteria

1. Given seeded in-memory matches and the agent-facing endpoints, when end-to-end tests exercise match listing, fog-filtered state polling, order submission, and follow-up state reads, then the tests validate the critical happy-path agent journey through the real API surface.
2. Given invalid or mismatched requests, when the end-to-end suite submits them through the API, then it verifies structured rejection behavior without corrupting stored match or order state.
3. Given multiple players interacting with the same seeded match, when the end-to-end tests fetch visible state, then they verify that fog-of-war boundaries are preserved and one player cannot observe information forbidden by the visibility contract.

## Tasks / Subtasks

- [x] Define the minimum critical API journeys. (AC: 1, 2, 3)
  - [x] Cover list -> state poll -> order submit -> follow-up read as the core happy path.
  - [x] Cover unknown match/player IDs and mismatched order-envelope cases.
  - [x] Cover at least one multi-player visibility boundary check.
- [x] Implement end-to-end tests against the real FastAPI app boundary. (AC: 1, 2, 3)
  - [x] Seed the in-memory registry/reset state in a test-safe way with no cross-test leakage.
  - [x] Prefer API-contract assertions on status codes and JSON payloads over handler internals.
  - [x] Keep test flows deterministic and easy to read.
- [x] Wire the suite into normal verification. (AC: 1, 2, 3)
  - [x] Ensure the e2e tests can be run as a focused target and as part of broader quality checks.
  - [x] Verify the suite remains lightweight enough for regular development use.
  - [x] Re-run the repository quality gate after the e2e suite lands.

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

GPT-5 Codex

### Debug Log References

- Red phase: `uv run --extra dev pytest --no-cov tests/api/test_agent_api.py tests/api/test_health.py tests/api/test_metadata.py` failed because `AgentStateProjection` still exposed optional `match_id` in OpenAPI and stale tick submissions were still accepted.
- Focused verification: `uv run --extra dev pytest --no-cov tests/api/test_agent_api.py tests/api/test_health.py tests/api/test_metadata.py tests/test_fog.py`
- Formatting: `make format`
- Quality gate: `make quality`

### Completion Notes List

- Reworked the API-boundary match fixture into a richer multi-player scenario so tests now cover list -> fog-filtered state poll -> order submit -> follow-up read through the real FastAPI surface.
- Added API-level rejection coverage for unknown match/player IDs, route/body match mismatches, stale tick submissions, and malformed request validation without mutating stored submissions.
- Tightened the API state projection contract by making `match_id` required in `AgentStateProjection` and kept fog projection callers explicit about the match context.
- Added an autouse test fixture that resets the default in-memory registry around each test so FastAPI app state cannot leak across test cases.
- Kept runtime light by reusing the in-memory registry and a focused seeded match fixture; the targeted `--no-cov` suite completes in well under a second.

### File List

- `_bmad-output/implementation-artifacts/11-4-add-critical-api-end-to-end-tests-for-agent-gameplay-journeys.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/fog.py`
- `server/main.py`
- `server/models/fog.py`
- `tests/api/test_agent_api.py`
- `tests/conftest.py`
- `tests/test_fog.py`

### Change Log

- 2026-03-28 14:40 UTC: Drafted Story 11.4 for critical API end-to-end gameplay journeys.
- 2026-03-28 16:10 UTC: Added narrow API journey coverage, rejected stale tick submissions, tightened the state projection contract, isolated default registry state between tests, and re-ran the focused suite plus `make quality`.
