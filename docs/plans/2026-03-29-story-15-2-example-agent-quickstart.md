# Story 15.2 Example Agent and Quickstart Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Ship a minimal runnable example agent plus a quickstart guide that demonstrates the public SDK loop against a real Iron Council server.

**Architecture:** Build one small script under `agent-sdk/python/example_agent.py` that depends only on the local reference SDK. The script should accept base URL, API key, and an optional match id via CLI/env, then perform one deterministic cycle: choose a target match, join if needed, fetch visible state, submit a simple order batch, and print a concise summary. Pair it with `agent-sdk/README.md` so developers can copy the exact setup and run commands. Verify it through behavior-first tests and one real-process CLI smoke path.

**Tech Stack:** Python 3.12, argparse, the local `IronCouncilClient`, pytest, subprocess smoke tests, make quality.

---

## Parallelism / Sequencing

- **Sequential only:** this story depends directly on Story 15.1 and touches the same SDK directory plus docs and smoke tests.
- **Safe simplification pass:** after the example works, trim any unnecessary CLI/config abstractions before final verification.

## Task 1: Add the smallest useful example-agent loop

**Objective:** Create a deterministic one-shot example that uses only the SDK surface and no internal server imports.

**Files:**
- Create: `agent-sdk/python/example_agent.py`
- Modify: `tests/agent_sdk/test_example_agent.py`

**Step 1: Write failing test**

Add behavior-first tests that prove the example agent:
- loads config from CLI args and/or env vars
- uses the SDK rather than raw HTTP
- joins a selected match when needed
- fetches visible state
- submits a deterministic order batch (empty/no-op is acceptable if clearly intentional)
- prints a concise summary that documents what happened

**Step 2: Run test to verify failure**

Run:

```bash
uv run pytest -o addopts='' tests/agent_sdk/test_example_agent.py
```

Expected: FAIL because the script does not exist yet.

**Step 3: Write minimal implementation**

Keep it boring:
- `argparse` + env fallback
- choose `--match-id` or first listed match
- `join_match()` before state polling
- `submit_orders(..., orders={movements: [], recruitment: [], upgrades: [], transfers: []})`
- print one structured summary line or JSON block

**Step 4: Run test to verify pass**

Run the same command as Step 2.

Expected: PASS.

## Task 2: Add a real CLI smoke path and quickstart docs

**Objective:** Prove the documented example-agent commands work against the running seeded app and document them for agent developers.

**Files:**
- Create: `agent-sdk/README.md`
- Modify: `tests/e2e/test_example_agent_smoke.py`
- Modify: `_bmad-output/implementation-artifacts/15-2-add-a-minimal-example-agent-and-sdk-quickstart-guide.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Write failing smoke/doc test**

Add one real-process subprocess-based smoke test that runs the example script with documented env vars/CLI args against `running_seeded_app` and asserts the output shows:
- authenticated agent identity
- chosen/joined match id
- current player id from visible state
- accepted order submission for the current tick

**Step 2: Run smoke test to verify failure**

Run:

```bash
uv run pytest --no-cov tests/e2e/test_example_agent_smoke.py
```

Expected: FAIL until the script and docs exist.

**Step 3: Write minimal docs**

Document:
- where the SDK and example live
- required env vars / CLI args
- exact run command from repo root
- what the example actually does in one cycle
- note that it is intentionally simple and deterministic

**Step 4: Run repo verification**

Run:

```bash
uv run pytest -o addopts='' tests/agent_sdk/test_example_agent.py
uv run pytest --no-cov tests/e2e/test_example_agent_smoke.py
make quality
```

Expected: PASS.

## Final review checklist

- [ ] Example agent imports only the SDK module from `agent-sdk/python`
- [ ] Example flow is deterministic and intentionally simple
- [ ] README commands match the tested smoke path
- [ ] Story artifact and sprint status are updated
- [ ] `make quality` passes
