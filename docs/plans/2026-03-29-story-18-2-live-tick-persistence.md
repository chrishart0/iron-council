# Story 18.2 Live Tick Persistence Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Persist each live runtime tick back into the database and append durable tick-log history so active matches survive restart and expose auditable replay/debug data.

**Architecture:** Keep tick resolution pure and in-memory, but add one thin persistence seam around runtime advancement. Introduce an explicit tick-advance result shape from the registry, add a DB writer that updates the `matches` row and appends a `tick_log` row in one transaction, then let `MatchRuntime` call that persistence-aware path only when the app is running against the DB-backed registry. Verify at three levels: focused registry/persistence tests, running-app DB tests, and a real-process smoke that proves persisted advancement survives a registry reload.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, SQLite/Postgres-compatible persistence, pytest, httpx, uvicorn, `make quality`.

---

## Parallelism / Sequencing

- **Sequential implementation only:** Story 18.2 touches the shared runtime seam across `server/agent_registry.py`, `server/runtime.py`, `server/db/registry.py`, `server/main.py`, and DB-backed tests. Parallel Codex implementers would collide on the same core files and public runtime contract.
- **Safe parallel work after implementation:** spec-compliance review and code-quality review can run as separate fresh reviewers after the implementation worker finishes.
- **Why not Story 18.3 in parallel:** WebSocket fanout depends on a stable persisted live-tick contract and real runtime semantics. Shipping 18.2 first reduces delivery risk and avoids parallel edits to the runtime loop.
- **Simplification pass required:** after the persistence path works, remove any duplicated tick-shaping logic, keep transaction boundaries explicit, and prefer one boring DB write path over clever abstractions.

## Task 1: Define the tick-advance result contract

**Objective:** Make runtime advancement return the exact resolved artifacts needed for durable persistence without re-resolving the tick.

**Files:**
- Modify: `server/agent_registry.py`
- Test: `tests/test_agent_registry.py`

**Step 1: Write failing tests**

Add behavior-first tests proving `advance_match_tick(...)` returns or exposes enough information to persist one completed tick:
- resolved next-state tick and state snapshot
- accepted orders for the resolved tick only
- emitted resolver events
- future-tick submissions remain queued

**Step 2: Run test to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py
```

Expected: FAIL because the registry currently mutates state but does not expose a durable tick result contract.

**Step 3: Write minimal implementation**

Add a small explicit result model/dataclass, for example `AdvancedMatchTick` or similar, carrying:
- `match_id`
- `resolved_tick`
- `next_state`
- `accepted_orders`
- `events`

Keep the registry as the single source of truth for combining same-player submissions, validating only the current tick, consuming only current-tick submissions, and incrementing canonical tick exactly once.

**Step 4: Run test to verify pass**

Run the same command as Step 2.

Expected: PASS.

## Task 2: Add a transactional DB persistence writer for live ticks

**Objective:** Persist the updated `matches` row and append the `tick_log` row in one DB transaction.

**Files:**
- Modify: `server/db/registry.py`
- Modify: `server/db/models.py` only if indexes/constraints or ORM helpers are truly needed
- Test: `tests/test_db_registry.py`

**Step 1: Write failing DB tests**

Add focused tests that prove a persistence helper:
- updates `matches.current_tick` and `matches.state` after one runtime tick
- appends exactly one new `tick_log` row for that tick
- stores accepted orders and emitted events in stable JSON form
- preserves restart semantics by allowing a fresh registry reload to observe the new tick/state

**Step 2: Run test to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py
```

Expected: FAIL because no persistence helper exists yet.

**Step 3: Write minimal implementation**

Inside `server/db/registry.py` add a narrow helper, such as `persist_advanced_match_tick(...)`, that:
- opens one SQLAlchemy transaction
- looks up the persisted `Match`
- updates `current_tick`, `state`, and `updated_at`
- appends one `TickLog` row with `tick`, `state_snapshot`, `orders`, and `events`
- serializes through Pydantic `model_dump(mode='json')` or an equivalently stable JSON path

Keep the implementation boring and explicit; do not add a second resolver path.

**Step 4: Run test to verify pass**

Run the same command as Step 2.

Expected: PASS.

## Task 3: Wire runtime persistence into the DB-backed app path

**Objective:** Make the async runtime loop durably persist ticks when the app is running in DB-backed mode while keeping the in-memory backend behavior intact.

**Files:**
- Modify: `server/runtime.py`
- Modify: `server/main.py`
- Modify: `tests/api/test_agent_process_api.py`
- Modify: `tests/e2e/test_api_smoke.py`
- Modify: `tests/conftest.py` if a dedicated fixture helps keep smoke tests readable

**Step 1: Write failing real-boundary tests**

Add tests that prove:
- a DB-backed active match advances and persists without any manual endpoint
- after the tick, a fresh registry reload sees the new `matches.current_tick` / `state`
- the new tick-log row contains the resolved tick
- the in-process public API still serves the post-tick state correctly

**Step 2: Run tests to verify failure**

```bash
uv run pytest --no-cov tests/api/test_agent_process_api.py
uv run pytest --no-cov tests/e2e/test_api_smoke.py
```

Expected: FAIL until runtime persistence is wired.

**Step 3: Write minimal implementation**

In `server/main.py`, decide at startup whether the app is using memory or DB backend and construct the runtime with an optional persistence callback/dependency.

In `server/runtime.py`:
- after `advance_match_tick(...)`, call the persistence callback only for DB-backed operation
- keep cancellation and lifecycle semantics simple
- avoid polluting the memory backend with fake persistence

**Step 4: Run tests to verify pass**

Run the same commands as Step 2.

Expected: PASS.

## Task 4: Update story tracking and run the repo gate

**Objective:** Record completion in BMAD artifacts and prove the repo remains shippable after the durability change.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/18-2-persist-live-tick-advancement-and-write-tick-log-history.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: README/docs only if the runtime persistence command path or local-dev notes materially changed

**Step 1: Focused verification**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py tests/test_db_registry.py
uv run pytest --no-cov tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py
```

Expected: PASS.

**Step 2: Update BMAD artifacts**

Update the story file with:
- agent model used
- debug log references
- completion notes
- file list
- change log

Update `sprint-status.yaml` to mark Story 18.2 done and advance Epic 18 appropriately.

**Step 3: Run repo verification**

```bash
make quality
```

Expected: PASS.

## Final review checklist

- [ ] Runtime advancement persists `matches.current_tick` and `matches.state` after each DB-backed live tick
- [ ] Exactly one `tick_log` row is appended per completed persisted tick
- [ ] Tick-log payload includes the resolved tick number, accepted orders, and emitted events
- [ ] A fresh registry reload sees the post-tick durable state
- [ ] In-memory backend behavior remains intact
- [ ] Story artifact and sprint status are updated
- [ ] `make quality` passes
