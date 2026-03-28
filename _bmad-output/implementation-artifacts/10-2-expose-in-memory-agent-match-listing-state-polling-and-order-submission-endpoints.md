# Story 10.2: Expose in-memory agent match listing, state polling, and order submission endpoints

Status: done

## Story

As an AI agent developer,
I want minimal REST endpoints for listing matches, polling my visible state, and submitting orders,
so that automated clients can drive headless matches before database-backed persistence lands.

## Acceptance Criteria

1. Given seeded in-memory matches, when the agent API lists matches, then it returns stable JSON summaries with match identity, status, and tick metadata suitable for polling clients.
2. Given a valid player in a seeded match, when the agent API fetches `/api/v1/matches/{id}/state`, then it returns the fog-filtered projection from Story 10.1 for that player and rejects unknown match or player IDs with structured HTTP errors.
3. Given valid and invalid order envelopes for a seeded match, when the agent API posts `/api/v1/matches/{id}/orders`, then it stores accepted submissions in deterministic in-memory order, echoes a stable acceptance payload, and rejects mismatched match IDs or unknown players without mutating stored submissions.

## Tasks / Subtasks

- [x] Add behavior-first API tests before implementation. (AC: 1, 2, 3)
  - [x] Cover stable match-list summaries from seeded in-memory data.
  - [x] Cover state polling success plus unknown match/player error contracts.
  - [x] Cover accepted order submission and rejection of mismatched/unknown envelopes without side effects.
- [x] Implement a small in-memory match registry and agent API router. (AC: 1, 2, 3)
  - [x] Keep scope to list/state/orders endpoints only; do not add Supabase auth, lobby joins, or websocket handling.
  - [x] Reuse Story 10.1 fog projection for state responses rather than duplicating visibility logic.
  - [x] Keep stored order submission order deterministic and easy to inspect in tests.
- [x] Re-verify API behavior after merge. (AC: 1, 2, 3)
  - [x] Re-run focused API coverage.
  - [x] Re-run the repository quality gate.

## Dev Notes

- Prefer API-boundary tests with `httpx.AsyncClient` over internal handler-only tests.
- Preserve the existing lightweight app scaffold and avoid speculative persistence abstractions.
- Keep the registry injectable/resettable so tests can seed matches without cross-test leakage.

### References

- `core-architecture.md` section 5.2 for the first agent REST endpoint set.
- `core-architecture.md` section 3.3 for the fog-filtered state payload intent.
- `_bmad-output/planning-artifacts/epics.md` Story 10.2 acceptance criteria.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Red phase: `PYTHONPATH=. pytest -o addopts='' tests/api/test_agent_api.py` failed during collection with `ModuleNotFoundError: No module named 'server.agent_registry'`.
- Environment sync: `make install`
- Focused API verification: `uv run pytest --no-cov tests/api/test_health.py tests/api/test_metadata.py tests/api/test_agent_api.py`
- Quality gate: `make quality`
- Follow-up red phase: `uv run pytest --no-cov tests/api/test_agent_api.py` failed because `/api/v1/matches/{match_id}/state` exposed an empty 200 response schema in OpenAPI while the new API-boundary test expected `AgentStateProjection`.
- Follow-up focused API verification: `uv run pytest --no-cov tests/api/test_agent_api.py`
- Follow-up quality gate: `make quality`
- Final narrow red phase: `uv run pytest --no-cov tests/api/test_agent_api.py -k structured_api_error_schemas` failed with `KeyError: '404'` because the state and orders endpoints did not declare structured `ApiErrorResponse` OpenAPI error schemas.
- Final narrow focused API verification: `uv run pytest --no-cov tests/api/test_health.py tests/api/test_metadata.py tests/api/test_agent_api.py`
- Final narrow quality gate: `make quality`

### Completion Notes List

- Added an injectable `InMemoryMatchRegistry` with deterministic per-match submission storage and reset/seed support for API-boundary tests.
- Added `GET /api/v1/matches`, `GET /api/v1/matches/{id}/state`, and `POST /api/v1/matches/{id}/orders` with stable JSON contracts and structured error payloads for unknown matches, unknown players, and mismatched route/body match IDs.
- Reused `server.fog.project_agent_state` for state polling so fog filtering stays in one deterministic implementation.
- Added behavior-first API tests covering list summaries, required `player_id`, fog-filtered state success, structured error contracts, accepted order submission, and rejection side-effect checks.
- Follow-up tightened the match-state endpoint to use FastAPI `response_model=AgentStateProjection`, added API-boundary coverage for the generated OpenAPI contract plus multi-post deterministic submission order and unknown-match order rejection, and constrained `OrderAcceptanceResponse.status` to the accepted literal contract.
- Final narrow follow-up declared structured `ApiErrorResponse` OpenAPI metadata for state/order endpoint 400/404 cases and added a focused API-boundary test covering those generated schemas without changing runtime error payloads.

### File List

- `_bmad-output/implementation-artifacts/10-2-expose-in-memory-agent-match-listing-state-polling-and-order-submission-endpoints.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/agent_registry.py`
- `server/main.py`
- `server/models/__init__.py`
- `server/models/api.py`
- `tests/api/test_agent_api.py`

### Change Log

- 2026-03-28 14:25 UTC: Drafted Story 10.2 for in-memory agent list/state/orders endpoints.
- 2026-03-28 14:45 UTC: Implemented the in-memory agent API endpoints, added behavior-first API coverage, and passed `make quality`.
- 2026-03-28 15:05 UTC: Applied a narrow follow-up fix to return `AgentStateProjection` through FastAPI response-model validation/OpenAPI generation, extended API-boundary order coverage, and re-ran `make quality`.
- 2026-03-28 15:12 UTC: Added OpenAPI `ApiErrorResponse` metadata for the state/order endpoint 400/404 contracts, covered the generated schemas with a focused API test, and re-ran focused API checks plus `make quality`.
