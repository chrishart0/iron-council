# Story 32.2 Authenticated Match Routes Phase 2 Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Reduce concentration in `server/main.py` by extracting authenticated match command, messaging, group-chat, treaty, and alliance routes into focused router modules while preserving the shipped FastAPI contracts and websocket side effects.

**Architecture:** Keep `create_app()` as the public composition entrypoint. Move only the authenticated match route wiring and the smallest supporting route helpers needed for those routes into `server/api` modules with explicit injected dependencies such as registry access, auth dependency, settings/history-aware player resolution, and broadcast callbacks. Do not change paths, response models, status codes, structured error codes/messages, auth precedence, or runtime semantics.

**Tech Stack:** FastAPI, Pydantic, existing `server` auth/registry/runtime modules, pytest/httpx/TestClient boundary tests, repo `make quality` gate.

---

## Parallelism / Sequencing

- **Sequential implementation only:** these routes share the same authenticated player-resolution helpers, registry interactions, and websocket broadcast side effects. One worktree should own the refactor end-to-end.
- **Safe parallel work after implementation:** spec-compliance review and code-quality review can run independently once the implementation worker finishes.
- **Scope guardrails:** no new endpoints, no new auth flows, no new route families, no SDK/client changes, no runtime-loop redesign.

### Task 1: Pin the authenticated route contract with focused regression tests

**Objective:** Add or tighten tests that fail if route extraction changes the shipped authenticated command/messaging/diplomacy behavior.

**Files:**
- Modify: `tests/api/test_agent_api.py`
- Modify if needed: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing tests**

Add/adjust focused API tests that prove at least one representative endpoint in each extracted family preserves:
- route/body mismatch handling (`match_id_mismatch`)
- tick mismatch handling (`tick_mismatch`)
- joined-player/auth requirements
- treaty/alliance/group-chat domain error mapping
- websocket broadcast-triggering write routes still return accepted payloads without changing visible contract

Representative families to pin:
- bundled command envelope: `POST /api/v1/matches/{match_id}/command`
- direct/world messaging: `GET/POST /api/v1/matches/{match_id}/messages`
- group chats: `GET/POST /api/v1/matches/{match_id}/group-chats` and `.../messages`
- treaties and alliances: `GET/POST /api/v1/matches/{match_id}/treaties` and `.../alliances`

**Step 2: Run test to verify failure**

Run:
```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'command or group_chat or treaty or alliance or message'
```

Expected: FAIL if the new assertions pin behavior not already covered.

**Step 3: Keep assertions boundary-focused**

Assert only on:
- HTTP status codes
- response JSON structure/content
- structured API error code/message payloads
- externally visible accepted write semantics

Do not assert internal helper names or router module implementation details.

**Step 4: Run test to verify pass**

Run:
```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'command or group_chat or treaty or alliance or message'
```

Expected: PASS.

### Task 2: Extract authenticated command/messaging/diplomacy routers

**Objective:** Move the authenticated match route registration out of `server/main.py` into one or more focused `server/api` modules with explicit dependencies.

**Files:**
- Create: `server/api/authenticated_match_routes.py`
- Modify if helpful for exports: `server/api/__init__.py`
- Modify: `server/main.py`
- Modify: `tests/api/test_agent_api.py`

**Step 1: Preserve the dependency seam**

Before moving routes, identify the smallest stable injected dependency surface the router builder needs, for example:
- registry dependency / provider
- `get_authenticated_agent` dependency
- settings/history-aware player-resolution helper(s)
- authenticated-response schema helper
- websocket broadcast callback

**Step 2: Write minimal implementation**

Create a router builder such as:
```python
def build_authenticated_match_router(... ) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    ...
    return router
```

Move these route families into the router module:
- command envelope route(s)
- match messages inbox/send routes
- group chat list/create/message routes
- treaty list/action routes
- alliance list/action routes

Keep behavior identical:
- same paths and aliases
- same response models and status codes
- same route/body/tick validation
- same domain-error translation
- same `await broadcast_current_match(match_id)` side effects on the same write routes

**Step 3: Keep `server/main.py` boring**

After extraction, `server/main.py` should still own high-level app composition and any still-unextracted auth/lobby/player helper seams, but no longer define the moved route handlers inline.

**Step 4: Run focused tests**

Run:
```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'command or group_chat or treaty or alliance or message'
```

Expected: PASS.

### Task 3: Simplify remaining route composition and verify repo behavior

**Objective:** Ensure the extracted modules are the simplest correct design and the repo stays green at the real quality boundary.

**Files:**
- Modify: `server/main.py`
- Modify: `server/api/authenticated_match_routes.py`
- Modify: `_bmad-output/implementation-artifacts/32-2-extract-authenticated-match-command-messaging-and-diplomacy-routes-from-server-main.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify if needed: `docs/plans/2026-04-01-story-32-2-authenticated-match-routes-phase-2.md`

**Step 1: Run a simplification pass**

Check for:
- duplicate record lookups or route-local helpers that should be tiny shared closures inside the router builder
- unnecessary generic abstractions or config objects
- import cycles or router code that leaks app-construction concerns back into the module

**Step 2: Run focused verification**

Run:
```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'command or group_chat or treaty or alliance or message'
```

Expected: PASS.

**Step 3: Run the real quality gate**

Run:
```bash
make quality
```

Expected: PASS.

**Step 4: Update BMAD tracking**

After verification:
- mark Story 32.2 done in sprint tracking
- set `next_story` to Story 32.3
- record completion notes and exact changed files in the story artifact

**Step 5: Commit**

```bash
git add server/main.py server/api tests/api/test_agent_api.py _bmad-output/implementation-artifacts/32-2-extract-authenticated-match-command-messaging-and-diplomacy-routes-from-server-main.md _bmad-output/implementation-artifacts/sprint-status.yaml docs/plans/2026-04-01-story-32-2-authenticated-match-routes-phase-2.md
git commit -m "refactor: extract authenticated match routes"
```
