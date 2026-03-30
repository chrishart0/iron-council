# Story 22.1: Add an authenticated lobby start endpoint

Status: done

## Story

As an authenticated lobby creator,
I want to start a ready lobby through the API,
So that a DB-created match can transition from browseable lobby state into a live active match with the real runtime loop.

## Acceptance Criteria

1. Given an authenticated creator has a lobby with enough joined players, when `POST /api/v1/matches/{match_id}/start` is called, then the server validates creator ownership and readiness rules, transitions the match status from `lobby` to `active`, and returns compact post-start metadata.
2. Given DB-backed mode is active, when the start succeeds, then the server durably persists the status transition and any required match metadata updates so the running app can observe the match as active without reseeded fixtures.
3. Given the caller is not the creator, the lobby is not ready, or the match is already active/completed, when the start route is called, then the server returns structured domain errors and does not partially transition the match.
4. Given the newly started match enters the runtime flow, when the real-process app is running, then a focused smoke proves the match becomes active and is eligible for the existing tick/runtime path without regressing public browse/detail reads.
5. Given the story ships, when focused unit/API/e2e checks and the repo quality gate run, then the start contract is proven from the public boundary.

## Tasks / Subtasks

- [x] Add narrow authenticated start-lobby request/response models plus creator/readiness domain validation rules. (AC: 1, 3)
- [x] Add a DB-backed lobby start helper that verifies creator ownership from persisted join mappings and writes the status transition atomically. (AC: 1, 2, 3)
- [x] Expose `POST /api/v1/matches/{match_id}/start` through the authenticated API with compact post-start metadata. (AC: 1, 2)
- [x] Add focused DB/API/e2e coverage for success, creator-only enforcement, readiness failures, and runtime eligibility. (AC: 3, 4, 5)
- [x] Update BMAD/source docs, run simplification/review, and pass `make quality`. (AC: 5)

## Dev Notes

- Reuse the existing DB-backed registry/runtime flow rather than inventing a second active-match bootstrap path.
- Keep the public response compact; browse/detail/state surfaces already exist for deeper reads.
- Treat creator ownership as persisted domain state, not a client-supplied field.
- Prefer a small readiness rule for the first cut: enough joined players to make the lobby legitimately startable, with deterministic structured errors for not-ready cases.

## Implementation Plan

- Plan file: `docs/plans/2026-03-30-story-22-1-authenticated-lobby-start.md`
- Parallelism assessment: sequential implementation because persistence, auth/ownership checks, route wiring, and runtime verification all share one lifecycle seam.
- Verification target: focused DB/API/e2e commands, then `make quality`.


## Dev Agent Record

### Agent Model Used

GPT-5 Codex + Hermes follow-up verification/fix pass

### Debug Log References

- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'start_match_lobby'`
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'start_match_lobby'`
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'start_match_lobby'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'start_match_lobby or create_match_lobby'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'start_match_lobby or create_match_lobby'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'start_match_lobby or create_match_lobby'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'start_match_lobby or create_match_lobby or runtime'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'start_match_lobby'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'start_match_lobby or create_match_lobby'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'create_match_lobby_route_rejects_missing_auth_and_memory_mode'`
- GREEN: `make quality`

### Completion Notes List

- Added a compact authenticated `POST /api/v1/matches/{match_id}/start` contract that promotes ready DB-backed lobbies to `active`.
- Persisted creator ownership in match config during lobby creation, then enforced creator-only start authorization from persisted state rather than client input.
- Added deterministic readiness validation requiring at least two joined players before start and returned structured domain errors for not-ready, forbidden, active, and completed cases.
- Built the started match record directly from the active DB session after persistence so the route can return success without depending on a second full-registry reload.
- Extended the in-process runtime with on-demand match scheduling so a lobby started after app boot enters the existing tick loop immediately.
- Added DB, API, and real-process smoke coverage proving the started lobby becomes active, remains visible in browse/detail reads, and advances into the runtime tick path.
- Added narrowly scoped coverage tests for DB invalid-key/missing-match/non-startable/same-user-different-key/no-registry-reload branches, API unavailable/missing-auth/not-found/conflict branches, and runtime no-op/dedupe behavior to lift total coverage above the repository threshold without widening story scope.
- `make quality` now passes with total coverage at `95.15%`.
- Updated source/BMAD architecture docs plus sprint/story tracking for the shipped endpoint.

### File List

- _bmad-output/implementation-artifacts/22-1-add-an-authenticated-lobby-start-endpoint.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- _bmad-output/planning-artifacts/architecture.md
- core-architecture.md
- server/db/registry.py
- server/main.py
- server/models/api.py
- server/runtime.py
- tests/api/test_agent_api.py
- tests/e2e/test_api_smoke.py
- tests/support.py
- tests/test_db_registry.py
