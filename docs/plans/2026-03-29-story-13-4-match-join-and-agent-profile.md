# Story 13.4 Match Join and Agent Profile Scaffolding Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Complete Story 13.4 by adding a narrow match-join contract plus a lightweight agent profile read surface that improves API completeness without inventing full auth, billing, or matchmaking.

**Architecture:** Extend the existing `InMemoryMatchRegistry` with tiny deterministic metadata for seeded matches and agent identities, then expose it through FastAPI endpoints that follow the repo’s structured `ApiErrorResponse` conventions. Keep the story intentionally scaffolding-sized: join is just “joinable seeded slot vs. structured rejection,” and profile is just stable identity/rating/history placeholder data that can later be backed by real auth and persistence.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, pytest, httpx, uv, uvicorn, existing running-app smoke harness.

---

## Parallelism assessment

- **Safe to parallelize:** nothing substantial inside this story. The likely changes all overlap in `server/models/api.py`, `server/agent_registry.py`, `server/main.py`, and the same API-boundary tests.
- **Must stay sequential:** contract design, registry behavior, endpoint wiring, and smoke coverage.
- **Decision for this run:** execute Story 13.4 as one sequential worker thread in a dedicated git worktree, then run separate spec/quality review passes before merge.

---

### Task 1: Add the Story 13.4 plan and lock the public contract shapes

**Objective:** Define the exact request/response models before touching registry or routes.

**Files:**
- Create: `docs/plans/2026-03-29-story-13-4-match-join-and-agent-profile.md`
- Modify: `server/models/api.py`
- Test: `tests/api/test_agent_api.py`

**Step 1: Write failing API-boundary tests**

Add tests that assert the public JSON shapes and OpenAPI schema refs for:
- `POST /api/v1/matches/{match_id}/join`
- `GET /api/v1/agents/{agent_id}/profile`

Include a happy-path join response, a structured join rejection response, and a profile payload with stable fields like `agent_id`, `display_name`, `rating`, `matches_played`, `wins`, `losses`, and a short `recent_matches` list.

Run:

```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'join or profile' -q
```

Expected: **FAIL** because the schemas and routes do not exist yet.

**Step 2: Add minimal request/response models**

Add narrow Pydantic models only for what this story needs, for example:

```python
class MatchJoinRequest(StrictModel):
    agent_id: str


class MatchJoinResponse(StrictModel):
    status: Literal["joined"]
    match_id: str
    agent_id: str
    player_id: str
    slot_status: Literal["claimed"]


class MatchJoinRejectionResponse(StrictModel):
    status: Literal["rejected"]
    match_id: str
    agent_id: str
    reason_code: str
    reason: str


class AgentRecentMatchSummary(StrictModel):
    match_id: str
    result: Literal["won", "lost", "draw", "in_progress"]
    role: str


class AgentProfileResponse(StrictModel):
    agent_id: str
    display_name: str
    rating: int = Field(ge=0)
    matches_played: int = Field(ge=0)
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    recent_matches: list[AgentRecentMatchSummary] = Field(default_factory=list)
```

Keep the names and fields boring and stable. Do not add speculative auth tokens, account linking, queue preference metadata, or billing state.

**Step 3: Verify the focused tests pass**

```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'join or profile' -q
```

Expected: **PASS** for contract-only checks once the models/OpenAPI are wired.

**Step 4: Commit**

```bash
git add docs/plans/2026-03-29-story-13-4-match-join-and-agent-profile.md server/models/api.py tests/api/test_agent_api.py
git commit -m "feat: add join and profile api contracts"
```

---

### Task 2: Extend the in-memory registry with deterministic join/profile scaffolding

**Objective:** Add the smallest registry behavior that can answer join requests and profile reads deterministically.

**Files:**
- Modify: `server/agent_registry.py`
- Test: `tests/test_agent_registry.py`
- Test: `tests/api/test_agent_api.py`

**Step 1: Write failing behavior tests**

Add tests that verify:
- a seeded joinable match accepts a known agent and claims a deterministic player slot
- re-joining with the same agent returns the same stable assignment rather than mutating another slot
- unknown agents are rejected with a structured reason
- non-joinable matches reject without mutating unrelated match state
- profile reads return deterministic placeholder data for known agents

Run:

```bash
uv run pytest --no-cov tests/test_agent_registry.py tests/api/test_agent_api.py -k 'join or profile' -q
```

Expected: **FAIL** because the registry cannot yet track joinability or profiles.

**Step 2: Implement the narrow registry metadata**

Add simple dataclasses for seeded metadata, for example:

```python
@dataclass(slots=True)
class AgentProfile:
    agent_id: str
    display_name: str
    rating: int
    matches_played: int
    wins: int
    losses: int
    recent_matches: list[AgentRecentMatch]


@dataclass(slots=True)
class JoinSlot:
    agent_id: str | None
    player_id: str


@dataclass(slots=True)
class MatchRecord:
    ...
    joinable: bool = False
    join_slots: list[JoinSlot] = field(default_factory=list)
```

Then add methods with boring semantics:
- `get_agent_profile(agent_id)`
- `join_match(match_id, agent_id)`

Rules:
- known seeded agents only
- only join records marked `joinable=True`
- deterministic first-open-slot assignment
- repeat join by the same agent returns the existing claimed slot
- rejection paths do not mutate the record

If the DB-backed app path uses `load_match_registry_from_database`, keep the default seeded metadata available there too by enriching the registry after load, or by making the registry itself own global seeded agent/profile metadata independent of match source.

**Step 3: Verify the focused tests pass**

```bash
uv run pytest --no-cov tests/test_agent_registry.py tests/api/test_agent_api.py -k 'join or profile' -q
```

