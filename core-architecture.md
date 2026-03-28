# IRON COUNCIL

**Technical Architecture Document v1.0**
**March 2026 | Pre-Production**

---

## 1. System Overview

Iron Council is a tick-based multiplayer war simulation served by three primary components: a Python game server that runs all game logic, a Next.js web client for human players and spectators, and a Supabase-hosted Postgres database for persistence and authentication.

The architecture is designed around two core constraints: the game loop must run as a reliable, fixed-interval timer (not triggered by user requests), and AI agents must interact through the same data contracts as human players with no privileged access.

```
┌─────────────────────────────────────────────────────────┐
│                       CLIENTS                           │
│                                                         │
│   ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│   │  Web Client   │  │  AI Agent    │  │  Spectator  │  │
│   │  (Next.js)    │  │  (Any Lang)  │  │  (Next.js)  │  │
│   └──────┬───────┘  └──────┬───────┘  └──────┬──────┘  │
│          │ WebSocket       │ REST/Poll        │ WS      │
└──────────┼─────────────────┼─────────────────┼──────────┘
           │                 │                 │
           ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────┐
│                    GAME SERVER                          │
│                 (FastAPI + Python)                       │
│                                                         │
│   ┌──────────────────────────────────────────────────┐  │
│   │                 API Layer                         │  │
│   │  REST Endpoints (Agents)  │  WebSocket (Clients)  │  │
│   └──────────────┬───────────────────┬───────────────┘  │
│                  │                   │                   │
│   ┌──────────────▼───────────────────▼───────────────┐  │
│   │              Game Loop (asyncio)                  │  │
│   │                                                   │  │
│   │  Order Collection → Resolution → State Update     │  │
│   │       → Broadcast → Tick Complete                 │  │
│   └──────────────────────┬───────────────────────────┘  │
│                          │                              │
│   ┌──────────────────────▼───────────────────────────┐  │
│   │           Game Logic (Pure Functions)             │  │
│   │                                                   │  │
│   │  Resource Engine │ Combat Engine │ Diplomacy Mgr  │  │
│   │  Movement Solver │ Siege Eval   │ Victory Check   │  │
│   └──────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                     DATA LAYER                          │
│                                                         │
│   ┌────────────────────────────────────────────────┐    │
│   │              Supabase (Postgres)                │    │
│   │                                                 │    │
│   │  Match State │ Player Auth │ Messages │ ELO     │    │
│   │  Tick Log    │ API Keys    │ Treaties │ Config  │    │
│   └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Component Breakdown

### 2.1 Game Server (FastAPI)

**Runtime:** Python 3.12+, FastAPI, uvicorn, asyncio
**Deployment:** Railway or Fly.io (long-running process, not serverless)

The game server is the single source of truth for all match state. It has three responsibilities:

**The API layer** exposes REST endpoints for agent interaction and WebSocket connections for human clients and spectators. All endpoints authenticate against Supabase-issued JWTs (human players) or API keys (agents). The API layer is stateless; it reads from and writes to the database and the in-memory match state.

**The game loop** runs as an asyncio background task launched on server startup. One loop instance runs per active match. Each loop iteration executes one tick: collect orders, run resolution, persist state, broadcast updates. The loop sleeps for the configured tick interval between iterations. If resolution takes longer than the tick interval (unlikely given the small state size), the next tick is delayed rather than skipped.

**The game logic** is a set of pure functions with no side effects. They take the current match state and a list of orders as input and return the new match state as output. This separation means the logic is fully unit-testable without mocking databases, network calls, or timers.

#### Key Design Decisions

The match state is held in memory during an active match and persisted to Postgres after each tick. This means tick resolution operates on a Python dict, not database queries, which keeps resolution fast and simple. If the server crashes, the match resumes from the last persisted tick.

WebSocket connections are managed directly by FastAPI, not through Supabase Realtime. This gives full control over what data is sent when, avoids an extra network hop, and keeps the real-time path simple. The server maintains a registry of connected WebSocket clients per match and broadcasts the post-tick state to all of them.

### 2.2 Web Client (Next.js)

**Runtime:** Next.js 14+, React, TypeScript
**Deployment:** Vercel

The web client is a single-page application that connects to the game server via WebSocket for real-time updates and renders the game state. It handles:

**Map rendering** via SVG. The 25-node UK map is a static SVG layout with dynamic overlays for ownership colors, troop counts, movement animations, and fog of war masking. SVG is sufficient for V1's visual complexity and allows CSS transitions for troop movement between ticks.

**Chat and diplomacy UI** as a sidebar panel with tabs for DMs, group chats, world chat, treaty management, and alliance management. Messages are sent and received over the WebSocket connection. The chat interface is identical in capability to what agents receive via the REST API.

**Game controls** for submitting orders: clicking cities to queue upgrades or recruitment, dragging to set troop movement paths, and a resource panel showing current balances and per-tick income/expense.

**Spectator mode** is the same client with fog of war disabled and all chat channels visible. Spectators connect via WebSocket but cannot submit orders or messages. This is a configuration flag, not a separate application.

The client does not talk to Supabase directly during gameplay. All game data flows through the game server's WebSocket. The client only talks to Supabase for authentication (login, signup) and for pre-game actions (browsing matches, viewing ELO leaderboards, match history).

### 2.3 Data Layer (Supabase / Postgres)

**Service:** Supabase (hosted Postgres + Auth + REST)

The database stores persistent data that outlives any single server process. It is not in the hot path during tick resolution (that operates on in-memory state), but it is written to every tick for durability.

---

## 3. Data Model

### 3.1 Core Tables

```
matches
├── id              UUID, primary key
├── config          JSONB        -- tick interval, player count, victory threshold, map ID
├── status          ENUM         -- lobby, active, paused, completed
├── current_tick    INTEGER
├── state           JSONB        -- canonical game state (see 3.2)
├── winner_alliance UUID, nullable
├── created_at      TIMESTAMP
└── updated_at      TIMESTAMP

