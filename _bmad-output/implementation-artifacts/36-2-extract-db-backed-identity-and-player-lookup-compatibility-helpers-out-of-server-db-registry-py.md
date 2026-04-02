# Story: 36.2 Extract DB-backed identity and player lookup compatibility helpers out of `server/db/registry.py`

Status: drafted

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

- [ ] Pin current DB-backed identity/player lookup behavior with focused regressions. (AC: 2, 3, 5)
- [ ] Extract identity/player lookup compatibility helpers into a focused module. (AC: 1, 2, 3, 6)
- [ ] Rewire `server/db/registry.py` as a thinner compatibility facade without contract drift. (AC: 1, 6)
- [ ] Run focused verification, simplification review, and the repo quality gate. (AC: 4, 5, 6)
- [ ] Update sprint tracking and completion notes after merge. (AC: 5)

## Dev Notes

- This is the planned follow-on slice after Story 36.1 reduced the DB registry's write-workflow surface.
- Treat this as refactor-only work; do not broaden into lobby write changes, public-read redesign, or route changes.
- Prefer plain functions and stable re-exports over new classes or framework layers.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the next Epic 36 slice after Story 36.1.

### Completion Notes

- Pending.

### File List

- `_bmad-output/implementation-artifacts/36-2-extract-db-backed-identity-and-player-lookup-compatibility-helpers-out-of-server-db-registry-py.md`

### Change Log

- 2026-04-02: Drafted Story 36.2 as the next pragmatic follow-on to Story 36.1.
