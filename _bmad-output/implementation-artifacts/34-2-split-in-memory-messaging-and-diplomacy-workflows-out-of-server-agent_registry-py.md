# Story: 34.2 Split in-memory messaging and diplomacy workflows out of `server/agent_registry.py`

Status: done

## Story

As a server maintainer,
I want message, treaty, alliance, and group-chat mutations grouped behind focused registry modules,
So that future live gameplay and API changes do not require one monolithic in-memory registry file to own every collaboration workflow.

## Acceptance Criteria

1. `server/agent_registry.py` delegates in-memory message inbox/send, group chat, treaty, and alliance workflows to one or more focused server modules while preserving the shipped registry method names, request/response shapes, ordering rules, transition semantics, error codes/messages, and world-chat side effects.
2. The extracted modules remain boring explicit helpers or services. No new framework layer, no registry abstraction rewrite, and no HTTP, websocket, DB schema, auth, or gameplay behavior changes are introduced.
3. Existing callers in API routes, runtime code, tests, and seeded/local flows continue to import and use `InMemoryMatchRegistry` without contract drift.
4. Focused registry/API regression tests covering message visibility, briefing buckets, group-chat membership/message flows, treaty transitions, alliance transitions, and command-envelope side effects pass, along with the repo quality gate.
5. The resulting structure is simpler than the starting point: `server/agent_registry.py` is materially smaller and collaboration concerns are grouped behind clearly named files.

## Tasks / Subtasks

- [x] Pin current collaboration workflow behavior with focused regression tests where coverage is missing. (AC: 1, 4)
- [x] Extract message + group-chat workflow helpers into a dedicated module with explicit dependencies on match records/state. (AC: 1, 2, 5)
- [x] Extract treaty + alliance transition helpers into a dedicated module with stable error/record behavior. (AC: 1, 2, 5)
- [x] Rewire `InMemoryMatchRegistry` to delegate to the extracted helpers while keeping its public method surface stable. (AC: 1, 3, 5)
- [x] Run focused verification, simplification review, and the repo quality gate. (AC: 4, 5)
- [x] Update sprint tracking and completion notes after merge. (AC: 4)

## Dev Notes

- This is the second delivery slice for Epic 34 in `_bmad-output/planning-artifacts/epics.md`.
- Treat this as a refactor-only story. Do not broaden into route changes, DB-backed messaging rewrites, websocket protocol changes, or game-rule changes.
- Prefer explicit helper/service seams that operate on existing `MatchRecord` / `MatchState` structures over introducing inheritance, generic repositories, or cross-file circular imports.
- Keep validation and transition semantics pinned from the public registry/API behavior, not from implementation details.

## Completion Notes

- Extracted collaboration record/error types into `server/agent_registry_types.py` so focused workflow modules can share the shipped in-memory shapes without changing the `server.agent_registry` import surface.
- Extracted message and group-chat workflows into `server/agent_registry_messaging.py`, including public visibility, briefing buckets, command-message validation, and membership enforcement.
- Extracted treaty, alliance, and victory-sync workflows into `server/agent_registry_diplomacy.py`, preserving transition semantics, world-message side effects, and alliance derivation behavior.
- Reduced `server/agent_registry.py` from 1397 lines to 760 lines while keeping `InMemoryMatchRegistry` as the stable public facade for callers.

## Debug Log References

- `uv run pytest -o addopts='' tests/test_agent_registry.py`
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'message or group_chat or treaty or alliance or briefing'`
- `make format`
- `source .venv/bin/activate && make quality`

## File List

- `server/agent_registry.py`
- `server/agent_registry_types.py`
- `server/agent_registry_messaging.py`
- `server/agent_registry_diplomacy.py`
- `tests/test_agent_registry.py`
