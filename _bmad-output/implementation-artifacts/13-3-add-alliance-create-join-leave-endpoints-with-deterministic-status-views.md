# Story 13.3: Add alliance create/join/leave endpoints with deterministic status views

Status: done

## Story

As an AI agent developer,
I want to create alliances, apply to them, and inspect membership through the API,
So that coalition structure can evolve through explicit public actions rather than only out-of-band assumptions.

## Acceptance Criteria

1. Given a player creates an alliance or changes membership, when the alliance API handles the request, then it returns a stable alliance status view with deterministic member ordering, leader identity, and join metadata.
2. Given alliance membership affects shared vision and shared victory semantics, when alliance state changes are exposed through the API, then the resulting read model aligns with the canonical player `alliance_id` state used elsewhere in the engine.
3. Given invalid alliance actions such as joining an unknown alliance or leaving a match that does not exist, when the API rejects the request, then it does so with structured errors and no hidden mutation.
4. Given the real running app quality workflow, when the alliance API story is implemented, then it includes behavior-first in-process API coverage plus at least one real-process integration or smoke flow covering alliance reads and membership changes.

## Tasks / Subtasks

- [x] Define narrow alliance API contracts and deterministic ordering rules. (AC: 1, 3)
  - [x] Add explicit read/write models for alliance lifecycle actions and alliance status views.
  - [x] Expose deterministic alliance ordering plus deterministic member ordering within each alliance.
  - [x] Keep lifecycle scope intentionally narrow: create, join, and leave only.
- [x] Extend the in-memory match registry with alliance storage aligned to canonical player state. (AC: 1, 2, 3)
  - [x] Store per-match alliance metadata with deterministic IDs for newly created alliances.
  - [x] Hydrate deterministic read models from existing canonical `players[*].alliance_id` state when explicit alliance metadata is absent.
  - [x] Update canonical player `alliance_id` values on successful create/join/leave actions so fog and victory logic stay aligned.
- [x] Add alliance REST endpoints and structured error handling. (AC: 1, 3)
  - [x] Add `GET /api/v1/matches/{match_id}/alliances` for stable alliance status reads.
  - [x] Add `POST /api/v1/matches/{match_id}/alliances` for create/join/leave requests.
  - [x] Preserve the repo's structured `ApiErrorResponse` contract for domain and validation failures.
- [x] Extend quality coverage at the API boundary. (AC: 4)
  - [x] Add behavior-first in-process API tests for happy paths, stable rereads, canonical membership updates, and failure cases.
  - [x] Add a real-process integration flow covering alliance creation, joining, deterministic reads, and updated fog-sharing state.
  - [x] Re-run the repository quality gate after the story lands.

## Dev Notes

- Follow the design docs: alliances are public, affect shared fog of war, and determine coalition victory grouping through canonical player membership.
- Keep this story intentionally small by treating alliance actions as API-layer state transitions over the current in-memory registry rather than adding full diplomacy workflow to the tick engine.
- The GDD mentions leader approval for new members. To keep the v1 surface narrow and deterministic without inventing an approval queue or invitation workflow, this story documents and tests an immediate public `join` action. The alliance read model still preserves explicit `leader_id`, so a later story can tighten join semantics without changing the status shape.
- Preserve deterministic reads by sorting alliances by `alliance_id` and members by `player_id`.
- Do not broaden scope into alliance chat, approval inboxes, auth/billing work, or treaty/message refactors.

### Candidate Implementation Surface

- `server/models/api.py`
- `server/agent_registry.py`
- `server/main.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `_bmad-output/implementation-artifacts/13-3-add-alliance-create-join-leave-endpoints-with-deterministic-status-views.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### References

- `core-plan.md` sections 6.4, 7.3, 8.1, and 9.2
- `core-architecture.md` sections 3.1, 3.2, 3.3, and Phase 2 Server & API
- `_bmad-output/planning-artifacts/epics.md` Story 13.3 acceptance criteria
- `AGENTS.md` guidance favoring behavior-first API tests and a real quality gate

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `./.venv/bin/pytest --no-cov tests/api/test_agent_api.py tests/api/test_agent_process_api.py -k alliance -q` (red, before implementation)
- `./.venv/bin/pytest --no-cov tests/api/test_agent_api.py tests/api/test_agent_process_api.py -k alliance -q`
- `./.venv/bin/pytest --no-cov tests/test_db_registry.py tests/api/test_agent_api.py tests/api/test_agent_process_api.py -q`
- `./.venv/bin/pytest --no-cov tests/api/test_agent_api.py tests/api/test_agent_process_api.py -q`
- `./.venv/bin/pytest --no-cov tests/test_db_registry.py tests/test_agent_registry.py -q` (red, before correctness fix)
- `./.venv/bin/pytest --no-cov tests/test_db_registry.py tests/test_agent_registry.py -q`
- `./.venv/bin/pytest --no-cov tests/api/test_agent_api.py tests/api/test_agent_process_api.py -k alliance -q`
- `make format`
- `make quality`

### Completion Notes List

- Added explicit alliance lifecycle and read models plus `GET` and `POST /api/v1/matches/{match_id}/alliances` routes following the repo's existing structured API pattern.
- Extended the in-memory registry with deterministic alliance metadata, derived seeded alliance views from canonical player membership when needed, and updated canonical `players[*].alliance_id` on create/join/leave so fog and coalition-victory semantics remain aligned.
- Added behavior-first in-process coverage for deterministic reads, canonical membership updates, invalid no-mutation cases, and OpenAPI response contracts.
- Added a real running-app integration flow covering alliance creation, joining, public status reads, and updated shared-vision state.
- Tightened the alliance write contract so contradictory action fields are rejected with structured validation errors, and added direct DB-loader coverage to preserve persisted alliance name and tick metadata while falling back safely when persisted rows do not match canonical state.
- Documented the intentionally narrow v1 contract choice: `join` is immediate and public for now, while the read model still preserves `leader_id` for a later approval-focused increment.
- Replaced persisted alliance metadata zipping with membership-set reconciliation plus canonical leader/member mapping so multi-alliance DB loads cannot swap names, leader identity, or join ticks across alliances.
- Aligned in-memory `_sync_victory_state()` initialization with resolver countdown semantics for alliance membership changes, and added focused regression coverage for the exact review failures.

### File List

- `server/models/api.py`
- `server/agent_registry.py`
- `server/main.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/test_db_registry.py`
- `tests/test_agent_registry.py`
- `_bmad-output/implementation-artifacts/13-3-add-alliance-create-join-leave-endpoints-with-deterministic-status-views.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-29 11:17 UTC: Drafted Story 13.3 for deterministic alliance lifecycle/status APIs.
- 2026-03-29 11:17 UTC: Completed Story 13.3 implementation with canonical membership updates, deterministic reads, and API/process coverage.
- 2026-03-29 11:26 UTC: Applied post-review blocker fixes for victory-state synchronization, DB-backed alliance metadata loading, stricter action validation, and added loader coverage to keep the quality gate green.
- 2026-03-29 UTC: Applied final correctness fixes for persisted alliance reconciliation and in-memory victory countdown initialization, added focused regression coverage, and re-ran the full quality gate.
