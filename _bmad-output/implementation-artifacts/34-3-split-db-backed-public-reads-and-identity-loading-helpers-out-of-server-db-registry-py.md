# Story: 34.3 Split DB-backed public reads and identity-loading helpers out of `server/db/registry.py`

Status: backlog

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

- [ ] Pin current DB public-read and identity-loading behavior with focused regression tests where coverage is missing. (AC: 1, 4)
- [ ] Extract public-read query/response helpers into a dedicated DB module with stable compatibility exports. (AC: 1, 2, 5)
- [ ] Extract persisted hydration + player/identity loading helpers into dedicated DB modules while preserving seeded fallback and canonical player-id mapping behavior. (AC: 1, 2, 5)
- [ ] Rewire `server/db/registry.py` to act as a thin compatibility facade over the extracted modules without contract drift. (AC: 1, 2, 5)
- [ ] Run focused verification, simplification review, and the repo quality gate. (AC: 4, 5)
- [ ] Update sprint tracking and completion notes after merge. (AC: 4)

## Dev Notes

- This is the third delivery slice for Epic 34 in `_bmad-output/planning-artifacts/epics.md`.
- Treat this as a refactor-only story. Do not broaden into persistence model redesign, auth redesign, new browse endpoints, or leaderboard semantics changes.
- Prefer small explicit modules grouped by concern (public reads, persisted hydration, auth/identity resolution) over generic repository/service frameworks.
- Pay special attention to seeded-agent fallback, human/agent identity reconstruction, and canonical public player-id mapping across both DB-backed and in-memory paths.
