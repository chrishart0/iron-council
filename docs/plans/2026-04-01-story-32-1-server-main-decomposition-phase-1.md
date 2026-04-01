# Story 32.1 Server Main Decomposition Phase 1 Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Reduce concentration in `server/main.py` by extracting the public/read-only API surface, realtime websocket wiring, and validation/app-wiring helpers into dedicated modules while preserving the shipped contracts.

**Architecture:** Keep `create_app()` as the public entrypoint and move only structural concerns in this slice: reusable app/validation wiring plus public/realtime route registration. Do not change route paths, response models, auth behavior, runtime semantics, or the existing registry/runtime/database contracts. Prefer boring module seams such as `server/api/errors.py`, `server/api/public_routes.py`, and `server/api/realtime_routes.py` over inventing a new framework abstraction.

**Tech Stack:** FastAPI, Pydantic, existing `server` runtime/auth/registry modules, pytest/httpx TestClient coverage, repo `make quality` gate.

---

## Parallelism / Sequencing

- **Sequential implementation only:** this story touches the same FastAPI app-factory seam, shared validation behavior, and websocket/runtime state wiring. One worktree should own the refactor end-to-end.
- **Safe parallel work after implementation:** spec-compliance review and code-quality review can run independently once the implementation worker finishes.
- **Scope guardrails:** no new endpoints, no response-shape changes, no auth-model changes, no runtime-loop redesign, no client work.

### Task 1: Lock the public contract with focused regression tests

**Objective:** Add or tighten tests that would fail if router extraction changes the shipped route surface or structured validation behavior.

**Files:**
- Modify: `tests/api/test_agent_api.py`
- Modify if needed: `tests/agent_sdk/test_python_client.py`
- Modify if needed: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing tests**

Add/adjust focused tests that prove:
- `create_app()` still serves `/`, `/health`, `/api/v1/matches`, `/api/v1/leaderboard`, `/api/v1/matches/{match_id}`, and the history routes.
- websocket endpoints `/ws/match/{match_id}` and `/ws/matches/{match_id}` still exist and preserve current auth/error behavior.
- route-specific validation mapping remains structured for at least one representative route in each family already handled by the custom validation brancher:
  - lobby create
  - join
  - commands
  - messages / group chats
  - treaties / alliances

**Step 2: Run test to verify failure**

Run:
```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'health or leaderboard or history or websocket or validation'
```

Expected: FAIL if the new coverage asserts contracts not yet pinned.

**Step 3: Write minimal implementation-support assertions**

Keep assertions at the public boundary:
- HTTP status / JSON payload shape
- websocket close reason / initial envelope behavior
- structured error code/message behavior

Do not assert internal module names or FastAPI registration details.

**Step 4: Run test to verify pass**

Run:
```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'health or leaderboard or history or websocket or validation'
```

Expected: PASS.

### Task 2: Extract reusable app-wiring and validation handling

**Objective:** Move `ApiError`, shared error-response helpers, and request-validation routing out of `server/main.py` into dedicated app-wiring modules.

**Files:**
- Create: `server/api/__init__.py`
- Create: `server/api/errors.py`
- Modify: `server/main.py`
- Modify tests only if import paths or direct helper coverage require it: `tests/api/test_agent_api.py`

**Step 1: Write failing test or coverage anchor**

If Task 1 did not already pin the validation behavior sufficiently, add one more focused API test for a route-specific validation mapping that would regress if the branch table changes.

**Step 2: Run test to verify failure (if new assertion added)**

Run:
```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'validation'
```

**Step 3: Write minimal implementation**

Extract into `server/api/errors.py`:
- `ApiError`
- shared `API_ERROR_RESPONSE_SCHEMA` / authenticated-response helper(s)
- reusable validation-response builders
- app exception-handler registration helper for `ApiError` + `RequestValidationError`

Keep the behavior identical:
- same status codes
- same `code` / `message` values
- same route-family matching rules

**Step 4: Run focused tests**

Run:
```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'validation or health'
```

Expected: PASS.

### Task 3: Extract public/read-only HTTP routes and websocket routes into router modules

**Objective:** Move the non-authenticated/public surface and realtime websocket registration out of `server/main.py` while keeping `create_app()` behavior unchanged.

**Files:**
- Create: `server/api/public_routes.py`
- Create: `server/api/realtime_routes.py`
- Modify: `server/main.py`
- Modify: `tests/api/test_agent_api.py`
- Modify if needed: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing tests**

If Task 1 did not already pin these routes strongly enough, add tests that prove:
- the extracted public routes still use the same response models and fallback behavior between memory and DB-backed mode
- websocket registration still sends the first envelope before long-lived receive handling and preserves invalid-viewer / auth mismatch behavior

**Step 2: Run test to verify failure**

Run:
```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'matches or leaderboard or history or websocket'
```

**Step 3: Write minimal implementation**

Create router-registration functions that receive explicit dependencies/services rather than reading globals. Keep the design simple:
- `build_public_api_router(...) -> APIRouter`
- `register_realtime_routes(app, ...) -> None` or similarly boring helpers

`server/main.py` should keep:
- environment/settings loading
- registry/runtime construction
- `FastAPI(...)` creation
- high-level composition of extracted helpers/routers
- the remaining authenticated write/read routes still not in scope for this story

**Step 4: Run focused tests**

Run:
```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'matches or leaderboard or history or websocket'
```

Expected: PASS.

### Task 4: Simplify the final composition and run the real gate

**Objective:** Leave the repo in a simpler coherent state, update BMAD artifacts, and prove the refactor at the real quality boundary.

**Files:**
- Modify: `server/main.py`
- Modify: `_bmad-output/planning-artifacts/epics.md`
- Create/Modify: `_bmad-output/implementation-artifacts/32-1-extract-public-and-realtime-route-registration-from-server-main.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify if needed: `docs/issues/public-readiness-follow-ups.md`

**Step 1: Do a simplification pass**

Before final verification, check for:
- duplicated closures/helpers left in `server/main.py`
- unnecessary indirection between router modules and existing server services
- any KISS violations introduced solely to make the refactor “generic”

**Step 2: Run focused server verification**

Run:
```bash
uv run pytest --no-cov tests/api/test_agent_api.py tests/agent_sdk/test_python_client.py
```

Expected: PASS.

**Step 3: Run the real repo quality gate**

Run:
```bash
make quality
```

Expected: PASS.

**Step 4: Update BMAD tracking**

After verification:
- mark Story 32.1 done in sprint tracking
- leave Epic 32 in progress unless Story 32.2 and 32.3 are also completed
- record the story artifact with completion notes and file list

**Step 5: Commit**

```bash
git add server/main.py server/api tests/api/test_agent_api.py tests/agent_sdk/test_python_client.py _bmad-output/planning-artifacts/epics.md _bmad-output/implementation-artifacts/32-1-extract-public-and-realtime-route-registration-from-server-main.md _bmad-output/implementation-artifacts/sprint-status.yaml docs/plans/2026-04-01-story-32-1-server-main-decomposition-phase-1.md
git commit -m "refactor: extract public and realtime server routes"
```
