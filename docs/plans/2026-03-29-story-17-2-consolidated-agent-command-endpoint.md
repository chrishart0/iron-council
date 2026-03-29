# Story 17.2 Consolidated Agent Command Endpoint Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Ship one authenticated command-envelope endpoint that lets an agent submit a turn’s orders, outgoing messages, and diplomacy/alliance actions in one validated all-or-nothing request.

**Architecture:** Keep the existing focused endpoints as the source of truth for public primitives, but add a thin orchestration contract on top. Introduce explicit command-envelope request/response models, implement a registry-level transactional preview/apply helper that validates every included action before mutating state, then expose `/api/v1/matches/{match_id}/command` plus a matching SDK helper. Cover the contract at three levels: API tests, running-app tests, and SDK tests.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, in-memory/db-backed match registries, pytest, httpx, reference Python SDK, `make quality`.

---

## Parallelism / Sequencing

- **Sequential only for implementation:** the story touches the same public API contract files (`server/models/api.py`, `server/main.py`, `server/agent_registry.py`, SDK client, and shared tests), so parallel Codex implementers would collide heavily.
- **Safe parallelism after implementation:** spec review and code-quality review can run as separate fresh reviewers after the worker finishes.
- **Simplification pass required:** after the endpoint works, remove any duplicate validation logic or unnecessary orchestration abstractions; keep the convenience layer thin and boring.

## Task 1: Define the command-envelope public contract

**Objective:** Add the smallest clear request/response models needed to describe a combined turn write without changing existing focused request shapes.

**Files:**
- Modify: `server/models/api.py`
- Modify: `agent-sdk/python/iron_council_client.py`
- Test: `tests/agent_sdk/test_python_client.py`

**Step 1: Write failing contract tests**

Add tests that prove:
- the SDK exposes one `submit_command(...)` helper
- the helper posts to `/api/v1/matches/{match_id}/command`
- request fields keep the existing nested shapes for orders, messages, treaty action, and alliance action
- the parsed response has a stable acceptance summary with only the accepted sections that were requested

**Step 2: Run test to verify failure**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py
```

Expected: FAIL because the client method and command-envelope models do not exist yet.

**Step 3: Write minimal implementation**

Add new Pydantic models in `server/models/api.py`, for example:
- `AgentCommandMessageRequest`
- `AgentCommandRequest`
- `AgentCommandAcceptanceResponse`
- lightweight acceptance item models for message/treaty/alliance sections

Keep them boring:
- `match_id` + `tick` at envelope level
- optional `orders`
- optional `messages: list[...]`
- optional `treaty`
- optional `alliance`
- no new semantics that the focused endpoints do not already support

Then add the matching typed SDK model(s) and `IronCouncilClient.submit_command(...)` helper.

**Step 4: Run test to verify pass**

Run the same command as Step 2.

Expected: PASS.

## Task 2: Add a registry-level all-or-nothing orchestration helper

**Objective:** Validate every included action against the authenticated player and current match before mutating any registry state.

**Files:**
- Modify: `server/agent_registry.py`
- Test: `tests/api/test_agent_api.py`

**Step 1: Write failing API/unit-style tests**

Add behavior-first tests that prove the combined endpoint/registry path:
- accepts a valid envelope containing orders + world/direct messages + treaty + alliance action
- records state changes in a deterministic order only after all validation passes
- leaves `order_submissions`, `messages`, `treaties`, and `alliances` unchanged when any contained action is invalid
- preserves the existing focused endpoints’ behavior by not changing their tests/assertions

**Step 2: Run test to verify failure**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py
```

Expected: FAIL because there is no combined orchestration path yet.

**Step 3: Write minimal implementation**

Inside `server/agent_registry.py`:
- add a command helper that first resolves the match record and player
- build/validate focused request objects from the nested envelope pieces
- preflight-check tick/match/player invariants for each included action
- snapshot or stage the record state, then apply mutations only after every check succeeds
- reuse existing helpers (`record_submission`, `record_message`, `apply_treaty_action`, `apply_alliance_action`) instead of duplicating business rules

If there is no generic preflight helper today, add the smallest internal helpers needed to validate without mutation.

**Step 4: Run test to verify pass**

Run the same command as Step 2.

Expected: PASS.

## Task 3: Add the authenticated endpoint and structured error mapping

**Objective:** Expose the command-envelope route from FastAPI with the same auth/match safety rules and stable error responses as the focused endpoints.

**Files:**
- Modify: `server/main.py`
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/api/test_agent_process_api.py`
- Modify: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing route tests**

Add tests that prove:
- POST `/api/v1/matches/{match_id}/command` requires auth and a joined agent
- route/body `match_id` mismatch returns a structured error
- stale `tick` mismatch returns a structured error
- invalid nested action returns a structured error and no partial side effects
- the running app accepts a valid command envelope and exposes the resulting side effects through the existing read endpoints / briefing

**Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py
uv run pytest --no-cov tests/api/test_agent_process_api.py
uv run pytest --no-cov tests/e2e/test_api_smoke.py
```

Expected: FAIL until the route exists.

**Step 3: Write minimal implementation**

In `server/main.py`:
- add request-validation mapping for `/command` if custom messaging is needed
- add the authenticated route under `/api/v1/matches/{match_id}/command`
- resolve the joined player once
- call the registry command helper once
- map match/tick/action failures to the existing structured API error format

Keep the endpoint thin: orchestration belongs in the registry helper, not the route.

**Step 4: Run tests to verify pass**

Run the same commands as Step 2.

Expected: PASS.

## Task 4: Finish SDK and story tracking, then run the real gate

**Objective:** Make the public convenience layer discoverable to SDK users, then prove the repo remains shippable.

**Files:**
- Modify: `agent-sdk/python/iron_council_client.py`
- Modify: `tests/agent_sdk/test_python_client.py`
- Modify: `_bmad-output/implementation-artifacts/17-2-add-a-consolidated-authenticated-agent-command-endpoint.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `README.md` or `agent-sdk/README.md` only if the new public command needs explicit mention

**Step 1: Write/extend failing documentation or SDK workflow tests**

Add assertions that the SDK workflow can submit one command envelope and receive typed accepted sections.

**Step 2: Run focused verification**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py
```

Expected: PASS after the method is complete.

**Step 3: Update BMAD artifacts**

Update the story file with:
- agent model used
- completion notes
- file list
- change log

Update `sprint-status.yaml` to mark Story 17.2 done and Epic 17 done if warranted.

**Step 4: Run repo verification**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py tests/agent_sdk/test_python_client.py
uv run pytest --no-cov tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py
make quality
```

Expected: PASS.

## Final review checklist

- [ ] The consolidated endpoint validates route/body match and tick exactly once at the envelope boundary
- [ ] Included actions are all-or-nothing; invalid nested work causes zero unrelated side effects
- [ ] Focused REST endpoints still exist and their current behavior-first tests stay green
- [ ] SDK exposes one typed convenience helper without depending on repo-internal server imports
- [ ] Running-app and smoke coverage exercise the real command path
- [ ] Story artifact and sprint status are updated
- [ ] `make quality` passes
