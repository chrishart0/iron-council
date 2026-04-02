# Story 36.2 DB Identity Compatibility Extraction Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extract DB-backed identity and player-lookup compatibility helpers out of `server/db/registry.py` into a focused module while preserving the existing import surface, auth/access behavior, session-factory semantics, and route/service contracts.

**Architecture:** Keep `server.db.registry` as the stable compatibility facade for current callers, but move the DB-backed identity/player-lookup wrapper functions and related compatibility exports behind a focused explicit module such as `server/db/identity_registry.py`. Leave the underlying query logic in `server/db/identity.py` intact unless a tiny cleanup is clearly simpler, preserve `Session`-injected wrapper behavior for DB URL entrypoints, and keep the refactor boring: no new service classes, framework layers, or auth-policy changes.

**Tech Stack:** Python 3.12, FastAPI server package, SQLAlchemy, Pydantic, pytest, uv, make quality.

---

## Parallelism Assessment

- **Implementation:** Keep Story 36.2 sequential. It centers on `server/db/registry.py`, import surfaces, and auth helper callers, so parallel Codex workers would collide on the same files and raise needless merge risk.
- **Safe parallel work:** Review/spec passes can run after implementation, but the actual code change should stay in one scoped worker worktree.
- **Next increment:** Story 36.3 should stay deferred until 36.2 lands because both stories trim the same facade and depend on seeing the post-36.2 shape.

### Task 1: Pin the DB-backed identity and player-lookup contract with focused regressions

**Objective:** Lock the current wrapper/import behavior before moving code.

**Files:**
- Modify: `tests/test_db_registry.py`
- Modify if needed: `tests/api/test_agent_api.py`
- Modify if needed: `server/api/app_services.py`

**Step 1: Write failing test**

Add or tighten behavior-first coverage for:
- `resolve_authenticated_agent_context_from_db()` preserving active-key auth, inactive-key rejection, and non-agent-key-owner rejection
- `resolve_human_player_id_from_db()` preserving canonical player-id mapping and missing-user behavior
- any compatibility alias/import surface currently consumed from `server.db.registry` that would be easy to break during extraction, especially `resolve_authenticated_agent_from_db_key_hash`, `resolve_loaded_agent_identity`, `resolve_human_display_name`, and `resolve_human_elo_rating`

Example addition:

```python
def test_registry_exports_identity_compatibility_surface() -> None:
    from server.db import registry as db_registry
    from server.db import identity_registry

    assert (
        db_registry.resolve_authenticated_agent_from_db_key_hash
        is identity_registry.resolve_authenticated_agent_from_db_key_hash
    )
    assert db_registry.resolve_loaded_agent_identity is identity_registry.resolve_loaded_agent_identity
    assert db_registry.resolve_human_display_name is identity_registry.resolve_human_display_name
    assert db_registry.resolve_human_elo_rating is identity_registry.resolve_human_elo_rating
```

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'resolve_authenticated_agent_context_from_db or resolve_human_player_id_from_db or identity_compatibility_surface'`
Expected: FAIL until the compatibility surface is pinned or the new module exists.

**Step 3: Write minimal implementation**

Only add/adjust tests that pin the current public behavior. Do not move production code yet.

**Step 4: Run test to verify baseline**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'resolve_authenticated_agent_context_from_db or resolve_human_player_id_from_db or identity_compatibility_surface'`
Expected: PASS or a clearly understood red defining the next edit.

**Step 5: Commit**

```bash
git add tests/test_db_registry.py tests/api/test_agent_api.py server/api/app_services.py
git commit -m "test: pin db identity compatibility contract"
```

### Task 2: Extract DB-backed identity/player lookup compatibility wrappers into a focused module

**Objective:** Move DB URL entrypoint wrappers and related compatibility exports out of `server/db/registry.py` into a narrower module.

**Files:**
- Create: `server/db/identity_registry.py`
- Modify: `server/db/registry.py`
- Modify if needed: `tests/test_db_registry.py`

**Step 1: Write failing test**

Reuse the Task 1 regressions as the contract.

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'resolve_authenticated_agent_context_from_db or resolve_human_player_id_from_db or identity_compatibility_surface'`
Expected: FAIL while imports/delegation are mid-extraction.

**Step 3: Write minimal implementation**

Create a focused module that owns:
- `ResolvedAuthenticatedDbAgent` compatibility export
- `resolve_authenticated_agent_context_from_db(...)`
- `resolve_human_player_id_from_db(...)`
- re-export/alias surface for `resolve_authenticated_agent_from_db_key_hash`, `resolve_human_display_name`, `resolve_human_elo_rating`, and `resolve_loaded_agent_identity`
- any tiny local helper only if it removes obvious duplication without hiding behavior

Target structure:

```python
from sqlalchemy.orm import Session
from server.db.identity import (
    ResolvedAuthenticatedDbAgent,
    resolve_authenticated_agent_context_from_db as _resolve_authenticated_agent_context_from_db,
    resolve_authenticated_agent_from_db_key_hash,
    resolve_human_display_name,
    resolve_human_elo_rating,
    resolve_human_player_id_from_db as _resolve_human_player_id_from_db,
    resolve_loaded_agent_identity,
)
from server.models.api import AuthenticatedAgentContext


