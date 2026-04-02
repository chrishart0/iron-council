# Story: 36.1 Extract DB-backed lobby lifecycle and tick persistence out of `server/db/registry.py`

Status: done

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
- `source .venv/bin/activate && uv run pytest -o addopts='' tests/test_db_registry.py -k 'create_match_lobby or join_match or start_match_lobby or persist_advanced_match_tick'`
- `source .venv/bin/activate && uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'create_match_lobby or start_match_lobby or join_match or openapi_declares_secured_access_route_contracts'`
- `source .venv/bin/activate && uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'create_match_lobby or join_match or start_match_lobby'`
- `uv sync --all-extras --dev`
- `source .venv/bin/activate && make quality`
- Spec-compliance review: PASS
- Code-quality/simplification review: APPROVED

### Completion Notes

- Extracted DB-backed tick persistence into `server/db/tick_persistence.py` and lobby create/join/start workflows into `server/db/lobby_registry.py` while preserving the stable `server.db.registry` import surface for callers.
- Reduced `server/db/registry.py` to a thinner compatibility facade over hydration, identity, public-read, lobby-write, and tick-write seams without changing route/service behavior.
- Added focused DB-registry regression coverage for join idempotency/reload durability and for public match detail visibility after lobby start, then passed focused DB/API/e2e checks plus the full repo quality gate.
- Drafted Story 36.2 and advanced sprint tracking so Epic 36 can continue with the identity/player-lookup compatibility surface next.

### File List

- `_bmad-output/implementation-artifacts/36-1-extract-db-backed-lobby-lifecycle-and-tick-persistence-out-of-server-db-registry-py.md`
- `_bmad-output/implementation-artifacts/36-2-extract-db-backed-identity-and-player-lookup-compatibility-helpers-out-of-server-db-registry-py.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/plans/2026-04-02-story-36-1-db-lobby-registry-extraction.md`
- `server/db/lobby_registry.py`
- `server/db/registry.py`
- `server/db/tick_persistence.py`
- `tests/test_db_registry.py`

### Change Log

- 2026-04-02: Drafted Story 36.1 as the next pragmatic refactor slice after Epic 35 route decomposition completion.
- 2026-04-02: Completed the DB-backed lobby/tick workflow extraction, passed focused regressions plus the full quality gate, and queued Story 36.2 as the next Epic 36 slice.
