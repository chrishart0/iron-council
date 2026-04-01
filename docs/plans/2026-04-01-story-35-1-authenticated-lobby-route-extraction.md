# Story 35.1 Authenticated Lobby Route Extraction Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extract authenticated lobby creation/start route wiring out of `server/api/authenticated_access_routes.py` into a focused route module without changing the shipped HTTP contract, mixed-auth behavior, or runtime side effects.

**Architecture:** Keep `server/api/authenticated_access_routes.py` as the stable composition entrypoint for profile/state/briefing/join/order routes, but delegate lobby lifecycle registration to a new focused module such as `server/api/authenticated_lobby_routes.py`. Reuse the existing `AppServices` mixed-auth helpers and keep DB-backed create/start error mapping, registry seeding, and `ensure_match_running()` behavior explicit and boring.

**Tech Stack:** FastAPI, Python 3.12, Pydantic, pytest, uv, make quality, Codex in an isolated git worktree.

---

### Task 1: Pin authenticated lobby lifecycle behavior with focused regressions

**Objective:** Lock the create/start route contract before moving code.

**Files:**
- Modify if needed: `tests/api/test_agent_api.py`
- Modify if needed: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing test**

Add or tighten behavior-first assertions for:
- `POST /api/v1/matches` preserving DB-only availability behavior
- `POST /api/v1/matches/{match_id}/start` preserving mixed-auth precedence and status-code mapping
- registry seeding after DB-backed create/start success
- runtime `ensure_match_running()` side effects after successful start

Prefer route-boundary assertions over internal import-path checks.

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'create_match_lobby or start_match_lobby'`
Expected: FAIL if new coverage exposes an unpinned seam, or PASS once the contract is pinned and understood.

**Step 3: Write minimal implementation**

Only add the smallest regression coverage needed to pin the contract. Do not refactor production code yet.

**Step 4: Run focused tests again**

Run:
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'create_match_lobby or start_match_lobby'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'create_match_lobby or start_match_lobby'`

Expected: PASS baseline with contract coverage in place.

**Step 5: Commit**

```bash
git add tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
git commit -m "test: pin authenticated lobby lifecycle routes"
```

### Task 2: Extract the authenticated lobby lifecycle router

**Objective:** Move create/start handlers into a focused route-builder module while preserving the public contract exactly.

**Files:**
- Create: `server/api/authenticated_lobby_routes.py`
- Modify: `server/api/authenticated_access_routes.py`
- Modify: `server/api/__init__.py`

**Step 1: Write failing test**

Reuse the Task 1 route contract. No implementation-detail unit tests.

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'create_match_lobby or start_match_lobby'`
Expected: FAIL while imports or delegated route wiring are mid-extraction.

**Step 3: Write minimal implementation**

Create a focused router builder with explicit injected dependencies, for example:

```python
def build_authenticated_lobby_router(
    *,
    match_registry_provider: RegistryProvider,
    app_services: AppServices,
    ensure_match_running: EnsureMatchRunning,
) -> APIRouter:
    ...
```

Keep these behaviors unchanged:
- `POST /api/v1/matches` path, response model, `201 Created`, and DB-backed-only enforcement
- `POST /api/v1/matches/{match_id}/start` path, response model, and exact status mapping
- Bearer-vs-API-key precedence through `AppServices.resolve_authenticated_lobby_actor(...)`
- `hash_api_key(...)`, DB registry calls, registry seeding, and `await ensure_match_running(match_id)`

Then have `build_authenticated_access_router(...)` include the extracted router rather than owning the handlers inline.

**Step 4: Run focused tests to verify pass**

Run:
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'create_match_lobby or start_match_lobby'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'create_match_lobby or start_match_lobby'`

Expected: PASS.

**Step 5: Commit**

```bash
git add server/api/authenticated_lobby_routes.py server/api/authenticated_access_routes.py server/api/__init__.py
git commit -m "refactor: extract authenticated lobby lifecycle routes"
```

### Task 3: Simplify the remaining authenticated access router

**Objective:** Leave `server/api/authenticated_access_routes.py` materially smaller and convention-aligned after the extraction.

**Files:**
- Modify: `server/api/authenticated_access_routes.py`
- Modify if needed: `server/api/authenticated_lobby_routes.py`

**Step 1: Review for obvious duplication**

Look for duplicated response helpers, repeated dependency declarations, or helper constants that can stay local and boring.

**Step 2: Apply the smallest simplification**

Prefer tiny helper reuse only if it clearly reduces repetition without introducing a frameworky abstraction.

**Step 3: Run focused tests**

Run: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing or join or orders or create_match_lobby or start_match_lobby'`
Expected: PASS.

**Step 4: Commit**

```bash
git add server/api/authenticated_access_routes.py server/api/authenticated_lobby_routes.py
git commit -m "refactor: simplify authenticated access route composition"
```

### Task 4: Full verification and BMAD closeout

**Objective:** Confirm the refactor is complete, simple, and fully documented.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/35-1-extract-authenticated-lobby-lifecycle-routes-out-of-server-api-authenticated_access_routes-py.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify if needed: `_bmad-output/planning-artifacts/epics.md`
- Modify: `docs/plans/2026-04-01-story-35-1-authenticated-lobby-route-extraction.md`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing or join or orders or create_match_lobby or start_match_lobby'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'profile or join or state or create_match_lobby or start_match_lobby'`

Expected: PASS.

**Step 2: Run formatting and repo gate**

Run:
- `make format`
- `source .venv/bin/activate && make quality`

Expected: PASS.

**Step 3: Simplification / review pass**

Check for:
- no contract drift in paths, response models, or auth/error semantics
- no unnecessary service layer or callback abstraction
- a materially smaller `server/api/authenticated_access_routes.py`
- alignment with the repo’s existing route-extraction style

**Step 4: Update BMAD artifacts**

Mark Story 35.1 done, capture debug commands, completion notes, and file list, and advance `sprint-status.yaml` to the next story pragmatically.

**Step 5: Commit**

```bash
git add server/api/ tests/api/test_agent_api.py tests/e2e/test_api_smoke.py \
  _bmad-output/implementation-artifacts/35-1-extract-authenticated-lobby-lifecycle-routes-out-of-server-api-authenticated_access_routes-py.md \
  _bmad-output/implementation-artifacts/sprint-status.yaml \
  docs/plans/2026-04-01-story-35-1-authenticated-lobby-route-extraction.md

git commit -m "refactor: extract authenticated lobby lifecycle routes"
```
