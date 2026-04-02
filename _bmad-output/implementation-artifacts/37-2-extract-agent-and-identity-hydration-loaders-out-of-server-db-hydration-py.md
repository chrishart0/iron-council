# Story: 37.2 Extract agent and identity hydration loaders out of `server/db/hydration.py`

Status: done

## Story

As a server maintainer,
I want the agent-profile, authenticated-key, joined-agent, joined-human, and public-competitor hydration loaders grouped behind a focused seam,
So that `server/db/hydration.py` can evolve without one file continuing to own both top-level reload orchestration and every persisted identity reconstruction detail.

## Acceptance Criteria

1. The clustered identity-related loaders in `server/db/hydration.py` (`load_agent_profiles_by_match`, `load_authenticated_agent_keys_by_match`, `load_joined_agents_by_match`, `load_joined_humans_by_match`, and `load_public_competitor_kinds_by_match`) move behind a focused module or grouped helper surface while preserving stable caller imports/behavior from `server.db.hydration` and `server.db.registry`.
2. Seeded/non-seeded agent identity reconstruction, authenticated-key loading, joined-player mapping, human join visibility, and public competitor kind metadata remain unchanged at the registry, route, and test boundary.
3. `server/db/hydration.py` keeps explicit top-level reload orchestration and does not gain a new framework/service abstraction.
4. Focused hydration/registry regression coverage passes, along with the strongest practical repo-managed verification for the touched seam.
5. The final structure is simpler than the post-37.1 starting point: fewer mixed responsibilities in `server/db/hydration.py`, clearer ownership for persisted identity reconstruction, and no new abstraction added only for test convenience.

## Tasks / Subtasks

- [ ] Audit the identity-related hydration loaders and identify the tightest extraction seam that preserves current behavior. (AC: 1, 5)
- [ ] Extract the grouped agent/identity/public-competitor hydration loaders into a focused compatibility-safe module or helper surface. (AC: 1, 2, 3, 5)
- [ ] Keep `server.db.hydration` and `server.db.registry` import behavior stable for current callers. (AC: 1, 2)
- [ ] Add or tighten focused regression coverage around DB-backed identity reconstruction and reload behavior. (AC: 2, 4)
- [ ] Run focused verification plus the strongest practical repo-managed checks. (AC: 4, 5)

## Dev Notes

- This is the next pragmatic follow-on after Story 37.1 centralized repeated `MatchRecord` assembly.
- Treat this as refactor-only work; do not broaden into new auth rules, route changes, or DB schema changes.
- Prefer plain functions and explicit inputs over classes, registries, or generalized hydration frameworks.
- Preserve seeded profile fallback behavior and the current player/agent identity mapping exactly.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the next Epic 37 slice after Story 37.1 completed.
- 2026-04-02: Implemented the focused identity-loader extraction in `/tmp/iron-37-2` and verified targeted hydration regressions plus repo-managed lint/type/full-test checks before integration.

### Completion Notes

- Extracted `load_agent_profiles_by_match`, `load_authenticated_agent_keys_by_match`, `load_joined_agents_by_match`, `load_joined_humans_by_match`, and `load_public_competitor_kinds_by_match` into the new focused module `server/db/identity_hydration.py` while keeping `server/db/hydration.py` as the explicit top-level reload orchestrator.
- Preserved the stable compatibility surface by re-exporting the moved loader functions from `server.db.hydration`, which keeps `server.db.registry` behavior unchanged for callers.
- Added a focused regression that locks the new compatibility seam between `server.db.hydration` and `server.db.identity_hydration`, then re-verified the full repo-managed test suite after the refactor landed on `master`.

### File List

- `server/db/hydration.py`
- `server/db/identity_hydration.py`
- `tests/test_db_registry.py`
- `_bmad-output/implementation-artifacts/37-2-extract-agent-and-identity-hydration-loaders-out-of-server-db-hydration-py.md`

### Change Log

- 2026-04-02: Drafted Story 37.2 to continue Epic 37 by extracting the clustered persisted identity hydration loaders out of `server/db/hydration.py`.
- 2026-04-02: Completed Story 37.2 by moving the persisted identity hydration loaders into `server/db/identity_hydration.py`, preserving stable hydration/registry imports, adding a compatibility regression, and re-running focused plus full repo-managed verification.
