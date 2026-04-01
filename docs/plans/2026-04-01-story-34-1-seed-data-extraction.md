# Story 34.1 Seed Data Extraction Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Move seeded registry fixture builders into a dedicated module, keep `server.agent_registry` compatibility exports stable, and remove duplicated seeded profile-key-hash construction from `server/db/registry.py` without changing shipped behavior.

**Architecture:** Create one small pure helper module under `server/` for seeded match state payloads, seeded agent profiles, seeded API keys, and seeded match records. Keep `server/agent_registry.py` as the compatibility import surface by re-exporting the moved builders, then rewire `server/db/registry.py` to consume a shared seeded profile-by-key-hash helper instead of rebuilding equivalent maps inline.

**Tech Stack:** Python 3.12, FastAPI server package, Pydantic models, pytest, uv, make quality.

---

### Task 1: Pin the current seeded-helper contract with focused tests

**Objective:** Prove the seeded helper surface and DB seeded-profile hash behavior before moving code.

**Files:**
- Modify: `tests/test_agent_registry.py`
- Modify: `tests/test_db_registry.py`

**Step 1: Write failing test**

Add behavior-first coverage for:
- compatibility imports from `server.agent_registry`
- seeded helper output shape remaining stable enough for current callers
- DB registry seeded profile-by-key-hash behavior using the shared helper path rather than ad hoc inline reconstruction

Example test additions:

```python
from server.agent_registry import build_seeded_agent_api_key, build_seeded_match_records
from server.db import registry as db_registry_module


def test_build_seeded_agent_api_key_preserves_public_seed_format() -> None:
    assert build_seeded_agent_api_key("agent-player-2") == "seed-api-key-for-agent-player-2"


def test_db_registry_seeded_profiles_by_key_hash_matches_seeded_agent_profiles() -> None:
    seeded_profiles = db_registry_module._build_seeded_profiles_by_key_hash()  # noqa: SLF001
    assert seeded_profiles[hash_api_key(build_seeded_agent_api_key("agent-player-2"))].agent_id == "agent-player-2"
```

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/test_agent_registry.py tests/test_db_registry.py -k 'seeded or key_hash'`
Expected: FAIL until the new expectations or shared helper seam are in place.

**Step 3: Write minimal implementation**

Only add the tests/assertions needed to pin the current contract. Do not move production code yet.

**Step 4: Run test to verify baseline**

Run: `uv run pytest -o addopts='' tests/test_agent_registry.py tests/test_db_registry.py -k 'seeded or key_hash'`
Expected: PASS or a clearly understood red state that defines the next edit.

**Step 5: Commit**

```bash
git add tests/test_agent_registry.py tests/test_db_registry.py
git commit -m "test: pin seeded registry helper contract"
```

### Task 2: Create the dedicated seeded-data module

**Objective:** Move the pure seeded fixture builders into one explicit server module.

**Files:**
- Create: `server/registry_seed_data.py`
- Modify: `server/agent_registry.py`

**Step 1: Write failing test**

Reuse the focused seeded-helper tests from Task 1; no new implementation-detail tests are required.

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/test_agent_registry.py tests/test_db_registry.py -k 'seeded or key_hash'`
Expected: FAIL during extraction until imports and types are wired correctly.

**Step 3: Write minimal implementation**

Create a pure helper module with moved builders and a shared hash-map helper, for example:

```python
def build_seeded_agent_api_key(agent_id: str) -> str:
    return f"seed-api-key-for-{agent_id}"


def build_seeded_profiles_by_key_hash() -> dict[str, AgentProfileResponse]:
    return {
        hash_api_key(build_seeded_agent_api_key(profile.agent_id)): profile
        for profile in build_seeded_agent_profiles()
    }
```

In `server/agent_registry.py`, import and re-export the moved builders so existing callers keep working.

**Step 4: Run tests to verify pass**

Run: `uv run pytest -o addopts='' tests/test_agent_registry.py tests/test_db_registry.py -k 'seeded or key_hash'`
Expected: PASS.

**Step 5: Commit**

```bash
git add server/registry_seed_data.py server/agent_registry.py
git commit -m "refactor: extract seeded registry fixture builders"
```

### Task 3: Rewire DB registry seeded helper usage

**Objective:** Remove duplicated seeded profile-by-key-hash construction from `server/db/registry.py`.

**Files:**
- Modify: `server/db/registry.py`
- Modify if needed: `tests/test_db_registry.py`

**Step 1: Write failing test**

Keep using the Task 1 focused coverage as the contract.

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'seeded or key_hash or authenticated_agent_context'`
Expected: FAIL while the DB registry is partially rewired.

**Step 3: Write minimal implementation**

Replace inline constructions like:

```python
seeded_profiles_by_key_hash = {
    hash_api_key(build_seeded_agent_api_key(profile.agent_id)): profile
    for profile in build_seeded_agent_profiles()
}
```

with the shared helper from the new seeded-data module. Keep `_build_seeded_profiles_by_key_hash()` only if it becomes a thin compatibility wrapper; otherwise delete it and update callers/tests.

**Step 4: Run tests to verify pass**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'seeded or key_hash or authenticated_agent_context'`
Expected: PASS.

**Step 5: Commit**

```bash
git add server/db/registry.py tests/test_db_registry.py
git commit -m "refactor: share seeded db registry lookup helpers"
```

### Task 4: Full verification, simplification, and BMAD closeout

**Objective:** Confirm the refactor is complete, minimal, and convention-aligned.

**Files:**
- Modify if needed: `server/agent_registry.py`
- Modify if needed: `server/registry_seed_data.py`
- Modify if needed: `server/db/registry.py`
- Modify: `_bmad-output/implementation-artifacts/34-1-extract-seeded-registry-fixture-builders-into-a-dedicated-module.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/test_agent_registry.py tests/test_db_registry.py`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'profile or join or state'`

Expected: PASS.

**Step 2: Run formatting/quality**

Run:
- `make format`
- `make quality`

Expected: PASS.

**Step 3: Simplification pass**

Review diffs for:
- accidental public import churn
- circular dependency risk
- unnecessary wrapper functions or alias layers
- any leftover duplicated seeded helper construction in `server/db/registry.py`
- KISS violations vs the existing explicit server refactor style

**Step 4: Update BMAD artifacts**

Mark Story 34.1 done, fill in debug commands/completion notes/file list, update `sprint-status.yaml`, and set the next story pragmatically.

**Step 5: Commit**

```bash
git add server/registry_seed_data.py server/agent_registry.py server/db/registry.py   tests/test_agent_registry.py tests/test_db_registry.py tests/e2e/test_api_smoke.py   _bmad-output/implementation-artifacts/34-1-extract-seeded-registry-fixture-builders-into-a-dedicated-module.md   _bmad-output/implementation-artifacts/sprint-status.yaml   _bmad-output/planning-artifacts/epics.md   docs/plans/2026-04-01-story-34-1-seed-data-extraction.md
git commit -m "refactor: extract seeded registry fixture builders"
```
