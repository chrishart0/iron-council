# Story 36.1 DB Lobby Registry Extraction Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extract DB-backed lobby lifecycle and tick-persistence workflows out of `server/db/registry.py` into focused modules while preserving the existing import surface, route behavior, persistence semantics, and test-facing contract.

**Architecture:** Keep `server.db.registry` as the stable compatibility facade for current callers, but move coherent write workflows into explicit modules such as `server/db/lobby_registry.py` and `server/db/tick_persistence.py`. Preserve current DB transaction boundaries, error codes/messages, joined-player reconstruction, creator ownership semantics, public browse/read-model behavior after writes, and the existing route/service imports by delegating rather than redesigning.

**Tech Stack:** Python 3.12, FastAPI server package, SQLAlchemy, Pydantic, pytest, uv, make quality.

---

### Task 1: Pin the DB-backed lobby and tick-write contract with focused regressions

**Objective:** Lock the current create/join/start/persist behavior before moving code.

**Files:**
- Modify: `tests/test_db_registry.py`
- Modify if needed: `tests/api/test_agent_api.py`
- Modify if needed: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing test**

Add or tighten behavior-first coverage for:
- `create_match_lobby()` preserving creator membership, open-slot counts, and post-write public browse/detail visibility
- `join_match()` preserving idempotent joins, persisted player rows, joined-agent / joined-human identity reconstruction, and error ordering
- `start_match_lobby()` preserving creator-only authorization, readiness checks, and started status visibility
- `persist_advanced_match_tick()` preserving tick-log persistence and state replacement semantics

Example addition:

```python
def test_start_match_lobby_keeps_creator_only_auth_and_public_status_after_reload(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'registry-start-reload.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    created = create_match_lobby(
        database_url=database_url,
        authenticated_api_key_hash=hash_api_key(build_seeded_agent_api_key("agent-player-2")),
        request=MatchLobbyCreateRequest(
            map="britain",
            tick_interval_seconds=20,
            max_players=2,
            victory_city_threshold=13,
            starting_cities_per_player=2,
        ),
    )
    join_match(
        database_url=database_url,
        match_id=created.response.match_id,
        authenticated_api_key_hash=hash_api_key(build_seeded_agent_api_key("agent-player-3")),
    )

    started = start_match_lobby(
        database_url=database_url,
        match_id=created.response.match_id,
        authenticated_api_key_hash=hash_api_key(build_seeded_agent_api_key("agent-player-2")),
    )

    assert started.response.status == MatchStatus.ACTIVE
    assert get_public_match_detail(database_url=database_url, match_id=created.response.match_id).status == MatchStatus.ACTIVE
```

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'create_match_lobby or join_match or start_match_lobby or persist_advanced_match_tick'`
Expected: FAIL until any missing contract coverage is pinned.

**Step 3: Write minimal implementation**

Only add/adjust tests that pin the existing public behavior. Do not move production code yet.

**Step 4: Run test to verify baseline**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'create_match_lobby or join_match or start_match_lobby or persist_advanced_match_tick'`
Expected: PASS or a clearly understood red defining the next edit.

**Step 5: Commit**

```bash
git add tests/test_db_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
git commit -m "test: pin db lobby registry contract"
```

### Task 2: Extract tick persistence into a focused module

**Objective:** Move tick-log/state persistence out of the mixed registry facade into a narrow write module.

**Files:**
- Create: `server/db/tick_persistence.py`
- Modify: `server/db/registry.py`
- Modify if needed: `tests/test_db_registry.py`

**Step 1: Write failing test**

Reuse the Task 1 `persist_advanced_match_tick` regressions as the contract.

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'persist_advanced_match_tick'`
Expected: FAIL while imports/delegation are mid-extraction.

**Step 3: Write minimal implementation**

Create a focused module that owns only the persisted tick-write workflow:

```python
def persist_advanced_match_tick(*, database_url: str, advanced_tick: AdvancedMatchTick) -> None:
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        ...
```

Keep `server.db.registry.persist_advanced_match_tick` as a compatibility re-export or thin delegate.

**Step 4: Run test to verify pass**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'persist_advanced_match_tick'`
Expected: PASS.

