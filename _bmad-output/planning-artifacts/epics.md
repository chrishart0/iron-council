---
stepsCompleted:
  - normalized-source-docs
  - drafted-epics
inputDocuments:
  - core-plan.md
  - core-architecture.md
---

# Iron Council - Epic Breakdown

## Overview

This document decomposes the current game design and technical architecture into an implementation-first roadmap for the initial FastAPI server foundation. The sequence intentionally front-loads shared contracts, map data, match initialization, order validation, and headless simulation so later API, client, and persistence work can build on stable deterministic primitives.

## Requirements Inventory

### Functional Requirements

- Run the match as a configurable fixed-interval tick loop that resolves resources, orders, combat, and state broadcast in a deterministic order.
- Represent the UK 1900 map as a canonical node graph with 25 cities, adjacency edges, resource profiles, and special neutral-Ireland rules.
- Maintain canonical match state for cities, armies, players, alliances, and victory countdown data.
- Accept and validate player/agent orders for movement, recruitment, upgrades, and transfers.
- Initialize matches with configurable settings, player rosters, spawn cities, and canonical starting state.
- Support headless simulation so the engine can be tested without database or network dependencies.

### NonFunctional Requirements

- Python 3.12+ FastAPI server architecture with pure-function game logic separated from I/O. [Source: core-architecture.md#2.1 Game Server (FastAPI)]
- Deterministic simultaneous resolution with explicit validation and edge-case tests. [Source: core-architecture.md#4.2 Order Validation and Simultaneity]
- Canonical state must be serializable to JSONB and unit-testable via Pydantic models.
- Early artifacts should be small, reviewable increments with tests covering validation and round-trip serialization.

### Additional Requirements

- Treat `core-plan.md` as the current GDD source and `core-architecture.md` as the current architecture source.
- Prefer greenfield sequencing: shared contracts, map data, match initialization, order validation, headless tick simulation.
- Use Codex for significant coding work and commit coherent increments.

### UX Design Requirements

- No dedicated UX work is required in the first server-foundation epics beyond preserving model shapes that can be mirrored by a future web client.

### FR Coverage Map

- FR1 deterministic tick loop -> Epics 1, 4
- FR2 UK map definition -> Epic 2
- FR3 canonical match state -> Epics 1, 3
- FR4 order submission + validation -> Epic 3
- FR5 match initialization -> Epic 3
- FR6 headless simulation -> Epic 4

## Epic List

1. **Epic 1 - Server Foundation and Shared Contracts**: scaffold the Python server workspace, FastAPI entrypoint, and core Pydantic state/order contracts.
2. **Epic 2 - Canonical UK 1900 Map Data**: encode the V1 map, adjacency graph, resource identities, and validation rules.
3. **Epic 3 - Match Bootstrap and Order Validation**: create deterministic match initialization and pre-resolution validation for player orders.
4. **Epic 4 - Headless Tick Simulation Skeleton**: implement the first pure-function resolver shell and smoke-testable headless tick loop.
5. **Epic 5 - Foundational Tick Economy and Movement**: add deterministic resource accounting and army transit progression so the resolver meaningfully changes state.
6. **Epic 6 - Attrition and Victory Safety Rails**: convert resource pressure and territorial control into deterministic elimination and endgame countdown behavior.
7. **Epic 7 - Combat Resolution and Territorial Pressure**: apply deterministic city combat and ownership handoff so territorial conflict materially changes the board.
8. **Epic 8 - Order Execution and Build Pipeline**: turn accepted upgrade and recruitment intents into concrete build-phase state changes.
9. **Epic 9 - Fortification Pressure and Siege Wear**: make fortifications cost upkeep each tick and start to crumble under deterministic siege pressure.
10. **Epic 10 - Agent-Facing Visibility and Match API**: project fog-filtered match state for agents and expose the first REST endpoints against an in-memory match registry.

## Epic 1: Server Foundation and Shared Contracts

Create the initial Python server package and the shared model contracts that every later engine and API feature will rely on.

### Story 1.1: Scaffold the FastAPI server package and core domain contracts

As a server developer,
I want a minimal FastAPI project with canonical state and order models,
So that later game-loop and API work can build on stable validated contracts.

**Acceptance Criteria:**

**Given** a greenfield repository
**When** the first server story is implemented
**Then** the repo contains a Python project scaffold with `server/`, `tests/`, dependency metadata, and importable packages.

**And Given** canonical state models for matches, cities, armies, players, and victory
**When** test fixtures serialize and deserialize those models
**Then** round-trip validation succeeds without data loss.

**And Given** core order payload models for movement, recruitment, upgrades, and transfers
**When** valid sample payloads are parsed
**Then** the payloads validate and expose stable field names for later API endpoints.

### Story 1.2: Add the shared domain enums and reusable validation primitives

As a server developer,
I want centralized enum and validation helpers,
So that later map, initialization, and resolver logic uses consistent identifiers and constraints.

**Acceptance Criteria:**

**Given** resource types, city upgrade tracks, fortification tiers, and match statuses
**When** models reference them
**Then** they come from shared enums/value objects instead of duplicated strings.

**And Given** future engine modules will validate counts and tick durations
**When** helper validators are introduced
**Then** the codebase has a single place for non-negative counts, troop totals, and tick-based duration checks.

## Epic 2: Canonical UK 1900 Map Data

Capture the initial board as testable shared data that the server, client, and future SDK can all consume.

### Story 2.1: Encode the UK 1900 map definition in shared data

As a game engine developer,
I want a canonical map artifact for cities, edges, and resource profiles,
So that initialization and movement logic can consume one source of truth.

**Acceptance Criteria:**

**Given** the V1 UK map specification
**When** the shared map file is loaded
**Then** it contains the full 25-city roster, resource profiles, neutrality flags, and movement edges.

**And Given** Ireland has special constraints
**When** the map is validated
**Then** Belfast, Dublin, Cork, and Galway are marked neutral and no-spawn by default.

### Story 2.2: Add validation tests for graph integrity and special crossings

As a game engine developer,
I want automated map validation,
So that malformed adjacency or missing cities are caught before runtime.

**Acceptance Criteria:**

**Given** the shared map definition
**When** graph validation tests run
**Then** every edge references valid cities, all distances are positive, and Liverpool-Belfast is the only Irish Sea crossing.

## Epic 3: Match Bootstrap and Order Validation

Turn the static contracts into the first playable engine inputs: a valid match state and accepted/rejected orders.

### Story 3.1: Build deterministic match initialization from map and roster inputs

As a game server,
I want to create a canonical starting match state,
So that every new match begins from validated map and player inputs.

**Acceptance Criteria:**

**Given** a match config and player roster
**When** initialization runs
**Then** players receive legal spawn cities, starting resources, and empty movement queues.

**And Given** neutral Ireland is excluded from spawning
**When** starting cities are assigned
**Then** no player begins in Belfast, Dublin, Cork, or Galway.

### Story 3.2: Validate queued orders against ownership, resources, and adjacency

As a game server,
I want to reject invalid orders before resolution,
So that tick execution stays deterministic and safe.

**Acceptance Criteria:**

**Given** movement, recruitment, upgrade, and transfer orders
**When** validation runs
**Then** invalid ownership, insufficient-resource, disconnected-route, and late-order cases are rejected with structured reasons.

## Epic 4: Headless Tick Simulation Skeleton

Establish the first end-to-end engine shell so tests can advance a match without API or database dependencies.

### Story 4.1: Add a pure-function tick resolver skeleton with phase ordering

As a game engine developer,
I want a resolver shell that advances the match through documented phases,
So that later resource, movement, combat, and victory logic plugs into a deterministic pipeline.

**Acceptance Criteria:**

**Given** a current state and order payload
**When** the resolver runs
**Then** it returns a new state object and phase/event metadata without mutating the input state.

**And Given** the documented phase order
**When** the resolver is instrumented
**Then** resource, build, movement, combat, siege, attrition, diplomacy, and victory phases execute in the expected sequence.

### Story 4.2: Provide a headless simulation harness for smoke testing ticks

As a game engine developer,
I want a headless tick runner,
So that CI can execute basic match progression without web or database infrastructure.

**Acceptance Criteria:**

**Given** a minimal match fixture
**When** the headless simulation runner advances N ticks
**Then** it produces deterministic state snapshots and event logs suitable for unit and integration tests.

## Epic 5: Foundational Tick Economy and Movement

Turn the resolver shell into the first meaningfully state-changing engine by implementing resource accounting and army transit behavior while keeping the logic pure and deterministic.

### Story 5.1: Apply deterministic resource accounting during the resolver resource phase

As a game engine developer,
I want the resource phase to update player stockpiles from owned-city yields and upkeep,
So that simulations reflect the real per-tick economic pressure described in the design docs.

**Acceptance Criteria:**

**Given** owned cities, player stockpiles, and stationed/transit armies
**When** the resource phase runs
**Then** each owning player gains the summed resource yields from their cities and pays per-tick food upkeep for owned-city population plus all owned armies.

**And Given** economy upgrade tiers on cities
**When** the resource phase computes city output
**Then** only the primary resource yield is boosted by deterministic tier multipliers and secondary-resource yields remain at their base values.

**And Given** the resolver remains a pure function
**When** the resource phase mutates the copied next-state
**Then** repeated runs from the same inputs produce identical post-phase player resources without mutating the caller-owned `MatchState`.

### Story 5.2: Advance army transit and accepted movement orders during the movement phase

As a game engine developer,
I want the movement phase to progress in-transit armies and start accepted new marches,
So that headless simulations can model travel time and arrivals across the map graph.

**Acceptance Criteria:**

**Given** armies already in transit
**When** the movement phase runs
**Then** `ticks_remaining` decrements deterministically and armies arrive into their destination city when the counter reaches zero.

**And Given** accepted movement orders for armies that are currently stationed in cities
**When** the movement phase runs
**Then** each army begins a one-edge march using the canonical edge distance for that route and leaves its current location until arrival.

**And Given** identical starting state and accepted orders
**When** the movement phase runs repeatedly
**Then** the resulting army positions and transit counters are identical and the original input state remains unchanged.

## Epic 6: Attrition and Victory Safety Rails

Convert the newly stateful resolver into one that also punishes starvation and recognizes endgame control, while keeping the logic pure, deterministic, and easy to smoke test.

### Story 6.1: Apply starvation attrition and elimination checks during the attrition phase

As a game engine developer,
I want the attrition phase to shrink starving armies and flag defeated players,
So that resource shortages and lost territory create deterministic consequences in headless simulations.

**Acceptance Criteria:**

**Given** players whose food stockpile is zero after the resource phase
**When** the attrition phase runs
**Then** each of their armies loses deterministic starvation casualties and any army reduced to zero is removed from the next state.

**And Given** players with no owned cities and no surviving armies after attrition resolution
**When** the attrition phase completes
**Then** those players are marked eliminated while players that still have territory or armies remain active.

**And Given** identical starting states with the same starvation conditions
**When** attrition resolves repeatedly
**Then** the casualty and elimination outcomes are identical and the caller-owned `MatchState` remains unchanged.

### Story 6.2: Track coalition city control and victory countdown during the victory phase

As a game engine developer,
I want the victory phase to count coalition-controlled cities and manage a countdown,
So that simulations can expose an explicit endgame race before combat, siege, and diplomacy are fully implemented.

**Acceptance Criteria:**

**Given** city ownership and player alliance membership in the canonical match state
**When** the victory phase runs
**Then** it groups owned cities by alliance-or-solo coalition, sets `VictoryState.leading_alliance`, and records the leading coalition's controlled city count.

**And Given** a coalition meeting or exceeding the configured city threshold
**When** the victory phase runs on consecutive ticks
**Then** `countdown_ticks_remaining` starts, decreases deterministically while the coalition stays above threshold, and clears if control drops below threshold or the leader changes.

**And Given** repeated runs from the same starting state and coalition ownership layout
**When** the victory phase resolves
**Then** the resulting victory metadata is deterministic and the caller-owned `MatchState` remains unchanged.

## Epic 7: Combat Resolution and Territorial Pressure

Turn the now-stateful resolver into one that can inflict deterministic battle losses and recognize when marching armies seize uncontested cities, so later siege and diplomacy systems sit on top of meaningful territorial conflict.

### Story 7.1: Resolve contested-city combat with defender and fortification advantages

As a game engine developer,
I want the combat phase to apply simultaneous deterministic casualties to opposing armies that share a city,
So that headless simulations can model frontline battles before diplomacy and full siege systems land.

**Acceptance Criteria:**

**Given** armies from different players occupying the same city at the start of the combat phase
**When** combat resolves
**Then** each side takes deterministic simultaneous casualties derived from the opposing force and armies reduced to zero troops are removed from the next state.

**And Given** one side qualifies as the city defender because it owns the contested city
**When** combat resolves in a fortified city
**Then** the defending side receives the documented base defender bonus plus the city's fortification multiplier while attackers do not.

**And Given** identical starting states and contested armies
**When** the combat phase resolves repeatedly
**Then** the resulting troop counts and surviving armies are identical and the caller-owned `MatchState` remains unchanged.

### Story 7.2: Hand uncontested city control to occupying armies after combat resolution

As a game engine developer,
I want the resolver to update city ownership when exactly one surviving force occupies a city after movement and combat,
So that match state, economy, and victory tracking reflect territorial gains without waiting for later API work.

**Acceptance Criteria:**

**Given** a neutral or enemy-owned city containing armies from exactly one surviving player after combat resolution
**When** the tick finishes the combat phase
**Then** the city owner changes to that occupying player in the copied next state.

**And Given** a contested city that still contains surviving armies from multiple players
**When** the combat phase completes
**Then** ownership does not change until only one force remains.

**And Given** repeated runs from the same starting state and occupying armies
**When** the ownership handoff resolves
**Then** the resulting city owners are deterministic and the caller-owned `MatchState` remains unchanged.

## Epic 8: Order Execution and Build Pipeline

Turn the validated order contracts into state-changing resolver behavior so accepted upgrade and recruitment intents actually materialize in the copied next state before later siege and diplomacy work lands.

### Story 8.1: Advance build queues and complete deterministic city upgrades during the build phase

As a game engine developer,
I want the build phase to progress queued upgrades and finish them deterministically,
So that economy, military, and fortification investments persist across ticks instead of remaining inert validated orders.

**Acceptance Criteria:**

**Given** a city with an in-progress building queue item
**When** the build phase runs
**Then** `ticks_remaining` decrements deterministically and completed items apply their target upgrade tier to the copied next state.

**And Given** accepted upgrade orders for player-owned cities with no conflicting queue on the same track
**When** the build phase runs
**Then** each accepted order starts a deterministic queue item and deducts the documented production cost exactly once from the copied next state.

**And Given** identical starting states and accepted upgrade orders
**When** the build phase resolves repeatedly
**Then** queue progression, completed upgrade tiers, player resources, and the caller-owned `MatchState` remain deterministic and unmutated.

### Story 8.2: Process accepted recruitment orders during the build phase

As a game engine developer,
I want the build phase to convert accepted recruitment orders into stationed armies,
So that validated troop purchases actually create military presence for later movement, combat, and attrition phases.

**Acceptance Criteria:**

**Given** accepted recruitment orders for player-owned cities
**When** the build phase runs
**Then** each order deducts the documented food and production cost and creates or reinforces a stationed army for that player in the ordered city.

**And Given** multiple accepted recruitment orders for the same player across different cities in one tick
**When** the build phase runs
**Then** all accepted orders resolve deterministically without depending on list order side effects beyond the already-validated order set.

**And Given** repeated runs from the same starting state and accepted recruitment orders
**When** the build phase resolves
**Then** the resulting armies, city occupants, player resources, and the caller-owned `MatchState` remain deterministic and unmutated.

## Epic 9: Fortification Pressure and Siege Wear

Turn completed fortification upgrades into an upkeep-and-pressure system so defensive structures meaningfully tax economies and erode when attackers isolate them.

### Story 9.1: Deduct fortification upkeep and degrade unpaid defenses deterministically

As a game engine developer,
I want fortified cities to charge recurring money upkeep and lose tiers when upkeep cannot be paid,
So that defensive investment carries the ongoing economic tradeoff described in the design docs.

**Acceptance Criteria:**

**Given** player-owned cities with fortification tiers and sufficient money
**When** the resolver runs the resource and attrition phases
**Then** the owning player's money is reduced by the documented per-tier maintenance total (Tier 1 = 1 money, Tier 2 = 2 money, Tier 3 = 3 money per tick) and the fortification tiers remain unchanged.

**And Given** multiple fortified cities whose combined upkeep exceeds the owning player's money
**When** upkeep resolves
**Then** payment is applied in a deterministic city order, money clamps at zero, and each unpaid fortification decays by exactly one tier during attrition.

**And Given** repeated runs from the same starting state with the same fortified-city layout
**When** upkeep and decay resolve
**Then** the resulting player money, fortification tiers, and caller-owned `MatchState` remain deterministic and unmutated.

### Story 9.2: Degrade besieged fortifications when hostile control seals every adjacent route

As a game engine developer,
I want the siege phase to recognize fully surrounded fortified cities and wear down their defenses,
So that entrenched defenders become vulnerable when attackers isolate every adjacent approach.

**Acceptance Criteria:**

**Given** a fortified city whose owner is different from the owner of every adjacent city on the map
**When** the siege phase runs
**Then** the city's fortification tier drops by exactly one level in the copied next state.

**And Given** a fortified city that still has at least one adjacent city owned by its controller or by an allied coalition member
**When** the siege phase runs
**Then** the fortification tier does not degrade from siege pressure.

**And Given** repeated runs from the same starting state and adjacency ownership layout
**When** the siege phase resolves
**Then** the resulting fortification tiers are deterministic and the caller-owned `MatchState` remains unchanged.

## Epic 10: Agent-Facing Visibility and Match API

Turn the deterministic core engine into something agents can actually consume by projecting fog-filtered state and exposing the first REST endpoints against a lightweight in-memory match service.

### Story 10.1: Project fog-filtered agent state from canonical match data

As an agent-platform developer,
I want a reusable fog-of-war projection over canonical match state,
So that agent polling and future broadcasts can share one deterministic visibility contract.

**Acceptance Criteria:**

**Given** a requesting player, owned cities, and alliance membership in the canonical match state
**When** visible state is projected
**Then** the result includes all cities owned by the player or allied members plus adjacent cities visible through shared vision.

**And Given** visible enemy cities and armies
**When** the projection is built
**Then** enemy ownership is exposed but sensitive details stay masked according to the visibility contract, while self/allied territory keeps exact data.

**And Given** repeated runs from the same match state and requesting player
**When** visibility is projected
**Then** the result is deterministic and the caller-owned `MatchState` remains unchanged.

### Story 10.2: Expose in-memory agent match listing, state polling, and order submission endpoints

As an AI agent developer,
I want minimal REST endpoints for listing matches, polling my visible state, and submitting orders,
So that automated clients can drive headless matches before database-backed persistence lands.

**Acceptance Criteria:**

**Given** seeded in-memory matches
**When** the agent API lists matches
**Then** it returns stable JSON summaries with match identity, status, and tick metadata suitable for polling clients.

**And Given** a valid player in a seeded match
**When** the agent API fetches `/api/v1/matches/{id}/state`
**Then** it returns the fog-filtered projection from Story 10.1 for that player and rejects unknown match or player IDs with structured HTTP errors.

**And Given** valid and invalid order envelopes for a seeded match
**When** the agent API posts `/api/v1/matches/{id}/orders`
**Then** it stores accepted submissions in deterministic in-memory order, echoes a stable acceptance payload, and rejects mismatched match IDs or unknown players without mutating stored submissions.
