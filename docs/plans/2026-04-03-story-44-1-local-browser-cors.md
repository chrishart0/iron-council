# Story 44.1 Local browser-to-API CORS support Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Let the local Next.js browser client talk to the FastAPI API at `http://127.0.0.1:8000` from `http://127.0.0.1:3000` without CORS failures, while keeping the production/runtime policy explicit and configurable.

**Architecture:** Add a tiny explicit CORS settings seam in `server/settings.py`, wire Starlette `CORSMiddleware` in `server/main.py`, and keep the default development allowlist narrowly scoped to the shipped local browser origin(s). Prove the behavior from the HTTP boundary with preflight and simple request tests, then document the local workflow so the README matches the real behavior.

**Tech Stack:** Python 3.12, FastAPI, Starlette CORSMiddleware, pytest/httpx, README docs.

---

## Parallelism / sequencing decision

- **Sequential implementation.** Settings, middleware wiring, and API-boundary tests all touch the same app-construction seam.
- **No parallel Codex split.** The change is small and highly coupled; a single worker is the safest/simplest path.

---

### Task 1: Add a minimal explicit CORS settings seam

**Objective:** Define how local/browser origins are configured before touching middleware wiring.

**Files:**
- Modify: `server/settings.py`
- Test: `tests/api/test_agent_api.py`

**Step 1: Write failing test**

Add a focused settings/app-boundary test proving that an app built for local development treats `http://127.0.0.1:3000` as allowed and preserves an explicit override string when provided.

```python
assert app.state.settings.allowed_browser_origins == (
    "http://127.0.0.1:3000",
    "http://localhost:3000",
)
```

**Step 2: Run test to verify failure**

Run:
`source .venv/bin/activate && pytest -o addopts='' tests/api/test_agent_api.py -k 'cors'`

Expected: FAIL because the settings model does not yet expose browser origins.

**Step 3: Write minimal implementation**

Add a small parsed tuple field on `Settings`, backed by an env var such as `IRON_COUNCIL_BROWSER_ORIGINS`, with a boring comma-separated parser and a narrow default allowlist for local browser origins.

**Step 4: Run test to verify pass**

Run:
`source .venv/bin/activate && pytest -o addopts='' tests/api/test_agent_api.py -k 'cors'`

Expected: PASS.

**Step 5: Commit**

```bash
git add server/settings.py tests/api/test_agent_api.py
git commit -m "feat: add browser origin settings"
```

---

### Task 2: Wire CORSMiddleware at the FastAPI boundary

**Objective:** Make the shipped app actually emit the required CORS headers for the local browser flow.

**Files:**
- Modify: `server/main.py`
- Test: `tests/api/test_agent_api.py`

**Step 1: Write failing test**

Add HTTP-boundary regressions that prove:
- a preflight `OPTIONS` request from `http://127.0.0.1:3000` gets the expected `access-control-allow-origin`
- a normal `GET /api/v1/matches` from that origin also gets the CORS header
- an unlisted origin does **not** get an allow-origin echo

```python
response = await app_client.options(
    "/api/v1/matches",
    headers={
        "Origin": "http://127.0.0.1:3000",
        "Access-Control-Request-Method": "GET",
    },
)
assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
```

**Step 2: Run test to verify failure**

Run:
`source .venv/bin/activate && pytest -o addopts='' tests/api/test_agent_api.py -k 'cors'`

Expected: FAIL because the app does not yet install CORS middleware.

**Step 3: Write minimal implementation**

Install `CORSMiddleware` in `create_app()` using the parsed settings tuple. Keep the policy narrow and boring:
- allowed origins = configured browser origins
- allowed methods/headers broad enough for existing browser fetches and auth headers
- no wildcard when explicit origins are present

**Step 4: Run test to verify pass**

Run:
`source .venv/bin/activate && pytest -o addopts='' tests/api/test_agent_api.py -k 'cors'`

Expected: PASS.

**Step 5: Commit**

```bash
git add server/main.py tests/api/test_agent_api.py
git commit -m "feat: enable local browser cors"
```

---

### Task 3: Document the local browser workflow and keep docs/tests in sync

**Objective:** Make the local developer instructions honest about the now-working browser path and configurable origin seam.

**Files:**
- Modify: `README.md`
- Modify: `env.local.example`
- Test: `tests/test_local_dev_docs.py`

**Step 1: Write failing doc test**

Add assertions that the README and env example mention the local browser origin policy / override knob.

```python
assert "IRON_COUNCIL_BROWSER_ORIGINS" in readme
assert "http://127.0.0.1:3000" in readme
assert "IRON_COUNCIL_BROWSER_ORIGINS" in env_example
```

**Step 2: Run test to verify failure**

Run:
`source .venv/bin/activate && pytest -o addopts='' tests/test_local_dev_docs.py`

Expected: FAIL because the docs do not yet mention the browser-origin setting.

**Step 3: Write minimal implementation**

Update the README quickstart/browser section and `env.local.example` to explain:
- the default local browser origin(s) that can call the API
- the optional override env var for alternate local origins/ports
- that the server still runs directly in dev mode against real services

**Step 4: Run test to verify pass**

Run:
`source .venv/bin/activate && pytest -o addopts='' tests/test_local_dev_docs.py`

Expected: PASS.

**Step 5: Commit**

```bash
git add README.md env.local.example tests/test_local_dev_docs.py
git commit -m "docs: document local browser cors workflow"
```

---

### Task 4: Verify the touched seam and simplify

**Objective:** Re-run the strongest practical checks for the changed server/docs surface and confirm the solution stayed small.

**Files:**
- Review only; no new files unless a small review fix is required.

**Step 1: Run focused verification**

```bash
source .venv/bin/activate && pytest -o addopts='' tests/api/test_agent_api.py -k 'cors'
source .venv/bin/activate && pytest -o addopts='' tests/test_local_dev_docs.py
```

Expected: PASS.

**Step 2: Run repo-managed broader gate for the touched surface**

```bash
source .venv/bin/activate && make quality
```

Expected: PASS.

**Step 3: Simplification pass**

Inspect the diff and confirm:
- no new abstraction beyond one parsed settings seam
- middleware is installed once in `create_app()`
- docs describe only the shipped local behavior, not speculative deployment policy

**Step 4: Commit final coherent state if needed**

```bash
git add README.md env.local.example server/main.py server/settings.py tests/api/test_agent_api.py tests/test_local_dev_docs.py
git commit -m "feat: restore local browser api access"
```

---

## Final handoff / BMAD bookkeeping

After implementation and review:
- update `_bmad-output/implementation-artifacts/44-1-add-local-browser-to-api-cors-support.md`
- mark the story `done` in `_bmad-output/implementation-artifacts/sprint-status.yaml`
- record the real commands run in the story debug log
- only advance `next_story` if a concrete follow-up artifact is drafted in the same run
