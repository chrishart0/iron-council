# Story 14.1: Add X-API-Key authentication and an authenticated current-agent profile endpoint

Status: done

## Story

As an AI agent developer,
I want the server to resolve my identity from the `X-API-Key` header,
So that profile and join flows stop relying on client-supplied agent identifiers.

## Acceptance Criteria

1. Given a request to a secured agent endpoint without a valid active API key, when the server evaluates authentication, then it rejects the request with a structured `401` response and no domain mutation.
2. Given a valid API key for a seeded or DB-backed agent identity, when the authentication dependency runs, then it resolves a stable authenticated agent context without exposing raw key material in the API surface.
3. Given the architecture calls for `GET /api/v1/agent/profile`, when an authenticated agent requests that endpoint, then the API returns the profile for the caller's key owner with behavior-first coverage plus at least one running-process integration or smoke flow.
4. Given join/profile scaffolding now has a real auth boundary, when the story is implemented, then the contract stays intentionally narrow, avoids speculative billing or full human-auth work, and remains aligned with repo conventions.

## Tasks / Subtasks

- [x] Define the minimal authenticated agent contract. (AC: 1, 2, 3, 4)
  - [x] Add a small auth helper and request context model for the authenticated agent identity.
  - [x] Keep the surface narrow: agent API keys only, no Supabase JWT implementation yet.
  - [x] Use deterministic hashing/lookup rules that work for both seeded in-memory and DB-backed registries.
- [x] Extend registry loading with API-key metadata. (AC: 2, 4)
  - [x] Seed deterministic API-key mappings for the in-memory fixture registry used by API tests.
  - [x] Load DB-backed key ownership from the existing `api_keys` and `players` tables without leaking raw key values into read models.
  - [x] Reject inactive or unknown keys without mutating match or profile state.
- [x] Add secured API routes for authenticated agent access. (AC: 1, 2, 3)
  - [x] Add `GET /api/v1/agent/profile` using authenticated agent context from `X-API-Key`.
  - [x] Preserve the repo's structured `ApiErrorResponse` contract for authentication failures.
  - [x] Decide whether existing profile scaffolding should remain temporarily for compatibility or be replaced outright; document the choice in the story notes and tests.
- [x] Extend quality coverage at the API boundary. (AC: 1, 2, 3, 4)
  - [x] Add behavior-first in-process API tests for missing, invalid, inactive, and valid API-key flows.
  - [x] Add direct loader/registry coverage for DB-backed key ownership resolution.
  - [x] Add at least one real-process integration or smoke flow proving authenticated profile access through the running app command path.
  - [x] Re-run the repository quality gate after the story lands.

## Dev Notes

- Follow `core-architecture.md` section 5.1: agent auth should use `X-API-Key`, and the server should resolve the key to an agent identity without exposing the raw secret.
- Keep this story focused on agent auth only. Do not broaden scope into human JWT auth, billing, pricing, or full match authorization for every match-scoped route.
- Prefer the simplest deterministic scheme that keeps test fixtures readable and makes future real-key storage straightforward.
- Behavior-first tests should assert HTTP contracts and visible auth outcomes, not internal helper implementation details.

### Candidate Implementation Surface

- `server/main.py`
- `server/agent_registry.py`
- `server/db/registry.py`
- `server/db/testing.py`
- `server/models/api.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/test_agent_registry.py`
- `tests/test_db_registry.py`
- `tests/e2e/test_api_smoke.py`
- `_bmad-output/implementation-artifacts/14-1-add-x-api-key-authentication-and-an-authenticated-current-agent-profile-endpoint.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### References

- `core-plan.md` sections 8.2, 9.1, 9.2, and 9.3
- `core-architecture.md` sections 2.1, 3.1, 5.1, and 5.2
- `_bmad-output/planning-artifacts/epics.md` Story 14.1 acceptance criteria
- `AGENTS.md` guidance favoring behavior-first API tests and real-process verification

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Red phase: `uv run pytest -o addopts='' tests/test_agent_registry.py -k 'authenticated_agent or api_key'`
- Red phase: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'api_keys or auth'`
- Red phase: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'authenticated_agent_profile'`
- Red phase: `uv run pytest -o addopts='' tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py -k 'authenticated_current_agent_profile or current_agent_profile or missing_or_invalid_agent_api_keys'`
- Green verification: `uv run pytest -o addopts='' tests/test_agent_registry.py tests/test_db_registry.py`
- Green verification: `uv run pytest -o addopts='' tests/api/test_agent_api.py tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py`
- Quality gate: `uv sync --extra dev`
- Quality gate: `make quality`

### Completion Notes List

- Added deterministic SHA-256 API-key hashing plus a narrow authenticated-agent context model that resolves seeded in-memory and DB-backed agent identities from `X-API-Key` without exposing raw key material in responses.
- Added secured `GET /api/v1/agent/profile` with structured `401` errors for missing, invalid, and inactive keys while keeping the existing `/api/v1/agents/{agent_id}/profile` route temporarily for compatibility; Story 14.2 remains responsible for removing client-supplied identity from join and match-scoped flows.
- Extended the in-memory registry and DB registry loader to carry authenticated key ownership metadata derived from seeded fixtures and persisted `api_keys`/`players` rows.
- Added behavior-first API, registry, running-process integration, and smoke coverage for authenticated current-agent profile access, then passed `make quality` with 202 tests green and 95.43% coverage.

### File List

- `server/auth.py`
- `server/models/api.py`
- `server/agent_registry.py`
- `server/db/registry.py`
- `server/db/testing.py`
- `server/main.py`
- `tests/test_agent_registry.py`
- `tests/test_db_registry.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/e2e/test_api_smoke.py`
- `_bmad-output/implementation-artifacts/14-1-add-x-api-key-authentication-and-an-authenticated-current-agent-profile-endpoint.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-29 14:12 UTC: Drafted Story 14.1 for API-key authentication and authenticated current-agent profile access.
- 2026-03-29 15:05 UTC: Implemented deterministic agent API-key authentication, authenticated current-agent profile access, DB-backed key ownership loading, and passing quality gates.
