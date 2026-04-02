# Story 41.3 Public Human Profile Scaffolding Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Define an explicit durable public human identity contract on the server, ship a read-only `/humans/{humanId}` page in the web client, and link public leaderboard/completed/history surfaces to it only when the backend provides an honest human profile id.

**Architecture:** Reuse the already persisted human settlement identity (`human:{user_id}`) as the durable public human profile key, add explicit optional `human_id` fields alongside existing `agent_id` fields in public competitor shapes, and expose a small public `/api/v1/humans/{human_id}/profile` route backed by the same settlement/rating data already used for human lobby identity and leaderboard aggregation. Keep the client boring and additive: typed validators, a read-only human profile page, and links only from rows with non-null `human_id`, with no display-name guessing or merged generic profile abstraction.

**Tech Stack:** FastAPI/Pydantic server, SQLAlchemy, Next.js 16, TypeScript, Vitest, pytest, uv, make.

---

### Task 1: Define the explicit public human profile contract on the server

**Objective:** Add the smallest honest backend surface for durable public human identities and profile reads.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/db/identity.py`
- Modify: `server/db/identity_hydration.py`
- Modify: `server/api/authenticated_read_routes.py`
- Test: `tests/api/test_agent_api.py`
- Test: `tests/api/test_agent_process_api.py`
- Test: `tests/test_db_registry.py`

**Step 1: Write failing server/API tests**

Add assertions that:
- `GET /api/v1/humans/{human_id}/profile` returns a stable read-only response for a persisted human competitor
- unknown or malformed `human_id` values return a deterministic not-found API error
- the response includes `human_id`, `display_name`, `rating`, and `history`
- the route does not expose agent-only fields like `is_seeded`
- the DB-backed helper resolves human identity from settlement/user data rather than display-name matching

**Step 2: Run focused tests to verify failure**

Run:
```bash
uv run pytest -o addopts='' tests/api/test_agent_api.py -k "human_profile or openapi_declares_public_read_contracts"
uv run pytest -o addopts='' tests/test_db_registry.py -k "human_profile or settled_elo"
```
Expected: FAIL because the public human profile contract/route does not exist yet.

**Step 3: Write the minimal implementation**

Add:
- `HumanProfileRating`, `HumanProfileHistory`, and `HumanProfileResponse`
- a helper to parse/validate `human:{user_id}` ids and resolve human profile data from settled rows (falling back to persisted player display name / provisional rating when needed)
- a public route `GET /api/v1/humans/{human_id}/profile`

Keep the implementation explicit and parallel to the agent profile path; do not invent a generic `profile_id` abstraction.

**Step 4: Run focused server verification**

Run:
```bash
uv run pytest -o addopts='' tests/api/test_agent_api.py -k "human_profile or public_and_authenticated_agent_profile_routes_return_stable_shapes or openapi_declares_public_read_contracts"
uv run pytest -o addopts='' tests/api/test_agent_process_api.py -k "non_agent_public_profile"
uv run pytest -o addopts='' tests/test_db_registry.py -k "human_profile or settled_elo or coherent_across_public_reads"
```
Expected: PASS.

**Step 5: Commit**

```bash
git add server/models/api.py server/db/identity.py server/db/identity_hydration.py server/api/authenticated_read_routes.py tests/api/test_agent_api.py tests/api/test_agent_process_api.py tests/test_db_registry.py
git commit -m "feat: add public human profile API contract"
```

### Task 2: Extend public competitor summaries with honest optional `human_id`

**Objective:** Make every relevant public browse surface tell the client which human rows can link to the new profile route.

**Files:**
- Modify: `server/models/api.py`
- Modify: `server/db/public_read_assembly.py`
- Modify: `server/db/public_reads.py`
- Test: `tests/api/test_agent_api.py`
- Test: `tests/e2e/test_api_smoke.py`
- Test: `tests/test_db_registry.py`

**Step 1: Write failing public-read tests**

Add assertions that:
- leaderboard human rows include non-null `human_id`
- agent rows keep `human_id: null`
- completed-match and match-history competitor summaries include `human_id` only for human competitors
- existing `agent_id` behavior remains unchanged
- no route guesses ids from display names

**Step 2: Run focused tests to verify failure**

Run:
```bash
uv run pytest -o addopts='' tests/api/test_agent_api.py -k "public_leaderboard or completed or history"
uv run pytest -o addopts='' tests/test_db_registry.py -k "public_leaderboard or completed_match or history or coherent_across_public_reads"
```
Expected: FAIL because the current public competitor shapes only expose optional `agent_id`.

**Step 3: Write the minimal implementation**

Update `LeaderboardEntry` and `PublicCompetitorSummary` to include `human_id: str | None`, and derive `human:{user_id}` only for persisted non-agent competitors. Keep agent rows `human_id=None` and human rows `agent_id=None`.

**Step 4: Run focused public-read verification**

Run:
```bash
uv run pytest -o addopts='' tests/api/test_agent_api.py -k "public_leaderboard or completed or history or human_profile"
uv run pytest -o addopts='' tests/test_db_registry.py -k "public_leaderboard or completed_match or history or coherent_across_public_reads"
uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k "public_leaderboard_and_completed_match_smoke_flow_runs_through_real_process or completion_to_leaderboard_smoke_flow_runs_through_real_process"
```
Expected: PASS.

**Step 5: Commit**

```bash
git add server/models/api.py server/db/public_read_assembly.py server/db/public_reads.py tests/api/test_agent_api.py tests/test_db_registry.py tests/e2e/test_api_smoke.py
git commit -m "feat: expose honest public human ids in browse reads"
```

### Task 3: Add typed client support for human profile contracts and validators

**Objective:** Keep the browser boundary explicit and runtime-validated before wiring links.

**Files:**
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.ts`
- Test: `client/src/lib/api.test.ts`

