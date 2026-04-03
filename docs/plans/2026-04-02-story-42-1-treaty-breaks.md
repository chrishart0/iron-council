# Story 42.1 Treaty Breaks on Hostile Attacks Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Automatically break active treaties when one treaty partner launches a hostile accepted attack against the other, announce the betrayal in world chat, and surface the new broken statuses consistently across registry/API/process reads.

**Architecture:** Keep the pure `resolve_tick()` contract unchanged. Detect treaty violations in `server/agent_registry_commands.py` immediately before/after tick resolution using the pre-resolution `MatchState` plus the accepted movement orders for the current tick, then delegate the treaty mutation/serialization details to small helpers in `server/agent_registry_diplomacy.py`. Update only the shared API/SDK treaty status contracts that truly need the expanded literal set.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, uv, existing in-memory registry + real-process API checks.

---

## Parallelism / sequencing decision

- **Sequential only for implementation.** The story touches the same treaty-status contract, diplomacy helpers, tick-advance path, and shared read surfaces. Parallel Codex workers would collide on the same files and increase merge risk.
- **Safe parallelism after implementation:** review passes can run independently once the worker branch is stable.

---

### Task 1: Expand treaty status contracts to model automatic breaks

**Objective:** Add the new broken treaty statuses anywhere the public/server/SDK contract currently hard-codes the smaller literal set.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/agent_registry_types.py`
- Modify: `agent-sdk/python/iron_council_client.py`
- Test: `tests/test_agent_registry.py`
- Test: `tests/api/test_agent_process_api.py`

**Step 1: Write failing tests**

Add/extend assertions that a treaty record can serialize with `status="broken_by_a"` and `status="broken_by_b"` without validation errors.

```python
from server.models.api import TreatyRecord


def test_treaty_record_accepts_broken_statuses() -> None:
    broken_by_a = TreatyRecord(
        treaty_id=7,
        player_a_id="player-1",
        player_b_id="player-2",
        treaty_type="non_aggression",
        status="broken_by_a",
        proposed_by="player-1",
        proposed_tick=10,
        signed_tick=11,
        withdrawn_by=None,
        withdrawn_tick=12,
    )
    broken_by_b = broken_by_a.model_copy(update={"status": "broken_by_b"})

    assert broken_by_a.status == "broken_by_a"
    assert broken_by_b.status == "broken_by_b"
```

**Step 2: Run test to verify failure**

Run:
`uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k broken_status`

Expected: FAIL because the treaty status literal set does not yet include `broken_by_a` / `broken_by_b`.

**Step 3: Write minimal implementation**

Update the treaty status literal aliases in the server and Python SDK.

```python
TreatyStatus = Literal[
    "proposed",
    "active",
    "broken_by_a",
    "broken_by_b",
    "withdrawn",
]
```

**Step 4: Run focused tests to verify pass**

Run:
`uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k broken_status`

Expected: PASS.

**Step 5: Commit**

```bash
git add server/models/api.py server/agent_registry_types.py agent-sdk/python/iron_council_client.py tests/test_agent_registry.py tests/api/test_agent_process_api.py
git commit -m "feat: add treaty broken status contracts"
```

---

### Task 2: Detect hostile treaty violations during tick advancement

**Objective:** Break active treaties deterministically from the match-registry tick path when accepted hostile movement orders target a treaty partner.

**Files:**
- Modify: `server/agent_registry_commands.py`
- Modify: `server/agent_registry_diplomacy.py`
- Test: `tests/test_agent_registry.py`

**Step 1: Write failing tests**

Add a behavior test around `advance_match_tick()` proving:
- active treaty exists between players 1 and 2
- player 1 submits an accepted movement attack into a city owned by player 2
- after tick advancement the treaty becomes `broken_by_a`
- `withdrawn_tick` records the break tick
- no longer appears active

```python
def test_advance_match_tick_breaks_active_treaty_when_player_a_attacks_partner(
    seeded_registry: InMemoryMatchRegistry,
) -> None:
    record = seeded_registry._matches["match-alpha"]
    record.state.tick = 50
    # arrange active treaty + legal hostile movement order here

    result = seeded_registry.advance_match_tick("match-alpha")

    treaty = record.treaties[-1]
    assert treaty.status == "broken_by_a"
    assert treaty.withdrawn_tick == 50
    assert result.next_state.tick == 51
```

Add the symmetric `broken_by_b` case if the attacker is `player_b_id`.

**Step 2: Run test to verify failure**

Run:
`uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'breaks_active_treaty'`

Expected: FAIL because tick advancement does not currently mutate treaties based on accepted hostile orders.

**Step 3: Write minimal implementation**

Add a tiny helper layer in `server/agent_registry_diplomacy.py` that:
1. Scans accepted movement orders against the pre-resolution state.
2. Treats a movement as hostile when the destination city is currently owned by a treaty partner.
3. Finds active treaties for that attacker/defender pair.
4. Marks each active treaty `broken_by_a` or `broken_by_b` based on the sorted treaty orientation.
5. Sets the break tick exactly once.

Wire that helper into `advance_match_tick()` using the **current** tick before increment.

```python
def reconcile_hostile_treaty_breaks(
    *,
    record: MatchRecord,
    pre_resolution_state: MatchState,
    accepted_orders: OrderBatch,
    match_id: str,
    record_world_message: WorldMessageRecorder,
) -> None:
    ...