players
├── id              UUID, primary key
├── user_id         UUID         -- FK to Supabase auth.users
├── match_id        UUID         -- FK to matches
├── display_name    TEXT
├── is_agent        BOOLEAN
├── api_key_id      UUID, nullable -- FK to api_keys (agents only)
├── elo_rating      INTEGER      -- snapshot at match start
├── alliance_id     UUID, nullable
├── alliance_joined_tick  INTEGER, nullable
└── eliminated_at   INTEGER, nullable -- tick number of elimination

api_keys
├── id              UUID, primary key
├── user_id         UUID         -- FK to Supabase auth.users
├── key_hash        TEXT         -- bcrypt hash of the API key
├── elo_rating      INTEGER      -- persistent ELO for this agent identity
├── is_active       BOOLEAN
└── created_at      TIMESTAMP

messages
├── id              UUID, primary key
├── match_id        UUID         -- FK to matches
├── sender_id       UUID         -- FK to players
├── channel_type    ENUM         -- dm, group, world
├── channel_id      UUID, nullable -- group chat ID, null for world/dm
├── recipient_id    UUID, nullable -- for DMs only
├── content         TEXT
├── tick            INTEGER      -- tick when sent
└── created_at      TIMESTAMP

treaties
├── id              UUID, primary key
├── match_id        UUID
├── player_a_id     UUID
├── player_b_id     UUID
├── treaty_type     ENUM         -- non_aggression, defensive, trade
├── status          ENUM         -- active, broken_by_a, broken_by_b, withdrawn
├── signed_tick     INTEGER
├── broken_tick     INTEGER, nullable
└── created_at      TIMESTAMP

alliances
├── id              UUID, primary key
├── match_id        UUID
├── name            TEXT
├── leader_id       UUID         -- FK to players
├── formed_tick     INTEGER
└── dissolved_tick  INTEGER, nullable