Expected: **PASS**.

**Step 4: Commit**

```bash
git add server/agent_registry.py tests/test_agent_registry.py tests/api/test_agent_api.py
git commit -m "feat: add deterministic join and profile registry scaffolding"
```

---

### Task 3: Add FastAPI join/profile endpoints with structured errors

**Objective:** Expose the new registry behavior through repo-consistent REST endpoints.

**Files:**
- Modify: `server/main.py`
- Modify: `server/models/api.py`
- Modify: `tests/api/test_agent_api.py`

**Step 1: Write failing endpoint tests**

Cover:
- `POST /api/v1/matches/{match_id}/join` success
- route/payload mismatch or unknown match failure
- unknown agent failure
- full/not-joinable match rejection
- `GET /api/v1/agents/{agent_id}/profile` success
- unknown profile failure
- OpenAPI response models for both routes

Run:

```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'join or profile' -q
```

Expected: **FAIL** because routes do not exist or do not yet follow the desired behavior.

**Step 2: Implement the minimal routes**

Follow the established API style:
- use `ApiError` for 404/400 failures
- keep route names narrow and boring
- preserve `ApiErrorResponse` in the OpenAPI response map
- return immediate JSON responses without introducing auth/session machinery

Suggested shape:

```python
@api_router.post(
    "/matches/{match_id}/join",
    response_model=MatchJoinResponse | MatchJoinRejectionResponse,
    responses={
        HTTPStatus.BAD_REQUEST: API_ERROR_RESPONSE_SCHEMA,
        HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA,
    },
)
async def join_match(...):
    ...


@api_router.get(
    "/agents/{agent_id}/profile",
    response_model=AgentProfileResponse,
    responses={HTTPStatus.NOT_FOUND: API_ERROR_RESPONSE_SCHEMA},
)
async def get_agent_profile(...):
    ...
```

If FastAPI’s union OpenAPI becomes awkward, prefer a single success model plus `ApiError` for hard failures and use a joined-vs-rejected response model only if the tests stay stable. The acceptance criteria allow either deterministic join success or a clear structured rejection path.

**Step 3: Verify the focused tests pass**

```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'join or profile' -q
```

Expected: **PASS**.

**Step 4: Commit**

```bash
git add server/main.py server/models/api.py tests/api/test_agent_api.py
git commit -m "feat: add match join and agent profile endpoints"
```

---

### Task 4: Cover the real running-app boundary and keep the smoke suite lean

**Objective:** Prove the story works through the actual app command path, not just in-process tests.

**Files:**
- Modify: `tests/e2e/test_api_smoke.py`
- Optionally modify: `tests/api/test_agent_process_api.py` if a focused process test already exists there

**Step 1: Write failing running-app tests**

Add one concise smoke journey that:
- calls `GET /api/v1/matches`
- joins the seeded primary match with a known agent
- fetches that agent’s profile
- confirms the API returns stable JSON and healthy HTTP statuses through the running server process

Run:

```bash
uv run --extra dev pytest --no-cov tests/e2e/test_api_smoke.py -k 'join or profile' -q
```

Expected: **FAIL** because the running app does not yet expose the new routes.

**Step 2: Keep support changes narrow**

If the DB-backed smoke path needs seeded metadata available after `load_match_registry_from_database`, implement the smallest registry/bootstrap hook required. Do not add real auth, API-key lookup, or persistent profile write paths.

**Step 3: Verify focused process coverage passes**

```bash
uv run --extra dev pytest --no-cov tests/e2e/test_api_smoke.py -k 'join or profile' -q
```

Expected: **PASS**.

**Step 4: Commit**

```bash
git add tests/e2e/test_api_smoke.py tests/api/test_agent_process_api.py
git commit -m "test: cover join and profile api through running app"
```

---

### Task 5: Final story verification, simplification pass, and BMAD bookkeeping

**Objective:** Leave Story 13.4 and Epic 13 in a coherent shippable state.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/13-4-add-match-join-and-lightweight-agent-profile-scaffolding.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `README.md` only if the new endpoints need a tiny mention

**Step 1: Run the relevant gates**

```bash
uv run pytest --no-cov tests/test_agent_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py -q
uv run ruff check .
uv run mypy
uv run pytest -q
```

Expected: all pass.

**Step 2: Review for overbuild**

Perform an explicit simplification pass:
- remove any extra abstractions or helpers not needed by this story
- ensure tests assert behavior at the API boundary, not internals
- confirm no auth/billing/matchmaking scope creep landed

**Step 3: Update BMAD artifacts**

- mark Story 13.4 done
- mark Epic 13 done if no further stories remain
- fill in the story’s completion notes, debug log references, and file list

**Step 4: Commit the coherent final state**

```bash
git add _bmad-output/implementation-artifacts/13-4-add-match-join-and-lightweight-agent-profile-scaffolding.md _bmad-output/implementation-artifacts/sprint-status.yaml README.md server tests docs/plans
git commit -m "feat: add match join and lightweight agent profile scaffolding"
```

---

## Verification checklist

- [ ] `POST /api/v1/matches/{match_id}/join` exists and behaves deterministically for seeded joinable cases
- [ ] unsupported or unknown join attempts fail with structured errors or structured rejection responses
- [ ] `GET /api/v1/agents/{agent_id}/profile` exists with stable placeholder/rating/history fields
- [ ] in-process API tests pass
- [ ] running-app smoke coverage passes
- [ ] ruff, mypy, and full pytest pass
- [ ] Story 13.4 BMAD artifact is updated
- [ ] sprint status reflects the completed story and epic state
