# Story: 36.3 Trim `server/db/registry.py` to a thin compatibility facade over hydration, read, identity, and write modules

Status: drafted

## Story

As a server maintainer,
I want the DB registry module reduced to a clearly boring compatibility layer,
So that future DB-backed features can extend focused modules without recreating a monolithic registry file.

## Acceptance Criteria

1. `server/db/registry.py` becomes a thin compatibility facade that mostly groups stable imports/re-exports over hydration, public-read, identity, lobby-write, and tick-write modules.
2. Current caller import paths from `server.db.registry` remain stable for routes, services, tests, and DB tooling.
3. No HTTP/OpenAPI contract, auth semantics, DB schema, websocket behavior, runtime-loop behavior, or gameplay rules change.
4. Focused regression coverage for the remaining registry facade surface passes, along with the repo quality gate or strongest repo-managed equivalent.
5. The final structure is simpler than the post-36.2 starting point: less local logic, fewer surprise aliases, and clearer ownership boundaries across DB modules.

## Tasks / Subtasks

- [ ] Audit the remaining `server/db/registry.py` surface and identify any residual local logic or confusing re-export churn. (AC: 1, 5)
- [ ] Simplify `server/db/registry.py` into a mostly import-and-alias compatibility layer over the focused DB modules. (AC: 1, 2, 5)
- [ ] Pin the remaining facade contract with focused regression coverage where needed. (AC: 2, 4)
- [ ] Run focused verification, simplification review, and the repo quality gate. (AC: 3, 4, 5)
- [ ] Update sprint tracking and completion notes after merge. (AC: 4)

## Dev Notes

- This is the planned follow-on slice after Stories 36.1 and 36.2 extracted the larger write and identity seams.
- Treat this as refactor-only work; do not broaden into public-read redesign, route changes, or new abstraction layers.
- Prefer explicit imports/re-exports and tiny compatibility helpers over classes, facades with behavior, or new framework patterns.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the next Epic 36 slice after Story 36.2.

### Completion Notes

- Pending.

### File List

- `_bmad-output/implementation-artifacts/36-3-trim-server-db-registry-py-to-a-thin-compatibility-facade-over-hydration-read-identity-and-write-modules.md`

### Change Log

- 2026-04-02: Drafted Story 36.3 as the next pragmatic follow-on to Story 36.2.
