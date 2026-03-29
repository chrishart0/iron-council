# Story 14.2 Authenticated Match Access Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Bind match joins and match-scoped reads/writes to the authenticated agent identity so clients can no longer spoof another player via request payload fields.

**Architecture:** Keep the auth surface narrow and consistent with Story 14.1 by resolving the authenticated agent from `X-API-Key`, then deriving the match player identity from the registry’s join mapping. Remove player/agent identity inputs from authenticated match-scoped request contracts where they are no longer needed, and preserve structured API errors for unjoined or mismatched access without mutating match state.

**Tech Stack:** FastAPI, Pydantic v2, in-memory and DB-backed match registries, pytest/httpx, real-process smoke tests, uv/make quality.

---

## Parallelism / Sequencing

- **Sequential only for implementation:** this story touches the same API contracts, registry access rules, and smoke tests across multiple endpoints, so parallel Codex workers would collide heavily.
- **Safe parallel work this run:** planning + later review can happen independently, but code changes should stay in one isolated worktree/branch and merge only after focused verification.

## Task 1: Lock the public contract around authenticated joins and derived player identity

**Objective:** Define the smallest public API changes required so authenticated match access no longer depends on client-supplied `agent_id` or `player_id` fields.

**Files:**
- Modify: `server/models/api.py`
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/e2e/test_api_smoke.py`
- Modify: `tests/api/test_agent_process_api.py`

**Step 1: Write failing tests**

Add/adjust behavior-first tests that assert:
- `POST /api/v1/matches/{match_id}/join` requires `X-API-Key` and only needs `match_id` in the body.
- `GET /api/v1/matches/{match_id}/state` requires auth and no longer accepts/needs `player_id` query spoofing.
- `POST /api/v1/matches/{match_id}/orders` derives `player_id` from auth+join instead of trusting the payload.
- Treaty, alliance, and message write/read endpoints reject unjoined agents before mutation.

Example request shapes to target:

```python
join_response = await client.post(
    "/api/v1/matches/match-beta/join",
    json={"match_id": "match-beta"},
    headers={"X-API-Key": build_seeded_agent_api_key("agent-player-2")},
)

state_response = await client.get(
    "/api/v1/matches/match-beta/state",
    headers={"X-API-Key": build_seeded_agent_api_key("agent-player-2")},
)
```

**Step 2: Run focused tests to verify failure**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' \
  tests/api/test_agent_api.py -k 'authenticated and (join or state or order or treaty or alliance or message)'
```

Expected: FAIL because the current contracts still require payload/query identity fields and do not consistently enforce authenticated join mappings.

**Step 3: Write minimal implementation**

Adjust request models so authenticated routes only carry non-identity inputs. Keep response payloads stable where possible, especially `MatchJoinResponse` and accepted write responses.

**Step 4: Re-run focused tests to verify pass**

Run the same command as Step 2.

Expected: PASS.

**Step 5: Commit**

```bash
git add server/models/api.py tests/api/test_agent_api.py tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py
git commit -m "feat: narrow authenticated match api contracts"
```

## Task 2: Teach the registry to resolve the authenticated player slot per match

**Objective:** Add one clear registry path that maps authenticated agent identity to a joined player slot for a match and raises structured domain errors when access is unauthorized or unjoined.

**Files:**
- Modify: `server/agent_registry.py`
- Modify: `server/db/registry.py`
- Modify: `tests/test_agent_registry.py`
- Modify: `tests/test_db_registry.py`

**Step 1: Write failing tests**

Add coverage for:
- deterministic join reuse for an already-joined authenticated agent
- derived match player resolution after join
- explicit rejection for authenticated-but-unjoined access
- DB-backed parity for the same behaviors

Sketch:

```python
join = registry.join_match(match_id="match-beta", agent_id="agent-player-2")
resolved_player_id = registry.require_joined_player_id(
    match_id="match-beta",
    agent_id="agent-player-2",
)
assert resolved_player_id == join.player_id
```

**Step 2: Run focused tests to verify failure**

Run:

```bash
uv run pytest -o addopts='' tests/test_agent_registry.py tests/test_db_registry.py -k 'joined_player or authenticated_match_access'
```

Expected: FAIL because the helper/path does not exist yet.

**Step 3: Write minimal implementation**

