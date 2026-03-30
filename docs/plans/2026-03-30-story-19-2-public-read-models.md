# Story 19.2 Public Leaderboard and Completed-Match Read Models Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Expose small public browse endpoints for leaderboard standings and completed-match summaries so pre-game clients and spectators can inspect strength and finished outcomes without private agent credentials.

**Architecture:** Reuse the existing DB-backed read path from Story 19.1 instead of inventing new caches or services. Add narrow public response models in `server/models/api.py`, implement two direct SQLAlchemy query helpers in `server/db/registry.py`, and expose two boring GET routes in `server/main.py`. Keep the responses intentionally compact: ordered leaderboard rows plus completed-match browse summaries, with deterministic ordering and explicit DB-backed availability/error handling.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, pytest, httpx, uvicorn, `uv run`, `make quality`.

---

## Parallelism / Sequencing

- **Implementation is mostly sequential:** the response shapes, DB queries, HTTP routes, and tests all touch the same public seam (`server/models/api.py`, `server/db/registry.py`, `server/main.py`, API tests, smoke tests).
- **Safe parallel work after implementation:** spec-compliance review and code-quality review can run independently once the implementation worker finishes.
- **Why this story now:** Story 19.1 exposed replay/history for one match, but there is still no public browse surface for who is strong overall and what happened in finished matches.
- **Simplification pass required:** do not add a repository layer, a leaderboard service, auth, pagination, or rating math. Read the persisted DB rows directly and return compact deterministic summaries.

## Task 1: Define public read-model contracts and DB query helpers

**Objective:** Add the minimal public response shapes and deterministic database helper functions for leaderboard rows and completed-match summaries.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/db/registry.py`
- Test: `tests/test_db_registry.py`

**Step 1: Write failing tests**

Add focused DB tests that prove a seeded or patched database can:
- return deterministic public leaderboard rows ordered by visible rating fields with stable tiebreakers
- aggregate minimal public history counters for each leaderboard row
- return only completed matches in compact browse order without replay payloads
- derive winner display names from persisted match/player/alliance rows

**Step 2: Run test to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'leaderboard or completed_match'
```

Expected: FAIL because the query helpers and response models do not exist yet.

**Step 3: Write minimal implementation**

Add narrow models such as:
- `PublicLeaderboardEntry`
- `PublicLeaderboardResponse`
- `CompletedMatchSummary`
- `CompletedMatchListResponse`

In `server/db/registry.py`, add two direct helpers that:
- load public leaderboard rows from persisted player/match data
- order leaderboard rows deterministically by visible rating fields and stable secondary keys
- aggregate public match history counters (`matches_played`, `wins`, `losses`, `draws`) without private state
- list completed matches only, ordered for browse views, and include compact metadata such as map, tick, player count, completion time, and winning display names

Keep the implementation boring and direct.

**Step 4: Run test to verify pass**

Run the same command as Step 2.

Expected: PASS.

## Task 2: Expose public browse endpoints with structured DB-backed behavior

**Objective:** Wire the new public read models through the FastAPI boundary without broadening scope.

**Files:**
- Modify: `server/main.py`
- Modify: `tests/api/test_agent_api.py`

**Step 1: Write failing tests**

Add API-boundary tests covering:
- `GET /api/v1/leaderboard` returns deterministic public ranking summaries in DB-backed mode
- `GET /api/v1/matches/completed` returns compact completed-match summaries only
- in-memory mode returns the same structured unavailability error style used by Story 19.1’s public DB-backed routes
- leaderboard ordering remains stable across ties and completed-match responses stay compact

**Step 2: Run tests to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'leaderboard or completed_match'
```

Expected: FAIL until the endpoints exist.

**Step 3: Write minimal implementation**

In `server/main.py`:
- reuse the existing DB-backed availability helper pattern
- expose `GET /api/v1/leaderboard`
- expose `GET /api/v1/matches/completed`
- translate missing/unavailable conditions into crisp structured API errors when needed

Do not add auth, mutation behavior, pagination, or personalized leaderboard variants.

**Step 4: Run tests to verify pass**

Run the same command as Step 2.

Expected: PASS.

## Task 3: Add real-process smoke coverage and refresh BMAD/source docs

**Objective:** Prove the public browse surface works against the running DB-backed app and keep project artifacts aligned.

**Files:**
- Modify: `tests/e2e/test_api_smoke.py`
- Create: `_bmad-output/implementation-artifacts/19-2-add-public-leaderboard-and-completed-match-summary-reads.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `core-architecture.md`
- Modify: `_bmad-output/planning-artifacts/architecture.md`
- Modify: `_bmad-output/planning-artifacts/epics.md` only if status/details drifted

**Step 1: Write failing smoke/doc tests**

Add a real-process smoke that boots the DB-backed app and verifies:
- the seeded leaderboard route returns stable public ranking rows
- a completed match inserted into the test database is surfaced by the running app’s completed-match browse route

**Step 2: Run tests to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'leaderboard or completed_match'
```

Expected: FAIL until the new routes are wired through the running app.

**Step 3: Write minimal implementation + artifact updates**

- add the smoke assertions
- create/update the Story 19.2 artifact with completion notes, debug log, and file list
- update sprint status to mark Story 19.2 done once complete
- update canonical/mirrored architecture docs so the public browse routes are part of the source of truth

**Step 4: Run verification**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'leaderboard or completed_match'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'leaderboard or completed_match'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'leaderboard or completed_match'
make quality
```

Expected: PASS.

## Final review checklist

- [ ] Public leaderboard ordering is deterministic and based on visible rating fields
- [ ] Leaderboard rows expose compact public history counters only
- [ ] Completed-match browse results exclude active/paused matches and avoid replay-sized payloads
- [ ] Winner metadata comes from persisted DB records, not in-memory state
- [ ] Public routes stay read-only and DB-backed
- [ ] Real-process smoke proves the running app serves the new public browse routes
- [ ] Story artifact, sprint status, and source-of-truth docs are updated
- [ ] `make quality` passes
