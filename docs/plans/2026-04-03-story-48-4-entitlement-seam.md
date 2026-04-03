# Story 48.4 Entitlement Seam Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a narrow typed entitlement seam that gates owned API-key creation and API-key match occupancy without introducing real billing dependencies.

**Architecture:** Introduce a small DB-backed entitlement module plus persistence table for explicit manual/dev grants, expose just enough typed summary data for lifecycle/UI honesty, and route current API-key lifecycle + occupancy checks through that seam. Keep request-time code synchronous, local, and provider-agnostic so later billing can replace only the grant source.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, pytest, existing DB-backed API + process tests.

---

### Task 1: Add the entitlement persistence seam

**Objective:** Create the minimal typed persistence model + migration for explicit manual/dev grants.

**Files:**
- Create/Modify: `server/db/models.py`
- Create: `server/db/agent_entitlements.py`
- Create: `alembic/versions/<new_revision>_agent_entitlements.py`
- Test: `tests/test_database_migrations.py`

**Step 1: Write failing tests**
- Add a migration test asserting a new entitlement table exists with grant source, active flag, and timestamps.
- Add a unit test for a typed loader returning a default “not entitled” result when no grant exists.

**Step 2: Run focused tests to verify failure**
- `source venv/bin/activate && python -m pytest tests/test_database_migrations.py -q`
- `source venv/bin/activate && python -m pytest tests/db/test_agent_entitlements.py -q`

**Step 3: Write minimal implementation**
- Add a tiny entitlement row model/table.
- Add a typed `AgentEntitlementStatus` result and loader/helper functions for manual/dev grants.
- Keep names billing-ready but behavior deliberately small.

**Step 4: Run focused tests to verify pass**
- Same commands as Step 2.

**Step 5: Commit**
- `git add alembic server/db tests && git commit -m "feat: add agent entitlement seam"`

### Task 2: Gate owned API-key lifecycle through the seam

**Objective:** Prevent non-entitled accounts from creating owned API keys while preserving honest structured errors and compact list/revoke behavior.

**Files:**
- Modify: `server/db/api_key_lifecycle.py`
- Modify: `server/api/authenticated_write_routes.py`
- Modify: `server/models/api.py`
- Test: `tests/api/test_agent_api.py`
- Test: `tests/api/test_agent_process_api.py`

**Step 1: Write failing tests**
- Add API tests proving create is rejected with a structured entitlement error when the owner lacks an active manual/dev grant.
- Add tests proving granted owners can still create/list/revoke keys.
- If the response model changes, add contract assertions for the typed summary/status fields.

**Step 2: Run focused tests to verify failure**
- `source venv/bin/activate && python -m pytest tests/api/test_agent_api.py -q -k "api_key_lifecycle or entitlement"`

**Step 3: Write minimal implementation**
- Resolve entitlement once per request path via the new seam.
- Keep list/revoke behavior simple; only creation should be blocked unless the story clearly needs broader gating.
- Return honest error code/message without mentioning future providers.

**Step 4: Run focused tests to verify pass**
- Repeat Step 2.

**Step 5: Commit**
- `git add server tests && git commit -m "feat: gate owned api key creation on entitlement grants"`

### Task 3: Route API-key occupancy checks through the entitlement seam

**Objective:** Preserve Story 48.3 occupancy behavior but source the allowed concurrency from the entitlement layer.

**Files:**
- Modify: `server/db/identity.py`
- Modify: `server/db/lobby_registry.py`
- Test: `tests/api/test_agent_api.py`
- Test: `tests/api/test_agent_process_api.py`

**Step 1: Write failing tests**
- Add behavior tests proving non-entitled or zero-capacity keys receive the existing honest occupancy rejection.
- Add tests proving a manual/dev grant with capacity can create/join within allowance and recovers after match completion.

**Step 2: Run focused tests to verify failure**
- `source venv/bin/activate && python -m pytest tests/api/test_agent_api.py -q -k "occupancy"`
- `source venv/bin/activate && python -m pytest tests/api/test_agent_process_api.py -q -k "occupancy"`

**Step 3: Write minimal implementation**
- Replace the fixed occupancy constant path with an entitlement-derived allowance.
- Preserve the existing public error code/message for over-capacity joins/creates.
- Keep the entitlement seam local; do not add checkout/admin concepts.

**Step 4: Run focused tests to verify pass**
- Repeat Step 2.

**Step 5: Commit**
- `git add server tests && git commit -m "feat: source api key occupancy from entitlements"`

### Task 4: Close out docs, BMAD artifacts, and full verification

**Objective:** Leave the repo in a coherent shippable state with docs and BMAD artifacts aligned.

**Files:**
- Modify: `README.md`
- Modify: `docs/index.md`
- Modify: `agent-sdk/README.md`
- Modify: `_bmad-output/implementation-artifacts/48-4-add-a-billing-ready-agent-entitlement-seam-with-manual-dev-grants.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Test: `tests/test_local_dev_docs.py`

**Step 1: Write/adjust failing docs tests if needed**
- Add assertions for entitlement/manual-dev-grant wording if the shipped docs should change.

**Step 2: Run focused docs tests**
- `source venv/bin/activate && python -m pytest tests/test_local_dev_docs.py -q`

**Step 3: Update docs and BMAD closeout**
- Replace stale “future work” wording with the shipped entitlement seam description.
- Mark story signoff/checklist/sprint tracker fields consistently with real verification results.

**Step 4: Run real repo gate**
- `source venv/bin/activate && make quality`

**Step 5: Commit**
- `git add README.md docs agent-sdk _bmad-output tests && git commit -m "docs: close out story 48-4"`
