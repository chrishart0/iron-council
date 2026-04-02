# Story: 36.2 Extract DB-backed identity and player lookup compatibility helpers out of `server/db/registry.py`

Status: done

## Story

As a server maintainer,
I want DB identity and player-lookup compatibility exports grouped behind a focused surface,
So that auth/access helper evolution does not require the DB registry facade to keep owning both write workflows and identity lookups together.

## Acceptance Criteria

1. `server/db/registry.py` delegates DB-backed identity/player lookup compatibility exports to focused module(s) while preserving the current import surface for callers and tests.
2. `resolve_authenticated_agent_context_from_db`, `resolve_authenticated_agent_from_db_key_hash`, `resolve_human_player_id_from_db`, and related compatibility aliases keep their current auth precedence, return shapes, and session-factory semantics.
3. Any remaining compatibility aliases for player-id helpers and loaded-agent identity resolution remain stable for current callers/tests.
4. The story remains refactor-only: no HTTP/OpenAPI contract, auth semantics, DB schema, websocket behavior, runtime-loop behavior, or gameplay rules change.
5. Focused DB/API regressions covering auth/access helper behavior pass, along with the repo quality gate or strongest repo-managed equivalent.
6. The resulting structure is simpler than the starting point: `server/db/registry.py` gets thinner and the extracted identity helper surface stays explicit and boring.

## Tasks / Subtasks

- [x] Pin current DB-backed identity/player lookup behavior with focused regressions. (AC: 2, 3, 5)
- [x] Extract identity/player lookup compatibility helpers into a focused module. (AC: 1, 2, 3, 6)
- [x] Rewire `server/db/registry.py` as a thinner compatibility facade without contract drift. (AC: 1, 6)
- [x] Run focused verification, simplification review, and the repo quality gate. (AC: 4, 5, 6)
- [x] Update sprint tracking and completion notes after merge. (AC: 5)

## Dev Notes

- This is the planned follow-on slice after Story 36.1 reduced the DB registry's write-workflow surface.
- Treat this as refactor-only work; do not broaden into lobby write changes, public-read redesign, or route changes.
- Prefer plain functions and stable re-exports over new classes or framework layers.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the next Epic 36 slice after Story 36.1.
- `source .venv/bin/activate && uv run pytest -o addopts='' tests/test_db_registry.py -k 'resolve_authenticated_agent_context_from_db or resolve_human_player_id_from_db'`
- `source .venv/bin/activate && uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'invalid_api_key or invalid_player_auth or join_match or current_agent_profile or bundled_agent_briefing'`
- `source .venv/bin/activate && make quality`
- Spec-compliance review: PASS
- Code-quality/simplification review: APPROVED

### Completion Notes

- Extracted the DB URL convenience wrappers and grouped the public identity/player-lookup compatibility surface in `server/db/identity_registry.py` while preserving the stable `server.db.registry` import contract for callers.
- Kept `server/db/registry.py` thinner by delegating public DB-backed auth/player lookup helpers through the focused compatibility module while leaving private underscore aliases available from the facade for existing internal callers/tests.
- Added a focused regression test proving the registry public identity/player-id compatibility exports delegate to the new module, then passed focused DB/API checks and the full repo quality gate.
- Drafted Story 36.3 as the next follow-on slice to trim `server/db/registry.py` further into a clearly boring compatibility facade.

### File List

- `_bmad-output/implementation-artifacts/36-2-extract-db-backed-identity-and-player-lookup-compatibility-helpers-out-of-server-db-registry-py.md`
- `_bmad-output/implementation-artifacts/36-3-trim-server-db-registry-py-to-a-thin-compatibility-facade-over-hydration-read-identity-and-write-modules.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/plans/2026-04-02-story-36-2-db-identity-compatibility-extraction.md`
- `server/db/identity_registry.py`
- `server/db/registry.py`
- `tests/test_db_registry.py`

### Change Log

- 2026-04-02: Drafted Story 36.2 as the next pragmatic follow-on to Story 36.1.
- 2026-04-02: Completed the DB identity/player-lookup compatibility extraction, passed focused regressions plus the full quality gate, and queued Story 36.3 as the next Epic 36 slice.
