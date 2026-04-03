# Story 49.3: Add pre-tick human override semantics for guided agents

Status: done

## Story

As an authenticated human player guiding my agent,
I want to override the next-tick orders or messages before they lock,
So that guided mode supports meaningful intervention instead of passive observation only.

## Acceptance Criteria

1. Given an owned agent has queued next-tick actions, when the owner submits a guided override before resolution, then the system records deterministic precedence and audit metadata so the resulting queued action set is unambiguous at tick time.
2. Given the override arrives too late or targets a non-owned agent, when the request is processed, then the API rejects it with a structured guided-mode error and leaves the existing queued action set unchanged.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add a small typed guided-override request/response contract plus persistence seam for audit metadata, keeping the scope limited to owned-agent pre-tick intervention rather than broader workflow redesign.
- [x] Add a human-authenticated guided-override route that reuses the existing owned-agent ownership path, enforces current-tick timing, and deterministically supersedes prior queued orders for the owned agent without widening visibility.
- [x] Cover the public contract with focused API/registry/DB regressions for precedence, audit metadata, and structured late/non-owner failure branches, then rerun the repo quality gate.
- [x] Update BMAD closeout artifacts with the actual verification commands and final outcomes.

## Dev Notes

- Keep this story server-side and contract-first. Do not build browser controls here; Story 49.4 will consume the resulting route/contracts.
- Reuse the explicit human-user -> owned API key -> agent participant ownership path from Stories 49.1 and 49.2. Do not authorize through broad user/display-name heuristics.
- Prefer the smallest honest semantics that match the current engine shape: guided overrides should make the resulting current-tick action set deterministic at resolution time and should not invent optimistic client-side state.
- Preserve the existing agent/gameplay surfaces for non-guided actors. This story should add an owned-agent override seam, not rewrite the normal agent command flow.
- Record enough audit metadata for later guided-session/client work to explain what happened, but keep the persistence/read model narrow and typed.

### References

- `core-plan.md#9.1 Bring Your Own Agent`
- `core-plan.md#9.2 Human vs. Agent vs. Guided Play`
- `_bmad-output/planning-artifacts/epics.md#Story 49.3: Add pre-tick human override semantics for guided agents`
- `_bmad-output/implementation-artifacts/49-1-add-an-owned-agent-guided-session-read-model.md`
- `_bmad-output/implementation-artifacts/49-2-deliver-private-human-to-agent-guidance-through-the-briefing-path.md`
- `server/api/authenticated_read_routes.py`
- `server/api/authenticated_write_routes.py`
- `server/api/app_services.py`
- `server/agent_registry.py`
- `server/agent_registry_commands.py`
- `server/models/api.py`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-03: Drafted Story 49.3 to add the first guided human override write surface after guided-session reads and private guidance delivery shipped in Stories 49.1 and 49.2.
- 2026-04-03: Shipped owned-agent guided order overrides with DB-backed audit persistence, focused rollback-safety hardening, and repo-gate verification.

## Debug Log References

- GREEN: `source .venv/bin/activate && python -m pytest tests/db/test_guided_overrides.py --no-cov -q`
- GREEN: `source .venv/bin/activate && python -m pytest tests/test_agent_registry.py --no-cov -q -k 'guided_override or replace_player_submissions'`
- GREEN: `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py --no-cov -q -k 'guided_override or guided_session or openapi_declares_secured_match_route_contracts'`
- GREEN: `source .venv/bin/activate && python -m pytest tests/api/test_agent_process_api.py --no-cov -q -k 'guided_override or guidance'`
- GREEN: `source .venv/bin/activate && python -m pytest tests/test_database_migrations.py --no-cov -q`
- GREEN: `source .venv/bin/activate && make quality`

## Completion Notes

- Added `POST /api/v1/matches/{match_id}/agents/{agent_id}/override` for authenticated humans who own the joined agent, limited to guided order overrides for the current tick.
- Persisted narrow audit rows in `owned_agent_overrides` with owner, persisted player, tick, superseded-submission count, serialized orders, and timestamp metadata.
- Kept the semantics deterministic and simple: the accepted override replaces only the owned player’s current-tick queued orders, leaves other players/ticks untouched, and returns a structured guided override tick-mismatch error for stale writes.
- Hardened the route with snapshot/restore rollback around queue replacement and audit persistence so failed writes leave the queued submissions unchanged while preserving deterministic superseded-count metadata on accepted overrides.

## File List

- `_bmad-output/implementation-artifacts/49-3-add-pre-tick-human-override-semantics-for-guided-agents.md`
- `alembic/versions/20260403_2100_owned_agent_overrides.py`
- `server/agent_registry.py`
- `server/api/authenticated_write_routes.py`
- `server/db/models.py`
- `server/db/overrides.py`
- `server/db/testing.py`
- `server/models/api.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/db/test_guided_overrides.py`
- `tests/test_agent_registry.py`
- `tests/test_database_migrations.py`
- `docs/plans/2026-04-03-story-49-3-guided-order-overrides.md`
