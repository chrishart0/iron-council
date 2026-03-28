# Story 10.1: Project fog-filtered agent state from canonical match data

Status: drafted

## Story

As an agent-platform developer,
I want a reusable fog-of-war projection over canonical match state,
so that agent polling and future broadcasts can share one deterministic visibility contract.

## Acceptance Criteria

1. Given a requesting player, owned cities, and alliance membership in the canonical match state, when visible state is projected, then the result includes all cities owned by the player or allied members plus adjacent cities visible through shared vision.
2. Given visible enemy cities and armies, when the projection is built, then enemy ownership is exposed but sensitive details stay masked according to the visibility contract, while self/allied territory keeps exact data.
3. Given repeated runs from the same match state and requesting player, when visibility is projected, then the result is deterministic and the caller-owned `MatchState` remains unchanged.

## Tasks / Subtasks

- [ ] Add behavior-first visibility tests before implementation. (AC: 1, 2, 3)
  - [ ] Cover direct ownership visibility, alliance-shared visibility, and adjacent-city reveal rules.
  - [ ] Cover masked enemy city and army details versus exact self/allied details.
  - [ ] Cover repeated runs and input-state immutability.
- [ ] Implement a narrow fog-projection module and API-facing view models. (AC: 1, 2, 3)
  - [ ] Keep scope to deterministic state projection only; do not add message polling, diplomacy payloads, or websocket broadcasting.
  - [ ] Reuse canonical map adjacency and current alliance membership from `MatchState`.
  - [ ] Keep iteration and output ordering deterministic.
- [ ] Re-verify visibility behavior after merge. (AC: 1, 2, 3)
  - [ ] Re-run focused visibility/API tests.
  - [ ] Re-run the repository quality gate.

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

_TBD_

### Debug Log References

- _TBD_

### Completion Notes List

- _TBD_

### File List

- _TBD_

### Change Log

- 2026-03-28 14:25 UTC: Drafted Story 10.1 for deterministic fog-filtered agent state projection.
