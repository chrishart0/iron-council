# Story 34.4 In-Memory Registry Decomposition Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extract in-memory authenticated access, join-slot resolution, tick advancement, and command-envelope mutation helpers out of `server/agent_registry.py` into focused modules while preserving the existing registry method names, API behavior, and test-facing contract.

**Architecture:** Keep `InMemoryMatchRegistry` as the stable facade and compatibility import surface. Move pure/explicit helper logic into narrowly named modules such as `server/agent_registry_access.py` and `server/agent_registry_commands.py` so authentication/join access paths and tick/command workflows stop living in one large class body. Preserve existing response models, errors, sort/order behavior, world-message side effects, and victory-state synchronization by having the registry delegate rather than redesign.

**Tech Stack:** Python 3.12, FastAPI server package, Pydantic models, pytest, uv, make quality.

---

### Task 1: Pin the current in-memory registry facade contract with focused regressions

**Objective:** Lock the join/auth/tick/command behavior before moving code.

**Files:**
- Modify: `tests/test_agent_registry.py`
- Modify if needed: `tests/api/test_agent_api.py`

**Step 1: Write failing test**

Add or tighten behavior-first coverage for:
- authenticated agent resolution and deactivation remaining stable
- deterministic join-slot assignment and joined-player access errors
- `advance_match_tick()` preserving current-tick filtering, same-player submission aggregation, and returned persistence payload shape
- `apply_command_envelope()` preserving accepted order/message/treaty/alliance responses and scratch-registry validation semantics

Example additions:

```python
def test_apply_command_envelope_preserves_world_message_side_effects_and_response_shape() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    response = registry.apply_command_envelope(
        match_id="match-alpha",
        player_id="player-1",
        command=AgentCommandEnvelopeRequest.model_validate({
            "match_id": "match-alpha",
            "tick": 0,
            "orders": {},
            "messages": [],
            "treaties": [{
                "counterparty_id": "player-2",
                "action": "propose",
                "treaty_type": "non_aggression",
            }],
        }),
    )

    assert response.treaties[0].treaty.status == "pending"
    assert registry.list_visible_messages(match_id="match-alpha", player_id="player-1")[-1].channel == "world"
```

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/test_agent_registry.py -k 'join or authenticated or advance_match_tick or command_envelope'`
Expected: FAIL until the contract is pinned or any missing edge-case coverage is added.

**Step 3: Write minimal implementation**

Only add/adjust tests that pin the existing public behavior. Do not move production code yet.

**Step 4: Run test to verify baseline**

Run: `uv run pytest -o addopts='' tests/test_agent_registry.py -k 'join or authenticated or advance_match_tick or command_envelope'`
Expected: PASS or a clearly understood red defining the next edit.

**Step 5: Commit**

```bash
git add tests/test_agent_registry.py tests/api/test_agent_api.py
git commit -m "test: pin in-memory registry facade contract"
```

### Task 2: Extract authenticated access and join helpers into a focused module

**Objective:** Move auth-key lookup, deactivation, join-slot resolution, and joined-player access helpers out of the main registry file.

**Files:**
- Create: `server/agent_registry_access.py`
- Modify: `server/agent_registry.py`
- Modify if needed: `tests/test_agent_registry.py`

**Step 1: Write failing test**

Reuse the Task 1 focused auth/join tests as the contract. No new implementation-detail assertions.

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/test_agent_registry.py -k 'join or authenticated'`
Expected: FAIL while imports/delegation are mid-extraction.

**Step 3: Write minimal implementation**

Create a helper module with explicit functions such as:

```python
def resolve_authenticated_agent(
    authenticated_agents_by_key_hash: dict[str, AuthenticatedAgentContext],
    *,
    api_key: str,
) -> AuthenticatedAgentContext | None:
    authenticated_agent = authenticated_agents_by_key_hash.get(hash_api_key(api_key))
    if authenticated_agent is None:
        return None
    return authenticated_agent.model_copy(deep=True)
```

