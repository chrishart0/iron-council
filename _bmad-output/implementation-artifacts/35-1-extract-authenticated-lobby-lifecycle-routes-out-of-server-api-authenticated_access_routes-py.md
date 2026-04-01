# Story: 35.1 Extract authenticated lobby lifecycle routes out of `server/api/authenticated_access_routes.py`

Status: drafted

## Story

As a server maintainer,
I want authenticated lobby creation/start flows and their mixed-auth helper logic separated into a focused route module,
So that lobby lifecycle changes do not require one large authenticated access router to own profile reads, state reads, joins, and writes as well.

## Acceptance Criteria

1. `server/api/authenticated_access_routes.py` delegates authenticated lobby creation/start route registration to a focused module while preserving the existing route paths, request/response models, dependency wiring, status codes, and compatibility behavior for current imports/callers.
2. DB-backed mixed-auth behavior remains unchanged: Bearer and X-API-Key auth precedence, unauthorized/misconfigured/service-unavailable cases, DB error-to-HTTP mapping, in-memory registry seeding, and `ensure_match_running()` side effects stay the same.
3. The story remains refactor-only: no HTTP/OpenAPI contract, auth semantics, runtime-loop behavior, websocket behavior, DB schema, or lobby lifecycle semantics change.
4. Focused authenticated API/process/e2e regressions covering create/start flows pass, along with the repo quality gate.
5. The resulting structure is simpler than the starting point: lobby lifecycle code is grouped behind clearly named files and `server/api/authenticated_access_routes.py` is materially smaller.

## Tasks / Subtasks

- [ ] Pin current authenticated lobby create/start behavior with focused API and real-process regressions. (AC: 2, 4)
- [ ] Extract lobby lifecycle route handlers and shared mixed-auth helper logic into a focused module. (AC: 1, 5)
- [ ] Rewire `server/api/authenticated_access_routes.py` to compose the extracted route builder without contract drift. (AC: 1, 5)
- [ ] Run focused verification, simplification review, and the repo quality gate. (AC: 4, 5)
- [ ] Update sprint tracking and completion notes after merge. (AC: 4)

## Dev Notes

- This is the first delivery slice for Epic 35 in `_bmad-output/planning-artifacts/epics.md`.
- Treat this as a route-surface refactor only. Do not broaden into auth redesign, DB workflow changes, runtime-loop changes, or websocket changes.
- Keep the route surface boring: prefer a focused route-builder module and small explicit helpers over new abstractions, base classes, or dependency-injection layers.
- Pay special attention to the current mixed-auth fallbacks when DB mode is absent vs present, exact error status mapping for `MatchLobbyCreationError` / `MatchLobbyStartError`, registry seeding after DB success, and `ensure_match_running(match_id)` side effects after successful starts.

## Dev Agent Record

### Debug Log

- Pending.

### Completion Notes

- Pending.

### File List

- Pending.

### Change Log

- 2026-04-01: Drafted Story 35.1 to continue autonomous cleanup after Epic 34 by decomposing authenticated lobby lifecycle routes from `server/api/authenticated_access_routes.py`.
