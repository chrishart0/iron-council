# Story 48.1 API key lifecycle endpoints for owned agent identities Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add the first honest self-serve BYOA onboarding slice by letting authenticated humans list, create, and revoke their own agent API keys through the shipped API, with docs discoverability but no client UI requirement yet.

**Architecture:** Keep this story server-first and contract-first. Reuse the existing Bearer-token authenticated human surface, add the smallest DB-backed lifecycle helpers and typed API models needed for compact key summaries plus one-time secret reveal, then prove the result from behavior-first API/process tests before any follow-on browser UX story. Preserve the existing `X-API-Key` agent auth contract by making revocation feed directly into the same active-key resolution path.

**Tech Stack:** FastAPI, SQLAlchemy models, existing auth/app-service dependencies, pytest API/process tests, Markdown docs, repo quality gate via `make quality`.

---

### Task 1: Pin the public contract with failing server-boundary tests

**Objective:** Define the lifecycle contract from the authenticated human API boundary before writing production code.

**Files:**
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/api/test_agent_process_api.py`
- Optionally modify: `tests/support.py`

**Step 1: Write failing tests for list/create/revoke flows**

Add behavior-first tests that prove:

```python
def test_authenticated_human_can_list_owned_agent_api_keys(client, human_token):
    response = client.get(
        "/api/v1/account/api-keys",
        headers={"Authorization": f"Bearer {human_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert all("raw_key" not in item for item in payload["items"])
```

```python
def test_create_agent_api_key_reveals_secret_once(client, human_token):
    response = client.post(
        "/api/v1/account/api-keys",
        headers={"Authorization": f"Bearer {human_token}"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["api_key"].startswith("iron_")
    assert payload["summary"]["is_active"] is True
```

```python
def test_revoked_api_key_is_rejected_by_existing_agent_auth_contract(client, created_key):
    revoke = client.delete(
        f"/api/v1/account/api-keys/{created_key.key_id}",
        headers={"Authorization": f"Bearer {created_key.owner_token}"},
    )
    assert revoke.status_code == 200

    current_profile = client.get(
        "/api/v1/agent/profile",
        headers={"X-API-Key": created_key.raw_key},
    )
    assert current_profile.status_code == 401
    assert current_profile.json()["error"]["code"] == "invalid_api_key"
```

Also add at least one ownership/negative-path test:
- missing bearer token -> 401
- revoke someone else’s key -> 404 or ownership-safe unauthorized response per repo convention
- a post-create list read never echoes the raw secret

**Step 2: Run the focused slice to verify failure**

Run:

```bash
source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'api_key and (lifecycle or current_agent_profile or invalid)'
```

Expected: FAIL because the lifecycle routes/models do not exist yet.

**Step 3: Add the smallest running-app proof**

Add one real-process test in `tests/api/test_agent_process_api.py` that exercises create -> revoke -> rejected `X-API-Key` auth against the running server boundary.

**Step 4: Run the running-app slice to verify failure**

Run:

```bash
source .venv/bin/activate && uv run pytest --no-cov tests/api/test_agent_process_api.py -k 'api_key and (lifecycle or invalid)' -q
```

Expected: FAIL before implementation.

**Step 5: Commit**

```bash
git add tests/api/test_agent_api.py tests/api/test_agent_process_api.py tests/support.py
git commit -m "test: pin agent api key lifecycle contract"
```

### Task 2: Add DB-backed lifecycle models and service helpers

**Objective:** Introduce the smallest typed persistence/service seam needed to back the lifecycle contract safely.

**Files:**
- Modify: `server/db/models.py`
- Create or modify: `server/db/identity.py`
- Create or modify: `server/models/api.py`
- Optionally create: `server/db/api_key_lifecycle.py`
- Optionally modify: `alembic/versions/...` only if an additive column is truly required

**Step 1: Model the response shapes explicitly**

Add compact response models such as:

```python
class OwnedApiKeySummary(BaseModel):
    key_id: str
    elo_rating: int
    is_active: bool
    created_at: datetime

class OwnedApiKeyListResponse(BaseModel):
    items: list[OwnedApiKeySummary]

class OwnedApiKeyCreateResponse(BaseModel):
    api_key: str
    summary: OwnedApiKeySummary
```

Keep the read model intentionally small and never include `key_hash` or raw secret fields on list/read responses.

**Step 2: Add minimal service helpers**

Implement narrowly scoped helpers for:
- list owned keys by `user_id`
- create a new key row with a generated raw secret and stored hash
- mark a key inactive by `user_id + key_id`

Prefer one small module if the logic does not fit cleanly into an existing DB helper file.

**Step 3: Preserve existing auth behavior**

Make revocation feed the already-shipped active-key lookup path. The implementation should not need a second auth registry: inactive keys should naturally fail where `resolve_authenticated_agent_from_db_key_hash(...)` currently rejects inactive rows.

**Step 4: Keep schema changes minimal**

If the current `api_keys` table is sufficient, do not add a migration. If you must add a tiny additive field (for example a display label), keep it optional, document why, and add the migration in the same task.

**Step 5: Commit**

```bash
git add server/db/models.py server/db/identity.py server/models/api.py server/db/api_key_lifecycle.py alembic/versions
git commit -m "feat: add owned api key lifecycle service models"
```

### Task 3: Add authenticated FastAPI lifecycle routes

**Objective:** Expose the lifecycle helpers through the existing authenticated human API surface.

**Files:**
- Modify: `server/api/authenticated_read_routes.py`
- Modify: `server/api/authenticated_write_routes.py`
- Modify: `server/api/app_services.py`
- Optionally modify: `server/main.py` or router registration only if needed by the current extraction layout

**Step 1: Add route handlers with stable auth semantics**

Prefer routes under a clearly human-owned account namespace, for example:

```python
@router.get("/account/api-keys", response_model=OwnedApiKeyListResponse)
async def list_owned_api_keys(...):
    ...

@router.post("/account/api-keys", response_model=OwnedApiKeyCreateResponse, status_code=201)
async def create_owned_api_key(...):
    ...

@router.delete("/account/api-keys/{key_id}", response_model=OwnedApiKeySummary)
async def revoke_owned_api_key(...):
    ...
```

Use the existing bearer-token human auth dependency. Do not allow `X-API-Key` auth to manage account-owned keys.

**Step 2: Return honest ownership-safe errors**

For nonexistent or non-owned keys, prefer the repo’s existing structured `ApiError` shape and avoid leaking whether another user owns the key.

**Step 3: Run the focused tests to verify green**

Run:

```bash
source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'api_key and (lifecycle or current_agent_profile or invalid)'
source .venv/bin/activate && uv run pytest --no-cov tests/api/test_agent_process_api.py -k 'api_key and (lifecycle or invalid)' -q
```

Expected: PASS.

**Step 4: Simplify before moving on**

Check for overengineering:
- no duplicate auth stacks
- no billing/entitlement abstractions yet
- no secret persistence beyond the existing hashed-key model
- the route surface is small and typed

**Step 5: Commit**

```bash
git add server/api/authenticated_read_routes.py server/api/authenticated_write_routes.py server/api/app_services.py server/main.py
git commit -m "feat: add authenticated api key lifecycle routes"
```

### Task 4: Refresh the BYOA entrypoint docs narrowly

**Objective:** Make the new onboarding surface discoverable without requiring any client UI work yet and without overselling future billing or guided-agent features.

**Files:**
- Modify: `README.md`
- Modify: `docs/index.md`
- Modify: `agent-sdk/README.md`
- Optionally modify: `core-plan.md` only if one sentence needs to clarify that pricing is future-facing while local/manual key issuance now exists

**Step 1: Add the minimal docs delta**

Document:
- authenticated humans can now create/revoke agent keys
- raw secret is shown once only
- the SDK/example agent uses the created key through `X-API-Key`
- billing/entitlement remains future work

**Step 2: Add or extend a tiny docs regression if needed**

If the repo already has a lightweight docs test location, add one small assertion that the BYOA entrypoint docs mention self-serve key creation without promising Stripe is already live.

**Step 3: Run docs verification**

Run:

```bash
source .venv/bin/activate && uv run pytest --no-cov tests/test_local_dev_docs.py -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add README.md docs/index.md agent-sdk/README.md tests/test_local_dev_docs.py core-plan.md
git commit -m "docs: describe self-serve agent key onboarding"
```

### Task 5: Run the full quality gate and close out BMAD artifacts

**Objective:** Finish in a coherent shippable state and update delivery tracking with real results.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/48-1-add-authenticated-api-key-lifecycle-endpoints-for-owned-agent-identities.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `docs/plans/2026-04-03-story-48-1-api-key-lifecycle.md`

**Step 1: Run the real repo gate**

```bash
source .venv/bin/activate && make quality
```

Expected: PASS.

**Step 2: Do the review/simplification pass**

Check:
- `git diff --stat`
- the route/auth surface is still narrow
- secrets are not echoed anywhere except the explicit one-time create response
- no accidental client/billing/guided-mode scope creep landed

**Step 3: Update the story artifact honestly**

Record the actual commands, failures, fixes, and final outcomes in the BMAD story file. Mark complete signoff only after controller-side verification passes.

**Step 4: Update sprint tracking**

Mark Story 48.1 done and advance `next_story` to Story 48.2 only if the controller verification is green.

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add self-serve agent api key lifecycle"
```