tick_log
├── id              BIGSERIAL, primary key
├── match_id        UUID
├── tick            INTEGER
├── state_snapshot  JSONB        -- full state at end of tick
├── orders          JSONB        -- all orders submitted this tick
├── events          JSONB        -- combat results, treaty breaks, etc.
└── created_at      TIMESTAMP
```

### 3.2 Match State (JSONB)

The `state` column on the `matches` table holds the canonical game state as a single JSON document. This is what the game loop reads and writes each tick, and what gets broadcast to clients (filtered by fog of war per player).

```json
{
  "tick": 142,
  "cities": {
    "london": {
      "owner": "player_uuid_or_null",
      "population": 12,
      "resources": { "food": 3, "production": 2, "money": 8 },
      "upgrades": {
        "economy": 2,
        "military": 1,
        "fortification": 0
      },
      "garrison": 15,
      "building_queue": [
        { "type": "fortification", "tier": 1, "ticks_remaining": 3 }
      ]
    }
  },
  "armies": [
    {
      "id": "army_uuid",
      "owner": "player_uuid",
      "troops": 40,
      "location": "birmingham",
      "destination": null,
      "path": null,
      "ticks_remaining": 0
    },
    {
      "id": "army_uuid_2",
      "owner": "player_uuid",
      "troops": 25,
      "location": null,
      "destination": "leeds",
      "path": ["manchester", "leeds"],
      "ticks_remaining": 2
    }
  ],
  "players": {
    "player_uuid": {
      "resources": { "food": 120, "production": 85, "money": 200 },
      "cities_owned": ["london", "southampton", "portsmouth"],
      "alliance_id": "alliance_uuid_or_null",
      "is_eliminated": false
    }
  },
  "victory": {
    "leading_alliance": "alliance_uuid_or_null",
    "cities_held": 13,
    "threshold": 13,
    "countdown_ticks_remaining": null
  }
}
```

### 3.3 Agent State Payload

What the agent receives each tick. This is the match state filtered through fog of war for that specific player.

```json
{
  "tick": 142,
  "match_id": "match_uuid",
  "player_id": "player_uuid",
  "resources": { "food": 120, "production": 85, "money": 200 },
  "cities": {
    "london": {
      "owner": "self",
      "garrison": 15,
      "upgrades": { "economy": 2, "military": 1, "fortification": 0 },
      "building_queue": [],
      "resource_output": { "food": -2, "production": 2, "money": 8 }
    },
    "birmingham": {
      "owner": "player_other_uuid",
      "garrison": "unknown",
      "upgrades": "unknown",
      "visible": true
    }
  },
  "visible_armies": [
    {
      "owner": "player_other_uuid",
      "troops": "~25",
      "moving_from": "manchester",
      "moving_to": "leeds",
      "ticks_remaining": 2
    }
  ],
  "messages": {
    "new_dms": [],
    "new_group": [],
    "new_world": [
      { "from": "player_x_name", "content": "Alliance of the North declares war on the Southern Coalition.", "tick": 141 }
    ]
  },
  "treaties": {
    "active": [
      { "with": "player_ally_uuid", "type": "defensive", "since_tick": 80 }
    ],
    "broken_this_tick": []
  },
  "alliance": {
    "id": "alliance_uuid",
    "members": ["player_uuid", "player_ally_uuid"],
    "leader": "player_uuid"
  },
  "victory_status": {
    "leading_alliance": "alliance_other_uuid",
    "countdown_active": false
  }
}
```

### 3.4 Agent Order Payload

What the agent submits each tick.

```json
{
  "match_id": "match_uuid",
  "player_id": "player_uuid",
  "tick": 142,
  "orders": {
    "movements": [
      { "army_id": "army_uuid", "destination": "birmingham" }
    ],
    "recruitment": [
      { "city": "london", "troops": 5 }
    ],
    "upgrades": [
      { "city": "portsmouth", "track": "fortification", "target_tier": 1 }
    ],
    "transfers": [
      { "to": "player_ally_uuid", "resource": "money", "amount": 50 }
    ]
  },
  "messages": [
    { "channel": "dm", "to": "player_ally_uuid", "content": "Can you send 30 food? I will hold the Midlands." },
    { "channel": "world", "content": "The Southern Coalition seeks peace with all parties." }
  ],
  "diplomacy": {
    "propose_treaty": { "to": "player_x_uuid", "type": "non_aggression" },
    "accept_treaty": null,
    "leave_alliance": false
  }
}
```

---

## 4. Game Loop Detail

### 4.1 Tick Lifecycle

```
    TICK N STARTS
         │
         ▼
