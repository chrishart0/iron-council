# Epic 16 Group Chat Messaging Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Close the biggest remaining agent-messaging gap by adding group chat workflows to the authenticated API, SDK, and example documentation.

**Architecture:** Extend the existing authenticated messaging surface instead of introducing a second chat subsystem. Story 16.1 should add minimal group-chat data contracts plus REST endpoints for creating chats, inviting members, listing visible chats, and sending/reading group messages through the current match registry. Story 16.2 should then expose the new public contract through the standalone Python SDK and teach it in the example docs/tests. Keep the implementation intentionally narrow: no permissions model beyond match membership + explicit group membership, no websocket work, and no speculative moderation/admin features.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, httpx/TestClient, standalone SDK module in `agent-sdk/python`, real-process smoke checks.

---

## Parallelism / Sequencing

- **Story 16.1 and 16.2 are sequential, not parallel.** They both touch the public messaging contract and SDK-facing payload shape; doing them concurrently would create avoidable churn in `server/models/api.py`, `server/agent_registry.py`, `server/main.py`, and `agent-sdk/python/iron_council_client.py`.
- **Within Story 16.1**, API models, registry behavior, and route tests should be developed together in a tight TDD loop because they share the same message/group-chat surface.
- **Safe refinement pass:** after both stories pass, simplify any message/group abstractions that feel more complex than the existing treaty/alliance patterns.

## Task 1: Draft BMAD story artifacts for Epic 16

**Objective:** Record the next delivery slice before implementation starts.

**Files:**
- Modify: `_bmad-output/planning-artifacts/epics.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Create: `_bmad-output/implementation-artifacts/16-1-add-authenticated-group-chat-creation-membership-and-message-workflows.md`
- Create: `_bmad-output/implementation-artifacts/16-2-extend-the-python-sdk-and-example-docs-for-group-chat-workflows.md`

**Step 1: Add the new epic/stories to BMAD planning**

Document that group chats are the next highest-value messaging gap because the GDD and architecture both require DMs + group chats + world chat, while the current authenticated API only exposes direct and world messaging.

**Step 2: Reflect the active sequence in sprint status**

Add `epic-16`, set Story 16.1 as the active implementation target, and keep Story 16.2 queued behind it.

## Task 2: Implement Story 16.1 backend group-chat workflows

**Objective:** Add the smallest complete authenticated group-chat feature set at the API boundary.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/agent_registry.py`
- Modify: `server/main.py`
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/api/test_agent_process_api.py`
- Modify: `tests/e2e/test_api_smoke.py` or another focused real-process API test file if needed
- Modify: `_bmad-output/implementation-artifacts/16-1-add-authenticated-group-chat-creation-membership-and-message-workflows.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Write failing behavior-first tests**

Add tests that prove:
- an authenticated joined player can create a group chat with a name and invited member ids
- invited members can read the chat and post messages to it
- non-members cannot read or post to that group chat
- group chat reads only include chats/messages visible to the authenticated player
- existing world/direct message behavior still works unchanged

**Step 2: Run focused tests to verify failure**

Run:

```bash
uv run pytest -o addopts='' tests/api/test_agent_api.py tests/api/test_agent_process_api.py
```

Expected: FAIL because group-chat contracts/endpoints do not exist yet.

**Step 3: Write minimal implementation**

Keep the design boring and close to existing patterns:
- add explicit group-chat record/request/response models
- store group-chat membership in the match registry
- expose dedicated endpoints for listing chats, creating chats, and posting/reading messages with group membership checks
- reuse the current authenticated-agent + joined-player gate
- avoid speculative chat roles, renames, deletions, unread state, or pagination unless tests require them

**Step 4: Run focused tests to verify pass**

Run the same command as Step 2.

Expected: PASS.

**Step 5: Run the real workflow boundary**

Run:

```bash
uv run pytest --no-cov tests/e2e/test_api_smoke.py
```

Expected: PASS with at least one running-process path exercising the documented group-chat API.

## Task 3: Implement Story 16.2 SDK and docs support

**Objective:** Make the new group-chat surface usable from the standalone Python SDK and teach it in the agent docs/examples.

**Files:**
- Modify: `agent-sdk/python/iron_council_client.py`
- Modify: `agent-sdk/README.md`
- Modify: `agent-sdk/python/example_agent.py` only if a tiny illustrative group-chat hook is needed; otherwise prefer docs-only usage examples
- Modify: `tests/agent_sdk/test_python_client.py`
- Modify: `tests/e2e/test_agent_sdk_smoke.py` and/or `tests/e2e/test_example_agent_smoke.py`
- Modify: `_bmad-output/implementation-artifacts/16-2-extend-the-python-sdk-and-example-docs-for-group-chat-workflows.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Write failing SDK/doc tests**

Add tests that prove:
- the standalone SDK returns typed group-chat records and supports create/list/send/read flows
- the SDK remains importable without repo-internal `server` imports
- the documented commands/examples match the tested workflow

**Step 2: Run focused tests to verify failure**

Run:

```bash
uv run pytest -o addopts='' tests/agent_sdk/test_python_client.py
```

Expected: FAIL until the SDK grows group-chat methods/models.

**Step 3: Write minimal SDK/docs implementation**

Keep it consistent with existing client patterns:
- add typed request/response models beside existing message/treaty/alliance models
- add minimal client methods for create/list/get/send group-chat workflows
- update `agent-sdk/README.md` with copyable examples using the public SDK only
- only touch the example agent if it materially improves onboarding without making the example less simple

**Step 4: Run verification**

Run:

```bash
uv run pytest -o addopts='' tests/agent_sdk/test_python_client.py
uv run pytest --no-cov tests/e2e/test_agent_sdk_smoke.py tests/e2e/test_example_agent_smoke.py
make quality
```

Expected: PASS.

## Final review checklist

- [ ] Group chats are implemented as an authenticated match-scoped capability, not a separate subsystem
- [ ] Non-members cannot read or write group-chat traffic
- [ ] Existing direct/world messaging behavior remains intact
- [ ] SDK stays self-contained and free of `server` imports
- [ ] Docs and smoke tests exercise the same public commands/contracts
- [ ] BMAD story artifacts and sprint status reflect both story outcomes
- [ ] Final simplification pass removes avoidable abstraction or API surface creep
