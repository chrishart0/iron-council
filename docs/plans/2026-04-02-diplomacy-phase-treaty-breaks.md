# Diplomacy Treaty-Break Resolution Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Detect hostile treaty violations during tick advancement, mark the active treaty as broken by the attacking player, and announce the break in world chat without regressing the existing diplomacy/API contract.

**Architecture:** Keep the resolver pure over `MatchState` and implement treaty-break reconciliation in the match-registry tick-advance path, where `MatchRecord` already owns treaties, messages, and alliance metadata. Reuse the existing accepted-order + post-resolution state transition seam, add only the smallest explicit helpers needed to detect hostile actions and serialize broken treaty statuses, and verify behavior from the registry/API boundary rather than through internal implementation details.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, uv, existing in-memory registry/runtime tick pipeline.

---

### Task 1: Draft the BMAD artifact and sprint pointer

**Objective:** Record the new post-Epic-41 story before coding so the worker can implement against a committed source of truth.

**Files:**
- Modify: `_bmad-output/planning-artifacts/epics.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Create: `_bmad-output/implementation-artifacts/42-1-break-active-treaties-on-hostile-attacks-and-announce-them.md`

**Step 1: Write the story artifact**

Create a story that explicitly says:
- active treaties can transition to `broken_by_a` / `broken_by_b`
- the break is triggered by hostile attack behavior during tick advancement, not by a manual HTTP action
- world chat must announce the break exactly once
- focused registry/API verification is required

**Step 2: Point sprint status at the story**

Set:
- `epic-42: in-progress`
- `42-1-break-active-treaties-on-hostile-attacks-and-announce-them: drafted`
- `next_story: 42-1-break-active-treaties-on-hostile-attacks-and-announce-them`

**Step 3: Commit the planning slice**

Run:
`git add _bmad-output/planning-artifacts/epics.md _bmad-output/implementation-artifacts/sprint-status.yaml _bmad-output/implementation-artifacts/42-1-break-active-treaties-on-hostile-attacks-and-announce-them.md docs/plans/2026-04-02-diplomacy-phase-treaty-breaks.md && git commit -m "docs: add story 42.1 treaty-break plan"`

Expected: planning commit created cleanly.

---

### Task 2: Write failing contract tests for broken treaty status surfacing

**Objective:** Pin the new broken-treaty contract at the smallest public seams before touching implementation.

**Files:**
- Modify: `tests/test_agent_registry.py`
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/api/test_agent_process_api.py`

**Step 1: Add a failing registry test**

Add a test that seeds:
- an active treaty between two players
- a city owned by the treaty partner
- an accepted hostile movement order by the attacker into that city

Then assert after `advance_match_tick(...)`:
- the treaty status becomes `broken_by_a` or `broken_by_b`
- `broken_tick` is set to the resolved tick
- exactly one new world message announces the break

**Step 2: Add failing API/briefing coverage**

Add focused tests that assert serialized treaty payloads can now return `broken_by_a` / `broken_by_b` from:
- treaty list endpoint / response model
- authenticated briefing / process payloads

**Step 3: Run focused tests to verify red**

Run:
`uv run pytest -o addopts='' tests/test_agent_registry.py -k treaty`

Expected: FAIL because broken treaty states are not yet supported end-to-end.

---

### Task 3: Implement explicit treaty-break detection in the tick-advance seam

**Objective:** Add the smallest boring helper layer that converts hostile accepted orders into treaty breaks and world-chat announcements.

**Files:**
- Modify: `server/agent_registry_commands.py`
- Modify: `server/agent_registry_diplomacy.py`
- Modify: `server/agent_registry_types.py`
- Modify: `server/models/api.py`

**Step 1: Extend the treaty status contract**

Update the treaty status literal surface to include:
```python
TreatyStatus = Literal["proposed", "active", "withdrawn", "broken_by_a", "broken_by_b"]
```

Keep existing fields and add an explicit broken-tick field on the in-memory treaty record if needed:
```python
@dataclass(slots=True)
class MatchTreaty:
    ...
    broken_tick: int | None = None
```

**Step 2: Add a focused break helper**

Create a helper in `agent_registry_diplomacy.py` that:
- finds active treaties for the record
- determines whether a player launched a hostile move into the partner’s city owned at tick start
- converts the active treaty into `broken_by_a` or `broken_by_b`
- records `broken_tick`
- appends one world-chat message such as:
  `Treaty broken: player-1 attacked player-2, ending their non_aggression treaty.`

Keep it explicit. No strategy classes or framework abstractions.

**Step 3: Wire the helper after tick resolution**

In `advance_match_tick(...)`:
- keep order validation and resolver behavior unchanged
- after `resolve_tick(...)` returns, reconcile treaty breaks against the pre-resolution state plus accepted movement orders
- then assign `record.state = next_state`
- keep `sync_victory_state(...)` and the returned `AdvancedTickResult` intact

**Step 4: Re-run focused tests for green**

Run:
`uv run pytest -o addopts='' tests/test_agent_registry.py -k treaty`

Expected: PASS.

---

### Task 4: Verify API/realtime contract propagation

**Objective:** Make sure the new treaty states flow through the actual shipped API surfaces instead of only the registry internals.

**Files:**
- Modify only if needed after the red/green loop above:
  - `server/api/...` route files
  - `server/models/realtime.py`
  - `agent-sdk/python/iron_council_client.py`
  - relevant tests

**Step 1: Run focused API tests**

Run:
`uv run pytest -o addopts='' tests/api/test_agent_api.py -k "treaty or briefing"`

Expected: PASS with broken treaty statuses serialized correctly.

**Step 2: Run focused process/realtime tests**

Run:
`uv run pytest -o addopts='' tests/api/test_agent_process_api.py -k treaty`

Expected: PASS.

**Step 3: Add the smallest follow-up fix if any path still assumes only three statuses**

Example shape to preserve:
```python
class TreatyRecord(StrictModel):
    ...
    status: TreatyStatus
```

Do not fork separate “broken treaty” models.

---

### Task 5: Review, simplify, and close the story

**Objective:** Leave the repo in a simple, coherent state with BMAD bookkeeping updated honestly.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/42-1-break-active-treaties-on-hostile-attacks-and-announce-them.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run the real quality gate**

Run:
`source .venv/bin/activate && make quality`

Expected: PASS.

**Step 2: Do a simplification pass**

Check:
- one small helper for treaty-break detection is enough
- no duplicate hostile-action logic in more than one module
- no new abstraction layer was introduced
- world-chat side effects remain explicit and easy to review

**Step 3: Update BMAD status**

Set:
- `42-1-break-active-treaties-on-hostile-attacks-and-announce-them: done`
- keep the story artifact debug log, completion notes, and file list accurate
- set `next_story` to the next diplomacy follow-up only if you also create that artifact in the same run; otherwise leave a clear note

**Step 4: Commit and push**

Run:
`git add -A && git commit -m "feat: break active treaties on hostile attacks" && git push`

Expected: clean coherent feature commit on `master`.

---

### Final verification checklist

- `uv run pytest -o addopts='' tests/test_agent_registry.py -k treaty`
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k "treaty or briefing"`
- `uv run pytest -o addopts='' tests/api/test_agent_process_api.py -k treaty`
- `source .venv/bin/activate && make quality`

---

Plan complete and saved. Ready to execute using subagent-driven-development with a Codex worker, spec review, quality review, and final simplification pass.