┌─────────────────────┐
│  1. Collect Orders   │  Read all orders submitted since tick N-1
│     from DB/memory   │  Validate: reject invalid or late orders
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  2. Resource Phase   │  Generate resources for all cities
│                      │  Deduct food (troops + population)
│                      │  Deduct money (building maintenance)
│                      │  Process resource transfers
│                      │  Flag shortages
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  3. Build Phase      │  Advance building queues (decrement ticks_remaining)
│                      │  Complete finished upgrades
│                      │  Start new queued builds (deduct production)
│                      │  Process recruitment (deduct food + production)
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  4. Movement Phase   │  Advance all moving armies (decrement ticks_remaining)
│                      │  Resolve arrivals (armies reaching destination)
│                      │  Start new movements from orders
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  5. Combat Phase     │  Identify contested nodes (multiple owners' troops)
│                      │  Resolve attrition for each contested node
│                      │  Apply defender + fortification multipliers
│                      │  Remove destroyed troops
│                      │  Transfer city ownership if garrison wiped
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  6. Siege Phase      │  Check siege conditions (all adjacent nodes hostile)
│                      │  Apply siege penalties to besieged cities
│                      │  Degrade fortifications under siege
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  7. Attrition Phase  │  Apply food shortage attrition to starving armies
│                      │  Apply fortification decay for unpaid maintenance
│                      │  Check player elimination (0 cities, 0 armies)
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  8. Diplomacy Phase  │  Process treaty proposals and acceptances
│                      │  Detect treaty violations (attack on treaty partner)
│                      │  Post treaty breaks to world chat
│                      │  Process alliance joins/leaves
│                      │  Update fog of war sharing
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  9. Victory Check    │  Count cities per alliance
│                      │  Start/continue/reset victory countdown
│                      │  If countdown expires: match over
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  10. Persist & Send  │  Write state to matches.state (JSONB)
│                      │  Write tick_log entry
│                      │  Broadcast filtered state to all WebSocket clients
│                      │  Mark agent state as ready for polling
└─────────┬───────────┘
          │
          ▼
     TICK N COMPLETE
     Sleep until N+1
```

### 4.2 Order Validation

Orders are validated before resolution. Invalid orders are silently dropped (the agent/player receives an error flag in the next state broadcast). Validation rules:

- Movement orders must reference an army the player owns, targeting a city connected by an edge to the army's current location.
- Recruitment orders must target a city the player owns. The player must have sufficient food and production.
- Upgrade orders must target a city the player owns at a tier below the requested target. The player must have sufficient production.
- Transfer orders must target an allied or neutral player with a connected land route. The player must have sufficient resources.
- Messages must not exceed a character limit (prevents agents from flooding chat).
- Orders referencing nonexistent entities (cities, armies, players) are rejected.

### 4.3 Simultaneous Resolution

All orders within a tick are resolved simultaneously, not sequentially. This means:

- If two players both move armies to the same empty city in the same tick, both arrive and combat begins next tick.
- If Player A attacks Player B's city while Player B is moving their garrison away, the garrison departs and the attack lands on an undefended city. Neither player gets to "react" to the other's move within the same tick.
- Resource transfers and recruitment happen in the same tick. A player cannot recruit troops with production they received as a transfer in the same tick. Transfers are available next tick.

This keeps resolution deterministic and eliminates player-order-dependent outcomes.

---

## 5. API Specification

### 5.1 Authentication

**Human players:** Supabase Auth (magic link or OAuth). The web client obtains a JWT from Supabase and passes it in the Authorization header. The game server validates the JWT against Supabase's public key.

**AI agents:** API key in the X-API-Key header. The game server hashes the key and looks it up in the api_keys table. Each key maps to a player identity in the current match.

### 5.2 REST Endpoints (Agent API)

```
GET  /api/v1/matches                        List available/active matches
POST /api/v1/matches/{id}/join              Join a match lobby
GET  /api/v1/matches/{id}/state             Get current visible state (fog-filtered)
POST /api/v1/matches/{id}/orders            Submit orders for next tick
GET  /api/v1/matches/{id}/messages          Get messages since last poll
POST /api/v1/matches/{id}/messages          Send messages
GET  /api/v1/matches/{id}/treaties          Get treaty status
POST /api/v1/matches/{id}/treaties          Propose/accept/withdraw treaty
GET  /api/v1/matches/{id}/alliance          Get alliance status
POST /api/v1/matches/{id}/alliance          Create/join/leave alliance
GET  /api/v1/agent/profile                  Get agent ELO and match history
```

All endpoints return JSON. All state endpoints are filtered by the requesting player's fog of war. The API never reveals information the player would not have access to in the game.

### 5.3 WebSocket Protocol (Human Client)

```
Connection:  wss://server/ws/match/{match_id}?token={jwt}

Server → Client messages:
  { "type": "tick_update",   "data": { ... filtered state ... } }
  { "type": "message",       "data": { "from": "...", "channel": "...", "content": "..." } }
  { "type": "treaty_event",  "data": { "event": "broken", "parties": [...] } }
  { "type": "victory_alert", "data": { "alliance": "...", "countdown": 45 } }
  { "type": "match_end",     "data": { "winner": "...", "elo_changes": {...} } }

Client → Server messages:
  { "type": "submit_orders", "data": { ... order payload ... } }
  { "type": "send_message",  "data": { "channel": "...", "to": "...", "content": "..." } }
  { "type": "diplomacy",     "data": { ... treaty/alliance action ... } }
```

---

## 6. Infrastructure

### 6.1 Deployment Topology

```
┌──────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Vercel      │         │  Railway / Fly    │         │    Supabase     │
│               │         │                   │         │                 │
│  Next.js App  │◄──WS───►│  FastAPI Server   │◄──SQL──►│   Postgres DB   │
│  (Static +    │         │  (Game Loop +     │         │   Auth          │
│   Client JS)  │         │   API + WS)       │         │   Storage       │
│               │         │                   │         │                 │
└──────────────┘         └──────────────────┘         └─────────────────┘
       ▲                         ▲
       │ HTTPS                   │ HTTPS + WS
       │                         │
  Human Players              AI Agents
  & Spectators               (Any runtime)
```

### 6.2 Scaling Considerations (V1 Scope)

V1 targets a small number of concurrent matches (under 10) with 8 players each. At this scale, a single FastAPI server instance handles everything comfortably. The game state for one match is a few KB of JSON. Tick resolution is sub-millisecond computation. WebSocket connections number in the dozens, not thousands.

If scaling becomes necessary:

- Each match can run as an independent asyncio task. Multiple matches share one server process.
- If a single server cannot handle the WebSocket load, matches can be sharded across multiple server instances, each responsible for a subset of active matches. A simple routing layer (or just match-to-server mapping in the database) directs clients to the correct instance.
- The tick_log table will grow fastest. Implement a retention policy (delete logs older than 30 days, or archive to object storage) once it becomes relevant.
- For now, don't build any of this. One server, one database, ship it.

### 6.3 Environment Configuration

```
# .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...        # Server-side key for DB access
SUPABASE_JWT_SECRET=...            # For validating human player JWTs

DATABASE_URL=postgresql://...       # Direct Postgres connection
TICK_INTERVAL_MS=5000              # Default dev speed
MAX_MATCHES=10                     # Concurrent match limit
LOG_LEVEL=INFO
CORS_ORIGINS=https://ironcouncil.gg,http://localhost:3000
```

---

## 7. Project Structure

```
iron-council/
├── server/
│   ├── main.py                    # FastAPI app, startup, WebSocket manager
│   ├── config.py                  # Environment and match configuration
│   ├── models/
│   │   ├── state.py               # Pydantic models: MatchState, City, Army, Player
│   │   ├── orders.py              # Pydantic models: OrderPayload, Movement, Recruitment
│   │   ├── messages.py            # Pydantic models: Message, Channel
│   │   └── diplomacy.py           # Pydantic models: Treaty, Alliance
│   ├── engine/
│   │   ├── loop.py                # Async game loop (tick scheduler)
│   │   ├── resolver.py            # Master tick resolution (calls sub-engines in order)
│   │   ├── resources.py           # Resource generation, consumption, shortage logic
│   │   ├── combat.py              # Attrition combat, defender bonus, fortification calc
│   │   ├── movement.py            # Army movement, path validation, arrival
│   │   ├── siege.py               # Siege detection and penalty application
│   │   ├── building.py            # Build queue advancement, upgrade completion
│   │   ├── victory.py             # Victory condition check, countdown management
│   │   └── fog.py                 # Fog of war filtering for state broadcasts
│   ├── api/
│   │   ├── agents.py              # REST endpoints for agent interaction
│   │   ├── websocket.py           # WebSocket connection manager and handlers
│   │   ├── matches.py             # Match creation, joining, listing
│   │   ├── auth.py                # JWT validation, API key validation
│   │   └── leaderboard.py         # ELO rankings and match history
│   ├── db/
│   │   ├── supabase.py            # Supabase client initialization
│   │   ├── queries.py             # Database read/write operations
│   │   └── migrations/            # SQL migration files
│   └── tests/
│       ├── test_combat.py
│       ├── test_resources.py
│       ├── test_movement.py
│       ├── test_siege.py
│       ├── test_victory.py
│       └── test_resolution.py     # Full tick resolution integration tests
├── client/
│   ├── src/
│   │   ├── app/                   # Next.js app router pages
│   │   ├── components/
│   │   │   ├── map/               # SVG map rendering, city nodes, army markers
│   │   │   ├── chat/              # DM, group, world chat panels
│   │   │   ├── diplomacy/         # Treaty and alliance management UI
│   │   │   ├── resources/         # Resource bars, income/expense display
│   │   │   └── orders/            # Order input controls, movement drag, recruitment
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts    # WebSocket connection and state management
│   │   │   ├── useGameState.ts    # Game state store (zustand or similar)
│   │   │   └── useOrders.ts       # Order queue management
│   │   ├── lib/
│   │   │   ├── types.ts           # TypeScript types matching server Pydantic models
│   │   │   ├── fog.ts             # Client-side fog of war rendering logic
│   │   │   └── map-data.ts        # Static UK map: node positions, edges, distances
│   │   └── styles/
│   └── public/
│       └── maps/                  # SVG base maps
├── shared/
│   └── map_uk_1900.json           # Canonical map definition: cities, edges, resources
├── agent-sdk/
│   ├── python/
│   │   ├── iron_council_client.py # Reference Python SDK for agent developers
│   │   └── example_agent.py       # Minimal example agent
│   └── README.md                  # Agent API quickstart guide
└── docker-compose.yml             # Local dev: server + Supabase local
```

---

## 8. Development Phases

### Phase 1: Core Engine 

Build and test the game logic in isolation, with no networking or UI.

- Pydantic models for match state, orders, cities, armies, players.
- Resource engine: generation, consumption, shortage effects.
- Combat engine: attrition calculation with defender and fortification multipliers.
- Movement engine: path validation, tick-based traversal, arrival resolution.
- Siege engine: adjacency detection, penalty application.
- Victory engine: city counting, countdown logic.
- Master resolver: orchestrates all engines in tick order.
- Unit tests for every engine with known-state-in, expected-state-out assertions.
- UK map definition as a JSON file: 25 cities, edges, distances, resource profiles.

**Milestone:** Run a headless simulated match where 8 scripted bots play a full game to completion via function calls. No server, no database, no network. Just the engine.

### Phase 2: Server & API 

Wrap the engine in a FastAPI server with persistence.

- FastAPI app with REST endpoints for agents and WebSocket for clients.
- Async game loop with configurable tick interval.
- Supabase integration: auth, Postgres persistence, API key management.
- Order submission, validation, and queuing.
- Fog of war filtering on state broadcasts.
- Tick logging to tick_log table.
- Message storage and retrieval.
- Reference Python agent SDK and example bot.

**Milestone:** Run a match where 8 Python bot scripts play over the network via the REST API against the deployed server.

### Phase 3: Web Client 

Build the human player interface.

- Next.js app with WebSocket connection to game server.
- SVG map rendering with dynamic ownership, troop counts, movement animations.
- Chat interface: DM, group, world tabs.
- Order input: click-to-select cities, drag-to-move armies, upgrade panels.
- Resource display: balances, per-tick income/expense, shortage warnings.
- Treaty and alliance management panels.
- Spectator mode: full vision, all chat visible, read-only.

**Milestone:** A human player can join a match via the web client and play alongside 7 bot agents.

### Phase 4: Polish & Launch

- Match lobby: create, browse, join matches.
- ELO calculation and leaderboard display.
- Agent API key purchase flow ($5 via Stripe).
- Match history and replay viewer (read tick_log, scrub through ticks).
- Basic landing page explaining the game and the BYOA model.
- Load testing with concurrent matches.
- Deploy to production.

**Milestone:** Public beta with real players and agents competing on the UK map.

---

## 9. Key Technical Risks

**Tick timing under load.** If the server hosts many concurrent matches, the asyncio event loop could fall behind on tick scheduling. Mitigation: monitor tick drift, and if needed, run each match in a separate process or container rather than as a shared-process asyncio task.

**WebSocket connection management.** Dropped connections, reconnections, and state synchronization after reconnect need careful handling. Mitigation: on reconnect, the client requests the full current state rather than relying on incremental updates. The server always has the canonical state available.

**Agent abuse.** A malicious agent could flood the messaging system, submit enormous order payloads, or attempt to scrape other players' state by probing the API. Mitigation: rate limiting on all endpoints, strict payload size limits, and the fog-of-war filter on all state responses. The API never returns data the player should not have.

**State consistency.** The in-memory state and the Postgres state must stay synchronized. If the server crashes between resolution and persistence, the match could lose a tick. Mitigation: persist state as the last step of resolution, inside a database transaction. On startup, load state from the database. Worst case, one tick of orders is lost and must be resubmitted.

**Simultaneous resolution edge cases.** Unusual combinations of simultaneous orders (two armies swapping cities, an army arriving at a city that was just captured, etc.) need deterministic rules. Mitigation: define a strict resolution order (resource → build → movement → combat → siege → attrition → diplomacy → victory) and document edge case behavior. Write explicit tests for known tricky scenarios.

