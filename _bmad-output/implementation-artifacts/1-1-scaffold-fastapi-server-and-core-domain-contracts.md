# Story 1.1: Scaffold the FastAPI server package and core domain contracts

Status: ready-for-dev

## Story

As a server developer,
I want a minimal FastAPI project with canonical state and order models,
so that later game-loop and API work can build on stable validated contracts.

## Acceptance Criteria

1. The repo contains a Python project scaffold with `server/`, `tests/`, dependency metadata, and importable packages.
2. A minimal FastAPI app entrypoint exists and exposes a basic health-style route so the server package is executable.
3. Canonical state models exist for `MatchState`, `CityState`, `ArmyState`, `PlayerState`, and `VictoryState`.
4. Core order payload models exist for movement, recruitment, upgrades, and transfers with stable validated field names.
5. Fixture-based tests prove model validation and round-trip serialization for representative match state and order payloads.

## Tasks / Subtasks

- [ ] Create the initial Python package scaffold and dependency metadata. (AC: 1, 2)
  - [ ] Add `pyproject.toml` with FastAPI, Pydantic, Uvicorn, and pytest configuration.
  - [ ] Create package init files under `server/` and `server/models/`.
  - [ ] Add a minimal `server/main.py` FastAPI app with `/health`.
- [ ] Implement canonical state contracts. (AC: 3)
  - [ ] Add `server/models/state.py` with match, city, army, player, and victory models.
  - [ ] Keep contracts JSON-serializable and aligned with the architecture document's sample state shape.
- [ ] Implement core order payload contracts. (AC: 4)
  - [ ] Add `server/models/orders.py` with movement, recruitment, upgrade, and transfer payloads plus an aggregate order envelope.
  - [ ] Use explicit literals/enums so downstream validation can switch on order type safely.
- [ ] Add fixture-based tests for validation and serialization. (AC: 5)
  - [ ] Add test fixtures for a representative match state and order payload.
  - [ ] Assert both `model_validate()` and `model_dump(mode="json")` round-trip cleanly.

## Dev Notes

- Follow the architecture's greenfield server layout under `server/` and keep game logic pure and framework-light for now. [Source: core-architecture.md#7. Project Structure]
- Align model field names with the documented canonical state JSON shape and the agent order payload example. [Source: core-architecture.md#3.2 Match State (JSONB); core-architecture.md#3.3 Agent State Payload; core-architecture.md#3.4 Order Submission Payload]
- This story should not implement map rules, resolver logic, persistence, or gameplay mechanics yet; it only establishes the shared contracts and importable scaffold.
- Prefer Pydantic v2 idioms and small reusable enums/value objects where that reduces later churn.

### Project Structure Notes

- Create `server/main.py` and `server/models/{state.py,orders.py}` now.
- Put tests in top-level `tests/` rather than `server/tests/` so future integration and shared-data tests have a consistent home.
- It is acceptable to add `tests/fixtures/` or fixture helper modules if that keeps serialization examples readable.

### References

- `core-plan.md` sections 2-6 for tick loop, map/resource concepts, and core state vocabulary.
- `core-architecture.md#2.1 Game Server (FastAPI)` for runtime expectations.
- `core-architecture.md#3.2 Match State (JSONB)` for canonical state shape.
- `core-architecture.md#3.4 Order Submission Payload` for order payload shape.
- `core-architecture.md#7. Project Structure` for file layout intent.

## Dev Agent Record

### Agent Model Used

OpenAI Codex CLI (`codex exec --full-auto`)

### Debug Log References

- To be filled during implementation.

### Completion Notes List

- To be filled during implementation.

### File List

- To be filled during implementation.
