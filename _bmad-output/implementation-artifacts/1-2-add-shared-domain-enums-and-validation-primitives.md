# Story 1.2: Add shared domain enums and validation primitives

Status: ready-for-dev

## Story

As a server developer,
I want centralized enums and reusable validation helpers,
so that future map, initialization, and resolver logic can share stable identifiers and constraints.

## Acceptance Criteria

1. Shared enum/value-object definitions exist for resource types, match status, upgrade tracks, and fortification tiers used by the current model layer.
2. Reusable validation primitives exist for common non-negative counts and tick-based durations so later models do not duplicate constraints.
3. Existing state and order models are updated to use the shared definitions where it reduces duplicated string literals without changing the current external payload contract.
4. Tests cover enum-backed serialization and at least one representative validation-helper failure path.

## Tasks / Subtasks

- [ ] Add a shared domain module for enums and typed literals. (AC: 1)
  - [ ] Create `server/models/domain.py` or equivalent.
  - [ ] Define shared identifiers for resources, match status, upgrade tracks, and fortification tiers.
- [ ] Add reusable validation primitives. (AC: 2)
  - [ ] Create constrained aliases or helper types for non-negative integers and positive tick durations.
  - [ ] Keep the helpers small and Pydantic-v2-friendly.
- [ ] Refactor existing model contracts to use the shared definitions. (AC: 3)
  - [ ] Update `server/models/state.py` and `server/models/orders.py`.
  - [ ] Preserve current JSON field names and accepted payloads.
- [ ] Extend tests. (AC: 4)
  - [ ] Add tests for enum serialization in representative state/order payloads.
  - [ ] Add a negative test proving a shared validation primitive rejects invalid input.

## Dev Notes

- Keep scope tight: this is a refactor-plus-hardening story, not a gameplay feature.
- Avoid introducing map logic, match initialization, or resolver logic in this story.
- Prefer shared types that reduce future churn across `state.py`, `orders.py`, and forthcoming map/init modules.

### Project Structure Notes

- Add the shared module under `server/models/` so later server subsystems can import from one place.
- Update only the existing scaffold and tests created in Story 1.1.

### References

- `core-plan.md` sections 3-6 for the canonical resource and fortification vocabulary.
- `core-architecture.md#3.2 Match State (JSONB)` for state field names.
- `core-architecture.md#3.4 Order Submission Payload` for order field names.
- `core-architecture.md#7. Project Structure` for model-module placement.

## Dev Agent Record

### Agent Model Used

OpenAI Codex CLI (`codex --yolo exec` recommended if workspace sandboxing blocks local shell access)

### Debug Log References

- To be filled during implementation.

### Completion Notes List

- To be filled during implementation.

### File List

- To be filled during implementation.
