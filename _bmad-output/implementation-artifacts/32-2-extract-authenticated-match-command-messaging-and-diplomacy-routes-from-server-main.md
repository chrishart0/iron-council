# Story: 32.2 Extract authenticated match command, messaging, and diplomacy routes from `server/main.py`

Status: done

## Story

As a server maintainer,
I want the authenticated match write surfaces grouped into focused router modules,
So that gameplay write contracts are easier to review and evolve without accidental regressions elsewhere in app setup.

## Acceptance Criteria

1. `server/main.py` delegates authenticated match command, messaging, group chat, treaty, and alliance route registration to one or more dedicated server modules while preserving the same FastAPI paths, response models, dependencies, auth requirements, validation behavior, and websocket broadcast side effects.
2. The extracted routes continue to return the same structured API errors for route/body mismatch, tick mismatch, missing match/player/group chat, joined-player requirements, and treaty/alliance/group-chat domain failures.
3. `create_app()` remains the stable composition entrypoint and still wires the shared registry, settings, runtime/websocket broadcast callback, and authenticated route dependencies without introducing framework-heavy abstractions.
4. Focused authenticated-route regression tests plus the repo quality gate pass.

## Tasks / Subtasks

- [x] Pin the authenticated command/messaging/diplomacy route contract with focused regression tests. (AC: 1, 2, 4)
- [x] Extract authenticated match route registration into dedicated router modules with explicit dependencies. (AC: 1, 3)
- [x] Keep `server/main.py` as high-level composition only, with no contract drift. (AC: 1, 3)
- [x] Run focused verification, code review, simplification, and the full quality gate. (AC: 4)
- [x] Update sprint tracking and completion notes after merge. (AC: 4)

## Dev Notes

- This is the second delivery slice for Epic 32 in `_bmad-output/planning-artifacts/epics.md`.
- Scope is refactor only. No new API surface, no auth redesign, no runtime-loop redesign, no client changes.
- Prefer boring router-registration seams over generic controller/service frameworks.
- Keep route-level behavior pinned from the public API boundary; do not replace behavior tests with internal registration assertions.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv sync --extra dev --frozen`
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'command or group_chat or treaty or alliance or message'`
- `make format`
- `make quality`

### Completion Notes List

- Added focused regression coverage for the hidden `/api/v1/matches/{match_id}/commands` alias and for treaty/alliance websocket refresh behavior to pin the extracted route contract from the API boundary.
- Extracted authenticated match command, messaging, group chat, treaty, and alliance routes into `server/api/authenticated_match_routes.py` with explicit injected registry, auth, joined-player, and broadcast dependencies.
- Kept `create_app()` as the stable composition entrypoint in `server/main.py` and reduced it to router composition for the moved authenticated match route family without changing paths, status codes, error payloads, auth requirements, or broadcast side effects.
- Synced the dev environment before verification because the initial local pytest invocation was missing the repo's declared `pytest-cov` plugin support.

### File List

- `_bmad-output/implementation-artifacts/32-2-extract-authenticated-match-command-messaging-and-diplomacy-routes-from-server-main.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/api/__init__.py`
- `server/api/authenticated_match_routes.py`
- `server/main.py`
- `tests/api/test_agent_api.py`
