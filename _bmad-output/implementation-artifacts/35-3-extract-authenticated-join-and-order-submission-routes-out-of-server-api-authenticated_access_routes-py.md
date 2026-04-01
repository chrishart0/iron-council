# Story: 35.3 Extract authenticated join and order submission routes out of `server/api/authenticated_access_routes.py`

Status: done

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

- [x] Pin current authenticated join and order submission behavior with focused regressions. (AC: 2, 4)
- [x] Extract join and order submission handlers into a focused route module. (AC: 1, 5)
- [x] Rewire `server/api/authenticated_access_routes.py` to compose the extracted write router without contract drift. (AC: 1, 5)
- [x] Run focused verification, simplification review, and the repo quality gate. (AC: 4, 5)
- [x] Update sprint tracking and completion notes after merge. (AC: 4)

## Dev Notes

- This is the third delivery slice for Epic 35 in `_bmad-output/planning-artifacts/epics.md`.
- Treat this as a route-surface refactor only. Do not broaden into auth redesign, DB workflow changes, runtime-loop changes, or order-processing changes beyond what is required to preserve existing behavior.
- Keep the route surface boring: prefer a focused route-builder module and small explicit helpers over new abstractions, base classes, or dependency-injection layers.
- Pay special attention to `POST /api/v1/matches/{match_id}/join` and `POST /api/v1/matches/{match_id}/orders`, including mixed-auth resolution, DB-backed human join behavior, lobby-only unauthenticated fallback, and submission tick validation.

## Dev Agent Record

### Debug Log

- Added `test_authenticated_write_routes_keep_api_key_precedence_over_human_bearer_auth` in `tests/api/test_agent_api.py` before the route extraction to pin the mixed-auth precedence used by both `POST /api/v1/matches/{match_id}/join` and `POST /api/v1/matches/{match_id}/orders`.
- `uv sync --extra dev --frozen`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'join_match or submit_orders or authenticated_write_routes_keep_api_key_precedence_over_human_bearer_auth'`
- `uv run pytest --no-cov tests/api/test_agent_process_api.py -k 'join or order'`
- `make quality`

### Completion Notes

- Extracted authenticated join and order submission registration into `server/api/authenticated_write_routes.py` without changing route paths, request/response models, status codes, DB-backed vs in-memory behavior, or mixed-auth resolution semantics.
- Reduced `server/api/authenticated_access_routes.py` to a thin composition module that now includes lobby, read, and write subrouters while preserving `build_authenticated_access_router` for existing callers.
- Added a focused regression covering API-key precedence over valid human Bearer auth on both authenticated write routes so the refactor cannot silently drift mixed-auth behavior.
- Focused authenticated API and real-process process tests passed after the extraction.
- Full repo quality/test commands were attempted, but the current local toolchain is missing `mypy` and pytest coverage-option support, so those broader gates could not complete in this environment.

### File List

- `_bmad-output/implementation-artifacts/35-3-extract-authenticated-join-and-order-submission-routes-out-of-server-api-authenticated_access_routes-py.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/api/authenticated_access_routes.py`
- `server/api/authenticated_write_routes.py`
- `tests/api/test_agent_api.py`

### Change Log

- 2026-04-01: Drafted Story 35.3 as the next Epic 35 cleanup slice after completing Story 35.2 authenticated read route extraction.
- 2026-04-01: Completed the authenticated join/order route extraction into `server/api/authenticated_write_routes.py`, kept `build_authenticated_access_router` as a composition seam, and added a mixed-auth precedence regression.
