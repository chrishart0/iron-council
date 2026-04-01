# Story: 35.2 Extract authenticated profile, state, and briefing reads out of `server/api/authenticated_access_routes.py`

Status: done

## Story

As a server maintainer,
I want authenticated profile/state/briefing read routes grouped behind focused helpers,
So that read-model and auth/access changes do not stay coupled to join and order submission handlers in one large file.

## Acceptance Criteria

1. `server/api/authenticated_access_routes.py` delegates authenticated profile/state/briefing read route registration to a focused module while preserving the existing route paths, response models, query parameters, auth dependencies, error codes, and compatibility behavior for current imports/callers.
2. Mixed-auth read behavior remains unchanged: API-key and Bearer resolution, joined-player lookup rules, not-found/unauthorized/bad-request mapping, and fog-filtered state projection semantics stay the same.
3. The story remains refactor-only: no HTTP/OpenAPI contract, auth semantics, websocket behavior, DB schema, or gameplay/read-model semantics change.
4. Focused authenticated API/process regressions covering profile/state/briefing reads pass, along with the repo quality gate.
5. The resulting structure is simpler than the starting point: read routes are grouped behind clearly named files and `server/api/authenticated_access_routes.py` is materially smaller again.

## Tasks / Subtasks

- [x] Pin current authenticated profile/state/briefing behavior with focused regressions. (AC: 2, 4)
- [x] Extract profile/state/briefing read route handlers into a focused module. (AC: 1, 5)
- [x] Rewire `server/api/authenticated_access_routes.py` to compose the extracted read router without contract drift. (AC: 1, 5)
- [x] Run focused verification, simplification review, and the repo quality gate. (AC: 4, 5)
- [x] Update sprint tracking and completion notes after merge. (AC: 4)

## Dev Notes

- This is the second delivery slice for Epic 35 in `_bmad-output/planning-artifacts/epics.md`.
- Treat this as a route-surface refactor only. Do not broaden into auth redesign, DB workflow changes, websocket changes, or route-contract cleanup beyond what is necessary to preserve the existing behavior.
- Keep the route surface boring: prefer a focused route-builder module and small explicit helpers over new abstractions, base classes, or dependency-injection layers.
- Pay special attention to `GET /api/v1/agent/profile`, `GET /api/v1/agents/{agent_id}/profile`, `GET /api/v1/matches/{match_id}/state`, and `GET /api/v1/matches/{match_id}/agent-briefing`, including joined-player resolution and fog-projection behavior.

## Dev Agent Record

### Debug Log

- 2026-04-01: Confirmed baseline authenticated read-route behavior with `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing'` before extraction.
- 2026-04-01: Extracted authenticated profile/state/briefing GET handlers into `server/api/authenticated_read_routes.py` and rewired `server/api/authenticated_access_routes.py` to compose lobby and read subrouters while retaining join/order POST handlers.
- 2026-04-01: Verified focused authenticated regressions with:
  - `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing'`
  - `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'profile or state or briefing'`
  - `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing or join or orders'`
- 2026-04-01: Ran `make format`.
- 2026-04-01: Initial `source .venv/bin/activate && make quality` failed because the worktree `.venv` was missing declared dev tools and `uv run mypy` could not spawn `mypy`.
- 2026-04-01: Synced the declared development environment with `uv sync --all-extras --dev` and reran `source .venv/bin/activate && make quality` successfully.

### Completion Notes

- Extracted authenticated profile, public profile, match state, and agent briefing GET route registration into `server/api/authenticated_read_routes.py` using the same focused router-composition style as the lobby extraction.
- Preserved the shipped HTTP contract for all extracted routes: paths, response models, query parameter validation, auth dependencies, error mapping, and fog-filtered state projection behavior remained unchanged.
- Kept `server/api/authenticated_access_routes.py` focused on composition plus join/order submission handling, making the file materially smaller without introducing new abstractions.
- Verified the refactor with focused API/e2e authenticated read regressions, join/order overlap coverage, and a passing full `make quality` gate after syncing the missing dev dependencies into `.venv`.

### File List

- `server/api/authenticated_access_routes.py`
- `server/api/authenticated_read_routes.py`
- `_bmad-output/implementation-artifacts/35-2-extract-authenticated-profile-state-and-briefing-reads-out-of-server-api-authenticated_access_routes-py.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-01: Drafted Story 35.2 as the next Epic 35 cleanup slice after completing Story 35.1 lobby lifecycle route extraction.
- 2026-04-01: Completed Story 35.2 by extracting authenticated read routes into `server/api/authenticated_read_routes.py`, validating focused API/e2e regressions, and passing `make quality`.
