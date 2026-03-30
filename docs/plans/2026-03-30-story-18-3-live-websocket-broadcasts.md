# Story 18.3 Live WebSocket Broadcasts Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a narrow realtime WebSocket surface that pushes initial and live match updates to subscribed player and spectator clients from the running FastAPI app.

**Architecture:** Add one explicit WebSocket connection manager plus one outbound realtime payload envelope reused for both initial send and live broadcasts. Keep the existing REST/registry/runtime seams as the source of truth: build player payloads from the current fog-filtered projection/briefing helpers, build spectator payloads from a simple full-visibility projection, and let the runtime invoke one broadcast callback after a completed tick. Verify at three levels: focused in-process WebSocket/API tests, running-app websocket smoke coverage, and the full repo quality gate.

**Tech Stack:** Python 3.12, FastAPI/Starlette WebSockets, Pydantic v2, asyncio, httpx, uvicorn, pytest, `make quality`.

---

## Parallelism / Sequencing

- **Sequential implementation only:** Story 18.3 touches the shared app/runtime/public-contract seam across `server/main.py`, `server/runtime.py`, new realtime helpers/models, and websocket tests. Parallel implementers would collide on the same files and protocol decisions.
- **Safe parallel work after implementation:** spec-compliance review and code-quality review can run as separate fresh reviewers after the implementation worker finishes.
- **Why not add bidirectional commands now:** order submission, chat sends, and diplomacy writes already have stable REST paths. Reusing those keeps the websocket story focused on outbound live updates only.
- **Simplification pass required:** prefer one boring connection registry and one payload-shaping path over layered broadcaster abstractions or event buses.

## Task 1: Define the realtime payload and connection manager seam

**Objective:** Introduce the minimal reusable contract for match websocket subscriptions and outbound payloads.

**Files:**
- Create: `server/models/realtime.py`
- Create: `server/websocket.py`
- Modify: `server/models/__init__.py` only if export consistency genuinely helps
- Test: `tests/api/test_agent_api.py`

**Step 1: Write failing tests**

Add behavior-first tests proving the new realtime contract can represent:
- one outbound envelope type for initial and live match updates
- player-view payloads that preserve fog filtering
- spectator-view payloads that expose full visibility
- connection-manager registration and cleanup per match/viewer role without leaking disconnected clients

**Step 2: Run test to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k websocket
```

Expected: FAIL because no realtime payload/manager seam exists yet.

**Step 3: Write minimal implementation**

Create a small explicit realtime contract, for example:
- `RealtimeEnvelope(type='tick_update', data=...)`
- player snapshot payload reusing existing briefing/state shapes as much as possible
- spectator snapshot payload with full match visibility plus all chat, treaty, and alliance context required by the spectator contract
- a per-match connection manager that can register, unregister, and broadcast JSON payloads to subscribed sockets

Keep the connection manager dumb: no background tasks, no retries, no cross-process ambitions.

**Step 4: Run test to verify pass**

Run the same command as Step 2.

Expected: PASS.

## Task 2: Expose the match websocket route and initial payload behavior

**Objective:** Accept websocket subscriptions for player and spectator viewers, send the initial payload, and keep the connection registered until disconnect.

**Files:**
- Modify: `server/main.py`
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/support.py` and/or `tests/conftest.py` only if small fixture helpers keep websocket tests readable

**Step 1: Write failing tests**

Add API-boundary websocket tests covering:
- authenticated player connection receives an initial `tick_update` payload shaped to the contract and fog-filtered to that player
- spectator connection receives an initial payload with full visibility
- disconnect unregisters the connection cleanly
- invalid match/viewer/auth combinations fail cleanly without partially registering clients

**Step 2: Run tests to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'websocket or realtime'
```

Expected: FAIL until the websocket route exists.

**Step 3: Write minimal implementation**

In `server/main.py`:
- add one websocket route such as `/ws/matches/{match_id}`
- accept the connection only after validating the match and resolving whether the viewer is a player or spectator
- send the initial envelope immediately after registration
- keep the receive loop minimal (heartbeat/disconnect only if needed)
- always unregister in `finally`

Use the narrowest auth contract that fits current repo reality and keeps later human JWT work possible without breaking the route shape.

**Step 4: Run tests to verify pass**

Run the same command as Step 2.

Expected: PASS.

## Task 3: Broadcast live updates from runtime and public-event paths

**Objective:** Push the same websocket payload shape after runtime ticks and when public/chat-visible state changes.

**Files:**
- Modify: `server/runtime.py`
- Modify: `server/main.py`
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/e2e/test_api_smoke.py`
- Modify: `tests/conftest.py` if a dedicated fast-tick websocket fixture materially improves readability

**Step 1: Write failing tests**

Add tests proving:
- a live tick sends a follow-up websocket payload to an already connected player
- the same tick sends a full-visibility follow-up payload to a spectator
- at least one public/chat-visible event path (for example world chat or treaty change) triggers a fresh payload/broadcast without waiting for a reconnect
- the runtime still preserves existing tick-persistence behavior and does not fork a second resolution path

**Step 2: Run tests to verify failure**

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'websocket or realtime'
uv run pytest --no-cov tests/e2e/test_api_smoke.py -k websocket
```

Expected: FAIL until broadcast wiring exists.

**Step 3: Write minimal implementation**

Wire one optional broadcast callback through the running app/runtime path so that:
- completed ticks emit one outbound websocket envelope per subscribed client
- player viewers get fog-filtered payloads
- spectator viewers get full-visibility payloads
- public/chat-visible REST writes reuse the same broadcast helper where the client contract would otherwise go stale

Do not create a second match-state cache or event bus; shape payloads directly from the registry state after the authoritative write/advance succeeds.

**Step 4: Run tests to verify pass**

Run the same commands as Step 2.

Expected: PASS.

## Task 4: Update BMAD tracking and run the repo gate

**Objective:** Record story completion and prove the repo remains shippable after the realtime addition.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/18-3-broadcast-live-match-updates-over-websockets-for-human-clients-and-spectators.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `_bmad-output/planning-artifacts/epics.md` or source docs only if the shipped public contract must be clarified to stay truthful

**Step 1: Focused verification**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'websocket or realtime'
uv run pytest --no-cov tests/e2e/test_api_smoke.py -k websocket
```

Expected: PASS.

**Step 2: Update BMAD artifacts**

Update the story file with:
- agent model used
- debug log references
- completion notes
- file list
- change log

Update `sprint-status.yaml` to mark Story 18.3 done and close Epic 18.

**Step 3: Run repo verification**

```bash
make quality
```

Expected: PASS.

## Final review checklist

- [ ] WebSocket route registers player and spectator subscribers per match and cleans up on disconnect
- [ ] Initial payload shape matches the documented realtime envelope contract
- [ ] Live tick broadcasts reach both a player view and a spectator view
- [ ] Player websocket payloads remain fog-filtered while spectator payloads expose full visibility
- [ ] At least one public/chat-visible event path refreshes subscribed clients without reconnecting
- [ ] Story artifact and sprint status are updated
- [ ] `make quality` passes
