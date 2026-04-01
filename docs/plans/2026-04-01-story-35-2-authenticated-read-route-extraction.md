# Story 35.2 Authenticated Read Route Extraction Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extract authenticated profile, match-state, and agent-briefing read route wiring out of `server/api/authenticated_access_routes.py` into a focused module without changing the shipped HTTP contract, mixed-auth behavior, or fog-filtered read semantics.

**Architecture:** Keep `server/api/authenticated_access_routes.py` as the stable composition entrypoint for authenticated access routes, but delegate the profile/state/briefing read registration to a new focused module such as `server/api/authenticated_read_routes.py`. Reuse existing `AppServices` mixed-auth helpers, preserve the current `project_agent_state(...)` behavior, and keep error mapping explicit rather than introducing a new generic routing framework.

**Tech Stack:** FastAPI, Python 3.12, Pydantic, pytest, uv, make quality, Codex in an isolated git worktree.

---

### Task 1: Pin authenticated read-route behavior with focused regressions

**Objective:** Lock the public and mixed-auth read contract before moving code.

**Files:**
- Modify if needed: `tests/api/test_agent_api.py`
- Modify if needed: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing test**

Add or tighten behavior-first assertions for:
- `GET /api/v1/agent/profile`
- `GET /api/v1/agents/{agent_id}/profile`
- `GET /api/v1/matches/{match_id}/state`
- `GET /api/v1/matches/{match_id}/agent-briefing`

Pin route-boundary behavior for:
- exact error/status mapping for missing auth, invalid auth, missing match, and missing agent cases
- mixed API-key/Bearer player resolution behavior
- joined-player requirements for agent briefing
- fog-filtered state projection and briefing message/treaty/group-chat visibility

**Step 2: Run test to verify failure**

Run:
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'profile or state or briefing'`

Expected: PASS if the contract is already pinned tightly enough, or FAIL only if new contract coverage exposes an unpinned seam.

**Step 3: Write minimal implementation**

Only add the smallest regression coverage needed to pin the contract. Do not refactor production code yet.

**Step 4: Run focused tests again**

Run:
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'profile or state or briefing'`

Expected: PASS baseline with contract coverage in place.

**Step 5: Commit**

```bash
git add tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
git commit -m "test: pin authenticated read routes"
```

### Task 2: Extract the authenticated read router

**Objective:** Move profile/state/briefing handlers into a focused route-builder module while preserving the public contract exactly.

**Files:**
- Create: `server/api/authenticated_read_routes.py`
- Modify: `server/api/authenticated_access_routes.py`
- Modify if needed: `server/api/__init__.py`

**Step 1: Reuse the pinned contract**

Use the Task 1 route-boundary tests as the contract. Do not add implementation-detail tests for import locations.

**Step 2: Run test to verify failure during extraction**

Run: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing'`
Expected: FAIL while imports or delegated route wiring are mid-extraction.

**Step 3: Write minimal implementation**

Create a focused router builder with explicit injected dependencies, for example:

```python
def build_authenticated_read_router(
    *,
    match_registry_provider: RegistryProvider,
    app_services: AppServices,
) -> APIRouter:
    ...
```

Keep these behaviors unchanged:
- `GET /api/v1/agent/profile` and `GET /api/v1/agents/{agent_id}/profile` paths, response models, and exact not-found/auth behavior
- `GET /api/v1/matches/{match_id}/state` mixed-auth resolution, joined-player lookup rules, and fog-filtered `project_agent_state(...)` semantics
- `GET /api/v1/matches/{match_id}/agent-briefing` path, query parameter handling, joined-player requirements, and response assembly
- all current response schemas, auth dependencies, error codes, and compatibility behavior

Then have `build_authenticated_access_router(...)` include the extracted read router rather than owning the handlers inline.

**Step 4: Run focused tests to verify pass**

Run:
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'profile or state or briefing'`

Expected: PASS.

**Step 5: Commit**

```bash
git add server/api/authenticated_read_routes.py server/api/authenticated_access_routes.py server/api/__init__.py
git commit -m "refactor: extract authenticated read routes"
```

### Task 3: Simplify authenticated access composition after extraction

**Objective:** Leave `server/api/authenticated_access_routes.py` materially smaller and convention-aligned after the extraction.

**Files:**
- Modify: `server/api/authenticated_access_routes.py`
- Modify if needed: `server/api/authenticated_read_routes.py`

**Step 1: Review for obvious duplication**

Look for duplicated response helpers, dependency declarations, or helper names that can stay small and explicit without creating a frameworky abstraction.

**Step 2: Apply the smallest useful simplification**

Prefer tiny local aliases or helper reuse only if they clearly reduce repetition without obscuring auth/error behavior.

**Step 3: Run focused tests**

Run: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing or join or orders'`
Expected: PASS.

**Step 4: Commit**

```bash
git add server/api/authenticated_access_routes.py server/api/authenticated_read_routes.py
git commit -m "refactor: simplify authenticated access route composition"
```

### Task 4: Full verification and BMAD closeout

**Objective:** Confirm the refactor is complete, simple, and fully documented.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/35-2-extract-authenticated-profile-state-and-briefing-reads-out-of-server-api-authenticated_access_routes-py.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify if needed: `_bmad-output/planning-artifacts/epics.md`
- Modify: `docs/plans/2026-04-01-story-35-2-authenticated-read-route-extraction.md`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing or join or orders'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'profile or state or briefing or join or orders'`

Expected: PASS.

**Step 2: Run formatting and repo gate**

Run:
- `make format`
- `source .venv/bin/activate && make quality`

Expected: PASS.

**Step 3: Simplification / review pass**

Check for:
- no contract drift in paths, response models, auth semantics, or fog/briefing behavior
- no unnecessary service layer or callback abstraction
- a materially smaller `server/api/authenticated_access_routes.py`
- alignment with the repo’s existing route-extraction style

**Step 4: Update BMAD artifacts**

Mark Story 35.2 done, capture debug commands, completion notes, and file list, and advance `sprint-status.yaml` to the next practical story.

**Step 5: Commit**

```bash
git add server/api/ tests/api/test_agent_api.py tests/e2e/test_api_smoke.py \
  _bmad-output/implementation-artifacts/35-2-extract-authenticated-profile-state-and-briefing-reads-out-of-server-api-authenticated_access_routes-py.md \
  _bmad-output/implementation-artifacts/sprint-status.yaml \
  docs/plans/2026-04-01-story-35-2-authenticated-read-route-extraction.md

git commit -m "refactor: extract authenticated read routes"
```
