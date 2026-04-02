# Story: 39.3 Extract public history and replay routes out of `server/api/public_routes.py`

Status: done

## Story

As a server maintainer,
I want the persisted match-history and replay route handlers grouped behind a focused public-route module,
So that `server/api/public_routes.py` can finish Epic 39 as a thin composition layer over metadata plus public route families without changing the shipped public contract.

## Acceptance Criteria

1. The `/api/v1/matches/{match_id}/history` and `/api/v1/matches/{match_id}/history/{tick}` route construction and any tiny helper seams they need move behind a compatibility-safe public-route module or helper surface while preserving the existing HTTP paths, response models, and caller wiring from `server.api.public_routes`.
2. Persisted history/replay behavior remains unchanged at the API and smoke-test boundary, including DB-backed-only availability, match-not-found and tick-not-found error translation, response payload fidelity, and OpenAPI schema declarations.
3. `server/api/public_routes.py` keeps simple route-composition ownership for the public router plus root/health metadata registration and does not gain a framework/service abstraction.
4. Focused API/OpenAPI/e2e regression coverage passes, along with the strongest practical repo-managed verification for the touched seam.
5. The resulting structure is simpler than the post-39.2 baseline: fewer mixed responsibilities in `server/api/public_routes.py`, clearer ownership for persisted history/replay routes, and no abstraction added only for test convenience.

## Tasks / Subtasks

- [x] Audit the remaining persisted history/replay route seams in `server/api/public_routes.py` and identify the tightest extraction that preserves current behavior. (AC: 1, 5)
- [x] Extract the public history/replay route handlers into a focused compatibility-safe route module or helper surface. (AC: 1, 2, 3, 5)
- [x] Keep `server.api.public_routes` imports and router wiring stable for current callers. (AC: 1, 2)
- [x] Add or tighten focused regressions around not-found/error mapping, OpenAPI contract, and real-process history/replay behavior if needed. (AC: 2, 4)
- [x] Run focused verification plus the strongest practical repo-managed checks. (AC: 4, 5)

## Dev Notes

- This is the next Epic 39 route-surface decomposition slice after Story 39.2 extracted public aggregate summary routes.
- Treat this as refactor-only work; do not broaden into new routes, API shape changes, auth changes, DB schema changes, or client work.
- Prefer plain router-builder functions and explicit dependency injection over classes, registries, or framework-heavy abstractions.
- Preserve the current match-not-found and tick-not-found semantics exactly.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted after Story 39.2 extracted public aggregate summary routes and left persisted history/replay handlers as the remaining concentrated responsibility in `server/api/public_routes.py`.
- 2026-04-02: Added the seam regression for `server.api.public_history_routes`, confirmed RED with `ModuleNotFoundError`, then extracted the persisted history/replay routes into `server/api/public_history_routes.py`.
- 2026-04-02: Rewired `server/api/public_routes.py` into a thinner composition layer over summary, match, and history router builders while preserving the existing DB-backed error translations and OpenAPI declarations.
- 2026-04-02: Focused verification passed for the extracted seam, history/replay API contract, real-process smoke flow, and the full repo-managed `make quality` gate after syncing the local dev environment with `make install`.

### Completion Notes

- Extracted `/api/v1/matches/{match_id}/history` and `/api/v1/matches/{match_id}/history/{tick}` into `server/api/public_history_routes.py` behind a plain `build_public_history_router(*, history_database_url)` helper that mirrors the existing public route-family extraction pattern.
- Preserved the shipped contract and behavior: route paths, response models, OpenAPI schema references, DB-backed-only availability, and the structured `match_not_found`, `tick_not_found`, and `match_history_unavailable` error translations are unchanged.
- Kept `server/api/public_routes.py` as the thin public composition layer for root/health metadata plus summary, match, and history router inclusion only.
- Verification: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'extracted_route_seams or match_history_routes or openapi_declares_public_read_contracts'` (RED before extraction, then GREEN); `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k match_history_and_replay_smoke_flow_runs_through_real_process`; `source .venv/bin/activate && make install`; `source .venv/bin/activate && make quality`.

### File List

- `_bmad-output/implementation-artifacts/39-3-extract-public-history-and-replay-routes-out-of-server-api-public_routes-py.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/api/public_history_routes.py`
- `server/api/public_routes.py`
- `tests/api/test_agent_api.py`

### Change Log

- 2026-04-02: Drafted Story 39.3 to continue decomposing `server/api/public_routes.py` by extracting persisted history/replay routes while preserving the shipped public-read contract.
- 2026-04-02: Completed Story 39.3 by extracting the public history/replay routes into `server/api/public_history_routes.py`.
