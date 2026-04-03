# Story 49.2 Private Guidance Briefing Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Let an authenticated human owner send private guidance to an owned agent and have that guidance appear on the agent’s next briefing in a dedicated additive field.

**Architecture:** Add a tiny DB-backed guidance persistence seam separate from chat messages, expose it through a human-authenticated owned-agent write route, and extend the existing agent briefing response/SDK with a deterministic `guidance` collection. Reuse the explicit human-user -> owned API key -> agent ownership path from Story 49.1, keep the zero-guidance path additive and empty, and avoid changing public/group/direct messaging semantics.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, pytest, existing DB-backed API + SDK + smoke tests.

---

### Task 1: Add the private guidance persistence seam

**Objective:** Create the smallest typed persisted model and read/write helpers for owner-to-agent guidance.

**Files:**
- Modify: `server/db/models.py`
- Create: `server/db/guidance.py`
- Create: `alembic/versions/<new_revision>_owned_agent_guidance.py`
- Modify: `server/db/testing.py`
- Test: `tests/test_database_migrations.py`
- Test: `tests/db/test_guidance.py`

**Step 1: Write failing tests**
- Add a migration/schema test asserting a dedicated guidance table exists and is separate from `messages`.
- Add DB helper tests proving writes/readbacks are deterministic by `(tick, created_at, id)` and that empty reads return `[]`.

**Step 2: Run focused tests to verify failure**
- `source .venv/bin/activate && python -m pytest tests/test_database_migrations.py --no-cov -q`
- `source .venv/bin/activate && python -m pytest tests/db/test_guidance.py --no-cov -q`

**Step 3: Write minimal implementation**
- Add a small row model storing match, sender human/user ownership context, recipient agent/player context, tick, content, and created timestamp.
- Add narrow helper functions for append/list behavior only; do not invent override or consumption semantics.
- Seed test DB cleanup/data paths so DB-backed tests remain honest.

**Step 4: Run focused tests to verify pass**
- Repeat Step 2.

**Step 5: Commit**
- `git add alembic server/db tests && git commit -m "feat: add owned agent guidance persistence seam"`

### Task 2: Add the owned-agent private guidance write route

**Objective:** Let an authenticated human owner enqueue guidance for an owned agent with ownership, membership, and tick checks.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/api/app_services.py`
- Modify: `server/api/authenticated_write_routes.py`
- Test: `tests/api/test_agent_api.py`
- Test: `tests/api/test_agent_process_api.py`

**Step 1: Write failing tests**
- Add API tests proving the owner can post guidance for an owned joined agent in a DB-backed match.
- Add negative-path tests for missing human bearer auth, wrong owner, wrong match/unjoined agent, and tick mismatch.
- Add OpenAPI/contract coverage for the new route if the repo already pins these routes.

**Step 2: Run focused tests to verify failure**
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py --no-cov -q -k "guided_session or agent_guidance or briefing"`
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_process_api.py --no-cov -q -k "guidance or briefing"`

**Step 3: Write minimal implementation**
- Add a typed request/acceptance model for private guidance.
- Reuse `require_owned_agent_context(...)` plus match membership resolution so authorization stays on the real owned-agent boundary.
- Persist guidance through the new DB seam and keep it isolated from `messages.direct`, `messages.group`, and `messages.world`.

**Step 4: Run focused tests to verify pass**
- Repeat Step 2.

**Step 5: Commit**
- `git add server tests && git commit -m "feat: add owned agent guidance write route"`

### Task 3: Extend the agent briefing and SDK contract

**Objective:** Surface the new private guidance in the agent briefing response and typed Python SDK without breaking the empty state.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/api/authenticated_read_routes.py`
- Modify: `agent-sdk/python/iron_council_client.py`
- Test: `tests/api/test_agent_api.py`
- Test: `tests/agent_sdk/test_python_client.py`
- Test: `tests/e2e/test_api_smoke.py`
- Test: `tests/e2e/test_agent_sdk_smoke.py`

**Step 1: Write failing tests**
- Add API tests proving `GET /api/v1/matches/{match_id}/agent-briefing` returns a dedicated `guidance` list with deterministic guidance items for owned agents and `[]` when none exists.
- Add SDK parsing tests proving the typed briefing model includes `guidance`.
- Add one real-process API smoke and one SDK smoke that exercise write-then-briefing behavior.

**Step 2: Run focused tests to verify failure**
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py --no-cov -q -k "agent_briefing or agent_guidance"`
- `source .venv/bin/activate && python -m pytest tests/agent_sdk/test_python_client.py --no-cov -q -k "briefing"`
- `source .venv/bin/activate && python -m pytest tests/e2e/test_api_smoke.py --no-cov -q -k "briefing or guidance"`
- `source .venv/bin/activate && python -m pytest tests/e2e/test_agent_sdk_smoke.py --no-cov -q -k "briefing or guidance"`

**Step 3: Write minimal implementation**
- Add a compact typed `guidance` record/collection to the briefing response and SDK models.
- Keep the field additive and always present with a default empty list.
- Ensure agent briefings read from the new guidance seam rather than reusing chat-message buckets.

**Step 4: Run focused tests to verify pass**
- Repeat Step 2.

**Step 5: Commit**
- `git add server agent-sdk tests && git commit -m "feat: deliver private guidance through agent briefing"`

### Task 4: Review, simplify, and close out BMAD artifacts

**Objective:** Leave the repo in the simplest coherent shippable state with honest story bookkeeping.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/49-2-deliver-private-human-to-agent-guidance-through-the-briefing-path.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Optional docs if needed: `core-plan.md`, `agent-sdk/README.md`, or adjacent docs only if the shipped contract changed user-facing guidance.

**Step 1: Run review/simplification pass**
- Check the implementation for scope creep, duplicated ownership logic, or accidental chat-channel coupling.
- Remove any unnecessary compatibility plumbing or abstractions.

**Step 2: Run focused verification**
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py --no-cov -q -k "guided_session or agent_guidance or agent_briefing"`
- `source .venv/bin/activate && python -m pytest tests/agent_sdk/test_python_client.py --no-cov -q -k "briefing"`
- `source .venv/bin/activate && python -m pytest tests/e2e/test_api_smoke.py --no-cov -q -k "briefing or guidance"`
- `source .venv/bin/activate && python -m pytest tests/e2e/test_agent_sdk_smoke.py --no-cov -q -k "briefing or guidance"`

**Step 3: Run the real repo gate**
- `source .venv/bin/activate && make quality`

**Step 4: Update BMAD closeout**
- Mark story tasks/signoffs/checklists accurately.
- Record the real final commands/results in debug/completion sections.
- Advance `sprint-status.yaml` to the next story only after final verification passes.

**Step 5: Commit**
- `git add _bmad-output docs/plans server agent-sdk tests alembic && git commit -m "docs: close out story 49-2"`
