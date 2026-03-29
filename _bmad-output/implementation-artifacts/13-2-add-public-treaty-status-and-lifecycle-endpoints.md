# Story 13.2: Add public treaty status and lifecycle endpoints

Status: done

## Story

As an AI agent developer,
I want to inspect and change treaty status through the API,
So that diplomatic commitments and betrayals become visible, replayable, and actionable during a match.

## Acceptance Criteria

1. Given two players proposing, accepting, or withdrawing a treaty action, when the treaty API handles the request, then it records a deterministic treaty status transition with the documented treaty types and exposes the resulting treaty state through a stable read model.
2. Given treaty actions are public in the design, when a treaty is signed or withdrawn, then the API emits or records a corresponding world-visible announcement through the messaging surface instead of hiding the event in a private-only side channel.
3. Given repeated reads from the same match state, when clients fetch treaty status again, then they receive deterministic ordering and no duplicate side effects.
4. Given invalid treaty actions such as unknown matches, unknown players, mismatched route/body match IDs, self-targeted treaties, unsupported transitions, or withdrawals for treaties that do not exist, when the API rejects the request, then it returns structured API errors without mutating treaty state.
5. Given the real running app quality workflow, when the treaty API story is implemented, then it includes behavior-first in-process API coverage plus at least one real-process integration or smoke flow covering treaty reads and public treaty announcements.

## Tasks / Subtasks

- [x] Define narrow treaty API contracts and deterministic ordering rules. (AC: 1, 3, 4)
  - [x] Add explicit read/write models for treaty lifecycle actions and treaty status views.
  - [x] Reuse the documented treaty types (`non_aggression`, `defensive`, `trade`) and expose deterministic player ordering.
  - [x] Keep lifecycle scope intentionally narrow: propose/accept/withdraw only.
- [x] Extend the in-memory match registry with treaty storage and public announcements. (AC: 1, 2, 3, 4)
  - [x] Store per-match treaties with stable integer IDs and deterministic read ordering.
  - [x] Record public world-chat announcement messages when a treaty becomes active or withdrawn.
  - [x] Reject invalid lifecycle actions without hidden mutation or duplicate side effects.
- [x] Add treaty REST endpoints and structured error handling. (AC: 1, 3, 4)
  - [x] Add `GET /api/v1/matches/{match_id}/treaties` for stable treaty status reads.
  - [x] Add `POST /api/v1/matches/{match_id}/treaties` for propose/accept/withdraw requests.
  - [x] Preserve the repo's structured `ApiErrorResponse` contract for domain and validation failures.
- [x] Extend quality coverage at the API boundary. (AC: 5)
  - [x] Add behavior-first in-process API tests for happy paths, stable rereads, public announcement visibility, and failure cases.
  - [x] Add at least one real-process integration or smoke flow covering treaty lifecycle actions through the running app.
  - [x] Re-run the repository quality gate after the story lands.

## Dev Notes

- Follow the design docs: treaty state is public, treaty breaks/withdrawals are world-visible, and treaty history is part of player reputation.
- Keep this story intentionally small by treating treaty actions as API-layer state transitions over the current in-memory registry rather than introducing diplomacy resolution inside the tick engine.
- Preserve deterministic ordering by normalizing treaty party order and returning stable list ordering across repeated reads.
- Reuse the existing messaging surface for public announcements instead of inventing a second announcement channel.
- Do not broaden scope into alliance membership, group chats, or persistent auth/billing work; those belong to later stories.

### Candidate Implementation Surface

- `server/models/api.py`
- `server/agent_registry.py`
- `server/main.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/e2e/test_api_smoke.py`
- `_bmad-output/implementation-artifacts/13-2-add-public-treaty-status-and-lifecycle-endpoints.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### References

- `core-plan.md` sections 7.2, 7.3, and 9.2
- `core-architecture.md` sections 3.1, 5.2, and 8 Phase 2
- `_bmad-output/planning-artifacts/epics.md` Story 13.2 acceptance criteria
- `AGENTS.md` guidance favoring behavior-first API tests and lean smoke coverage

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest --no-cov tests/api/test_agent_api.py -k 'post_messages_rejects_stale_and_future_ticks or post_treaties_maps_validation_failures'`
- `uv run pytest --no-cov tests/api/test_agent_process_api.py -k 'stale_and_future_messages'`
- `make quality`

### Completion Notes List

- Added a `tick_mismatch` guard to `POST /api/v1/matches/{match_id}/messages` so message posting now matches the current-tick contract already used by orders and treaty lifecycle APIs.
- Added behavior-first regression coverage for stale and future message ticks in both the in-process API suite and the running-app process suite, asserting structured errors and no message mutation.
- Added focused treaty validation tests covering invalid action, invalid treaty type, and missing required fields to lock in the custom `ApiErrorResponse` 422 mapping.
- Re-ran the focused regressions and `make quality`; the full local gate passed.

### File List

- `server/agent_registry.py`
- `server/main.py`
- `server/models/api.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `_bmad-output/implementation-artifacts/13-2-add-public-treaty-status-and-lifecycle-endpoints.md`

### Change Log

- 2026-03-29 10:18 UTC: Drafted Story 13.2 for deterministic treaty lifecycle APIs and public announcement coverage.
- 2026-03-29 10:32 UTC: Completed Story 13.2 implementation, including reviewer follow-up coverage for message tick validation and treaty request 422 mappings.
