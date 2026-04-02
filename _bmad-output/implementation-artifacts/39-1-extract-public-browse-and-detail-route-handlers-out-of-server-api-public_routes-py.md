# Story: 39.1 Extract public browse and detail route handlers out of `server/api/public_routes.py`

Status: drafted

## Story

As a server maintainer,
I want the public match browse/detail route handlers and their in-memory/DB-backed payload branching grouped behind a focused route module,
So that `server/api/public_routes.py` can stop mixing root/health metadata endpoints with the main public match browse/detail surface.

## Acceptance Criteria

1. The `/api/v1/matches` and `/api/v1/matches/{match_id}` route construction and any focused helper seams they need move behind a compatibility-safe public-route module or helper surface while preserving the existing HTTP paths, response models, and caller wiring from `server.api.public_routes`.
2. Public browse/detail behavior remains unchanged at the API and smoke-test boundary, including DB-backed versus in-memory fallback semantics, public roster ordering, open-slot counts, completed-match exclusion, and match-not-found mapping.
3. `server/api/public_routes.py` keeps simple route-composition ownership for the public router plus root/health metadata registration and does not gain a framework/service abstraction.
4. Focused API/OpenAPI/e2e regression coverage passes, along with the strongest practical repo-managed verification for the touched seam.
5. The resulting structure is simpler than the post-Epic-38 baseline: fewer mixed responsibilities in `server/api/public_routes.py`, clearer ownership for public browse/detail routes, and no abstraction added only for test convenience.

## Tasks / Subtasks

- [ ] Audit the browse/detail route seams in `server/api/public_routes.py` and identify the tightest extraction that preserves current behavior. (AC: 1, 5)
- [ ] Extract the public browse/detail route handlers into a focused compatibility-safe route module or helper surface. (AC: 1, 2, 3, 5)
- [ ] Keep `server.api.public_routes` imports and router wiring stable for current callers. (AC: 1, 2)
- [ ] Add or tighten focused regressions around browse/detail fallback semantics and match-not-found behavior if needed. (AC: 2, 4)
- [ ] Run focused verification plus the strongest practical repo-managed checks. (AC: 4, 5)

## Dev Notes

- This is the first pragmatic Epic 39 slice after closing Epic 38's DB public-read decomposition.
- Treat this as refactor-only work; do not broaden into new routes, API shape changes, auth changes, DB schema changes, or client work.
- Prefer plain route-builder functions and explicit dependency injection over classes, registries, or framework-heavy abstractions.
- Preserve both DB-backed and in-memory browse/detail behavior exactly.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the next route-surface decomposition slice after Epic 38 completed.

### Completion Notes

- Pending.

### File List

- `_bmad-output/implementation-artifacts/39-1-extract-public-browse-and-detail-route-handlers-out-of-server-api-public_routes-py.md`

### Change Log

- 2026-04-02: Drafted Story 39.1 to begin decomposing `server/api/public_routes.py` while preserving the shipped public browse/detail contract.
