# Story 49.1: Add an owned-agent guided-session read model

Status: done

## Story

As an authenticated human player who owns an agent,
I want a guided-session read surface for that agent in a live match,
So that I can see the current visible state, queued actions, and recent agent activity before intervening.

## Acceptance Criteria

1. Given the authenticated human owns an agent participant in a match, when the guided-session route is requested, then it returns a player-safe snapshot, the current queued orders/messages, and concise recent activity for that owned agent without widening visibility beyond the agent's normal fog-of-war envelope.
2. Given the caller does not own the target agent or the agent is not in the requested match, when the same route is requested, then the API returns a structured auth or ownership error rather than leaking cross-account guided state.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add a small typed guided-session response model that reuses existing player-safe state, message, and order contracts instead of inventing a second visibility surface.
- [x] Add human-authenticated route coverage proving an owner can read guided state for an owned agent, while non-owners, wrong-match requests, and malformed auth fail with structured errors.
- [x] Reuse current registry/read seams for queued orders, visible chats/messages, and recent treaty/alliance activity so the first read model stays additive and billing/guidance-write work can layer on later.
- [x] Re-run focused verification plus the repo quality gate, then update BMAD closeout artifacts with the real final commands and outcomes.

## Dev Notes

- Keep this story contract-first and read-only. Do not add guidance writes, override semantics, or browser UI here.
- Prefer reusing the existing `AgentBriefingResponse`-adjacent read seams so guided mode reflects the agent's real fog-of-war and visible communication surfaces.
- The ownership check should be explicit on the human-user -> owned API key -> agent participant boundary. Do not authorize through broad shared display-name or player-name heuristics.
- Keep the initial activity summary small and deterministic. It only needs enough recent context to support later guidance/override stories.

### References

- `core-plan.md#9.1 Bring Your Own Agent`
- `core-plan.md#9.2 Human vs. Agent vs. Guided Play`
- `_bmad-output/planning-artifacts/epics.md#Story 49.1: Add an owned-agent guided-session read model`
- `server/api/authenticated_read_routes.py`
- `server/api/app_services.py`
- `server/models/api.py`
- `server/agent_registry.py`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-03: Drafted Story 49.1 as the first Guided Agent Mode increment after Epic 48 completed the BYOA ownership and entitlement seams.
- 2026-04-03: Implemented the owned-agent guided-session read route, DB ownership lookup, focused regression coverage, and green quality gate.
- 2026-04-03: Corrected reviewer-found scope gap so guided-session `recent_activity` is limited to the owned player's current alliance and recent treaties involving that player only.
- 2026-04-03: Applied quality-review cleanup to remove temporary ownership re-export plumbing, reuse a shared app-level DB session seam on the live guided-session path, and add the non-DB-backed `503 guided_session_unavailable` regression.

## Debug Log References

- `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py --no-cov -q -k 'owned_agent_guided_session'`
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py --no-cov -q -k 'owned_agent_guided_session_route_returns_owned_agent_snapshot_and_queued_context'` (red first: failed before the route fix because `recent_activity.alliances` leaked an unrelated alliance)
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py --no-cov -q -k 'owned_agent_guided_session_route_returns_owned_agent_snapshot_and_queued_context or owned_agent_guided_session_route_requires_human_bearer_and_enforces_ownership_and_match_membership or openapi_declares_secured_match_route_contracts'`
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py -q -k 'owned_agent_guided_session_route_returns_owned_agent_snapshot_and_queued_context or owned_agent_guided_session_route_requires_human_bearer_and_enforces_ownership_and_match_membership or openapi_declares_secured_match_route_contracts'` (route and contract assertions passed; command exited non-zero on the repo-wide coverage threshold applied to the subset run)
- `source .venv/bin/activate && python -m pytest tests/test_db_registry.py --no-cov -q -k 'owned_agent_context'`
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py --no-cov -q -k 'guided_session or account_api_keys or agent_briefing or openapi_declares_secured_match_route_contracts'`
- `source .venv/bin/activate && python -m pytest tests/test_db_registry.py --no-cov -q -k 'owned_agent_context or resolve_human_player_id_from_db_maps_persisted_human_membership_to_canonical_player_id'`
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py -q -k 'guided_session or account_api_keys or agent_briefing'` (relevant tests passed; command exited non-zero on the repo-wide coverage threshold applied to the subset run)
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py -q --override-ini addopts='' -k 'owned_agent_guided_session'`
- `source .venv/bin/activate && python -m pytest tests/test_db_registry.py -q --override-ini addopts='' -k 'owned_agent_context or registry_identity_compatibility_exports_delegate_to_identity_registry_module'`
- `source .venv/bin/activate && make format`
- `source .venv/bin/activate && make lint`
- `source .venv/bin/activate && make test`
- `source .venv/bin/activate && make quality`

## Completion Notes

- Added `GET /api/v1/matches/{match_id}/agents/{agent_id}/guided-session` for human Bearer auth only, backed by explicit DB ownership resolution on the authenticated user -> owned API key -> agent identity path.
- Kept the response additive and typed: fog-filtered state, aggregated queued orders for the owned player at the current tick, visible group chats and messages, and a small recent-activity block scoped to the owned player.
- Scoped `recent_activity.alliances` to the owned player's current alliance record only, returning an empty list when the player is unaffiliated.
- Scoped `recent_activity.treaties` to the same recent tick window already used by the route, filtered down to treaties involving the owned player so unrelated diplomacy does not leak into guided-session reads.
- Returned structured `agent_not_owned`, `agent_not_joined`, `match_not_found`, and existing human Bearer auth errors without widening match visibility or adding guidance-write behavior.
- Added a regression that seeds unrelated alliance and treaty activity in the same match and proves the guided-session response excludes it.
- Removed the story-only `resolve_owned_agent_context_from_db` registry facade plumbing so `server/api/app_services.py` imports the ownership read from `server.db.identity`, the smallest honest module.
- Kept the public DB-url helper shape for tests, but moved the live app path onto a shared startup-created SQLAlchemy engine/sessionmaker seam instead of constructing a fresh engine on each guided-session ownership lookup.
- Added a focused regression proving the guided-session route returns `503 guided_session_unavailable` when the app is running in non-DB-backed mode.
- Focused guided-session verification passed, the targeted DB compatibility check passed, and the full repo quality gate passed.

## File List

- `server/api/app_services.py`
- `server/api/authenticated_read_routes.py`
- `server/db/identity.py`
- `server/main.py`
- `server/models/api.py`
- `tests/api/test_agent_api.py`
- `tests/test_db_registry.py`
