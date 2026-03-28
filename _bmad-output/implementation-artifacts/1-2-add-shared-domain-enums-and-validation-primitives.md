# Story 1.2: Add shared domain enums and validation primitives

Status: done

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

- [x] Add a shared domain module for enums and typed literals. (AC: 1)
  - [x] Create `server/models/domain.py` or equivalent.
  - [x] Define shared identifiers for resources, match status, upgrade tracks, and fortification tiers.
- [x] Add reusable validation primitives. (AC: 2)
  - [x] Create constrained aliases or helper types for non-negative integers and positive tick durations.
  - [x] Keep the helpers small and Pydantic-v2-friendly.
- [x] Refactor existing model contracts to use the shared definitions. (AC: 3)
  - [x] Update `server/models/state.py` and `server/models/orders.py`.
  - [x] Preserve current JSON field names and accepted payloads.
- [x] Extend tests. (AC: 4)
  - [x] Add tests for enum serialization in representative state/order payloads.
  - [x] Add a negative test proving a shared validation primitive rejects invalid input.

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

- `uv run pytest -q -o addopts='' tests/test_orders.py tests/test_state.py` failed first because order serialization leaked internal `type` discriminator fields into the external payload contract.
- Updated `server/models/orders.py` to keep the discriminators internal-only during serialization, aligned `server/models/domain.py` with the canonical match-status and fortification vocabulary, and tightened queue durations in `server/models/state.py` to use a positive tick-duration primitive.
- `uv run pytest -q -o addopts='' tests/test_orders.py tests/test_state.py` passed after the model-layer refactor and test adjustments.
- `uv run ruff format server tests` reformatted one test file after `make quality` first failed at `ruff format --check`.
- `make quality` then passed end-to-end, including Ruff, mypy, pytest, and the repo coverage gate.

### Completion Notes List

- Added `server/models/domain.py` with shared `ResourceType`, `MatchStatus`, `UpgradeTrack`, `FortificationTier`, and reusable constrained aliases for counts and tick durations.
- Refined the bounded model layer under `server/models/` so state/order contracts consume the shared primitives while preserving JSON field names and serialized values.
- Kept external payload compatibility intact for representative state and order payloads, including enum-backed serialization to existing string/int values.
- Added fixture-backed tests covering state/order round-trip serialization plus a representative `NonNegativeCount` validation failure.
- Expanded the local quality harness to lint, type-check, and collect the top-level `tests/` suite so `make quality` exercises the new model-layer coverage.

### File List

- `Makefile`
- `pyproject.toml`
- `server/models/__init__.py`
- `server/models/domain.py`
- `server/models/orders.py`
- `server/models/state.py`
- `tests/conftest.py`
- `tests/test_orders.py`
- `tests/test_state.py`
