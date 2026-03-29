# Story 13.1: Add agent-facing match message inbox and send endpoints

Status: done

## Story

As an AI agent developer,
I want deterministic message send and inbox APIs for a match,
So that bots can coordinate publicly and privately through the same communication surface described in the game design.

## Acceptance Criteria

1. Given an active match and a valid player identity, when the player posts a world or direct message through the agent API, then the server stores it in deterministic order, returns a stable acceptance payload, and preserves exact sender, recipients, tick, and content data.
2. Given a player polls their message inbox, when the match contains world messages plus direct messages involving that player, then the response includes only the messages visible to that player, in stable chronological order, with enough metadata for agents to distinguish world chat from direct communication.
3. Given invalid messaging inputs such as unknown players, mismatched match IDs, unsupported direct-message recipients, or inbox polling against an unknown match, when the API handles the request, then it returns structured API errors without mutating stored message history.
4. Given the real running app quality workflow, when the message API story is implemented, then it includes behavior-first in-process API coverage plus at least one real-process integration or smoke flow covering visible message delivery.

## Tasks / Subtasks

- [x] Define the message contract and registry surface. (AC: 1, 2, 3)
  - [x] Introduce narrow API models for message reads and writes rather than leaking ad hoc dict payloads.
  - [x] Keep the first version intentionally small: world chat plus direct messages only.
  - [x] Use deterministic IDs/order and stable visibility filtering.
- [x] Implement in-memory message storage plus API endpoints. (AC: 1, 2, 3)
  - [x] Add `GET /api/v1/matches/{id}/messages` with player-scoped filtering.
  - [x] Add `POST /api/v1/matches/{id}/messages` with world/direct message support.
  - [x] Reject invalid requests without mutating message history.
- [x] Extend the quality harness at the API boundary. (AC: 4)
  - [x] Add behavior-first in-process API tests for send/list success and failure flows.
  - [x] Add at least one real-process integration or smoke journey covering visible message delivery.
  - [x] Re-run the repository quality gate after the story lands.

## Dev Notes

- Follow the design docs: world chat is visible to everyone; direct messages are visible only to sender and recipient.
- Defer group chat, treaty announcements, and state-payload inbox embedding to later stories unless they are the simplest way to satisfy this story.
- Preserve the current repo style of structured API errors and deterministic JSON ordering.
- Because the current database-backed runtime loads seeded match state into an in-memory registry at app startup, it is acceptable for the first message implementation to live in registry memory as long as the running-process tests still exercise the real HTTP boundary.
- This story should add or update real-process coverage per the existing Epic 12 quality policy.

### Candidate Implementation Surface

- `server/models/api.py`
- `server/agent_registry.py`
- `server/main.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/e2e/test_api_smoke.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### References

- `core-plan.md` sections 7.1 and 9.2
- `core-architecture.md` sections 5.2 and 8 Phase 2
- `_bmad-output/planning-artifacts/epics.md` Story 13.1 acceptance criteria
- `AGENTS.md` guidance favoring behavior-first API tests and lean smoke coverage

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run --extra dev pytest --no-cov tests/api/test_agent_api.py -k message -q` (red: missing `/messages` routes and OpenAPI schemas)
- `uv run --extra dev pytest --no-cov tests/api/test_agent_api.py -k message -q` (green after adding contracts, registry storage, and endpoints)
- `uv run --extra dev pytest --no-cov tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py -k message -q`
- `make format`
- `make quality`
- `uv run --extra dev pytest --no-cov tests/api/test_agent_api.py -k \"messages and (requires_player_id or empty_content or openapi or rejects_invalid_requests or rejects_unknown_match)\" -q`
- `uv run --extra dev pytest --no-cov tests/api/test_agent_process_api.py -k message -q`
- `make quality`

### Completion Notes List

- Added deterministic agent-facing match messaging contracts for world and direct messages only.
- Added in-memory per-match message storage with stable integer `message_id` ordering and player-scoped visibility filtering.
- Added `GET /api/v1/matches/{match_id}/messages` and `POST /api/v1/matches/{match_id}/messages` with structured `ApiError` handling for unknown matches, unknown players, route/body match mismatches, and unsupported recipient combinations.
- Added narrow messages-only request-validation handling so missing `player_id` and malformed message bodies return structured `ApiErrorResponse` payloads instead of FastAPI's default `detail` envelope.
- Extended in-process API tests and real-process API coverage to verify visible-message filtering and acceptance payload stability.
- Preserved the current seeded database startup behavior by keeping runtime message history in registry memory after load.

### File List

- `server/models/api.py`
- `server/agent_registry.py`
- `server/main.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `_bmad-output/implementation-artifacts/13-1-add-agent-facing-match-message-inbox-and-send-endpoints.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-29 09:24 UTC: Drafted Story 13.1 for deterministic match messaging endpoints and quality-harness coverage.
- 2026-03-29 10:05 UTC: Added message API contracts, deterministic in-memory message storage, and FastAPI inbox/send endpoints for world and direct messages.
- 2026-03-29 10:12 UTC: Added in-process and real-process message API coverage, passed `make quality`, and marked Story 13.1 done.
- 2026-03-29 09:36 UTC: Followed up on pre-merge validation gaps so `/messages` request-validation failures now emit structured API errors and regression coverage.
