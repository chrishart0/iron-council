# Story 15.1 Python Agent SDK Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Ship a small reference Python SDK that wraps the authenticated agent API with a stable, behavior-first client surface and one real-process verification path.

**Architecture:** Add a narrow synchronous `httpx` client under `agent-sdk/python/` with one shared request helper, typed parsing for existing public API responses, and one repo-style exception for structured API failures. Keep the implementation boring: methods map directly to current REST endpoints, tests exercise behavior through the FastAPI boundary, and the quality harness is extended to include the new SDK files.

**Tech Stack:** Python 3.12, httpx, existing FastAPI app + Pydantic models, pytest, real-process smoke tests, Ruff, mypy, make quality.

---

## Parallelism / Sequencing

- **Sequential for implementation:** the client module, its tests, and quality-harness updates all touch the same public contract and should stay in one worktree.
- **Safe additional work this run:** draft Story 15.2 in parallel conceptually, but implement it only after Story 15.1 is green because the example bot depends on the SDK surface.

## Task 1: Define the smallest useful SDK surface

**Objective:** Create one client module with explicit methods for the current authenticated agent workflows and one consistent error type.

**Files:**
- Create: `agent-sdk/python/iron_council_client.py`
- Modify: `pyproject.toml`
- Modify: `Makefile`

**Step 1: Write failing test**

Add a contract test that expects methods like these to exist and perform authenticated calls:

```python
client = IronCouncilClient(
    base_url="http://testserver",
    api_key=build_seeded_agent_api_key("agent-player-2"),
    transport=ASGITransport(app=create_app(match_registry=seeded_registry)),
)

profile = client.get_current_agent_profile()
assert profile.agent_id == "agent-player-2"
```

**Step 2: Run test to verify failure**

Run:

```bash
uv run pytest -o addopts='' tests/agent_sdk/test_python_client.py -k 'profile or matches'
```

Expected: FAIL because the SDK module does not exist yet.

**Step 3: Write minimal implementation**

Implement:
- `IronCouncilClient`
- `IronCouncilApiError`
- one `_request_json()` helper
- direct methods for list/profile/join/state/orders/messages/treaties/alliances

Keep `repr` safe by never storing or echoing the raw API key in exception strings.

**Step 4: Run test to verify pass**

Run the same command as Step 2.

Expected: PASS.

**Step 5: Commit**

```bash
git add agent-sdk/python/iron_council_client.py pyproject.toml Makefile tests/agent_sdk/test_python_client.py
git commit -m "feat: add reference python agent sdk"
```

## Task 2: Cover SDK happy paths and failure propagation at the API boundary

**Objective:** Prove the SDK maps onto the existing agent API contract and surfaces structured failures cleanly.

**Files:**
- Create: `tests/agent_sdk/test_python_client.py`
- Modify: `tests/api/test_agent_api.py` only if fixture reuse or helper extraction is needed

**Step 1: Write failing tests**

Cover:
- `list_matches()`
- `get_current_agent_profile()`
- `join_match()`
- `get_match_state()`
- `submit_orders()`
- one message/treaty/alliance happy path
- structured API failure raising `IronCouncilApiError`
- transport failure raising the same wrapper or a clearly documented SDK exception

Example assertion:

```python
with pytest.raises(IronCouncilApiError) as excinfo:
    client.get_match_state("missing-match")

assert excinfo.value.status_code == 404
assert excinfo.value.error_code == "match_not_found"
```

**Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest -o addopts='' tests/agent_sdk/test_python_client.py
```

Expected: FAIL until the SDK methods and error handling exist.

**Step 3: Write minimal implementation**

Parse JSON into existing public models where that reduces ambiguity; otherwise keep returned payloads simple and typed. Do not add async support, retries, pagination abstractions, or packaging machinery in this story.

**Step 4: Run tests to verify pass**

Run the same command as Step 2.

Expected: PASS.

**Step 5: Commit**

```bash
git add agent-sdk/python/iron_council_client.py tests/agent_sdk/test_python_client.py
git commit -m "test: cover python sdk api workflows"
```

## Task 3: Prove the real running-app path and fold the SDK into the quality harness

**Objective:** Verify the SDK against the real local server boundary and make sure the standard repo checks include the new source files.

**Files:**
- Create: `tests/e2e/test_agent_sdk_smoke.py`
- Modify: `pyproject.toml`
- Modify: `Makefile`
- Modify: `_bmad-output/implementation-artifacts/15-1-add-a-reference-python-sdk-for-authenticated-agent-workflows.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Write failing smoke test**

Add a real-process path using `running_seeded_app`:
1. instantiate the SDK with `base_url` and a seeded API key
2. fetch current profile
3. join the secondary match if needed
4. fetch visible state
5. submit one deterministic order or diplomacy action

**Step 2: Run smoke test to verify failure**

Run:

```bash
uv run pytest --no-cov tests/e2e/test_agent_sdk_smoke.py
```

Expected: FAIL until the SDK works against the real app boundary.

**Step 3: Write minimal implementation and harness updates**

Update lint/type/test config so `agent-sdk/python` is included in Ruff/mypy/quality commands. Keep the change minimal and aligned with current repo patterns.

**Step 4: Run repo verification**

Run:

```bash
uv run pytest -o addopts='' tests/agent_sdk/test_python_client.py
uv run pytest --no-cov tests/e2e/test_agent_sdk_smoke.py
make quality
```

Expected: PASS.

**Step 5: Commit**

```bash
git add agent-sdk/python/iron_council_client.py tests/agent_sdk/test_python_client.py tests/e2e/test_agent_sdk_smoke.py pyproject.toml Makefile _bmad-output/implementation-artifacts/15-1-add-a-reference-python-sdk-for-authenticated-agent-workflows.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "feat: add authenticated python agent sdk"
```

## Final review checklist

- [ ] SDK methods map directly to existing public endpoints and require `X-API-Key`
- [ ] API and transport failures surface one clear exception with structured details
- [ ] No raw API key leakage in logs, errors, or reprs
- [ ] Tests validate public behavior, not helper internals
- [ ] Real-process SDK smoke path passes
- [ ] `make quality` passes with the new SDK files included
- [ ] BMAD story + sprint artifacts updated
