# Story: 35.3 Extract authenticated join and order submission routes out of `server/api/authenticated_access_routes.py`

Status: drafted

## Story

As a server maintainer,
I want authenticated join and order submission flows isolated behind focused route helpers,
So that join semantics and order-write validation can evolve without unrelated authenticated reads sharing the same monolithic module.

## Acceptance Criteria

1. `server/api/authenticated_access_routes.py` delegates authenticated join and order submission route registration to a focused module while preserving the existing route paths, request/response models, auth dependencies, error codes, DB-backed/in-memory behavior, and compatibility behavior for current imports/callers.
2. Mixed-auth write behavior remains unchanged: join auth precedence, lobby-only unauthenticated join fallback, DB-backed human join handling, player resolution for order submission, tick mismatch handling, and error/status mapping stay the same.
3. The story remains refactor-only: no HTTP/OpenAPI contract, auth semantics, websocket behavior, DB schema, runtime-loop behavior, or gameplay/order-validation semantics change.
4. Focused authenticated API/process regressions covering join and order submission pass, along with the repo quality gate.
5. The resulting structure is simpler than the starting point: join/order write routes are grouped behind clearly named files and `server/api/authenticated_access_routes.py` shrinks again into a thin composition module.

## Tasks / Subtasks

- [ ] Pin current authenticated join and order submission behavior with focused regressions. (AC: 2, 4)
- [ ] Extract join and order submission handlers into a focused route module. (AC: 1, 5)
- [ ] Rewire `server/api/authenticated_access_routes.py` to compose the extracted write router without contract drift. (AC: 1, 5)
- [ ] Run focused verification, simplification review, and the repo quality gate. (AC: 4, 5)
- [ ] Update sprint tracking and completion notes after merge. (AC: 4)

## Dev Notes

- This is the third delivery slice for Epic 35 in `_bmad-output/planning-artifacts/epics.md`.
- Treat this as a route-surface refactor only. Do not broaden into auth redesign, DB workflow changes, runtime-loop changes, or order-processing changes beyond what is required to preserve existing behavior.
- Keep the route surface boring: prefer a focused route-builder module and small explicit helpers over new abstractions, base classes, or dependency-injection layers.
- Pay special attention to `POST /api/v1/matches/{match_id}/join` and `POST /api/v1/matches/{match_id}/orders`, including mixed-auth resolution, DB-backed human join behavior, lobby-only unauthenticated fallback, and submission tick validation.

## Dev Agent Record

### Debug Log

- Pending.

### Completion Notes

- Pending.

### File List

- Pending.

### Change Log

- 2026-04-01: Drafted Story 35.3 as the next Epic 35 cleanup slice after completing Story 35.2 authenticated read route extraction.
