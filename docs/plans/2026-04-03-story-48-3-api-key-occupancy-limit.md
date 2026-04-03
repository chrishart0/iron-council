# Story 48.3 API-key occupancy limit Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Enforce a small deterministic concurrent-match occupancy limit per agent API key so create/join routes fail honestly when a key is already occupying too many lobby/active matches.

**Architecture:** Keep the change DB-backed and pre-billing. Add the smallest reusable occupancy-counting helper near the existing authenticated DB identity/lobby registry seams, wire it into the authenticated lobby create/join paths, and expose one structured domain error for both route families. Prove the contract from the API boundary first, then add one running-app/process regression to ensure occupancy is recomputed correctly after match completion in the DB-backed runtime.

**Tech Stack:** FastAPI, SQLAlchemy ORM, SQLite test DBs via `provision_seeded_database`, pytest/httpx process + ASGI tests, existing DB-backed match registry and authenticated API-key auth.

---

### Task 1: Add failing API-boundary coverage for honest occupancy-limit errors

**Objective:** Capture the required create/join behavior at the public API boundary before implementation.

**Files:**
- Modify: `tests/api/test_agent_api.py`
- Optionally modify: `tests/api/test_agent_process_api.py`

**Step 1: Write failing tests**

Add focused async API tests that:
- create or seed one active/lobby occupancy for a valid API key, then assert a second `POST /api/v1/matches` fails with a structured occupancy error
- create or seed one active/lobby occupancy for a valid API key, then assert `POST /api/v1/matches/{match_id}/join` fails with the same structured occupancy error
- verify the error is honest (`api_key_match_occupancy_limit_reached` or equivalent) rather than `invalid_api_key`, `match_not_found`, or another fallback
- keep the tests behavior-first by asserting status code + response envelope, not helper internals

**Step 2: Run test to verify failure**

```bash
source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py -k occupancy -q
```

Expected: FAIL because the current routes still allow the second create/join.

**Step 3: Write minimal implementation target notes**

Use one deterministic occupancy constant for now (for example 1 concurrent lobby/active match per API key) and count only DB-backed occupancy that should block new create/join attempts.

**Step 4: Run the focused slice again after implementation**

```bash
source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py -k occupancy -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/api/test_agent_api.py
git commit -m "test: add api-key occupancy limit coverage"
```

### Task 2: Implement the smallest DB-backed occupancy helper and wire create/join routes

**Objective:** Add one honest occupancy seam and use it consistently in DB-backed lobby creation and join flows.

**Files:**
- Modify: `server/db/identity.py`
- Modify: `server/db/lobby_registry.py`
- Modify: `server/api/authenticated_lobby_routes.py` and/or `server/api/authenticated_write_routes.py` only if route-level status mapping must be updated

**Step 1: Implement the counting seam**

Add a tiny helper that counts active occupancy for an API key across `matches` joined through `players.api_key_id`, including `lobby` and `active` matches and excluding completed/closed states.

**Step 2: Wire create path**

Before inserting a new lobby for an authenticated API key, check the occupancy limit and raise a dedicated `MatchLobbyCreationError` if exceeded.

**Step 3: Wire join path**

Before adding a new agent player row for an authenticated API key that is not already joined to the target match, check the same occupancy limit and raise a dedicated `MatchJoinError` if exceeded.

**Step 4: Map the error honestly at the API boundary**

Ensure both create and join routes translate the occupancy error to a deterministic structured client response (likely `409 CONFLICT`) instead of auth/not-found fallbacks.

**Step 5: Run focused verification**

```bash
source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py -k occupancy -q
source .venv/bin/activate && python -m pytest tests/api/test_agent_api.py -k "create_match_lobby_route or join_match" -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add server/db/identity.py server/db/lobby_registry.py server/api/authenticated_lobby_routes.py server/api/authenticated_write_routes.py tests/api/test_agent_api.py
git commit -m "feat: enforce api-key match occupancy limit"
```

### Task 3: Add recomputation/process verification and close out BMAD artifacts

**Objective:** Prove occupancy is recomputed after a match stops counting, then close out the story with real results.

**Files:**
- Modify: `tests/api/test_agent_process_api.py`
- Modify: `_bmad-output/implementation-artifacts/48-3-enforce-per-api-key-concurrent-match-occupancy-with-honest-join-errors.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Optionally create: next-story BMAD artifact only if Story 48.4 needs a concrete handoff file update this run

**Step 1: Add process/runtime recomputation coverage**

Add one running-app or DB-backed API test that:
- uses a valid key that already occupies one counted match
- verifies the next create/join attempt is rejected with the occupancy error
- marks the earlier occupied match completed (or otherwise no longer counted) in the DB
- retries create/join and proves it now succeeds without manual cleanup or server restart drift if that is part of the real path

**Step 2: Run focused process verification**

```bash
source .venv/bin/activate && python -m pytest tests/api/test_agent_process_api.py -k occupancy -q
```

Expected: PASS.

**Step 3: Run the repo quality gate**

```bash
source .venv/bin/activate && make quality
```

Expected: PASS.

**Step 4: Review and simplify**

Check:
- `git diff --stat`
- the occupancy logic stayed tiny and pre-billing
- no entitlement/billing schema or config creep was introduced
- create/join now share the same honest limit semantics

**Step 5: Update BMAD artifacts with actual outcomes**

Mark the story done, fill in testing/debug/completion notes with the real commands and outcomes, set complete signoff, and advance `sprint-status.yaml` to Story 48.4 if 48.3 ships cleanly.

**Step 6: Commit**

```bash
git add docs/plans/2026-04-03-story-48-3-api-key-occupancy-limit.md tests/api/test_agent_process_api.py _bmad-output/implementation-artifacts/48-3-enforce-per-api-key-concurrent-match-occupancy-with-honest-join-errors.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "docs: close out story 48-3"
```
