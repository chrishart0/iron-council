# Story 49.3 Guided Order Override Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Let an authenticated human owner deterministically replace their owned agent’s current-tick queued orders before resolution, while recording narrow DB-backed audit metadata for later guided-session/client explanation.

**Architecture:** Keep the scope honest to the current engine shape: implement pre-tick **order** overrides only, because orders are the only queued next-tick action surface in the server today. Add a small audit table/helper for override metadata, add a human-authenticated owned-agent override route that replaces same-player same-tick queued submissions in the in-memory registry, and verify the guided-session read model now reflects the replacement orders via existing aggregation logic.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, pytest, existing DB-backed guided-session ownership/auth seams.

---

### Task 1: Add the guided override audit persistence seam

**Objective:** Create the smallest typed persisted audit record for owned-agent guided order overrides.

**Files:**
- Modify: `server/db/models.py`
- Create: `server/db/guided_overrides.py`
- Create: `alembic/versions/<new_revision>_owned_agent_guided_overrides.py`
- Modify: `server/db/testing.py`
- Test: `tests/test_database_migrations.py`
- Test: `tests/db/test_guided_overrides.py`

**Step 1: Write failing tests**
- Add a migration/schema test asserting a dedicated `owned_agent_guided_overrides` table exists with owner/agent/match/tick metadata, serialized order payload, superseded-count metadata, and created timestamp.
- Add DB helper tests proving append/list ordering is deterministic and owner filtering is preserved.

**Step 2: Run focused tests to verify failure**
- `source .venv/bin/activate && python -m pytest tests/test_database_migrations.py --no-cov -q`
- `source .venv/bin/activate && python -m pytest tests/db/test_guided_overrides.py --no-cov -q`

**Step 3: Write minimal implementation**
- Add a narrow SQLAlchemy row model plus helper dataclass/functions for append/list only.
- Persist the override’s accepted order batch and superseded submission count as the audit record.
- Keep the seam additive; do not invent consumption or replay logic yet.

**Step 4: Run focused tests to verify pass**
- Repeat Step 2.

**Step 5: Commit**
- `git add alembic server/db tests && git commit -m "feat: add guided override audit seam"`

### Task 2: Add registry-level guided order replacement semantics

**Objective:** Give the in-memory registry a single honest way to replace one player’s queued orders for the current tick.

**Files:**
- Modify: `server/agent_registry.py`
- Test: `tests/test_agent_registry.py`
- Optional helper reuse if needed: `server/agent_registry_commands.py`

**Step 1: Write failing tests**
- Add a registry test proving a guided override for a player/tick removes that player’s earlier queued submissions for the same tick, leaves other players/ticks untouched, and returns deterministic replacement metadata.
- Add a regression proving later tick or unrelated-player submissions are unchanged.

**Step 2: Run focused tests to verify failure**
- `source .venv/bin/activate && python -m pytest tests/test_agent_registry.py --no-cov -q -k "guided_override or replace_player_orders"`

**Step 3: Write minimal implementation**
- Add a small `replace_player_submissions(...)` or equivalent method on `InMemoryMatchRegistry`.
- Replace same-player same-tick queued submissions with one deep-copied envelope and return the surviving submission index / superseded count deterministically.
- Do not widen tick-resolution semantics beyond queue replacement.

**Step 4: Run focused tests to verify pass**
- Repeat Step 2.

**Step 5: Commit**
- `git add server tests && git commit -m "feat: add guided order replacement semantics"`

### Task 3: Add the human-authenticated owned-agent guided override route

**Objective:** Expose a DB-backed write route that enforces ownership/current-tick timing and replaces queued orders for the owned agent.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/api/authenticated_write_routes.py`
- Modify: `server/api/authenticated_read_routes.py` (only if a tiny additive read-field/helper is honestly needed; otherwise leave it untouched)
- Test: `tests/api/test_agent_api.py`
- Test: `tests/api/test_agent_process_api.py`
- Test: `tests/e2e/test_api_smoke.py` if needed for real running-app coverage

**Step 1: Write failing tests**
- Add API tests proving the owner can replace current-tick queued orders for an owned joined agent and that guided-session reads now show the replacement order batch instead of the earlier queue.
- Add negative-path tests for non-DB-backed mode, wrong owner, missing/unjoined agent, match-id mismatch, and stale tick.
- Add at least one test proving a stale/forbidden override leaves the existing queue unchanged.
- Update OpenAPI contract assertions for the new route.

**Step 2: Run focused tests to verify failure**
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py --no-cov -q -k "guided_override or guided_session or openapi_declares_secured_match_route_contracts"`
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_process_api.py --no-cov -q -k "guided_override or guidance"`

**Step 3: Write minimal implementation**
- Add a typed request/acceptance model for owned-agent guided order overrides.
- Reuse `require_owned_agent_match_player(...)` so authorization stays on the human user -> owned API key -> joined agent boundary.
- Persist audit metadata through the new DB seam and replace the registry queue only after all validations pass.
- Use a structured guided-mode error code for stale overrides so the failure is distinct from generic order submission mismatch.

**Step 4: Run focused tests to verify pass**
- Repeat Step 2.

**Step 5: Commit**
- `git add server tests && git commit -m "feat: add guided order override route"`

### Task 4: Review, simplify, and close out BMAD artifacts

**Objective:** Leave Story 49.3 in the simplest coherent shippable state with honest verification records.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/49-3-add-pre-tick-human-override-semantics-for-guided-agents.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `docs/plans/2026-04-03-story-49-3-guided-order-overrides.md` only if the shipped scope needs a clarifying note

**Step 1: Run review/simplification pass**
- Check for scope creep, duplicated ownership validation, unnecessary abstractions, or misleading “message override” claims not supported by the current engine.
- Make sure the route and completion notes describe the honest shipped scope: deterministic guided **order** overrides against the existing queued-order surface.

**Step 2: Run focused verification**
- `source .venv/bin/activate && python -m pytest tests/db/test_guided_overrides.py --no-cov -q`
- `source .venv/bin/activate && python -m pytest tests/test_agent_registry.py --no-cov -q -k "guided_override or replace_player_orders"`
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py --no-cov -q -k "guided_override or guided_session or openapi_declares_secured_match_route_contracts"`
- `source .venv/bin/activate && python -m pytest tests/api/test_agent_process_api.py --no-cov -q -k "guided_override"`

**Step 3: Run the real repo gate**
- `source .venv/bin/activate && make quality`

**Step 4: Update BMAD closeout**
- Mark story status/signoffs accurately.
- Record the real final commands/results in debug/completion sections.
- Advance `sprint-status.yaml` to the next story only after final verification passes.

**Step 5: Commit**
- `git add _bmad-output docs/plans server tests alembic && git commit -m "docs: close out story 49.3"`
