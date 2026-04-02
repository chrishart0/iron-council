# Story: 39.2 Extract public aggregate summary routes out of `server/api/public_routes.py`

Status: done

## Story

As a server maintainer,
I want the public leaderboard and completed-match summary route handlers grouped behind a focused public-route module,
So that `server/api/public_routes.py` can continue shrinking toward a thin composition layer over metadata and route families without changing the shipped public contract.

## Acceptance Criteria

1. The `/api/v1/leaderboard` and `/api/v1/matches/completed` route construction and any tiny helper seams they need move behind a compatibility-safe public-route module or helper surface while preserving the existing HTTP paths, response models, and caller wiring from `server.api.public_routes`.
2. Public aggregate-read behavior remains unchanged at the API and smoke-test boundary, including DB-backed-only availability, structured unavailable errors in memory mode, completed-match summary ordering, and leaderboard row ordering/content.
3. `server/api/public_routes.py` keeps simple route-composition ownership for the public router plus root/health metadata registration and does not gain a framework/service abstraction.
4. Focused API/OpenAPI/e2e regression coverage passes, along with the strongest practical repo-managed verification for the touched seam.
5. The resulting structure is simpler than the post-39.1 baseline: fewer mixed responsibilities in `server/api/public_routes.py`, clearer ownership for public aggregate summary routes, and no abstraction added only for test convenience.

## Tasks / Subtasks

- [x] Audit the leaderboard/completed-summary route seams in `server/api/public_routes.py` and identify the tightest extraction that preserves current behavior. (AC: 1, 5)
- [x] Extract the public leaderboard/completed-summary route handlers into a focused compatibility-safe route module or helper surface. (AC: 1, 2, 3, 5)
- [x] Keep `server.api.public_routes` imports and router wiring stable for current callers. (AC: 1, 2)
- [x] Add or tighten focused regressions around DB-backed-only availability and compatibility-safe extraction seams without coupling tests to internal FastAPI route-registration order. (AC: 2, 4)
- [x] Run focused verification plus the strongest practical repo-managed checks. (AC: 4, 5)

## Dev Notes

- This is the next Epic 39 route-surface decomposition slice after Story 39.1 extracted public browse/detail routes.
- Treat this as refactor-only work; do not broaden into new routes, API shape changes, auth changes, DB schema changes, or client work.
- Prefer plain router-builder functions and explicit dependency injection over classes, registries, or framework-heavy abstractions.
- Preserve DB-backed-only semantics and the existing `/matches/completed` versus `/matches/{match_id}` route-order safety.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted after Story 39.1 extracted public browse/detail routes and left leaderboard/completed/history/replay handlers as the next public-route concentration in `server/api/public_routes.py`.
- 2026-04-02: Added a seam regression for `server.api.public_summary_routes` plus a route-order regression asserting `/api/v1/matches/completed` stays registered before `/api/v1/matches/{match_id}`; confirmed RED with `ModuleNotFoundError` before extraction.
- 2026-04-02: Extracted the leaderboard and completed-match summary handlers into `server/api/public_summary_routes.py`, rewired `server/api/public_routes.py` to include the summary router before the public match router, then reran focused API and e2e coverage.
- 2026-04-02: Synced the repo-managed dev environment with `make install`, fixed formatter findings, and ran `make quality` successfully.
- 2026-04-02: Follow-up review fix removed the brittle `APIRoute` ordering assertion from `tests/api/test_agent_api.py`, kept the public-summary seam import regression, and re-verified the behavioral leaderboard/completed-match coverage plus touched-file quality checks before amending the story commit.

### Completion Notes

- Extracted `/api/v1/leaderboard` and `/api/v1/matches/completed` into `server/api/public_summary_routes.py` behind a plain `build_public_summary_router(...)` helper that mirrors the existing route extraction style.
- Preserved the shipped public contract: the HTTP paths, response models, OpenAPI schema references, leaderboard/completed-match DB-backed behavior, and structured unavailable errors are unchanged.
- Kept `server/api/public_routes.py` as the compatibility-safe composition layer for metadata, summary router inclusion, match router inclusion, and the remaining history/replay routes.
- Kept the compatibility-safe import seam regression for `server.api.public_summary_routes` and relied on existing behavioral coverage for `/api/v1/matches/completed` instead of asserting FastAPI's internal route-registration order.
- Verification: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'openapi_declares_public_read_contracts or extracted_route_seams or completed_match_summary_route_ahead_of_dynamic_match_detail_route'` (RED before extraction, then GREEN with the broader leaderboard/completed subset); `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k public_leaderboard_and_completed_match_smoke_flow_runs_through_real_process`; `uv run ruff check server/api/public_routes.py server/api/public_match_routes.py server/api/public_summary_routes.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py`; `uv run mypy server tests`; `make quality`.
- Follow-up verification after review feedback: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'leaderboard or completed_match or openapi_declares_public_read_contracts or extracted_route_seams'`; `uv run pytest --no-cov tests/e2e/test_api_smoke.py -k public_leaderboard_and_completed_match_smoke_flow_runs_through_real_process`; `uv run ruff check server/api/public_routes.py server/api/public_summary_routes.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py`; `uv run mypy server tests`.

### File List

- `_bmad-output/implementation-artifacts/39-2-extract-public-aggregate-summary-routes-out-of-server-api-public_routes-py.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/api/public_summary_routes.py`
- `server/api/public_routes.py`
- `tests/api/test_agent_api.py`

### Change Log

- 2026-04-02: Drafted Story 39.2 to continue decomposing `server/api/public_routes.py` by extracting public aggregate summary routes while preserving the shipped public-read contract.
- 2026-04-02: Completed Story 39.2 by extracting public aggregate summary routes into `server/api/public_summary_routes.py`.
- 2026-04-02: Follow-up review fix removed the brittle route-order regression and kept verification anchored to public behavior plus the import seam.
