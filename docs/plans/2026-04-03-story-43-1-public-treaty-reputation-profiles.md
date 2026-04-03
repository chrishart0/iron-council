# Story 43.1 Public Treaty Reputation Profiles Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add an additive treaty-reputation section to the public agent and human profile contracts/pages so competitor reputation reflects signed, honored, withdrawn, and broken treaties without inventing data.

**Architecture:** Reuse the existing public profile routes and profile assembly seams. Add small shared API models for treaty-reputation counts/history, aggregate DB-backed treaty rows onto persistent public identities in `server/db/identity_hydration.py` (or a tight sibling helper), and keep in-memory/empty-history modes honest by returning zeroed counts and an empty history list. Then update the existing Next.js public profile pages to render the new summary/history sections read-only.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic, pytest, Next.js/React/TypeScript, Vitest.

---

## Parallelism / sequencing decision

- **Sequential for server contract + aggregation.** The public profile models, DB assembly, and API tests all touch the same contract seam.
- **Safe parallelism after the server shape is stable:** the public agent profile page and public human profile page rendering/tests can be split, but one worker can still complete the story cleanly.

---

### Task 1: Add additive treaty-reputation profile models and failing contract tests

**Objective:** Define the smallest explicit response-shape additions before changing assembly logic.

**Files:**
- Modify: `server/models/api.py`
- Modify: `client/src/lib/types.ts`
- Test: `tests/api/test_agent_api.py`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing tests**

Add API/client contract assertions that the public profile payload now includes:
- `treaty_reputation.summary.signed`
- `treaty_reputation.summary.active`
- `treaty_reputation.summary.honored`
- `treaty_reputation.summary.withdrawn`
- `treaty_reputation.summary.broken_by_self`
- `treaty_reputation.summary.broken_by_counterparty`
- `treaty_reputation.history` as a list of explicit records

```python
assert payload["treaty_reputation"] == {
    "summary": {
        "signed": 0,
        "active": 0,
        "honored": 0,
        "withdrawn": 0,
        "broken_by_self": 0,
        "broken_by_counterparty": 0,
    },
    "history": [],
}
```

**Step 2: Run test to verify failure**

Run:
`source .venv/bin/activate && uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'public_and_authenticated_agent_profile_routes_return_stable_shapes or human_profile_route_returns_structured_unavailable_error_without_db_backing'`

Expected: FAIL because the profile routes do not yet include `treaty_reputation`.

**Step 3: Write minimal implementation**

Add explicit Pydantic models for treaty-reputation summary/history and wire them into `AgentProfileResponse` and `HumanProfileResponse`. Mirror the types in the client runtime types.

```python
class ProfileTreatyReputationSummary(StrictModel):
    signed: int = Field(ge=0)
    active: int = Field(ge=0)
    honored: int = Field(ge=0)
    withdrawn: int = Field(ge=0)
    broken_by_self: int = Field(ge=0)
    broken_by_counterparty: int = Field(ge=0)

class ProfileTreatyHistoryRecord(StrictModel):
    match_id: str
    counterparty_display_name: str
    treaty_type: TreatyType
    status: TreatyStatus
    signed_tick: TickDuration
    ended_tick: TickDuration | None = None
    broken_by_self: bool

class ProfileTreatyReputation(StrictModel):
    summary: ProfileTreatyReputationSummary
    history: list[ProfileTreatyHistoryRecord] = Field(default_factory=list)
```

**Step 4: Run focused tests to verify pass**

Run:
`source .venv/bin/activate && uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'public_and_authenticated_agent_profile_routes_return_stable_shapes or human_profile_route_returns_structured_unavailable_error_without_db_backing'`

Expected: PASS.

**Step 5: Commit**

```bash
git add server/models/api.py client/src/lib/types.ts tests/api/test_agent_api.py client/src/lib/api.test.ts
git commit -m "feat: add treaty reputation profile contract"
```

---

### Task 2: Aggregate DB-backed treaty history onto persistent profile identities

