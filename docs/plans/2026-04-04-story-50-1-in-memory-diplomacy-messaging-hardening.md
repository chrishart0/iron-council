# Story 50.1 In-Memory Diplomacy and Messaging Hardening Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Harden the in-memory `AgentRegistry` diplomacy and messaging compatibility surface with behavior-first regressions and only the smallest production fixes required.

**Architecture:** Keep the scope at the public `InMemoryMatchRegistry` boundary in `tests/test_agent_registry.py`, adding narrow regressions for treaty/alliance transitions, `since_tick` filtering, recipient validation, group membership, and briefing bucketing. If tests expose drift, patch only `server/agent_registry_diplomacy.py` and/or `server/agent_registry_messaging.py` with the smallest convention-aligned fix.

**Tech Stack:** Python 3.12, pytest, uv, FastAPI-era Pydantic models, in-memory registry helpers.

---

### Task 1: Pin diplomacy edge transitions at the registry boundary

**Objective:** Add failing registry-level tests for missing inputs, unsupported treaty transitions, alliance leader handoff, and treaty `since_tick` visibility.

**Files:**
- Modify: `tests/test_agent_registry.py`
- Verify context in: `server/agent_registry_diplomacy.py`

**Step 1: Write failing test**

Add focused tests near the existing alliance/treaty coverage for cases like:
- create alliance without `name` -> structured `alliance_name_required`
- join alliance without `alliance_id` -> structured `alliance_id_required`
- accept nonexistent treaty -> structured `unsupported_treaty_transition`
- proposer cannot accept their own treaty
- leaving alliance reassigns leader deterministically and removes empty alliance
- `list_treaties(..., since_tick=...)` includes only records whose latest visible tick meets the filter

**Step 2: Run test to verify failure**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'treaty or alliance'`
Expected: FAIL with one or more uncovered edge cases.

**Step 3: Write minimal implementation**

If needed, make the smallest fix in `server/agent_registry_diplomacy.py` only. Prefer preserving current helper structure over introducing new layers.

**Step 4: Run test to verify pass**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'treaty or alliance'`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_agent_registry.py server/agent_registry_diplomacy.py
git commit -m "test: harden in-memory diplomacy edge contracts"
```

### Task 2: Pin messaging and briefing visibility edges

**Objective:** Add failing behavior tests for message recipient validation, group membership enforcement, and briefing grouping/`since_tick` behavior.

**Files:**
- Modify: `tests/test_agent_registry.py`
- Verify context in: `server/agent_registry_messaging.py`

**Step 1: Write failing test**

Add focused tests for cases like:
- world message rejects `recipient_id`
- direct message requires `recipient_id`
- group message rejects `recipient_id` and requires `group_chat_id`
- non-member cannot post to or read group chat
- briefing buckets remain deterministic across mixed world/direct/group traffic with `since_tick`

**Step 2: Run test to verify failure**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'message or group_chat or briefing'`
Expected: FAIL if any edge contract is currently unpinned or drifting.

**Step 3: Write minimal implementation**

If tests reveal drift, patch only `server/agent_registry_messaging.py` with the smallest honest change.

**Step 4: Run test to verify pass**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'message or group_chat or briefing'`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_agent_registry.py server/agent_registry_messaging.py
git commit -m "test: harden in-memory messaging edge contracts"
```

### Task 3: Run focused verification and repo gate, then close BMAD artifact

**Objective:** Verify the story through focused tests plus the real repo quality gate and update the story artifact with real outcomes.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/50-1-harden-in-memory-diplomacy-and-messaging-contract-edges.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run focused verification**

Run: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'treaty or alliance or message or group_chat or briefing'`
Expected: PASS.

**Step 2: Run full repo gate**

Run: `source .venv/bin/activate && make quality`
Expected: PASS.

**Step 3: Update BMAD closeout**

Mark the story done, fill in `Debug Log References`, `Completion Notes`, `File List`, and move sprint tracking to the next story.

**Step 4: Commit**

```bash
git add _bmad-output/implementation-artifacts/50-1-harden-in-memory-diplomacy-and-messaging-contract-edges.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "docs: close story 50-1"
```
