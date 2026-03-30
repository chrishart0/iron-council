# Story 19.1 Match History and Replay API Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Expose a small public read API for persisted tick history so replay tooling and spectator surfaces can enumerate recorded ticks and fetch an authoritative snapshot for a chosen tick.

**Architecture:** Reuse the existing tick-log persistence seam from Story 18.2 instead of inventing a second history store. Add narrow Pydantic response models plus one DB query helper that reads `matches` and `tick_log`, then expose two boring GET routes in `server/main.py`: one summary/list route and one per-tick snapshot route. Keep the scope read-only, validate the database-backed path at the HTTP boundary, and return explicit structured errors when the history surface is unavailable or the requested match/tick does not exist.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, pytest, httpx, uvicorn, `make quality`.

---

## Parallelism / Sequencing

- **Sequential implementation only:** the route contract, DB query helper, response models, docs, and API tests all share the same public seam (`server/models/api.py`, `server/db/registry.py`, `server/main.py`, and API/e2e tests).
- **Safe parallel work after implementation:** spec-compliance review and code-quality review can run as fresh reviewers after the implementation worker finishes.
- **Why this story now:** Story 18 already persists tick history and pushes live websocket state, but there is still no supported replay/history read surface for clients or debugging tools.
- **Simplification pass required:** do not add a repository layer, service bus, or caching abstraction for this. One query helper plus two GET endpoints is enough.

## Task 1: Define the replay API response models and focused DB query seam

**Objective:** Add the explicit API contract and the minimal database helper needed to read persisted tick-log history.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/db/registry.py`
- Test: `tests/test_db_registry.py`

**Step 1: Write failing tests**

Add focused tests that prove a seeded database can:
- list the persisted tick-log entries for one match in deterministic tick order
- return the persisted snapshot/orders/events for one requested tick
- distinguish match-not-found from tick-not-found

**Step 2: Run test to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'tick_history or replay'
```

Expected: FAIL because no history query helper exists yet.

**Step 3: Write minimal implementation**

Add small response/query shapes such as:
- `MatchHistoryEntry`
- `MatchHistoryResponse`
- `MatchReplayTickResponse`

In `server/db/registry.py`, add a narrow helper that:
- opens a SQLAlchemy session from a provided database URL
- verifies the match exists
- loads ordered `tick_log` rows for that match
- returns a lightweight summary list and a single requested tick snapshot without mutating any registry state

Keep the helper boring and direct.

**Step 4: Run test to verify pass**

Run the same command as Step 2.

Expected: PASS.

## Task 2: Expose public history and replay endpoints with structured errors

**Objective:** Make the persisted history available at the HTTP boundary with crisp error behavior.

**Files:**
- Modify: `server/main.py`
- Modify: `tests/api/test_agent_api.py`

**Step 1: Write failing tests**

Add API-boundary tests covering:
- `GET /api/v1/matches/{match_id}/history` returns ordered persisted tick entries and current match metadata in DB-backed mode
- `GET /api/v1/matches/{match_id}/history/{tick}` returns the persisted state snapshot, accepted orders, and events for that tick
- unknown match and unknown tick return structured 404 errors
- non-DB mode returns a clear structured unavailability error instead of pretending history exists

**Step 2: Run tests to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'history or replay'
```

Expected: FAIL until the endpoints exist.

**Step 3: Write minimal implementation**

In `server/main.py`:
- add one helper to detect whether persisted history is available (`IRON_COUNCIL_MATCH_REGISTRY_BACKEND=db` with a configured database URL)
- expose `GET /api/v1/matches/{match_id}/history`
- expose `GET /api/v1/matches/{match_id}/history/{tick}`
- translate helper failures into explicit API errors like `match_not_found`, `tick_not_found`, or `match_history_unavailable`

Do not broaden scope into auth, lobby creation, or full replay playback mechanics.

**Step 4: Run tests to verify pass**

Run the same command as Step 2.

Expected: PASS.

## Task 3: Add running-process smoke coverage and refresh docs/BMAD artifacts

**Objective:** Prove the route works against the real process boundary and keep planning/docs truthful.

**Files:**
- Modify: `tests/e2e/test_api_smoke.py`
- Modify: `README.md` only if the new route should be mentioned for local verification
- Modify: `_bmad-output/planning-artifacts/epics.md`
- Create: `_bmad-output/implementation-artifacts/19-1-expose-persisted-tick-history-and-replay-snapshots.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `core-architecture.md` and mirrored architecture doc only if the shipped API surface should now explicitly mention the history route

**Step 1: Write failing smoke/doc tests**

Add a real-process smoke that boots the DB-backed app and verifies:
- the seeded match history route returns persisted tick-log rows
- the single-tick replay route returns the seeded snapshot payload for the seeded tick

**Step 2: Run tests to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'history or replay'
```

Expected: FAIL until the route is wired through the running app.

**Step 3: Write minimal implementation + artifact updates**

- add the smoke assertions
- refresh the story artifact with completion notes, debug log, and file list
- update sprint status to mark Story 19.1 done (or in progress while working)
- update architecture docs if the public route contract needs to be source-of-truth, not tribal knowledge

**Step 4: Run verification**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'tick_history or replay'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'history or replay'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'history or replay'
make quality
```

Expected: PASS.

## Final review checklist

- [ ] The history API reads from persisted `tick_log` rows instead of inventing a second store
- [ ] The list route returns deterministic ordered entries for one match
- [ ] The per-tick route returns persisted state, orders, and events for the requested tick
- [ ] Unknown match / unknown tick / unavailable-backend failures return structured API errors
- [ ] Real-process smoke proves the DB-backed server exposes the route correctly
- [ ] Story artifact, sprint status, and any source-of-truth docs are updated
- [ ] `make quality` passes
