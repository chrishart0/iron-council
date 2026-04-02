# Story: 39.2 Extract public aggregate summary routes out of `server/api/public_routes.py`

Status: drafted

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

- [ ] Audit the leaderboard/completed-summary route seams in `server/api/public_routes.py` and identify the tightest extraction that preserves current behavior. (AC: 1, 5)
- [ ] Extract the public leaderboard/completed-summary route handlers into a focused compatibility-safe route module or helper surface. (AC: 1, 2, 3, 5)
- [ ] Keep `server.api.public_routes` imports and router wiring stable for current callers. (AC: 1, 2)
- [ ] Add or tighten focused regressions around DB-backed-only availability and static-route ordering if needed. (AC: 2, 4)
- [ ] Run focused verification plus the strongest practical repo-managed checks. (AC: 4, 5)

## Dev Notes

- This is the next Epic 39 route-surface decomposition slice after Story 39.1 extracted public browse/detail routes.
- Treat this as refactor-only work; do not broaden into new routes, API shape changes, auth changes, DB schema changes, or client work.
- Prefer plain router-builder functions and explicit dependency injection over classes, registries, or framework-heavy abstractions.
- Preserve DB-backed-only semantics and the existing `/matches/completed` versus `/matches/{match_id}` route-order safety.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted after Story 39.1 extracted public browse/detail routes and left leaderboard/completed/history/replay handlers as the next public-route concentration in `server/api/public_routes.py`.

### Completion Notes

- Pending.

### File List

- `_bmad-output/implementation-artifacts/39-2-extract-public-aggregate-summary-routes-out-of-server-api-public_routes-py.md`

### Change Log

- 2026-04-02: Drafted Story 39.2 to continue decomposing `server/api/public_routes.py` by extracting public aggregate summary routes while preserving the shipped public-read contract.