```

**Step 4: Run focused tests to verify pass**

Run:
`uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'breaks_active_treaty or treaty_break'`

Expected: PASS.

**Step 5: Commit**

```bash
git add server/agent_registry_commands.py server/agent_registry_diplomacy.py tests/test_agent_registry.py
git commit -m "feat: break treaties on hostile attacks"
```

---

### Task 3: Record deterministic world-chat treaty-break announcements exactly once

**Objective:** Ensure every automatic break emits one and only one public announcement, even if multiple accepted hostile orders exist in the same tick.

**Files:**
- Modify: `server/agent_registry_diplomacy.py`
- Test: `tests/test_agent_registry.py`
- Test: `tests/api/test_agent_api.py`

**Step 1: Write failing tests**

Add a test proving world chat gets a single deterministic announcement per treaty break and that repeated hostile orders in the same tick do not duplicate the message.

```python
def test_advance_match_tick_posts_single_world_message_for_automatic_treaty_break(...) -> None:
    ...
    world_messages = [message.content for message in record.messages if message.channel == "world"]
    assert world_messages[-1] == (
        "Treaty broken: player-1 attacked player-2 and broke their non_aggression treaty."
    )
    assert world_messages.count(world_messages[-1]) == 1
```

**Step 2: Run test to verify failure**

Run:
`uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'single_world_message_for_automatic_treaty_break'`

Expected: FAIL because no automatic break message is recorded yet.

**Step 3: Write minimal implementation**

Emit the announcement inside the same diplomacy helper that performs the break and guard on `withdrawn_tick is None` / prior non-broken status so each treaty is announced once.

```python
record_world_message(
    match_id=match_id,
    tick=break_tick,
    content=(
        f"Treaty broken: {attacker_id} attacked {defender_id} and broke their "
        f"{treaty.treaty_type} treaty."
    ),
)
```

**Step 4: Run focused tests to verify pass**

Run:
`uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'automatic_treaty_break'`

Expected: PASS.

**Step 5: Commit**

```bash
git add server/agent_registry_diplomacy.py tests/test_agent_registry.py tests/api/test_agent_api.py
git commit -m "feat: announce automatic treaty breaks"
```

---

### Task 4: Verify broken statuses flow through API/process/SDK read surfaces

**Objective:** Prove the new statuses surface honestly in authenticated reads, process-backed API reads, and SDK parsing without regressing existing diplomacy behavior.

**Files:**
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/api/test_agent_process_api.py`
- Modify: `tests/agent_sdk/test_python_client.py`
- Modify: `tests/e2e/test_api_smoke.py` (only if needed for an honest real-process contract check)

**Step 1: Write failing tests**

Add/extend behavior-first tests that assert a broken treaty is returned with the exact new status and break tick fields through:
- authenticated treaty list / briefing reads
- real-process API surface
- Python SDK parsing of treaty lists / briefing responses

```python
assert treaty_payload["status"] == "broken_by_a"
assert treaty_payload["withdrawn_tick"] == 50
```

**Step 2: Run tests to verify failure**

Run:
`uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'broken_by_a or broken_by_b'`

Expected: FAIL until all read surfaces accept and assert the new statuses.

**Step 3: Write minimal implementation**

Only patch the failing shared contract or serialization seam. Avoid client/UI scope unless a contract validator truly rejects the new statuses.

**Step 4: Run focused tests to verify pass**

Run:
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'treaty_break or broken_by'`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_process_api.py -k 'treaty'`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py -k 'treaty'`

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/api/test_agent_api.py tests/api/test_agent_process_api.py tests/agent_sdk/test_python_client.py tests/e2e/test_api_smoke.py
git commit -m "test: cover treaty break read surfaces"
```

---

### Task 5: Run final verification, review, and simplification pass

**Objective:** Confirm the story works end-to-end, then simplify any unnecessary abstraction before merge.

**Files:**
- Review: `server/agent_registry_commands.py`
- Review: `server/agent_registry_diplomacy.py`
- Review: changed tests and contract files
- Modify: only if simplification/review finds a real issue
- Modify: `_bmad-output/implementation-artifacts/42-1-break-active-treaties-on-hostile-attacks-and-announce-them.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run focused repository checks**

Run:
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'treaty'`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'treaty'`
- `uv run pytest --no-cov tests/api/test_agent_process_api.py -k treaty`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py -k 'treaty'`

Expected: PASS.

**Step 2: Run the real quality path most likely affected**

Run:
- `uv run ruff check server tests agent-sdk/python`
- `uv run mypy server tests agent-sdk/python`

Expected: PASS.

**Step 3: Review for KISS / overcomplexity**

Checklist:
- no new framework or lifecycle object just for one treaty rule
- treaty-break detection reads from existing accepted orders, not raw submissions
- helper names describe behavior directly
- duplicate scans / branching minimized

**Step 4: Update BMAD artifacts**

Mark Story 42.1 complete in the story file and sprint status with exact checks run and final commit hash.

**Step 5: Final commit**

```bash
git add server agent-sdk/python tests _bmad-output/implementation-artifacts/sprint-status.yaml _bmad-output/implementation-artifacts/42-1-break-active-treaties-on-hostile-attacks-and-announce-them.md docs/plans/2026-04-02-story-42-1-treaty-breaks.md
git commit -m "feat: break treaties on hostile attacks"
```

---

## Expected verification bundle

Run these before merge/push:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'treaty'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'treaty'
uv run pytest --no-cov tests/api/test_agent_process_api.py -k treaty
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py -k 'treaty'
uv run ruff check server tests agent-sdk/python
uv run mypy server tests agent-sdk/python
```

## Notes for the implementer

- Preserve the existing distinction between **formal withdrawal** and **actual betrayal**; the new broken statuses are not synonyms for manual withdraw.
- Break detection must use the **pre-resolution owner of the destination city**, because the hostile act is the submitted attack, not the post-combat state.
- Do not invent a generic diplomacy event bus.
- If one attack breaks multiple active treaties of different types between the same pair, announce each treaty break once.
- After implementation, run two explicit review passes: (1) spec compliance against Story 42.1 acceptance criteria, then (2) code quality / KISS / repo-convention review.
