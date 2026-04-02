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

- [x] Audit the identity-related hydration loaders and identify the tightest extraction seam that preserves current behavior. (AC: 1, 5)
- [x] Extract the grouped agent/identity/public-competitor hydration loaders into a focused compatibility-safe module or helper surface. (AC: 1, 2, 3, 5)
- [x] Keep `server.db.hydration` and `server.db.registry` import behavior stable for current callers. (AC: 1, 2)
- [x] Add or tighten focused regression coverage around DB-backed identity reconstruction and reload behavior. (AC: 2, 4)
- [x] Run focused verification plus the strongest practical repo-managed checks. (AC: 4, 5)

## Dev Notes

- This is the next pragmatic follow-on after Story 37.1 centralized repeated `MatchRecord` assembly.
- Treat this as refactor-only work; do not broaden into new auth rules, route changes, or DB schema changes.
- Prefer plain functions and explicit inputs over classes, registries, or generalized hydration frameworks.
- Preserve seeded profile fallback behavior and the current player/agent identity mapping exactly.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the next Epic 37 slice after Story 37.1 completed.
- 2026-04-02: Bootstrapped the repo dev extras with `uv sync --extra dev --frozen` after the focused red-phase pytest run failed because `pytest-cov` was not yet installed in the local `.venv`.
- 2026-04-02: Verified focused hydration/registry regressions with `uv run pytest --no-cov tests/test_db_registry.py -k "hydration_identity_loader_exports_delegate_to_focused_identity_module or registry_facade_re_exports_stable_module_surfaces or create_match_lobby_reload_preserves_authenticated_creator_identity or create_match_lobby_reload_preserves_non_seeded_authenticated_creator_identity or load_match_record_from_session_matches_registry_reload_for_lobby_membership_fields"`.
- 2026-04-02: Re-ran the strongest practical touched-seam checks with `uv run pytest --no-cov tests/test_db_registry.py`, `uv run ruff check server/db/hydration.py server/db/hydration_identity.py tests/test_db_registry.py`, `uv run ruff format --check server/db/hydration.py server/db/hydration_identity.py tests/test_db_registry.py`, and `uv run mypy server tests/api`.

### Completion Notes

- Extracted the five persisted identity-related hydration loaders into a focused plain-function module, `server/db/hydration_identity.py`, so seeded/non-seeded agent identity reconstruction, authenticated-key loading, joined agent/human mapping, and public competitor kind hydration now have clearer ownership outside the top-level reload orchestrator.
- Kept `server.db.hydration` as the stable compatibility surface by re-exporting the extracted loaders there, which preserves existing imports from both `server.db.hydration` and `server.db.registry` without introducing a new service or framework abstraction.
- Added a focused regression proving the `server.db.hydration` compatibility exports now delegate to the focused identity hydration module while existing registry compatibility assertions and full repo verification remain green.

### File List

- `server/db/hydration.py`
- `server/db/hydration_identity.py`
- `tests/test_db_registry.py`
- `_bmad-output/implementation-artifacts/37-2-extract-agent-and-identity-hydration-loaders-out-of-server-db-hydration-py.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-02: Drafted Story 37.2 to continue Epic 37 by extracting the clustered persisted identity hydration loaders out of `server/db/hydration.py`.
- 2026-04-02: Completed Story 37.2 by moving the clustered identity loaders into `server/db/hydration_identity.py`, preserving hydration/registry compatibility exports, tightening the focused regression seam, and passing the focused DB hydration/registry verification plus lint/type checks.