**Step 5: Commit**

```bash
git add server/db/tick_persistence.py server/db/registry.py tests/test_db_registry.py
git commit -m "refactor: extract db tick persistence"
```

### Task 3: Extract DB-backed lobby lifecycle workflows into a focused module

**Objective:** Move create/join/start lobby write paths out of `server/db/registry.py` while preserving current contracts and transaction semantics.

**Files:**
- Create: `server/db/lobby_registry.py`
- Modify: `server/db/registry.py`
- Modify if needed: `tests/test_db_registry.py`
- Modify if needed: `server/api/authenticated_lobby_routes.py`
- Modify if needed: `server/api/authenticated_write_routes.py`

**Step 1: Write failing test**

Reuse the Task 1 `create_match_lobby`, `join_match`, and `start_match_lobby` regressions as the contract.

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'create_match_lobby or join_match or start_match_lobby'`
Expected: FAIL while extraction wiring is in progress.

**Step 3: Write minimal implementation**

Create explicit functions in `server/db/lobby_registry.py` for:
- `create_match_lobby(...)`
- `join_match(...)`
- `start_match_lobby(...)`
- local helper functions only where they simplify repeated DB row assembly / authorization checks

Guardrails:
- no new service classes or framework layers
- preserve existing exception types and codes/messages
- preserve first-time valid credential behavior, creator-only ownership checks, and DB-backed reload semantics
- keep `server.db.registry` as the stable facade used by current imports

**Step 4: Run tests to verify pass**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'create_match_lobby or join_match or start_match_lobby'`
Expected: PASS.

**Step 5: Commit**

```bash
git add server/db/lobby_registry.py server/db/registry.py tests/test_db_registry.py \
  server/api/authenticated_lobby_routes.py server/api/authenticated_write_routes.py
git commit -m "refactor: extract db lobby lifecycle workflows"
```

### Task 4: Full verification, simplification, and BMAD closeout

**Objective:** Confirm the refactor is complete, minimal, and convention-aligned.

**Files:**
- Modify if needed: `server/db/registry.py`
- Modify if needed: `server/db/lobby_registry.py`
- Modify if needed: `server/db/tick_persistence.py`
- Modify: `_bmad-output/implementation-artifacts/36-1-extract-db-backed-lobby-lifecycle-and-tick-persistence-out-of-server-db-registry-py.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `_bmad-output/planning-artifacts/epics.md`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/test_db_registry.py -k 'create_match_lobby or join_match or start_match_lobby or persist_advanced_match_tick'`
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'create_match_lobby or start_match_lobby or join_match or openapi_declares_secured_access_route_contracts'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'create_match_lobby or join_match or start_match_lobby'`

Expected: PASS.

**Step 2: Run formatting/quality**

Run:
- `make format`
- `source .venv/bin/activate && make quality`

Expected: PASS.

**Step 3: Simplification pass**

Review diffs for:
- accidental import-surface churn from `server.db.registry`
- duplicated engine/session setup that could stay as plain explicit helpers
- auth/ordering drift in lobby create/join/start checks
- unnecessary callback or service abstractions
- remaining large write-workflow blocks in `server/db/registry.py` that obviously belong in the new modules

**Step 4: Update BMAD artifacts**

Mark Story 36.1 done, capture debug commands/completion notes/file list, update `sprint-status.yaml`, and set up the next pragmatic decomposition slice.

**Step 5: Commit**

```bash
git add server/db/registry.py server/db/lobby_registry.py server/db/tick_persistence.py \
  tests/test_db_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py \
  _bmad-output/implementation-artifacts/36-1-extract-db-backed-lobby-lifecycle-and-tick-persistence-out-of-server-db-registry-py.md \
  _bmad-output/implementation-artifacts/sprint-status.yaml \
  _bmad-output/planning-artifacts/epics.md \
  docs/plans/2026-04-02-story-36-1-db-lobby-registry-extraction.md

git commit -m "refactor: extract db lobby lifecycle workflows"
```
