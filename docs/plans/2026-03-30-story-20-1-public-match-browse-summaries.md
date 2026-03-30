# Story 20.1 Public Match Browse Summaries Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Turn `GET /api/v1/matches` into a compact DB-backed public browse surface for lobby/active/paused matches so human pre-game and spectator flows can choose where to enter without private credentials.

**Architecture:** Reuse the existing DB-backed read-model approach already used for replay, leaderboard, and completed-match browsing. Add a narrow public browse summary contract in `server/models/api.py`, a direct SQLAlchemy helper in `server/db/registry.py`, and route wiring in `server/main.py` that uses the DB-backed helper when `DATABASE_URL` is configured while preserving the lightweight in-memory seeded fallback. Keep the response intentionally compact and boring: status, map, current tick, tick interval, player counts, and open slots only.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, pytest, httpx, uvicorn, `uv run`, `make quality`.

---

## Parallelism / Sequencing

- **Implementation is sequential:** the model shape, DB query, route behavior, and tests all share the same public seam and would conflict if split across workers.
- **Safe parallel work after implementation:** spec-compliance review and code-quality review can run independently once the Codex implementation is complete.
- **Why this story now:** the repo now has public leaderboard, completed-match, and replay reads, but the main public matches route still behaves like an agent/dev list instead of a durable browse surface for human pre-game entry.
- **Simplification pass required:** do not add pagination, filters, auth, mutation behavior, join tokens, or match-detail payloads. Keep completed matches on their dedicated route.

## Task 1: Define the compact public browse contract and DB-backed query helper

**Objective:** Add the minimal public response shape and a direct DB helper that returns deterministic non-completed match browse summaries.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/db/registry.py`
- Test: `tests/test_db_registry.py`

**Step 1: Write failing tests**

Add focused DB helper tests that prove a seeded or patched database can:
- return only non-completed matches
- expose compact browse rows containing `match_id`, `status`, `map`, `tick`, `tick_interval_seconds`, `current_player_count`, `max_player_count`, and `open_slot_count`
- order rows deterministically for browse usefulness (`lobby`, then `active`, then `paused`, with stable recency/id tiebreakers)
- derive counts from persisted player rows and `config.max_players`

**Step 2: Run test to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'match_browse or list_matches'
```

Expected: FAIL because the browse helper/fields do not exist yet.

**Step 3: Write minimal implementation**

- Extend the public match summary model with the compact browse metadata.
- Add a direct helper in `server/db/registry.py` that reads `matches` and `players`, excludes completed matches, calculates counts, and orders deterministically.
- Keep the implementation read-only and boring.

**Step 4: Run test to verify pass**

Run the same command as Step 2.

Expected: PASS.

## Task 2: Wire `GET /api/v1/matches` to use the DB-backed browse helper when available

**Objective:** Keep seeded/dev mode simple while making DB-backed mode serve the public browse contract.

**Files:**
- Modify: `server/main.py`
- Test: `tests/api/test_agent_api.py`

**Step 1: Write failing tests**

Add API-boundary tests covering:
- seeded/in-memory mode still returns deterministic browse summaries for existing sample matches
- DB-backed mode returns compact public browse metadata and excludes completed matches
- ordering remains stable and useful for browse surfaces
- response shape stays compact and public-only

**Step 2: Run tests to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'list_matches or match_browse'
```

Expected: FAIL until the route uses the richer browse contract consistently.

**Step 3: Write minimal implementation**

In `server/main.py`:
- detect DB-backed mode using the existing database URL wiring
- serve `GET /api/v1/matches` from the new DB helper when available
- preserve the in-memory fallback for seeded/dev operation
- do not add auth or a new endpoint; this story intentionally improves the existing public route

**Step 4: Run tests to verify pass**

Run the same command as Step 2.

Expected: PASS.

## Task 3: Add real-process browse smoke coverage and align BMAD/source docs

**Objective:** Prove the running app serves the compact browse contract from the DB-backed path and keep delivery artifacts aligned.

**Files:**
- Modify: `tests/e2e/test_api_smoke.py`
- Modify: `_bmad-output/implementation-artifacts/20-1-add-db-backed-public-match-browse-summaries.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `_bmad-output/planning-artifacts/architecture.md`
- Modify: `core-architecture.md`
- Modify: `_bmad-output/planning-artifacts/epics.md` only if implementation details drift from the planned story

**Step 1: Write failing smoke/doc tests**

Add a real-process smoke that boots the DB-backed app and verifies:
- `GET /api/v1/matches` returns compact browse rows with the new public fields
- completed matches inserted into the database do not appear on the public matches route
- ordering remains deterministic at the running-app boundary

**Step 2: Run tests to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'match_browse or list_matches'
```

Expected: FAIL until the running app serves the richer browse contract.

**Step 3: Write minimal implementation + artifact updates**

- add the smoke assertions
- update the Story 20.1 artifact with debug logs, completion notes, and the final file list
- mark Story 20.1 done in sprint status once verified
- refresh canonical/mirrored architecture docs so the public matches route is explicitly a compact browse read for lobby/active/paused matches

**Step 4: Run verification**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'match_browse or list_matches'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'list_matches or match_browse'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'match_browse or list_matches'
make quality
```

Expected: PASS.

## Final review checklist

- [ ] `GET /api/v1/matches` is a compact browse surface, not a replay/state dump
- [ ] DB-backed mode excludes completed matches and derives counts from persisted rows
- [ ] Lobby/active/paused ordering is deterministic and useful for browse surfaces
- [ ] In-memory seeded mode still works for local/dev usage
- [ ] Real-process smoke proves the running app serves the public browse contract
- [ ] Story artifact, sprint status, and source-of-truth docs are updated
- [ ] `make quality` passes