**Objective:** Assemble honest treaty-reputation data from persisted treaties for both agent and human public profiles.

**Files:**
- Modify: `server/db/identity_hydration.py`
- Modify: `server/db/models.py` only if imports/types need it (prefer no schema change)
- Test: `tests/test_db_registry.py`
- Test: `tests/api/test_agent_api.py`

**Step 1: Write failing tests**

Add a DB-backed regression proving a profiled competitor gets:
- summary counts relative to the profiled identity
- a deterministic treaty-history list ordered stably (for example by `signed_tick`, then treaty id)
- honest counterparty display names and `ended_tick`

Also add one empty-history regression for a valid profile with no treaty rows.

```python
assert profile.treaty_reputation.summary.broken_by_self == 1
assert profile.treaty_reputation.summary.broken_by_counterparty == 1
assert profile.treaty_reputation.history == [
    {
        "match_id": str(match_id),
        "counterparty_display_name": "West March",
        "treaty_type": "trade",
        "status": "broken_by_a",
        "signed_tick": 141,
        "ended_tick": 142,
        "broken_by_self": True,
    },
]
```

**Step 2: Run test to verify failure**

Run:
`source .venv/bin/activate && uv run pytest -o addopts='' tests/test_db_registry.py -k 'human_profile or agent_profile or treaty_reputation'`

Expected: FAIL because the DB profile assembly does not yet aggregate treaties.

**Step 3: Write minimal implementation**

In `server/db/identity_hydration.py`:
1. Load persisted treaty rows alongside the relevant player rows.
2. Build a mapping from persisted player ids to persistent public identities (`agent_id` / `human:{user_id}`).
3. Aggregate treaty rows per profiled identity.
4. Convert treaty status into identity-relative summary counts:
   - `active`
   - `withdrawn`
   - `broken_by_self`
   - `broken_by_counterparty`
   - `honored` = finished without the profiled competitor breaking it (keep this boring and explicit; if a treaty is still active it is not honored yet)
5. Return empty treaty reputation when no rows exist.

Prefer a helper like:

```python
def build_treaty_reputation_by_identity(...) -> dict[str, ProfileTreatyReputation]:
    ...
```

Do **not** fabricate provenance fields the DB does not store.

**Step 4: Run focused tests to verify pass**

Run:
`source .venv/bin/activate && uv run pytest -o addopts='' tests/test_db_registry.py -k 'human_profile or agent_profile or treaty_reputation' && source .venv/bin/activate && uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'public_and_authenticated_agent_profile_routes_return_stable_shapes or human_profile or automatic_treaty_breaks_surface_through_authenticated_reads'`

Expected: PASS.

**Step 5: Commit**

```bash
git add server/db/identity_hydration.py tests/test_db_registry.py tests/api/test_agent_api.py
git commit -m "feat: aggregate treaty reputation for public profiles"
```

---

### Task 3: Keep in-memory/seeded profile modes honest with deterministic empty treaty reputation

**Objective:** Ensure existing non-DB profile surfaces remain additive and explicit rather than breaking or inventing treaty history.

**Files:**
- Modify: `server/agent_registry.py` or `server/registry_seed_data.py` only if constructors need the new field
- Modify: `server/db/lobby_registry.py` if creator profiles need the additive empty payload
- Test: `tests/api/test_agent_api.py`

**Step 1: Write failing tests**

Add/extend a profile-shape test proving the in-memory agent profile route now returns the additive empty treaty-reputation payload and the human-profile no-DB unavailable contract is unchanged.

**Step 2: Run test to verify failure**

Run:
`source .venv/bin/activate && uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'public_and_authenticated_agent_profile_routes_return_stable_shapes or human_profile_route_returns_structured_unavailable_error_without_db_backing'`

Expected: FAIL until in-memory constructors include the new field.

**Step 3: Write minimal implementation**

Add a shared zero-value constructor/helper and use it in seeded/in-memory profile builders.

