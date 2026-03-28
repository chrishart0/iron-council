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