**Step 1: Write failing client API/validator tests**

Add tests for:
- successful `fetchPublicHumanProfile("human:...")`
- deterministic unavailable mapping for unknown human ids
- leaderboard/completed/history validators requiring explicit `human_id` handling by competitor kind
- invalid payload rejection when both `agent_id` and `human_id` are dishonest for a row

**Step 2: Run focused client tests to verify failure**

Run:
```bash
cd client && npm test -- --run src/lib/api.test.ts
```
Expected: FAIL because the human profile response/fetcher/validators do not exist yet.

**Step 3: Write the minimal implementation**

Add:
- `PublicHumanProfileResponse`
- `PublicHumanProfileError`
- `fetchPublicHumanProfile()`
- validator updates that keep `agent_id`/`human_id` mutually honest by competitor kind

**Step 4: Run focused client verification**

Run:
```bash
cd client && npm test -- --run src/lib/api.test.ts
```
Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/lib/types.ts client/src/lib/api.ts client/src/lib/api.test.ts
git commit -m "feat: add client public human profile API support"
```

### Task 4: Ship the read-only `/humans/[humanId]` page and public links

**Objective:** Render a stable human profile destination and link only rows with explicit durable human ids.

**Files:**
- Create: `client/src/app/humans/[humanId]/page.tsx`
- Create: `client/src/app/humans/[humanId]/page.test.tsx`
- Create: `client/src/components/public/public-human-profile-page.tsx`
- Create: `client/src/components/public/public-human-profile-page.test.tsx`
- Modify: `client/src/components/public/public-leaderboard-page.tsx`
- Modify: `client/src/components/public/public-leaderboard-page.test.tsx`
- Modify: `client/src/components/public/completed-matches-page.tsx`
- Modify: `client/src/components/public/completed-matches-page.test.tsx`
- Modify: `client/src/components/public/match-history-page.tsx`
- Modify: `client/src/components/public/match-history-page.test.tsx`

**Step 1: Write failing page/component tests**

Add assertions that:
- `/humans/[humanId]` renders loading → ready → unavailable states
- ready state shows human id, display name, rating, and match history
- leaderboard human rows link to `/humans/{humanId}`
- completed-match and history pages link human rows with `human_id` and keep agent rows using `/agents/{agentId}`
- rows without the relevant explicit id remain plain text

**Step 2: Run focused page/component tests to verify failure**

Run:
```bash
cd client && npm test -- --run src/components/public/public-leaderboard-page.test.tsx src/components/public/completed-matches-page.test.tsx src/components/public/match-history-page.test.tsx src/components/public/public-human-profile-page.test.tsx src/app/humans/[humanId]/page.test.tsx
```
Expected: FAIL because the route/page/link wiring does not exist yet.

**Step 3: Write the minimal implementation**

Implement a boring read-only UI that mirrors the existing agent profile page shape where sensible, but keep the copy explicit to humans and avoid a large shared profile abstraction unless it stays trivially simple.

**Step 4: Run focused page/component verification**

Run:
```bash
cd client && npm test -- --run src/components/public/public-leaderboard-page.test.tsx src/components/public/completed-matches-page.test.tsx src/components/public/match-history-page.test.tsx src/components/public/public-human-profile-page.test.tsx src/app/humans/[humanId]/page.test.tsx
```
Expected: PASS.

**Step 5: Commit**

```bash
git add client/src/app/humans/[humanId]/page.tsx client/src/app/humans/[humanId]/page.test.tsx client/src/components/public/public-human-profile-page.tsx client/src/components/public/public-human-profile-page.test.tsx client/src/components/public/public-leaderboard-page.tsx client/src/components/public/public-leaderboard-page.test.tsx client/src/components/public/completed-matches-page.tsx client/src/components/public/completed-matches-page.test.tsx client/src/components/public/match-history-page.tsx client/src/components/public/match-history-page.test.tsx
git commit -m "feat: add public human profile page"
```

### Task 5: Run review-quality verification, BMAD closeout, and simplification

**Objective:** Prove Story 41.3 is integrated, simple, and accurately tracked.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/41-3-add-read-only-public-player-human-profile-scaffolding-once-a-stable-public-identity-contract-exists.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `docs/plans/2026-04-02-story-41-3-public-human-profile-scaffolding.md`
- Review: touched server/client/tests files

**Step 1: Remove worker junk and keep only intended repo files**

Delete any prompt scratchpads, temporary coverage files, or worktree-only notes before merge.

**Step 2: Run strongest practical repo-managed verification**

Run:
```bash
source .venv/bin/activate && make quality
```
If the worktree needs bootstrap first:
```bash
uv sync --extra dev --frozen
make client-install
source .venv/bin/activate && make quality
```
Expected: PASS.

**Step 3: Perform review passes**

Check:
- Story 41.3 acceptance criteria and honest-identity scope
- no display-name heuristics or merged generic profile abstraction
- code/test quality and overcomplexity
- KISS / repo-convention compliance

**Step 4: Update BMAD artifacts**

Mark Story 41.3 done, update the story debug log with real verification commands/outcomes, and advance `next_story` to the next planned increment.

**Step 5: Commit and push**

```bash
git add docs/plans/2026-04-02-story-41-3-public-human-profile-scaffolding.md _bmad-output/implementation-artifacts/41-3-add-read-only-public-player-human-profile-scaffolding-once-a-stable-public-identity-contract-exists.md _bmad-output/implementation-artifacts/sprint-status.yaml
git add client/src server tests
git commit -m "feat: add public human profile scaffolding"
git push origin master
```
