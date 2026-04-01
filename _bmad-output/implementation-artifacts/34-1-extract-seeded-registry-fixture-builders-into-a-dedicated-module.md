# Story: 34.1 Extract seeded registry fixture builders into a dedicated module

Status: done

## Story

As a server maintainer,
I want the seeded match/profile/API-key fixture builders moved out of `server/agent_registry.py` into a dedicated module,
So that the registry and DB persistence layers can share one pure seeded-data seam without leaving test helpers and public imports scattered across multiple oversized files.

## Acceptance Criteria

1. A dedicated server module owns the seeded match/profile/API-key fixture builders and payload helpers that previously lived inline at the bottom of `server/agent_registry.py`.
2. `server.agent_registry` preserves stable compatibility exports for existing callers such as tests, e2e smoke flows, and DB seed tooling.
3. `server/db/registry.py` reuses shared seeded helper(s) for profile-by-key-hash lookup instead of rebuilding equivalent seeded maps inline.
4. The story stays refactor-only: no HTTP, websocket, DB schema, or gameplay behavior changes.
5. Focused registry tests plus the repo quality gate pass.

## Tasks / Subtasks

- [x] Pin import-compatibility and shared seeded-profile lookup behavior with focused tests. (AC: 2, 3, 5)
- [x] Create a dedicated seeded-data module and move the pure builders there. (AC: 1, 2)
- [x] Rewire `server/agent_registry.py` and `server/db/registry.py` to consume the shared helpers without contract drift. (AC: 2, 3, 4)
- [x] Run focused verification, simplification review, and the repo quality gate. (AC: 4, 5)
- [x] Update sprint tracking and completion notes after merge. (AC: 5)

## Dev Notes

- This is the first delivery slice for Epic 34 in `_bmad-output/planning-artifacts/epics.md`.
- Scope is deliberately narrow and structural. Do not broaden into runtime method extraction, auth redesign, route changes, or DB transaction rewrites.
- Preserve current import sites from `server.agent_registry` unless there is a compelling compatibility-safe reason to change them.
- Prefer a one-way dependency from runtime/DB modules into the new seeded-data module; avoid circular imports and avoid making the new module depend on DB code.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest -o addopts='' tests/test_agent_registry.py tests/test_db_registry.py`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'profile or join or state'`
- `make format`
- `source .venv/bin/activate && make quality`

### Completion Notes List

- Extracted the seeded match/profile/API-key builders into `server/registry_seed_data.py` and removed the large inline seeded fixture block from `server/agent_registry.py`.
- Preserved stable compatibility imports from `server.agent_registry` by re-exporting the seeded helper surface, including the shared `build_seeded_profiles_by_key_hash()` helper.
- Rewired `server/db/registry.py` to reuse the shared seeded profile-by-key-hash helper instead of duplicating equivalent inline maps across multiple DB-loading paths.
- Added focused compatibility and seeded-helper regression coverage while keeping the refactor behavior-neutral for HTTP, websocket, DB schema, and gameplay flows.

### File List

- `_bmad-output/implementation-artifacts/34-1-extract-seeded-registry-fixture-builders-into-a-dedicated-module.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/agent_registry.py`
- `server/db/registry.py`
- `server/registry_seed_data.py`
- `tests/test_agent_registry.py`
- `tests/test_db_registry.py`
