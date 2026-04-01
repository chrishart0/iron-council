# Story: 36.1 Extract DB-backed lobby lifecycle and tick persistence out of `server/db/registry.py`

Status: in-progress

## Story

As a server maintainer,
I want DB-backed lobby lifecycle writes and tick persistence moved into focused modules,
So that lobby creation/join/start behavior and persisted tick writes can evolve without one large registry facade owning unrelated hydration, identity, public-read, and write workflows.

## Acceptance Criteria

1. `server/db/registry.py` delegates DB-backed `create_match_lobby`, `join_match`, `start_match_lobby`, and `persist_advanced_match_tick` workflows to focused module(s) while preserving the current import surface for callers and tests.
2. Lobby creation behavior remains unchanged: match config validation, creator membership persistence, creator identity reconstruction, open-slot/public-read visibility, and structured creation errors all stay the same.
3. Lobby join behavior remains unchanged: idempotent joins, agent-vs-human auth precedence, join-slot assignment, reload durability, and structured join errors all stay the same.
4. Lobby start behavior remains unchanged: creator-only authorization, readiness checks, active/completed status guards, runtime-facing response shape, and public browse/detail status visibility all stay the same.
5. Tick persistence behavior remains unchanged: persisted match state and tick-log rows update atomically with the same stored payload shape and error behavior.
6. The story remains refactor-only: no HTTP/OpenAPI contract, auth semantics, DB schema, websocket behavior, runtime-loop behavior, or gameplay rules change.
7. Focused DB/API/e2e regressions covering lobby lifecycle and tick persistence pass, along with the repo quality gate or the strongest repo-managed equivalent that can run in the worker environment.
8. The resulting structure is simpler than the starting point: `server/db/registry.py` becomes a thinner compatibility facade and the extracted modules stay explicit and boring rather than introducing new service/framework layers.

## Tasks / Subtasks

- [ ] Pin current DB-backed lobby/tick-write behavior with focused regressions. (AC: 2, 3, 4, 5, 7)
- [ ] Extract tick persistence into a focused DB write module. (AC: 1, 5, 8)
- [ ] Extract lobby create/join/start workflows into a focused DB write module. (AC: 1, 2, 3, 4, 8)
- [ ] Rewire `server/db/registry.py` as a compatibility facade without contract drift. (AC: 1, 8)
- [ ] Run focused verification, simplification review, and the repo quality gate. (AC: 6, 7, 8)
- [ ] Update sprint tracking and completion notes after merge. (AC: 7)

## Dev Notes

- This is the first delivery slice of a new DB-registry decomposition epic following the authenticated route decomposition work in Epic 35.
- Treat this as a refactor-only story. Do not broaden into schema redesign, auth-policy changes, route changes, or public read-model redesign.
- Keep the extracted surfaces explicit and procedural. Prefer plain functions and local helpers over new classes, registries, factories, or dependency-injection layers.
- Review carefully for first-time valid credential behavior, creator-only authorization boundaries, reload/restart durability, and public read visibility after DB writes.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted Story 36.1 and implementation plan for DB-backed lobby/tick workflow extraction.

### Completion Notes

- Pending.

### File List

- `_bmad-output/implementation-artifacts/36-1-extract-db-backed-lobby-lifecycle-and-tick-persistence-out-of-server-db-registry-py.md`
- `docs/plans/2026-04-02-story-36-1-db-lobby-registry-extraction.md`

### Change Log

- 2026-04-02: Drafted Story 36.1 as the next pragmatic refactor slice after Epic 35 route decomposition completion.