Also move the join-slot and joined-player lookup logic into pure helper functions that operate on `MatchRecord` and return the same `MatchJoinResponse` / `MatchAccessError` semantics. Keep `InMemoryMatchRegistry` methods as thin delegates.

**Step 4: Run tests to verify pass**

Run: `uv run pytest -o addopts='' tests/test_agent_registry.py -k 'join or authenticated'`
Expected: PASS.

**Step 5: Commit**

```bash
git add server/agent_registry_access.py server/agent_registry.py tests/test_agent_registry.py
git commit -m "refactor: extract registry access helpers"
```

### Task 3: Extract tick advancement and command-envelope workflows into a focused module

**Objective:** Move queued-order aggregation, tick advancement, scratch-registry command validation, and accepted-response assembly behind a dedicated registry helper module.

**Files:**
- Create: `server/agent_registry_commands.py`
- Modify: `server/agent_registry.py`
- Modify if needed: `tests/test_agent_registry.py`
- Modify if needed: `tests/api/test_agent_api.py`

**Step 1: Write failing test**

Reuse the Task 1 focused tick/command regressions as the contract.

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/test_agent_registry.py -k 'advance_match_tick or command_envelope'`
Expected: FAIL while delegation is partially wired.

**Step 3: Write minimal implementation**

Create explicit helpers for:
- `command_has_orders(...)`
- `combine_submissions_by_player(...)`
- `validate_queued_orders(...)`
- `advance_match_tick(...)`
- `apply_command_envelope_mutations(...)`

Keep collaboration behavior delegated through the existing messaging/diplomacy modules, and pass in the small callbacks/dependencies needed instead of introducing classes or generic service frameworks.

**Step 4: Run tests to verify pass**

Run: `uv run pytest -o addopts='' tests/test_agent_registry.py -k 'advance_match_tick or command_envelope'`
Expected: PASS.

**Step 5: Commit**

```bash
git add server/agent_registry_commands.py server/agent_registry.py tests/test_agent_registry.py tests/api/test_agent_api.py
git commit -m "refactor: extract registry command workflows"
```

### Task 4: Full verification, simplification, and BMAD closeout

**Objective:** Confirm the refactor is complete, minimal, and convention-aligned.

**Files:**
- Modify if needed: `server/agent_registry.py`
- Modify if needed: `server/agent_registry_access.py`
- Modify if needed: `server/agent_registry_commands.py`
- Modify: `_bmad-output/implementation-artifacts/34-4-split-in-memory-access-and-command-workflows-out-of-server-agent_registry-py.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `_bmad-output/planning-artifacts/epics.md`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/test_agent_registry.py`
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'join_match or command or profile or messages or treaties or alliances'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'profile or join or state or command'`

Expected: PASS.

**Step 2: Run formatting/quality**

Run:
- `make format`
- `source .venv/bin/activate && make quality`

Expected: PASS.

**Step 3: Simplification pass**

Review diffs for:
- accidental import-surface churn from `server.agent_registry`
- unnecessary wrapper layers or callback indirection
- command/tick helpers that could stay plain functions instead of new classes
- any remaining large logic blocks in `server/agent_registry.py` that should obviously live in the new helper modules
- KISS violations vs the repo's existing refactor style

**Step 4: Update BMAD artifacts**

Mark Story 34.4 done, capture debug commands/completion notes/file list, update `sprint-status.yaml`, and choose the next story pragmatically.

**Step 5: Commit**

```bash
git add server/agent_registry.py server/agent_registry_access.py server/agent_registry_commands.py \
  tests/test_agent_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py \
  _bmad-output/implementation-artifacts/34-4-split-in-memory-access-and-command-workflows-out-of-server-agent_registry-py.md \
  _bmad-output/implementation-artifacts/sprint-status.yaml \
  _bmad-output/planning-artifacts/epics.md \
  docs/plans/2026-04-01-story-34-4-in-memory-registry-decomposition.md

git commit -m "refactor: extract registry access and command workflows"
```