Keep the logic boring:
- reuse `joined_agents` as the source of truth
- expose a single helper for “require joined player in match for this agent”
- use repo-style exceptions carrying `code` and `message`
- avoid speculative role/permission layers

**Step 4: Re-run focused tests to verify pass**

Run the same command as Step 2.

Expected: PASS.

**Step 5: Commit**

```bash
git add server/agent_registry.py server/db/registry.py tests/test_agent_registry.py tests/test_db_registry.py
git commit -m "feat: derive match player ids from authenticated joins"
```

## Task 3: Bind match state, orders, messages, treaties, and alliances to authenticated access

**Objective:** Update the REST handlers so every match-scoped read/write derives the acting player identity from auth + join mapping and rejects spoofing or unjoined access before mutation.

**Files:**
- Modify: `server/main.py`
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/api/test_agent_process_api.py`

**Step 1: Write failing tests**

Add/adjust API tests that prove:
- authenticated state reads succeed after join and fail before join
- order submissions use the caller’s joined player id even if a mismatched payload is attempted
- messages/treaties/alliances cannot impersonate another player
- structured errors are returned for missing auth, unknown match, unjoined access, and route/body mismatch

**Step 2: Run focused tests to verify failure**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' \
  tests/api/test_agent_api.py tests/api/test_agent_process_api.py -k 'authenticated and (state or orders or messages or treaties or alliances or join)'
```

Expected: FAIL while handlers still trust payload/query identity inputs.

**Step 3: Write minimal implementation**

Pattern to follow:
- inject `authenticated_agent: Annotated[AuthenticatedAgentContext, Depends(get_authenticated_agent)]`
- resolve joined player id once per route via the registry helper
- for write payloads, either remove player/sender identity fields from the request model or reject if they are present/mismatched, whichever is simpler and keeps the contract narrow
- return accepted responses with the derived player/sender id so the API remains self-describing

**Step 4: Re-run focused tests to verify pass**

Run the same command as Step 2.

Expected: PASS.

**Step 5: Commit**

```bash
git add server/main.py tests/api/test_agent_api.py tests/api/test_agent_process_api.py
git commit -m "feat: secure match-scoped api access by authenticated join"
```

## Task 4: Prove the real running app path and simplify anything overbuilt

**Objective:** Verify the DB-backed/running-process flow works end to end, then perform a simplification pass before final merge.

**Files:**
- Modify: `tests/e2e/test_api_smoke.py`
- Modify: `_bmad-output/implementation-artifacts/14-2-bind-match-joins-and-match-scoped-reads-writes-to-the-authenticated-agent-identity.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Write/adjust failing smoke tests**

Cover one high-value authenticated journey through the running app:
1. fetch current profile with `X-API-Key`
2. join a joinable match with no `agent_id` payload field
3. read match state with no `player_id` query field
4. submit an order or diplomacy/message action using the derived player identity
5. assert the running app rejects a different agent that has not joined

**Step 2: Run smoke tests to verify failure**

Run:

```bash
uv run pytest --no-cov tests/e2e/test_api_smoke.py -k 'authenticated'
```

Expected: FAIL until the real-process path honors the new access control behavior.

**Step 3: Write minimal implementation and simplification edits**

After the smoke path passes, remove or simplify any helper/branching that exists only to preserve spoofable old behavior. Keep the route logic straightforward and repo-consistent.

**Step 4: Run repo verification**

Run:

```bash
uv run pytest -o addopts='' tests/test_agent_registry.py tests/test_db_registry.py
uv run pytest -o addopts='' tests/api/test_agent_api.py tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py
make quality
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/e2e/test_api_smoke.py _bmad-output/implementation-artifacts/14-2-bind-match-joins-and-match-scoped-reads-writes-to-the-authenticated-agent-identity.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "feat: bind match access to authenticated agent identity"
```

## Final review checklist

- [ ] No match-scoped endpoint trusts client-supplied `agent_id` or `player_id` to decide who the caller is.
- [ ] Unjoined authenticated agents receive structured errors and no domain mutation.
- [ ] In-memory and DB-backed registries behave the same for authenticated match access.
- [ ] Tests assert visible API behavior, not helper internals.
- [ ] Real-process smoke flow covers the new authenticated journey.
- [ ] Implementation remains KISS and avoids speculative auth/authorization architecture.