def resolve_authenticated_agent_context_from_db(
    *, database_url: str, api_key: str
) -> AuthenticatedAgentContext | None:
    return _resolve_authenticated_agent_context_from_db(
        database_url=database_url,
        api_key=api_key,
        session_factory=Session,
    )
```

Guardrails:
- preserve existing caller signatures from `server.db.registry`
- preserve `Session` injection semantics for DB URL wrappers
- no auth-precedence drift, no schema/query redesign, no new abstraction layer
- keep `server.db.registry` as the stable import surface for current callers

**Step 4: Run tests to verify pass**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'resolve_authenticated_agent_context_from_db or resolve_human_player_id_from_db or identity_compatibility_surface'`
Expected: PASS.

**Step 5: Commit**

```bash
git add server/db/identity_registry.py server/db/registry.py tests/test_db_registry.py
git commit -m "refactor: extract db identity compatibility helpers"
```

### Task 3: Verify route/service callers and simplify the facade

**Objective:** Confirm the compatibility facade still behaves identically for app-level consumers and stays boring.

**Files:**
- Modify if needed: `server/api/app_services.py`
- Modify if needed: `server/db/registry.py`
- Modify if needed: `server/db/identity_registry.py`
- Modify if needed: `tests/api/test_agent_api.py`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/test_db_registry.py -k 'resolve_authenticated_agent_context_from_db or resolve_human_player_id_from_db'`
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'invalid_api_key or invalid_player_auth or join_match or current_agent_profile or bundled_agent_briefing'`

Expected: PASS.

**Step 2: Simplification pass**

Review diffs for:
- duplicated import/re-export noise in `server/db/registry.py`
- accidental contract drift in `__all__`
- hidden cross-module indirection that makes the new surface less obvious
- chances to keep the facade thinner by grouping identity-related exports together without adding abstraction

**Step 3: Commit**

```bash
git add server/db/identity_registry.py server/db/registry.py server/api/app_services.py tests/api/test_agent_api.py tests/test_db_registry.py
git commit -m "refactor: slim db registry identity surface"
```

### Task 4: Full verification, review, and BMAD closeout

**Objective:** Confirm the refactor is complete, minimal, and properly tracked.

**Files:**
- Modify if needed: `server/db/identity_registry.py`
- Modify if needed: `server/db/registry.py`
- Modify: `_bmad-output/implementation-artifacts/36-2-extract-db-backed-identity-and-player-lookup-compatibility-helpers-out-of-server-db-registry-py.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify if needed: `_bmad-output/planning-artifacts/epics.md`
- Create if needed: `_bmad-output/implementation-artifacts/36-3-trim-server-db-registry-py-to-a-thin-compatibility-facade-over-hydration-read-identity-and-write-modules.md`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/test_db_registry.py -k 'resolve_authenticated_agent_context_from_db or resolve_human_player_id_from_db'`
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'invalid_api_key or invalid_player_auth or join_match or current_agent_profile or bundled_agent_briefing'`

Expected: PASS.

**Step 2: Run quality gate**

Run:
- `source .venv/bin/activate && make quality`

Expected: PASS.

**Step 3: Review passes**

Run explicit spec-compliance and code-quality/simplification reviews against the acceptance criteria and changed files before merge.

**Step 4: Update BMAD artifacts**

Mark Story 36.2 done, capture actual debug commands/completion notes/file list, update `sprint-status.yaml`, and set the next story to 36.3. If the 36.3 story file does not yet exist, draft it as the next pragmatic facade-thinning slice.

**Step 5: Commit**

```bash
git add server/db/identity_registry.py server/db/registry.py \
  tests/test_db_registry.py tests/api/test_agent_api.py \
  _bmad-output/implementation-artifacts/36-2-extract-db-backed-identity-and-player-lookup-compatibility-helpers-out-of-server-db-registry-py.md \
  _bmad-output/implementation-artifacts/sprint-status.yaml \
  _bmad-output/planning-artifacts/epics.md \
  _bmad-output/implementation-artifacts/36-3-trim-server-db-registry-py-to-a-thin-compatibility-facade-over-hydration-read-identity-and-write-modules.md \
  docs/plans/2026-04-02-story-36-2-db-identity-compatibility-extraction.md

git commit -m "refactor: extract db identity compatibility helpers"
```
