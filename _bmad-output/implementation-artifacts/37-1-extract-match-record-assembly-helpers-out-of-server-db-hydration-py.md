# Story: 37.1 Extract match-record assembly helpers out of `server/db/hydration.py`

Status: drafted

## Story

As a server maintainer,
I want the duplicated match-record assembly logic in DB hydration isolated behind focused helpers,
So that registry reloads and session-scoped match reloads can evolve without one large hydration file owning both row loading and record composition.

## Acceptance Criteria

1. `server/db/hydration.py` no longer duplicates the same `MatchRecord` construction logic across `load_match_registry_from_database` and `load_match_record_from_session`; shared composition helper(s) own the repeated assembly while preserving the stable caller contracts.
2. Current caller import paths and behavior remain stable for `server.db.hydration`, `server.db.registry`, routes, DB tooling, and tests.
3. No HTTP/OpenAPI contract, auth semantics, DB schema, websocket behavior, runtime-loop behavior, or gameplay rules change.
4. Focused regression coverage for DB hydration/registry reload behavior passes, along with the strongest practical repo-managed verification for the touched seam.
5. The final structure is simpler than the starting point: clearer ownership between row-loading and match-record composition, less repeated assembly logic, and no new framework-style abstraction.

## Tasks / Subtasks

- [ ] Audit the repeated `MatchRecord` assembly paths in `load_match_registry_from_database` and `load_match_record_from_session`. (AC: 1, 5)
- [ ] Extract focused helper(s) that compose `MatchRecord` values from already-loaded persisted/state inputs without changing behavior. (AC: 1, 2, 5)
- [ ] Keep hydration row-loading responsibilities explicit and compatibility-safe. (AC: 2, 3)
- [ ] Add or tighten focused regression coverage around hydrated record composition and reload behavior. (AC: 2, 4)
- [ ] Run focused verification plus the strongest practical repo-managed static checks. (AC: 3, 4)

## Dev Notes

- This is the next pragmatic refactor after Epic 36 trimmed `server/db/registry.py` to a compatibility facade.
- Treat this as refactor-only work; do not broaden into new DB features, public-read redesign, or route changes.
- Prefer plain helper functions fed by explicit inputs over introducing classes, registries, or generalized hydration frameworks.
- Preserve seeded/non-seeded agent identity reconstruction, joined-player mapping, joinability calculations, and persisted alliance/public visibility metadata exactly.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the next follow-on slice after completing Epic 36.

### Completion Notes

- Pending.

### File List

- `_bmad-output/implementation-artifacts/37-1-extract-match-record-assembly-helpers-out-of-server-db-hydration-py.md`

### Change Log

- 2026-04-02: Drafted Story 37.1 to continue DB surface decomposition with hydration-focused refactoring.
