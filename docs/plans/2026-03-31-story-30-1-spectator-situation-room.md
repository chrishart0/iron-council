# Story 30.1 Spectator Situation Room Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make the public live spectator page materially easier to understand by rendering readable world-chat, treaty, and alliance panels from the existing live-update contracts.

**Architecture:** Keep the feature boring and public-first. Extend the compact public match-detail/read contracts just enough to carry stable public `player_id` values alongside roster display names, then use that roster map inside the existing spectator live page to translate websocket player IDs into readable labels for world chat, treaties, and alliances. Reuse the shipped `/api/v1/matches/{match_id}` read plus the existing spectator websocket; do not invent a new spectator API.

**Tech Stack:** FastAPI + Pydantic server models, SQLAlchemy DB-backed read helpers, Next.js App Router, React client components, TypeScript, Vitest + Testing Library, pytest, repo `make quality` gate.

---

## Parallelism / Sequencing

- **Sequential:** this story touches the shared public match-detail contract, client types, and the existing spectator live view, so one worktree should own it end-to-end.
- **No new transport surface:** reuse only `/api/v1/matches/{match_id}` plus `/ws/match/{match_id}?viewer=spectator`.
- **Keep scope tight:** no SVG map, no replay playback, no player-only controls, no new write APIs.

### Task 1: Add failing server tests for stable public roster IDs

**Objective:** Pin the public read-model contract needed to map spectator websocket IDs to readable labels.

**Files:**
- Modify: `tests/test_db_registry.py`
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/e2e/test_api_smoke.py`
- Modify: `server/models/api.py`
- Modify: `server/db/registry.py`

**Step 1: Write failing tests**

Add/extend tests that prove:
- `get_public_match_detail()` includes `player_id` on each roster row
- `/api/v1/matches/{match_id}` returns the same stable roster IDs in API and real-process smoke coverage
- roster ordering remains deterministic even after adding the new field

**Step 2: Run test to verify failure**

Run:
```bash
uv run pytest --no-cov tests/test_db_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
```

Expected: FAIL because `player_id` is not yet present in the compact public roster contract.

**Step 3: Write minimal implementation**

Update the public roster model and DB-backed detail loader so each row includes:
- `player_id`
- `display_name`
- `competitor_kind`

Do not expose private auth identifiers or add any other browse metadata.

**Step 4: Run test to verify pass**

Run:
```bash
uv run pytest --no-cov tests/test_db_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
```

Expected: PASS.

### Task 2: Add failing client tests for readable spectator panels

**Objective:** Drive the spectator UX from the browser boundary before implementation.

**Files:**
- Modify: `client/src/lib/types.ts`
- Modify: `client/src/lib/api.test.ts`
- Modify: `client/src/components/matches/match-detail.test.tsx`
- Modify: `client/src/components/matches/public-match-live-page.test.tsx`
- Modify: `client/src/components/matches/match-live-view.test.tsx`
- Modify: `client/src/components/matches/match-detail.tsx`
- Modify: `client/src/components/matches/public-match-live-page.tsx`
- Modify: `client/src/components/matches/match-live-view.tsx`

**Step 1: Write failing tests**

Add tests that prove:
- client public match-detail types parse roster rows with `player_id`
- the spectator live page uses the public roster to show readable labels instead of raw player IDs where possible
- the live view renders a world-chat feed, treaty status panel, and alliance tracker from the shipped websocket payload
- empty states stay deterministic and read-only

**Step 2: Run test to verify failure**

Run:
```bash
cd client && npm test -- --run src/lib/api.test.ts src/components/matches/match-detail.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/match-live-view.test.tsx
```

Expected: FAIL because the new roster shape and spectator panels do not exist yet.

**Step 3: Write minimal implementation**

Implement the smallest coherent UI:
- keep the existing spectator summary block
- add helper(s) that resolve `player_id -> display_name` from the fetched public roster map
- render text-first sections for recent world messages, treaty statuses, and alliance membership
- fall back deterministically to the raw `player_id` only when no public label is available

**Step 4: Run test to verify pass**

Run:
```bash
cd client && npm test -- --run src/lib/api.test.ts src/components/matches/match-detail.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/match-live-view.test.tsx
cd client && npm run build
```

Expected: PASS.

### Task 3: Close docs/BMAD artifacts and run the full gate

**Objective:** Leave the story aligned with source docs, BMAD tracking, and the repo quality harness.

**Files:**
- Modify: `README.md`
- Modify: `_bmad-output/planning-artifacts/epics.md`
- Modify: `_bmad-output/implementation-artifacts/30-1-add-a-spectator-situation-room-to-the-live-web-client.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Update docs/BMAD artifacts**

Document the enriched spectator live surface, mark Story 30.1 complete, and advance sprint tracking to Story 30.2.

**Step 2: Run focused verification**

Run:
```bash
uv run pytest --no-cov tests/test_db_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
cd client && npm test -- --run src/lib/api.test.ts src/components/matches/match-detail.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/match-live-view.test.tsx
cd client && npm run build
```

Expected: PASS.

**Step 3: Run the repo gate**

Run:
```bash
make quality
```

Expected: PASS.

---

## Verification Checklist

- `uv run pytest --no-cov tests/test_db_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py`
- `cd client && npm test -- --run src/lib/api.test.ts src/components/matches/match-detail.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/match-live-view.test.tsx`
- `cd client && npm run build`
- `make quality`
