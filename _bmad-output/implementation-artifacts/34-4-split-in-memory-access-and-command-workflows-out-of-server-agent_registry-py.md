# Story: 34.4 Split in-memory access and command workflows out of `server/agent_registry.py`

Status: drafted

## Story

As a server maintainer,
I want the in-memory registry's authenticated access, join-slot resolution, tick advancement, and command-envelope mutation helpers separated into focused modules,
So that future API/runtime changes do not require one monolithic registry file to own every non-persistence workflow.

## Acceptance Criteria

1. `server/agent_registry.py` delegates in-memory authenticated-key resolution/deactivation, join-slot resolution, and joined-player access helpers to focused modules while preserving the shipped method names, error codes/messages, idempotent join behavior, and compatibility imports for current callers.
2. `server/agent_registry.py` delegates queued-order aggregation, tick advancement, and command-envelope mutation helpers to focused modules while preserving accepted response shapes, world-message side effects, scratch-registry validation behavior, and victory-state synchronization.
3. The story remains refactor-only: no HTTP contract, auth semantics, DB schema, runtime-loop behavior, websocket behavior, or gameplay resolution semantics change.
4. Focused registry/API/e2e regressions covering authenticated access, join flows, command-envelope behavior, and tick advancement pass, along with the repo quality gate.
5. The resulting structure is simpler than the starting point: `server/agent_registry.py` is materially smaller and the extracted concerns are grouped into clearly named files.

## Tasks / Subtasks

- [ ] Pin current in-memory auth/join/tick/command behavior with focused regressions. (AC: 1, 2, 4)
- [ ] Extract authenticated access and join helpers into a dedicated registry module with stable compatibility delegation. (AC: 1, 5)
- [ ] Extract queued-order aggregation, tick advancement, and command-envelope workflows into a dedicated registry module with stable compatibility delegation. (AC: 2, 5)
- [ ] Rewire `server/agent_registry.py` to act as a thinner compatibility facade without contract drift. (AC: 1, 2, 5)
- [ ] Run focused verification, simplification review, and the repo quality gate. (AC: 4, 5)
- [ ] Update sprint tracking and completion notes after merge. (AC: 4)

## Dev Notes

- This is the fourth delivery slice for Epic 34 in `_bmad-output/planning-artifacts/epics.md`.
- Treat this as a refactor-only story. Do not broaden into auth redesign, API route changes, DB-backed workflow changes, or gameplay rule changes.
- Prefer small explicit modules grouped by concern (registry access/join helpers, registry command/tick helpers) over new service abstractions or base classes.
- Pay special attention to idempotent join behavior, authenticated-key deactivation, command-envelope scratch validation, world-message side effects for treaty changes, and current/future tick submission handling.

## Dev Agent Record

### Debug Log

- Pending.

### Completion Notes

- Pending.

### File List

- Pending.

### Change Log

- 2026-04-01: Drafted Story 34.4 to continue Epic 34 by decomposing the remaining in-memory access and command workflows in `server/agent_registry.py`.
