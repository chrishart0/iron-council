# Epic 13 Diplomacy Messaging API Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Deliver the next Phase 2 server increments by adding deterministic agent-facing messaging first, then layering public treaty/alliance surfaces on top of that communication foundation.

**Architecture:** Keep the current in-memory match-registry architecture and extend it with narrow diplomacy read/write contracts rather than jumping straight to full persistence or auth. Story 13.1 adds message inbox/send endpoints with deterministic filtering and structured error handling; later stories reuse that contract for treaty announcements, alliance visibility, and minimal join/profile scaffolding.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, pytest, httpx, uvicorn, uv, existing real-process API test harness.

---

### Task 1: Create the Epic 13 BMAD artifacts

**Objective:** Add the next-epic planning and story artifacts before implementation so the delivery loop stays grounded in BMAD source-of-truth files.

**Files:**
- Modify: `_bmad-output/planning-artifacts/epics.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Create: `_bmad-output/implementation-artifacts/13-1-add-agent-facing-match-message-inbox-and-send-endpoints.md`

**Step 1: Extend the epic roadmap**

Append Epic 13 with Stories 13.1–13.4, sequencing messaging before treaties and alliances.

**Step 2: Mark Story 13.1 active**

Update sprint status so Epic 11 is fully done, Epic 13 is in progress, and Story 13.1 is the active increment.

**Step 3: Save the story file**

Draft Story 13.1 with acceptance criteria, subtasks, implementation surface, and references.

**Step 4: Commit**

```bash
git add _bmad-output/planning-artifacts/epics.md _bmad-output/implementation-artifacts/sprint-status.yaml _bmad-output/implementation-artifacts/13-1-add-agent-facing-match-message-inbox-and-send-endpoints.md
git commit -m "docs: add epic 13 diplomacy messaging artifacts"
```

### Task 2: Add message API contracts with focused TDD

**Objective:** Define stable request/response models for world and direct messages before wiring endpoints.

**Files:**
- Modify: `server/models/api.py`
- Test: `tests/api/test_agent_api.py`

**Step 1: Write failing API-boundary tests**

Add tests that assert the public JSON shapes for:
- `GET /api/v1/matches/{match_id}/messages?player_id=...`
- `POST /api/v1/matches/{match_id}/messages`
- OpenAPI references for the new schemas

Run:

```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k messages -q
```

Expected: FAIL because the message schemas/endpoints do not exist yet.

**Step 2: Add the minimal contracts**

Create narrow Pydantic models similar to the existing match/order API models. Keep v1 intentionally small:
- channels: `world`, `direct`
- deterministic message record shape with sender, recipient, tick, content, and sequence/id metadata
- structured acceptance response for POST

**Step 3: Verify focused tests pass**

```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k messages -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add server/models/api.py tests/api/test_agent_api.py
git commit -m "feat: add message API contracts"
```

### Task 3: Extend the in-memory registry with deterministic message storage

**Objective:** Add the smallest registry abstraction that can store and filter match messages deterministically.

**Files:**
- Modify: `server/agent_registry.py`
- Test: `tests/api/test_agent_api.py`

**Step 1: Write failing behavior tests**

Add tests that verify:
- posting messages appends deterministic history in acceptance order
- inbox listing returns world messages plus direct messages involving the requesting player only
- invalid requests do not mutate stored message history

Run:

```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'messages and not openapi' -q
```

Expected: FAIL because the registry cannot store or filter messages yet.

**Step 2: Write the minimal implementation**

Extend `MatchRecord`/`InMemoryMatchRegistry` with a small message store and helper methods. Keep it simple:
- no group chats yet
- deterministic integer sequence per match is fine
- use deep copies when exposing stored payloads

**Step 3: Verify focused tests pass**

```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k 'messages and not openapi' -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add server/agent_registry.py tests/api/test_agent_api.py
git commit -m "feat: add deterministic match message storage"
```

### Task 4: Add message endpoints in the FastAPI app with TDD

**Objective:** Expose the registry behavior through structured GET/POST agent API routes that match repo conventions.

**Files:**
- Modify: `server/main.py`
- Modify: `server/models/api.py`
- Modify: `tests/api/test_agent_api.py`

**Step 1: Write failing endpoint tests**

Cover:
- send world message success
- send direct message success
- list inbox success for sender/recipient/non-recipient cases
- unknown match/player and route/payload mismatch failures
- unsupported direct recipient failure

Run:

```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k messages -q
```

Expected: FAIL because routes do not exist or do not yet validate behavior.

**Step 2: Implement the minimal routes**

Follow the existing API style:
- structured `ApiError` responses
- route match ID validation
- 202 Accepted for POST if you mirror order submission semantics, or 200 OK if the response is an immediate message echo; choose one and keep tests/docs consistent
- player-scoped GET query param like the state endpoint

**Step 3: Verify focused tests pass**

```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k messages -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add server/main.py server/models/api.py tests/api/test_agent_api.py
git commit -m "feat: add match message API endpoints"
```

### Task 5: Add real-process API coverage for the messaging story

**Objective:** Extend the existing running-app harness so this user-facing story is validated through the real HTTP boundary.

**Files:**
- Modify: `tests/api/test_agent_process_api.py`
- Modify: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing process-boundary tests**

Add one focused integration test or smoke flow that:
- posts a world or direct message to the running app
- polls messages for two different players
- proves only visible messages are returned to each player

Run:

```bash
uv run --extra dev pytest --no-cov tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py -k message -q
```

Expected: FAIL because the running app does not yet support message routes.

**Step 2: Implement only what the boundary test needs**

If the real-process path needs tiny support changes for deterministic registry initialization, keep them narrow and avoid speculative persistence work.

**Step 3: Verify focused process tests pass**

```bash
uv run --extra dev pytest --no-cov tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py -k message -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py
git commit -m "test: cover message API through running app"
```

### Task 6: Finish the story, review it, and simplify it

**Objective:** Close Story 13.1 with verification, artifact updates, and an explicit simplification pass.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/13-1-add-agent-facing-match-message-inbox-and-send-endpoints.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Review: `server/agent_registry.py`
- Review: `server/main.py`
- Review: `server/models/api.py`
- Review: `tests/api/test_agent_api.py`
- Review: `tests/api/test_agent_process_api.py`
- Review: `tests/e2e/test_api_smoke.py`

**Step 1: Run focused verification**

```bash
uv run pytest --no-cov tests/api/test_agent_api.py -k messages -q
uv run --extra dev pytest --no-cov tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py -k message -q
```

Expected: PASS.

**Step 2: Run the repository quality gate**

```bash
make quality
```

Expected: PASS.

**Step 3: Run the final review pass**

Check explicitly for:
- spec compliance
- message visibility correctness
- overcomplexity / unnecessary abstraction
- KISS / simplest-correct-solution
- repo-convention alignment

**Step 4: Update BMAD artifacts and commit**

```bash
git add _bmad-output/implementation-artifacts/13-1-add-agent-facing-match-message-inbox-and-send-endpoints.md _bmad-output/implementation-artifacts/sprint-status.yaml
# include AGENTS.md if it becomes part of the intended story change set
git commit -m "feat: add deterministic match messaging API"
```
