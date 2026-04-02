# Story: 39.3 Extract public history and replay routes out of `server/api/public_routes.py`

Status: drafted

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

- [ ] Audit the remaining persisted history/replay route seams in `server/api/public_routes.py` and identify the tightest extraction that preserves current behavior. (AC: 1, 5)
- [ ] Extract the public history/replay route handlers into a focused compatibility-safe route module or helper surface. (AC: 1, 2, 3, 5)
- [ ] Keep `server.api.public_routes` imports and router wiring stable for current callers. (AC: 1, 2)
- [ ] Add or tighten focused regressions around not-found/error mapping, OpenAPI contract, and real-process history/replay behavior if needed. (AC: 2, 4)
- [ ] Run focused verification plus the strongest practical repo-managed checks. (AC: 4, 5)

## Dev Notes

- This is the next Epic 39 route-surface decomposition slice after Story 39.2 extracted public aggregate summary routes.
- Treat this as refactor-only work; do not broaden into new routes, API shape changes, auth changes, DB schema changes, or client work.
- Prefer plain router-builder functions and explicit dependency injection over classes, registries, or framework-heavy abstractions.
- Preserve the current match-not-found and tick-not-found semantics exactly.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted after Story 39.2 extracted public aggregate summary routes and left persisted history/replay handlers as the remaining concentrated responsibility in `server/api/public_routes.py`.

### Completion Notes

- Pending.

### File List

- `_bmad-output/implementation-artifacts/39-3-extract-public-history-and-replay-routes-out-of-server-api-public_routes-py.md`

### Change Log

- 2026-04-02: Drafted Story 39.3 to continue decomposing `server/api/public_routes.py` by extracting persisted history/replay routes while preserving the shipped public-read contract.
