# Story 49.1: Add an owned-agent guided-session read model

Status: in-progress

## Story

As an authenticated human player who owns an agent,
I want a guided-session read surface for that agent in a live match,
So that I can see the current visible state, queued actions, and recent agent activity before intervening.

## Acceptance Criteria

1. Given the authenticated human owns an agent participant in a match, when the guided-session route is requested, then it returns a player-safe snapshot, the current queued orders/messages, and concise recent activity for that owned agent without widening visibility beyond the agent's normal fog-of-war envelope.
2. Given the caller does not own the target agent or the agent is not in the requested match, when the same route is requested, then the API returns a structured auth or ownership error rather than leaking cross-account guided state.

## Ready Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Tasks / Subtasks

- [ ] Add a small typed guided-session response model that reuses existing player-safe state, message, and order contracts instead of inventing a second visibility surface.
- [ ] Add human-authenticated route coverage proving an owner can read guided state for an owned agent, while non-owners, wrong-match requests, and malformed auth fail with structured errors.
- [ ] Reuse current registry/read seams for queued orders, visible chats/messages, and recent treaty/alliance activity so the first read model stays additive and billing/guidance-write work can layer on later.
- [ ] Re-run focused verification plus the repo quality gate, then update BMAD closeout artifacts with the real final commands and outcomes.

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

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-03: Drafted Story 49.1 as the first Guided Agent Mode increment after Epic 48 completed the BYOA ownership and entitlement seams.

## Debug Log References

- Pending implementation.

## Completion Notes

- Pending implementation.

## File List

- Pending implementation.
