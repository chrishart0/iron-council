# Story 10.1: Project fog-filtered agent state from canonical match data

Status: done

## Story

As an agent-platform developer,
I want a reusable fog-of-war projection over canonical match state,
so that agent polling and future broadcasts can share one deterministic visibility contract.

## Acceptance Criteria

1. Given a requesting player, owned cities, and alliance membership in the canonical match state, when visible state is projected, then the result includes all cities owned by the player or allied members plus adjacent cities visible through shared vision.
2. Given visible enemy cities and armies, when the projection is built, then enemy ownership is exposed but sensitive details stay masked according to the visibility contract, while self/allied territory keeps exact data.
3. Given repeated runs from the same match state and requesting player, when visibility is projected, then the result is deterministic and the caller-owned `MatchState` remains unchanged.

## Tasks / Subtasks

- [x] Add behavior-first visibility tests before implementation. (AC: 1, 2, 3)
  - [x] Cover direct ownership visibility, alliance-shared visibility, and adjacent-city reveal rules.
  - [x] Cover masked enemy city and army details versus exact self/allied details.
  - [x] Cover repeated runs and input-state immutability.
- [x] Implement a narrow fog-projection module and API-facing view models. (AC: 1, 2, 3)
  - [x] Keep scope to deterministic state projection only; do not add message polling, diplomacy payloads, or websocket broadcasting.
  - [x] Reuse canonical map adjacency and current alliance membership from `MatchState`.
  - [x] Keep iteration and output ordering deterministic.
- [x] Re-verify visibility behavior after merge. (AC: 1, 2, 3)
  - [x] Re-run focused visibility/API tests.
  - [x] Re-run the repository quality gate.

## Dev Notes

- Prefer behavior-first tests at the projection boundary over helper-only assertions.
- Match the current architecture intent without overbuilding hidden-information systems that depend on future chat/treaty payloads.
- Keep the exported projection contract stable enough for REST polling and future websocket reuse.

### References

- `core-plan.md` section 6.4 for fog-of-war rules and alliance-shared vision.
- `core-architecture.md` sections 3.3 and 5.2 for the agent state payload and fog-filtered state endpoint intent.
- `_bmad-output/planning-artifacts/epics.md` Story 10.1 acceptance criteria.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Red phase: `uv run pytest tests/test_fog.py` failed during collection with `ModuleNotFoundError: No module named 'server.fog'`.
- Focused verification: `uv run pytest --no-cov tests/test_fog.py`
- Quality gate: `make quality`
- Follow-up red phase: `uv run pytest --no-cov tests/test_fog.py` failed because stationary enemy armies in visible cities were omitted and `project_agent_state()` did not yet accept `match_id`.
- Follow-up verification: `uv run pytest --no-cov tests/test_fog.py`
- Follow-up quality gate: `make quality`

### Completion Notes List

- Added `server.fog.project_agent_state` to derive deterministic fog-filtered agent state from canonical `MatchState` plus canonical map adjacency.
- Added API-facing fog view models for projected cities and armies, keeping self/allied territory exact while masking enemy city and army details.
- Projection includes owned and allied cities plus adjacent revealed cities through shared vision, sorts cities and armies deterministically, and does not mutate the caller-owned `MatchState`.
- Follow-up fix: stationary enemy armies now remain visible when positioned inside a visible city, even when they are not in transit.
- Follow-up fix: fog tests now inject a small synthetic `MapDefinition`, reducing brittleness against unrelated canonical map changes.
- Follow-up contract alignment: `AgentStateProjection` and `project_agent_state()` now accept optional `match_id` without expanding into the Story 10.2 REST payload shape.

### File List

- `_bmad-output/implementation-artifacts/10-1-project-fog-filtered-agent-state-from-canonical-match-data.md`
- `server/fog.py`
- `server/models/__init__.py`
- `server/models/fog.py`
- `tests/test_fog.py`

### Change Log

- 2026-03-28 14:25 UTC: Drafted Story 10.1 for deterministic fog-filtered agent state projection.
- 2026-03-28 14:30 UTC: Implemented deterministic fog projection, added projection-boundary tests, and passed `make quality`.
- 2026-03-28 14:45 UTC: Fixed stationary visible enemy army projection, switched fog tests to an injected synthetic map, added optional `match_id` to the projection contract, and re-ran focused tests.
