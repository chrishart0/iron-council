# Story: 34.2 Split in-memory messaging and diplomacy workflows out of `server/agent_registry.py`

Status: backlog

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

- [ ] Pin current collaboration workflow behavior with focused regression tests where coverage is missing. (AC: 1, 4)
- [ ] Extract message + group-chat workflow helpers into a dedicated module with explicit dependencies on match records/state. (AC: 1, 2, 5)
- [ ] Extract treaty + alliance transition helpers into a dedicated module with stable error/record behavior. (AC: 1, 2, 5)
- [ ] Rewire `InMemoryMatchRegistry` to delegate to the extracted helpers while keeping its public method surface stable. (AC: 1, 3, 5)
- [ ] Run focused verification, simplification review, and the repo quality gate. (AC: 4, 5)
- [ ] Update sprint tracking and completion notes after merge. (AC: 4)

## Dev Notes

- This is the second delivery slice for Epic 34 in `_bmad-output/planning-artifacts/epics.md`.
- Treat this as a refactor-only story. Do not broaden into route changes, DB-backed messaging rewrites, websocket protocol changes, or game-rule changes.
- Prefer explicit helper/service seams that operate on existing `MatchRecord` / `MatchState` structures over introducing inheritance, generic repositories, or cross-file circular imports.
- Keep validation and transition semantics pinned from the public registry/API behavior, not from implementation details.
