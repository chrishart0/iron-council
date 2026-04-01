# Story: 34.3 Split DB-backed public reads and identity-loading helpers out of `server/db/registry.py`

Status: done

## Story

As a server maintainer,
I want the DB registry's public-read models, identity resolution, and hydration helpers separated into stable modules,
So that persistence code can evolve without one 1.5k-line file remaining the only place that knows how lobby lifecycle, read models, and seeded auth fallback fit together.

## Acceptance Criteria

1. `server/db/registry.py` delegates DB-backed public match browse/detail/completed-history/leaderboard reads plus persisted-hydration and identity-loading helpers to focused modules while preserving the shipped function names, response shapes, sort/order rules, seeded-auth fallback behavior, and player-ID mapping semantics.
2. The extraction keeps stable top-level compatibility exports for current callers such as API routes, app services, tests, and seed/reset tooling.
3. The story remains refactor-only: no HTTP contract, auth behavior, DB schema, migration flow, runtime-loop behavior, or public docs semantics change.
4. Focused DB registry/API/e2e regressions covering public reads, authenticated agent context resolution, human joined-player lookup, and DB-to-registry hydration pass, along with the repo quality gate.
5. The resulting structure is simpler than the starting point: `server/db/registry.py` is materially smaller and public-read / identity-loading concerns are grouped into clearly named files.

## Tasks / Subtasks

- [x] Pin current DB public-read and identity-loading behavior with focused regression tests where coverage is missing. (AC: 1, 4)
- [x] Extract public-read query/response helpers into a dedicated DB module with stable compatibility exports. (AC: 1, 2, 5)
- [x] Extract persisted hydration + player/identity loading helpers into dedicated DB modules while preserving seeded fallback and canonical player-id mapping behavior. (AC: 1, 2, 5)
- [x] Rewire `server/db/registry.py` to act as a thin compatibility facade over the extracted modules without contract drift. (AC: 1, 2, 5)
- [x] Run focused verification, simplification review, and the repo quality gate. (AC: 4, 5)
- [x] Update sprint tracking and completion notes after merge. (AC: 4)

## Dev Notes

- This is the third delivery slice for Epic 34 in `_bmad-output/planning-artifacts/epics.md`.
- Treat this as a refactor-only story. Do not broaden into persistence model redesign, auth redesign, new browse endpoints, or leaderboard semantics changes.
- Prefer small explicit modules grouped by concern (public reads, persisted hydration, auth/identity resolution) over generic repository/service frameworks.
- Pay special attention to seeded-agent fallback, human/agent identity reconstruction, and canonical public player-id mapping across both DB-backed and in-memory paths.

## Dev Agent Record

### Debug Log

- 2026-04-01 15:17 UTC: Added a DB regression in `tests/test_db_registry.py` covering DB-backed human joined-player lookup and canonical public player-id mapping.
- 2026-04-01 15:17 UTC: Extracted concern-specific modules: `server/db/public_reads.py`, `server/db/hydration.py`, `server/db/identity.py`, and `server/db/player_ids.py`, then rewired `server/db/registry.py` into a compatibility facade.
- 2026-04-01 15:17 UTC: Ran `uv run pytest -o addopts='' tests/test_db_registry.py`.
- 2026-04-01 15:17 UTC: Ran `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing or join or start or create_match_lobby'`.
- 2026-04-01 15:17 UTC: Ran `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'profile or join or state or start'`.
- 2026-04-01 15:17 UTC: Ran `make format`.
- 2026-04-01 15:17 UTC: Installed missing dev tooling with `uv sync --extra dev --frozen` after `make quality` initially failed because `mypy` was absent from `.venv`.
- 2026-04-01 15:17 UTC: Ran `source .venv/bin/activate && make quality`.

### Completion Notes

- Split DB-backed public-read queries and response assembly into `server/db/public_reads.py` without changing browse/detail/history/leaderboard/completed-match response contracts or ordering rules.
- Split persisted match hydration, alliance metadata merge, joined-player reconstruction, authenticated-key loading, and public competitor-kind reconstruction into `server/db/hydration.py`.
- Split seeded/non-seeded agent resolution, DB auth fallback, human display/ELO lookup, and DB-backed human player-id resolution into `server/db/identity.py`.
- Split canonical/persisted player-id helpers into `server/db/player_ids.py` and preserved top-level compatibility access through `server/db/registry.py` for current callers and tests.
- Kept `server/db/registry.py` materially smaller and limited to persistence writes, lobby lifecycle workflows, and stable compatibility exports.

### File List

- `server/db/registry.py`
- `server/db/public_reads.py`
- `server/db/hydration.py`
- `server/db/identity.py`
- `server/db/player_ids.py`
- `tests/test_db_registry.py`
- `_bmad-output/implementation-artifacts/34-3-split-db-backed-public-reads-and-identity-loading-helpers-out-of-server-db-registry-py.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-01: Completed Story 34.3 by extracting DB public-read, hydration, and identity-loading helpers from `server/db/registry.py` into focused modules while preserving the compatibility surface and shipped behavior.
