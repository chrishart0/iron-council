# Story: 32.1 Extract public and realtime route registration from `server/main.py`

Status: done

## Story

As a server maintainer,
I want the public/read-only and websocket route wiring to live outside the monolithic main module,
So that future API work can change those contracts without forcing every concern through one 2k-line file.

## Acceptance Criteria

1. `server/main.py` delegates public route registration and realtime websocket wiring to dedicated server modules while preserving the same FastAPI paths, response models, dependencies, and runtime behavior.
2. Structured request-validation handling for lobby creation, commands, joins, messaging, treaties, alliances, and group chats remains intact after the extraction.
3. `create_app()` remains the stable composition entrypoint and continues to wire settings, registry, runtime, websocket manager, and exception handling without changing the public contract.
4. Focused API regression tests plus the repo quality gate pass.

## Tasks / Subtasks

- [x] Pin the public/read-only and websocket contract with focused regression tests. (AC: 1, 2, 4)
- [x] Extract shared app/error/validation wiring into dedicated modules. (AC: 2, 3)
- [x] Extract public API and realtime websocket route registration into dedicated modules. (AC: 1, 3)
- [x] Run focused verification, the full quality gate, and a simplification pass. (AC: 4)
- [x] Update sprint tracking and completion notes after merge. (AC: 4)

## Dev Notes

- This story is the first delivery slice for Epic 32 in `_bmad-output/planning-artifacts/epics.md`.
- Scope is refactor only. No new API surface, no auth redesign, no runtime-loop redesign, no client changes.
- Keep `create_app()` import path stable for existing tests, SDK coverage, and real-process smoke flows.
- Prefer explicit helper/module boundaries over introducing framework-heavy abstractions.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest --override-ini addopts=' -q --strict-config --strict-markers ' tests/api/test_agent_api.py tests/agent_sdk/test_python_client.py`
- `uv sync --extra dev --frozen`
- `make quality`

### Completion Notes List

- Extracted API error/validation handling from `server/main.py` into `server/api/errors.py` and kept the route-family-specific validation envelopes intact for lobby creation, joins, commands, messages, treaties, alliances, and group chats.
- Moved public read-only HTTP route wiring into `server/api/public_routes.py` and realtime websocket registration into `server/api/realtime_routes.py` while preserving the shipped paths, response models, fallback behavior, and websocket auth/error semantics.
- Kept `create_app()` as the stable composition entrypoint that still wires settings, registry, runtime, websocket manager, app state, and exception handling.
- Added focused regression coverage for public route declaration and the legacy websocket path, then passed targeted API/SDK verification and the full `make quality` gate.

### File List

- `_bmad-output/implementation-artifacts/32-1-extract-public-and-realtime-route-registration-from-server-main.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/api/__init__.py`
- `server/api/errors.py`
- `server/api/public_routes.py`
- `server/api/realtime_routes.py`
- `server/main.py`
- `tests/api/test_agent_api.py`
