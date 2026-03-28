# Story 3.2: Validate queued orders against ownership, resources, and adjacency

Status: done

## Story

As a game server,
I want to reject invalid orders before resolution,
so that tick execution stays deterministic and safe.

## Acceptance Criteria

1. Given movement, recruitment, upgrade, and transfer orders, when validation runs, then invalid ownership, insufficient-resource, disconnected-route, and late-order cases are rejected with structured reasons.
2. Keep validation pure and deterministic. Do not implement tick resolution.

## Tasks / Subtasks

- [x] Add a public pure order-validation surface under `server/`. (AC: 1, 2)
  - [x] Expose `validate_order_envelope(...)` that accepts `OrderEnvelope`, `MatchState`, and a `MapDefinition`.
  - [x] Return accepted orders plus structured rejected-order metadata with stable reason codes/messages.
- [x] Validate movement orders against ownership, existence, adjacency, and transit state. (AC: 1, 2)
  - [x] Reject missing armies and missing destination cities.
  - [x] Reject armies not owned by the submitting player.
  - [x] Reject non-adjacent moves and armies already in transit.
- [x] Validate recruitment and upgrade orders against ownership, resources, and tier rules. (AC: 1, 2)
  - [x] Reject missing cities and cities not owned by the submitting player.
  - [x] Enforce explicit simple recruitment and upgrade costs from a start-of-tick budget snapshot.
  - [x] Enforce one-tier-at-a-time upgrade progression.
- [x] Validate transfer orders against recipient/resource rules and route connectivity. (AC: 1, 2)
  - [x] Reject missing recipient players.
  - [x] Require a connected land route for food and production transfers.
  - [x] Allow money transfers without a land-route requirement.
- [x] Add behavior-first public contract tests for mixed valid orders and rejected invalid cases. (AC: 1, 2)
  - [x] Cover late-order rejection across the queued envelope.
  - [x] Cover ownership, missing-entity, disconnected-route, and insufficient-resource cases.
  - [x] Cover deterministic budget reservation from the sender's starting resources.

## Dev Notes

- Validation is intentionally pure and does not mutate the input `MatchState` or attempt any phase resolution.
- The deterministic late-order rule is strict equality: `OrderEnvelope.tick` must equal `MatchState.tick`, otherwise every queued order is rejected as `late_order`.
- Envelope-local conflicts are resolved deterministically by first occurrence: later movement orders for the same army and later upgrade orders for the same `(city, track)` pair are rejected as `conflicting_duplicate_order`.
- Resource affordability uses the sender's start-of-validation resources as a snapshot budget. Reservations follow the validator's deterministic batch order: recruitment orders first, then upgrade orders, then transfer orders; same-tick incoming transfers never increase that budget.
- Simple explicit costs used for this story:
  - Recruitment: `1 food + 5 production` per troop.
  - Upgrade production costs by target tier:
    - Economy: `7 / 11 / 15`
    - Military: `8 / 12 / 16`
    - Fortification: `6 / 10 / 14`
- Source reconciliation: `core-plan.md` section 4.4 explicitly allows money transfers without any land route, while requiring land connectivity for food and production. This implementation keeps that product rule and treats any stricter reading elsewhere as superseded for Story 3.2.
- Transfer recipients must be allied or neutral. Allied means both players share the same non-null `alliance_id`; enemy means both have non-null and different `alliance_id` values and is rejected; all remaining cases are neutral and allowed.
- Land-route checks traverse only land edges and cities whose ownership in `MatchState.cities` belongs to the sender, recipient, or members of their shared alliance when both players belong to the same alliance. `PlayerState.cities_owned` is treated as derivative metadata, not a second authority for routing.

### References

- `core-plan.md` section 4.4 for resource-transfer route rules.
- `core-architecture.md` sections 4.1 to 4.3 for pre-resolution validation and same-tick transfer budget behavior.
- `_bmad-output/planning-artifacts/epics.md` Story 3.2 acceptance criteria.

## Dev Agent Record

### Agent Model Used

OpenAI Codex CLI (`codex --yolo exec` recommended in this environment)

### Debug Log References

- RED: `uv run pytest tests/test_order_validation.py -q` -> failed with `ModuleNotFoundError: No module named 'server.order_validation'`
- RED (env): `uv run pytest tests/test_order_validation.py -q` -> failed before collection because `pytest-cov` was not installed in the fresh local `.venv`
- Setup: `uv sync --extra dev --frozen`
- GREEN (focused TDD): `uv run pytest tests/test_order_validation.py --no-cov -q`
- Targeted verification: `uv run pytest tests/test_order_validation.py tests/test_orders.py tests/test_state.py tests/test_match_initialization.py tests/test_map_data.py tests/api/test_health.py tests/api/test_metadata.py -q`
- Quality gate: `make quality`

### Completion Notes List

- Added a public `server.order_validation` surface that partitions an order envelope into accepted and rejected orders without throwing control-flow exceptions for expected validation failures.
- Structured rejection output now carries stable reason codes and messages for late orders, unknown entities, invalid ownership, invalid adjacency, in-transit armies, disconnected routes, invalid upgrade progression, and insufficient resources.
- Structured rejection output now also covers per-envelope conflicting duplicates for movement and upgrade orders.
- Validation uses a deterministic local resource budget snapshot from the submitting player's current stored resources, so accepted same-tick outbound spending reduces later validations in recruitment -> upgrade -> transfer batch order while incoming transfers remain unavailable until a later tick.
- Transfer validation now rejects enemy recipients based on pragmatic `alliance_id` semantics, allows allied or neutral recipients, derives route ownership from `MatchState.cities`, and keeps the product-rule interpretation that only food and production require a connected land route.

### File List

- `_bmad-output/implementation-artifacts/3-2-validate-queued-orders-against-ownership-resources-and-adjacency.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/order_validation.py`
- `tests/test_order_validation.py`

### Change Log

- Implemented Story 3.2 order validation as a pure public server module.
- Added behavior-first validation coverage for accepted and rejected queued orders.
- Marked Story 3.2 and Epic 3 complete in the sprint tracker.
