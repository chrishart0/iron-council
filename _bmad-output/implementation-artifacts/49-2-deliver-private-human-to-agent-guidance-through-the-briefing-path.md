# Story 49.2: Deliver private human-to-agent guidance through the briefing path

Status: done

## Story

As an authenticated human player guiding my agent,
I want to send private strategic guidance that reaches the agent on its next briefing,
So that guided play can influence behavior without impersonating public game messages.

## Acceptance Criteria

1. Given an owned agent and a guidance message from its owner, when the agent requests its next briefing, then the response includes the new private guidance in a deterministic dedicated field or channel that is not confused with world, DM, or group chat traffic.
2. Given no new guidance exists, when the briefing is requested, then the existing briefing contract remains stable and the new guidance field stays empty rather than inventing placeholder content.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add a small typed guidance contract and persistence/read seams so private owner-to-agent guidance is stored separately from public/direct/group chat traffic.
- [x] Add a human-authenticated owned-agent guidance write route that enforces ownership, match membership, and deterministic tick semantics without widening access.
- [x] Extend the agent briefing contract, SDK types, and focused smoke/contract coverage so new guidance appears in a dedicated field while the empty-state response remains additive and stable.
- [x] Re-run focused verification plus the repo quality gate, then update BMAD closeout artifacts with the real final commands and outcomes.

## Dev Notes

- Keep this story strictly about private guidance delivery. Do not add override precedence, browser controls, or public/chat-message impersonation semantics here.
- Guidance must stay separate from existing `messages.direct`, `messages.group`, and `messages.world` so agents can distinguish owner whispers from gameplay communication.
- Reuse the explicit human-user -> owned API key -> agent participant ownership path from Story 49.1; do not authorize via broad user/display-name heuristics.
- Prefer deterministic ordering and additive contract changes. The zero-guidance path should serialize an empty list/default rather than placeholder prose.

### References

- `core-plan.md#9.1 Bring Your Own Agent`
- `core-plan.md#9.2 API Contract`
- `_bmad-output/planning-artifacts/epics.md#Story 49.2: Deliver private human-to-agent guidance through the briefing path`
- `_bmad-output/implementation-artifacts/49-1-add-an-owned-agent-guided-session-read-model.md`
- `server/api/authenticated_read_routes.py`
- `server/api/authenticated_write_routes.py`
- `server/models/api.py`
- `agent-sdk/python/iron_council_client.py`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-03: Drafted Story 49.2 to add private guided-agent whispers as a dedicated briefing surface after Story 49.1 established owned-agent guided-session reads.
- 2026-04-03: Added focused route-level regression coverage for owned-agent guidance fallback/error branches and re-ran the full repository quality gate to restore Python coverage above the 95.00% requirement.

## Debug Log References

- `source .venv/bin/activate && pytest tests/api/test_agent_api.py -k 'guidance_write_returns_not_found_mismatch_and_unavailable_errors or keeps_guidance_empty_when_agent_owner_cannot_be_resolved_from_db or support_db_url_fallback_without_session_factory' --no-cov`
- `source .venv/bin/activate && make quality`

## Completion Notes

- Added focused public-boundary API tests for Story 49.2 guidance behavior without changing production code.
- Covered briefing empty-guidance fallback when owner lookup cannot resolve DB guidance for an authenticated agent.
- Covered owned-agent guidance write error contracts for DB-unavailable, missing-match, and route/payload match-id mismatch branches.
- Covered the DB-backed URL fallback path without a session factory by exercising owned-agent guidance write/read flows through the authenticated access router.
- `make quality` passed end to end; Python coverage finished at 95.13%.

## File List

- `alembic/versions/20260403_1900_owned_agent_guidance.py`
- `server/db/models.py`
- `server/db/guidance.py`
- `server/db/testing.py`
- `server/api/app_services.py`
- `server/api/authenticated_read_routes.py`
- `server/api/authenticated_write_routes.py`
- `server/models/api.py`
- `agent-sdk/python/iron_council_client.py`
- `tests/test_database_migrations.py`
- `tests/db/test_guidance.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/agent_sdk/test_python_client.py`
- `tests/e2e/test_api_smoke.py`
- `tests/e2e/test_agent_sdk_smoke.py`
- `_bmad-output/implementation-artifacts/49-2-deliver-private-human-to-agent-guidance-through-the-briefing-path.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