```python
def empty_treaty_reputation() -> ProfileTreatyReputation:
    return ProfileTreatyReputation(
        summary=ProfileTreatyReputationSummary(
            signed=0,
            active=0,
            honored=0,
            withdrawn=0,
            broken_by_self=0,
            broken_by_counterparty=0,
        ),
        history=[],
    )
```

**Step 4: Run focused tests to verify pass**

Run the same focused API command again and expect PASS.

**Step 5: Commit**

```bash
git add server/models/api.py server/db/lobby_registry.py tests/api/test_agent_api.py
git commit -m "feat: keep empty treaty reputation explicit"
```

---

### Task 4: Render treaty reputation on the public profile pages

**Objective:** Surface the new contract on the shipped agent/human profile pages with deterministic empty-state UI.

**Files:**
- Modify: `client/src/lib/api.ts`
- Modify: `client/src/components/public/public-agent-profile-page.tsx`
- Modify: `client/src/components/public/public-human-profile-page.tsx`
- Test: `client/src/components/public/public-agent-profile-page.test.tsx`
- Test: `client/src/components/public/public-human-profile-page.test.tsx`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing tests**

Add page assertions for:
- treaty summary counts
- rendered history rows
- deterministic empty-state copy when `history` is empty

```tsx
expect(screen.getByRole("heading", { name: /Treaty reputation/i })).toBeVisible();
expect(screen.getByText("Broken by self")).toBeVisible();
expect(screen.getByText("No public treaty history has been recorded yet.")).toBeVisible();
```

**Step 2: Run test to verify failure**

Run:
`cd client && npm test -- --run src/lib/api.test.ts src/components/public/public-agent-profile-page.test.tsx src/components/public/public-human-profile-page.test.tsx`

Expected: FAIL because the pages do not yet render treaty reputation.

**Step 3: Write minimal implementation**

Keep the UI boring and read-only:
- a summary `<dl>` section for counts
- a simple history list/table below it
- empty-state text when there are no records

Do not add filters, tabs, or new navigation.

**Step 4: Run focused tests to verify pass**

Run the same client command and expect PASS.

**Step 5: Commit**

```bash
git add client/src/lib/api.ts client/src/components/public/public-agent-profile-page.tsx client/src/components/public/public-human-profile-page.tsx client/src/components/public/public-agent-profile-page.test.tsx client/src/components/public/public-human-profile-page.test.tsx client/src/lib/api.test.ts
git commit -m "feat: render public treaty reputation"
```

---

### Task 5: Final verification, simplification, and BMAD closeout

**Objective:** Re-run the strongest practical checks, simplify if needed, and update story bookkeeping truthfully.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/43-1-add-public-treaty-reputation-to-competitor-profiles.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run focused server/client verification**

Run:
- `source .venv/bin/activate && uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'agent_profile or human_profile or treaty_reputation'`
- `source .venv/bin/activate && uv run pytest -o addopts='' tests/test_db_registry.py -k 'agent_profile or human_profile or treaty_reputation'`
- `cd client && npm test -- --run src/lib/api.test.ts src/components/public/public-agent-profile-page.test.tsx src/components/public/public-human-profile-page.test.tsx src/app/agents/[agentId]/page.test.tsx src/app/humans/[humanId]/page.test.tsx`

**Step 2: Run strongest practical repo-managed checks**

Run:
`source .venv/bin/activate && make quality`

Expected: PASS.

**Step 3: Simplification pass**

Verify:
- no duplicate aggregation logic between agent/human profile builders
- no fabricated treaty provenance
- no unnecessary client abstraction beyond a small rendering helper if clearly beneficial

**Step 4: Update BMAD artifacts**

Mark the story `done`, record the commands actually run, and advance `next_story` only if a clear Story 43.2 is drafted in the same run.

**Step 5: Commit**

```bash
git add _bmad-output/implementation-artifacts/43-1-add-public-treaty-reputation-to-competitor-profiles.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "docs: close story 43.1 treaty reputation"
```
