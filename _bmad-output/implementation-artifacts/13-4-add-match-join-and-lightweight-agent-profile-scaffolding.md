# Story 13.4: Add match join and lightweight agent profile scaffolding

Status: done

## Story

As an AI agent developer,
I want a minimal join/profile surface,
So that Phase 2 API completeness improves without blocking on the full production authentication and billing stack.

## Acceptance Criteria

1. Given a lobby or joinable match record, when an agent requests to join, then the API exposes a minimal deterministic join contract or a clear not-yet-joinable rejection path consistent with repo conventions.
2. Given the architecture calls for agent profile visibility, when the lightweight profile endpoint is introduced, then it returns a stable placeholder or DB-backed rating/history shape that can evolve later without breaking clients.
3. Given these surfaces remain early-phase scaffolding, when they are implemented, then they stay intentionally narrow, avoid speculative auth/billing complexity, and remain covered by behavior-first tests.

## Tasks / Subtasks

- [x] Define minimal join/profile API contracts. (AC: 1, 2, 3)
  - [x] Add explicit read/write models for match join requests/responses and lightweight agent profile responses.
  - [x] Keep join scope narrow: deterministic success for joinable seeded cases or a clear structured rejection path.
  - [x] Keep profile scope narrow: stable rating/history placeholder fields that can evolve later.
- [x] Extend the in-memory registry with minimal join/profile support. (AC: 1, 2)
  - [x] Represent joinability without introducing speculative auth or billing machinery.
  - [x] Return deterministic profile data for known agent/player identities.
  - [x] Reject unsupported or unknown cases without mutating unrelated match state.
- [x] Add join/profile REST endpoints and structured error handling. (AC: 1, 2, 3)
  - [x] Add a match join endpoint under `/api/v1/matches/{match_id}`.
  - [x] Add a lightweight profile read endpoint under `/api/v1/agents` or equivalent repo-consistent path.
  - [x] Preserve the repo's structured `ApiErrorResponse` contract for domain and validation failures.
- [x] Extend quality coverage at the API boundary. (AC: 3)
  - [x] Add behavior-first in-process API tests for happy paths and failure cases.
  - [x] Add at least one running-app integration or smoke flow through the real app command path.
  - [x] Re-run the repository quality gate after the story lands.

## Dev Notes

- Follow the design docs: agents should have a stable API surface, but this story is scaffolding and should not invent the full auth, billing, or matchmaking stack.
- Prefer the smallest contract that improves API completeness while staying compatible with later DB-backed identity and ELO work.
- Keep repeated reads deterministic and avoid implementation-detail-only tests.
- Do not broaden scope into full player onboarding, account linking, or post-match ELO calculation.

### Candidate Implementation Surface

- `server/models/api.py`
- `server/agent_registry.py`
- `server/db/registry.py`
- `server/main.py`
- `tests/test_agent_registry.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/e2e/test_api_smoke.py`
- `_bmad-output/implementation-artifacts/13-4-add-match-join-and-lightweight-agent-profile-scaffolding.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### References

- `core-plan.md` sections 8.2, 9.1, and 9.2
- `core-architecture.md` sections 2.1, 3.1, 3.3, and 5.2
- `_bmad-output/planning-artifacts/epics.md` Story 13.4 acceptance criteria
- `AGENTS.md` guidance favoring behavior-first API tests and lean smoke coverage

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py`
- `uv run ruff check .`
- `uv run mypy`
- `uv run pytest -q`

### Completion Notes List

- Added deterministic `POST /api/v1/matches/{match_id}/join` and `GET /api/v1/agents/{agent_id}/profile` endpoints with structured validation and domain error responses.
- Extended both the in-memory and DB-backed match registries with lightweight agent-profile scaffolding plus deterministic join-slot assignment.
- Restricted DB-backed profile exposure to persisted agent identities and added behavior-first coverage for non-agent rejection paths.
- Verified the story through focused API/registry tests, real running-app smoke coverage, Ruff, mypy, and the full pytest suite at 95.43% total coverage.

### File List

- `server/models/api.py`
- `server/agent_registry.py`
- `server/db/registry.py`
- `server/main.py`
- `tests/test_agent_registry.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/e2e/test_api_smoke.py`

### Change Log

- 2026-03-29 11:10 UTC: Drafted Story 13.4 for minimal match-join and agent-profile scaffolding.
- 2026-03-29 13:35 UTC: Implemented deterministic join/profile scaffolding, DB-backed agent filtering, and passing quality gates.
