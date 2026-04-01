# Story: 32.3 Extract authenticated lobby and player-access helpers behind stable app services

Status: done

## Story

As a server maintainer,
I want route-level auth and DB-backed availability helpers to come from stable shared app services,
So that the server can keep growing without `server/main.py` remaining the only place that knows how runtime state, DB-backed mode, and authenticated actor resolution fit together.

## Acceptance Criteria

1. `server/main.py` delegates authenticated lobby creation/start/join plus authenticated player-access reads/writes to dedicated router/service modules while preserving the shipped FastAPI paths, response models, auth requirements, DB-backed availability checks, runtime side effects, and structured API error payloads.
2. Shared helper logic for authenticated agent resolution, human JWT resolution, joined-player lookup, lobby actor resolution, and mixed-auth player access lives behind stable app-service seams reusable by routes and websocket registration without introducing framework-heavy abstractions.
3. `create_app()` remains the stable composition entrypoint that wires registry, settings, runtime, websocket manager, history DB mode, and shared service dependencies explicitly.
4. Focused regression tests covering lobby/player-access contracts and the repo quality gate pass.

## Tasks / Subtasks

- [x] Pin the remaining lobby/player-access contract with focused regression tests. (AC: 1, 4)
- [x] Extract shared authenticated access helpers into a stable app-services module. (AC: 2, 3)
- [x] Extract remaining authenticated lobby/player-access route registration out of `server/main.py`. (AC: 1, 3)
- [x] Run focused verification, review/simplification, and the full quality gate. (AC: 4)
- [x] Update sprint tracking and completion notes after merge. (AC: 4)

## Dev Notes

- This is the third delivery slice for Epic 32 in `_bmad-output/planning-artifacts/epics.md`.
- Scope is refactor only. No new API surface, no auth redesign, no runtime-loop redesign, no client changes.
- Prefer boring explicit service objects / helper functions over generic dependency-injection frameworks.
- Keep websocket auth/player-view resolution aligned with the HTTP route helpers so the app has one source of truth for mixed agent/human access rules.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing or join or start or orders or create_match_lobby'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'profile or join or state or start'`
- `make format`
- `uv sync --extra dev --frozen`
- `make quality`

### Completion Notes List

- Added `server/api/app_services.py` as the explicit shared seam for authenticated agent resolution, human JWT resolution, joined-player lookup, mixed-auth player access, and websocket player-view resolution.
- Moved the remaining authenticated lobby/profile/state/briefing/join/orders routes into `server/api/authenticated_access_routes.py` and simplified `server/main.py` back to app composition and lifecycle wiring.
- Rewired `server/api/authenticated_match_routes.py` and `server/api/realtime_routes.py` to reuse the shared app services so HTTP and websocket player resolution stay aligned.
- Added a focused regression test that proves DB-backed human HTTP state access and player websocket identity resolution agree on the same joined player.

### File List

- `_bmad-output/implementation-artifacts/32-3-extract-authenticated-lobby-and-player-access-helpers-behind-stable-app-services.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/api/__init__.py`
- `server/api/app_services.py`
- `server/api/authenticated_access_routes.py`
- `server/api/authenticated_match_routes.py`
- `server/api/realtime_routes.py`
- `server/main.py`
- `tests/api/test_agent_api.py`
