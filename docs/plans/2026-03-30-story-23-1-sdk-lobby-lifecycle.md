# Story 23.1 SDK Lobby Lifecycle Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extend the standalone Python SDK and runnable example so external agents can create, join, and start DB-backed lobbies through the public API.

**Architecture:** Keep the SDK self-contained in `agent-sdk/python/iron_council_client.py` with narrow typed request/response models and one new `start_match_lobby()` helper mirroring the compact server contract. Verify the consumer boundary with behavior-first SDK tests plus a real-process smoke that follows the documented lifecycle against the DB-backed app. Update the example and README to stay deterministic and runnable in one shot.

**Tech Stack:** Python 3.12, Pydantic v2, httpx, pytest, FastAPI TestClient, uv, Make quality gate.

---

### Task 1: Add failing SDK contract tests for lobby start

**Objective:** Prove the standalone client is missing the new authenticated lobby-start surface before implementation.

**Files:**
- Modify: `tests/agent_sdk/test_python_client.py`
- Test: `tests/agent_sdk/test_python_client.py`

**Step 1: Write failing tests**

Add behavior-first tests that:
- create a DB-backed/TestClient-backed session
- call `client.start_match_lobby(match_id)` on a ready lobby
- assert a typed compact response with `status == MatchStatus.ACTIVE`
- assert structured errors wrap creator-only or not-ready failures

**Step 2: Run test to verify failure**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py -k 'start_match_lobby'`
Expected: FAIL because `IronCouncilClient` lacks `start_match_lobby()` and/or missing response model.

**Step 3: Write minimal implementation**

Add the minimal SDK model/method surface required to satisfy the tests without importing server modules.

**Step 4: Run test to verify pass**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py -k 'start_match_lobby'`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/agent_sdk/test_python_client.py agent-sdk/python/iron_council_client.py
git commit -m "feat: add sdk lobby start helper"
```

### Task 2: Add a real-process SDK lifecycle smoke

**Objective:** Prove an external client can create, join, and start a lobby against the running DB-backed app.

**Files:**
- Modify: `tests/e2e/test_agent_sdk_smoke.py`
- Test: `tests/e2e/test_agent_sdk_smoke.py`

**Step 1: Write failing smoke test**

Add a real-process smoke using two SDK clients that:
- creates a lobby with client A
- joins it with client B
- starts it with client A
- asserts the started response is active and compact

**Step 2: Run test to verify failure**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_agent_sdk_smoke.py -k 'lobby_lifecycle'`
Expected: FAIL until the SDK surface/example is in place.

**Step 3: Implement minimal support**

Reuse existing fixtures/utilities; add only the smoke needed for the public lifecycle.

**Step 4: Run test to verify pass**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_agent_sdk_smoke.py -k 'lobby_lifecycle'`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/e2e/test_agent_sdk_smoke.py
git commit -m "test: add sdk lobby lifecycle smoke"
```

### Task 3: Update the runnable example and quickstart docs

**Objective:** Make the documented consumer flow match the shipped SDK lifecycle.

**Files:**
- Modify: `agent-sdk/python/example_agent.py`
- Modify: `agent-sdk/README.md`
- Test: `tests/agent_sdk/test_example_agent.py`

**Step 1: Write failing example/doc tests**

Add or update tests so the example supports both:
- target an existing match
- create a lobby, optionally join/start it, and emit a concise summary

Also add/adjust doc assertions if needed so the README covers the exact verified commands.

**Step 2: Run tests to verify failure**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_example_agent.py tests/test_local_dev_docs.py`
Expected: FAIL until the example/docs are updated.

**Step 3: Write minimal implementation**

Keep the example deterministic and one-shot. Favor explicit flags over hidden behavior.

**Step 4: Run tests to verify pass**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_example_agent.py tests/test_local_dev_docs.py`
Expected: PASS.

**Step 5: Commit**

```bash
git add agent-sdk/python/example_agent.py agent-sdk/README.md tests/agent_sdk/test_example_agent.py tests/test_local_dev_docs.py
git commit -m "docs: add sdk lobby lifecycle quickstart"
```

### Task 4: Run focused gates, full quality, and review

**Objective:** Verify the story from the consumer boundary and leave a simple shippable result.

**Files:**
- Verify: `agent-sdk/python/iron_council_client.py`
- Verify: `agent-sdk/python/example_agent.py`
- Verify: `agent-sdk/README.md`
- Verify: `tests/agent_sdk/test_python_client.py`
- Verify: `tests/e2e/test_agent_sdk_smoke.py`

**Step 1: Run focused verification**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py -k 'start_match_lobby or create_match_lobby'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_agent_sdk_smoke.py -k 'lobby_lifecycle or smoke_flow'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_example_agent.py
```

Expected: PASS.

**Step 2: Run the repo quality gate**

Run: `make quality`
Expected: PASS.

**Step 3: Review and simplify**

- remove unnecessary abstractions
- keep the SDK independent from repo-internal server modules
- ensure the README command path matches the verified smoke path

**Step 4: Commit**

```bash
git add agent-sdk/python/iron_council_client.py agent-sdk/python/example_agent.py agent-sdk/README.md tests/agent_sdk/test_python_client.py tests/e2e/test_agent_sdk_smoke.py tests/agent_sdk/test_example_agent.py _bmad-output/implementation-artifacts/23-1-extend-the-python-sdk-and-example-quickstart-for-authenticated-lobby-lifecycle-flows.md _bmad-output/implementation-artifacts/sprint-status.yaml _bmad-output/planning-artifacts/epics.md docs/plans/2026-03-30-story-23-1-sdk-lobby-lifecycle.md
git commit -m "feat: add sdk lobby lifecycle workflow"
```
