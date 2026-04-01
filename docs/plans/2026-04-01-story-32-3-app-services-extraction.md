# Story 32.3 App Services Extraction Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Refactor the remaining authenticated lobby and player-access HTTP wiring out of `server/main.py` and centralize mixed agent/human access resolution behind explicit reusable app services without changing the shipped API or websocket contracts.

**Architecture:** Add a small `server/api/app_services.py` module that owns authenticated actor resolution, joined-player lookup, DB-backed availability checks, and websocket player-view resolution. Then move the remaining authenticated lobby/profile/state/briefing/join/orders routes into one dedicated router module that receives those services explicitly from `create_app()`.

**Tech Stack:** FastAPI, Pydantic, Python 3.12, pytest, httpx/ASGITransport, uv, make quality.

---

### Task 1: Pin the remaining contract with focused tests

**Objective:** Add/adjust API-boundary tests that prove the extracted lobby and player-access helpers preserve the current contract.

**Files:**
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/e2e/test_api_smoke.py` (only if a real-process regression seam is missing)

**Step 1: Write failing tests**

Add or tighten assertions around:
- authenticated `/api/v1/agent/profile`
- mixed-auth `/api/v1/matches/{match_id}/state`
- `/api/v1/matches/{match_id}/agent-briefing`
- `/api/v1/matches/{match_id}/join`
- `/api/v1/matches`
- `/api/v1/matches/{match_id}/start`
- `/api/v1/matches/{match_id}/orders`
- websocket auth/player-view helper reuse if a focused seam is missing

Prefer route-level behavior assertions over import-path or internal helper assertions.

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing or join or start or orders or create_match_lobby'`
Expected: at least one focused regression should fail before the refactor or reveal the missing seam.

**Step 3: Write minimal implementation**

Only enough test scaffolding/expectations to pin the current contract; do not refactor production code yet.

**Step 4: Run test to verify pass/fail state is understood**

Run: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing or join or start or orders or create_match_lobby'`
Expected: stable baseline with any newly added expectations enforcing the intended contract.

**Step 5: Commit**

```bash
git add tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
git commit -m "test: pin lobby and player access route contract"
```

### Task 2: Extract shared app services

**Objective:** Create a stable service layer for mixed-auth actor resolution and player access.

**Files:**
- Create: `server/api/app_services.py`
- Modify: `server/api/__init__.py`
- Modify: `server/main.py`

**Step 1: Write failing test**

Use the API tests from Task 1 as the contract; no new implementation-detail unit tests needed unless a small pure helper seam is useful.

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'state or briefing or join or start or create_match_lobby'`
Expected: FAIL once production code is partially moved or imports are unresolved.

**Step 3: Write minimal implementation**

Add an explicit service module with small boring pieces, for example:

```python
@dataclass(frozen=True, slots=True)
class AuthenticatedLobbyActor:
    kind: Literal["agent", "human"]
    agent: AuthenticatedAgentContext | None = None
    api_key: str | None = None
    human_user_id: str | None = None

@dataclass(frozen=True, slots=True)
class AppServices:
    settings: Settings
    history_database_url: str | None
    resolve_authenticated_agent_context: Callable[..., AuthenticatedAgentContext | None]
    resolve_authenticated_human_user_id: Callable[..., str]
    resolve_authenticated_lobby_actor: Callable[..., AuthenticatedLobbyActor]
    require_joined_player_id: Callable[..., str]
    resolve_match_player_id: Callable[..., str]
    resolve_websocket_player_viewer: Callable[..., str | None]
```

Keep implementation explicit; use existing registry/db/auth helpers rather than inventing new abstractions.

**Step 4: Run tests to verify pass**

Run: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'state or briefing or join or start or create_match_lobby'`
Expected: PASS.

**Step 5: Commit**

```bash
git add server/api/app_services.py server/api/__init__.py server/main.py
git commit -m "refactor: extract authenticated app services"
```

### Task 3: Extract lobby and player-access routes

**Objective:** Move the remaining authenticated HTTP routes out of `server/main.py` while keeping `create_app()` as composition only.

**Files:**
- Create: `server/api/authenticated_access_routes.py`
- Modify: `server/api/__init__.py`
- Modify: `server/main.py`

**Step 1: Write failing test**

Reuse the focused route contract from Task 1.

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing or join or start or orders or create_match_lobby'`
Expected: FAIL during extraction until the router is fully wired.

**Step 3: Write minimal implementation**

Move these routes into the new router module with explicit injected dependencies:
- `POST /api/v1/matches`
- `POST /api/v1/matches/{match_id}/start`
- `GET /api/v1/agent/profile`
- `GET /api/v1/agents/{agent_id}/profile`
- `GET /api/v1/matches/{match_id}/state`
- `GET /api/v1/matches/{match_id}/agent-briefing`
- `POST /api/v1/matches/{match_id}/join`
- `POST /api/v1/matches/{match_id}/orders`

Do not change response models, status codes, error codes, or runtime side effects such as `ensure_match_running()`.

**Step 4: Run tests to verify pass**

Run: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing or join or start or orders or create_match_lobby'`
Expected: PASS.

**Step 5: Commit**

```bash
git add server/api/authenticated_access_routes.py server/api/__init__.py server/main.py
git commit -m "refactor: extract authenticated access routes"
```

### Task 4: Full verification and simplification

**Objective:** Confirm the refactor is complete, simple, and convention-aligned.

**Files:**
- Modify if needed: `server/main.py`
- Modify if needed: `server/api/app_services.py`
- Modify if needed: `server/api/authenticated_access_routes.py`
- Modify: `_bmad-output/implementation-artifacts/32-3-extract-authenticated-lobby-and-player-access-helpers-behind-stable-app-services.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'profile or state or briefing or join or start or orders or create_match_lobby'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'profile or join or state or start'`

Expected: PASS.

**Step 2: Run formatting/quality**

Run:
- `make format`
- `make quality`

Expected: PASS.

**Step 3: Simplification pass**

Review diffs for:
- unnecessary wrapper classes
- duplicated auth/error mapping
- any `server/main.py` helper that now belongs in app services or can be deleted
- KISS violations vs the existing router extraction style

**Step 4: Update BMAD artifacts**

Mark story done, record debug commands/completion notes/file list, update `sprint-status.yaml`, and set the next story/epic status pragmatically.

**Step 5: Commit**

```bash
git add server/api/ server/main.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py \
  _bmad-output/implementation-artifacts/32-3-extract-authenticated-lobby-and-player-access-helpers-behind-stable-app-services.md \
  _bmad-output/implementation-artifacts/sprint-status.yaml docs/plans/2026-04-01-story-32-3-app-services-extraction.md
git commit -m "refactor: extract authenticated lobby and access app services"
```
