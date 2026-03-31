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

## Epic 11: QA Hardening and Gameplay Confidence

Add a quality-focused epic that turns the deterministic engine and first agent-facing API into something we can trust through structured review, realistic smoke scenarios, large-batch simulation checks, and a small set of critical end-to-end journeys.

Note: this epic should follow establishment of a real local persistence-backed developer environment so its integration and end-to-end tests run against production-like infrastructure rather than only in-memory fixtures.

### Story 11.1: Run a multi-agent quality review and simplification sweep across the game server

As a delivery lead,
I want multiple focused review agents to inspect the codebase in parallel,
So that correctness gaps, overcomplexity, weak tests, and convention drift are found and fixed before broader validation work proceeds.

**Acceptance Criteria:**

**Given** the current server, engine, API, and test suite
**When** multiple review agents inspect bounded slices of the codebase in parallel
**Then** each review lane reports concrete findings for correctness, test quality, and maintainability without overlapping ownership chaotically.

**And Given** critical or important findings from those review lanes
**When** remediation work is completed
**Then** the affected code and tests are updated, the relevant verification commands pass, and the repo remains in a coherent shippable state.

**And Given** the final review pass for the story
**When** the quality sweep is closed out
**Then** it explicitly confirms overcomplexity, KISS, and by-the-book convention checks were performed and no unresolved high-severity issues remain.

### Story 11.2: Add realistic scenario-based smoke tests for deterministic gameplay flows

As a game engine developer,
I want realistic multi-tick scenario tests,
So that the game rules are validated through meaningful gameplay situations rather than only isolated unit behaviors.

**Acceptance Criteria:**

**Given** deterministic headless simulation support and the implemented resolver phases
**When** realistic scenarios are executed across multiple ticks
**Then** the tests cover representative flows including legal movement, invalid order rejection, attrition pressure, combat resolution, occupation/control handoff, build progression, siege degradation, and victory countdown behavior.

**And Given** repeated runs of the same scenario fixtures
**When** the smoke suite executes
**Then** the resulting snapshots, events, and asserted business outcomes are deterministic.

**And Given** the scenario assertions
**When** the suite validates outcomes
**Then** it checks externally meaningful gameplay results and invariants instead of brittle implementation-detail internals.

### Story 11.3: Add a large-batch simulation regression harness with invariant checks

As a game engine developer,
I want a batch-oriented simulation regression harness,
So that many deterministic scenarios can be exercised quickly to catch invalid states and rule regressions that single examples may miss.

**Acceptance Criteria:**

**Given** a collection of seeded or fixture-driven simulation inputs
**When** the regression harness executes a large batch of runs
**Then** it completes within CI-friendly limits while checking for crashes, invalid references, impossible negative values, ownership/resource inconsistencies, and other documented state invariants.

**And Given** a failing regression scenario
**When** the harness reports the failure
**Then** it identifies the exact scenario or seed and the violated invariant clearly enough for reproduction.

**And Given** repeated executions with the same batch inputs
**When** the harness runs again
**Then** the pass/fail outcomes remain deterministic.

### Story 11.4: Add critical API end-to-end tests for agent gameplay journeys

As an AI agent developer,
I want true API-level end-to-end tests,
So that the first agent workflows are validated through the actual FastAPI boundary instead of only lower-level helpers.

**Acceptance Criteria:**

**Given** seeded in-memory matches and the agent-facing endpoints
**When** end-to-end tests exercise match listing, fog-filtered state polling, order submission, and follow-up state reads
**Then** the tests validate the critical happy-path agent journey through the real API surface.

**And Given** invalid or mismatched requests
**When** the end-to-end suite submits them through the API
**Then** it verifies structured rejection behavior without corrupting stored match or order state.

**And Given** multiple players interacting with the same seeded match
**When** the end-to-end tests fetch visible state
**Then** they verify that fog-of-war boundaries are preserved and one player cannot observe information forbidden by the visibility contract.

## Epic 12: Production-Like Local Development and Persistence Foundation

Correct the current gap between feature implementation and real environment validation by establishing a high-quality local developer stack with containerized services, real database lifecycle management, deterministic seed data, migration discipline, and test isolation that works across parallel worktrees.

Epic 11.4 already covered in-process FastAPI journey tests through the ASGI app boundary. Epic 12 remains necessary because the project still lacks per-worktree isolated databases, deterministic reset-and-seed workflows, and real running-app validation against a database-backed environment.

### Story 12.1: Add a local support-services stack for database-backed development and validation

As a server developer,
I want local support services that boot cleanly while the app itself runs in normal dev mode,
So that development, debugging, and integration testing happen against real infrastructure rather than only in-memory fixtures.

**Acceptance Criteria:**

**Given** a fresh checkout of the repository
**When** the documented local support-services startup command is run
**Then** it starts the truly required backing services, including a real database, with clear environment-variable wiring for running the app locally in dev mode.

**And Given** the local support-services definition
**When** developers inspect it
**Then** it keeps service responsibilities clear, avoids unnecessary complexity such as containerizing the app without need, and supports reproducible startup and teardown.

**And Given** local development and CI-oriented usage
**When** the support-services stack is configured
**Then** it supports normal developer workflows such as `pnpm dev` and `uv run` alongside focused integration-test runs without manual service tinkering.

### Story 12.2: Introduce a proper database migration service and migration-driven schema lifecycle

As a server developer,
I want all schema changes to flow through a real migration system,
So that local environments, test databases, and future deployments share one deterministic schema history.

**Acceptance Criteria:**

**Given** a fresh database
**When** the migration workflow runs
**Then** it can create the full current schema from scratch without manual SQL hand-edits.

**And Given** future schema evolution
**When** developers add or modify persistence structures
**Then** those changes are represented through versioned migrations rather than ad hoc runtime table creation.

**And Given** the migration service in local and test workflows
**When** integration or end-to-end tests prepare a database
**Then** they apply migrations to head before tests execute.

### Story 12.3: Add deterministic seed/reset tooling and per-worktree isolated test databases

As a delivery lead,
I want every worktree to be able to create a fresh database with fresh test data,
So that integration and end-to-end tests can run in parallel without state collisions or manual cleanup.

**Acceptance Criteria:**

**Given** multiple git worktrees or parallel test lanes
**When** each one provisions its integration-test environment
**Then** it receives an isolated database identity, migrated schema, and deterministic seed data without conflicting with sibling worktrees.

**And Given** a developer or Codex worker needs a clean starting point
**When** the reset workflow runs
**Then** it can recreate the database state from migrations plus seed data using a stable documented command.

**And Given** repeated setup runs from the same inputs
**When** the seed/reset workflow executes
**Then** the resulting test data is deterministic and suitable for reproducible debugging.

### Story 12.4: Wire real API integration tests and small end-to-end smoke flows into the quality workflow

As a delivery lead,
I want real API integration tests and a small set of high-value end-to-end smoke flows to become part of the normal quality bar,
So that we stop shipping large amounts of unvalidated code that has never run against a real database-backed environment.

**Acceptance Criteria:**

**Given** the local support-services stack, migration workflow, and seed/reset tooling
**When** integration and end-to-end suites run
**Then** they execute against the real running app and database boundaries instead of only in-memory stand-ins.

**And Given** user-facing stories
**When** they are completed
**Then** each story adds or updates appropriate real-API coverage and contributes to a small smoke-level set of high-value end-to-end user flows rather than an excessive e2e suite.

**And Given** developers and autonomous workers running checks in parallel
**When** the quality workflow executes per worktree
**Then** each lane can run the relevant DB-backed tests without shared-state interference.

**And Given** the repository quality workflow and CI configuration
**When** the new test layers are introduced
**Then** the project has clear command targets and an enforceable quality gate for real-API validation plus a maintainable smoke-level e2e suite.

## Epic 13: Diplomacy Messaging and Reputation Surface

Build the next layer of the agent-facing server API by adding deterministic messaging and diplomacy surfaces that match the design docs closely enough for real bot-vs-bot play to begin. Sequence the work so message transport lands first, treaty status builds on those public communications, and alliance management follows once diplomatic state can be inspected and announced.

### Story 13.1: Add agent-facing match message inbox and send endpoints

As an AI agent developer,
I want deterministic message send and inbox APIs for a match,
So that bots can coordinate publicly and privately through the same communication surface described in the game design.

**Acceptance Criteria:**

**Given** an active match and a valid player identity
**When** the player posts a world or direct message through the agent API
**Then** the server stores it in deterministic order, returns a stable acceptance payload, and preserves exact sender, recipients, tick, and content data.

**And Given** a player polls their message inbox
**When** the match contains world messages plus direct messages involving that player
**Then** the response includes only the messages visible to that player, in stable chronological order, with enough metadata for agents to distinguish world chat from direct communication.

**And Given** invalid messaging inputs such as unknown players, mismatched match IDs, unsupported direct-message recipients, or inbox polling against an unknown match
**When** the API handles the request
**Then** it returns structured API errors without mutating stored message history.

**And Given** the real running app quality workflow
**When** the message API story is implemented
**Then** it includes behavior-first in-process API coverage plus at least one real-process integration or smoke flow covering visible message delivery.

### Story 13.2: Add public treaty status and lifecycle endpoints

As an AI agent developer,
I want to inspect and change treaty status through the API,
So that diplomatic commitments and betrayals become visible, replayable, and actionable during a match.

**Acceptance Criteria:**

**Given** two players proposing, accepting, or withdrawing a treaty action
**When** the treaty API handles the request
**Then** it records a deterministic treaty status transition with the documented treaty types and exposes the resulting treaty state through a stable read model.

**And Given** treaty actions are public in the design
**When** a treaty is signed or withdrawn
**Then** the API emits or records a corresponding world-visible announcement through the messaging surface instead of hiding the event in a private-only side channel.

**And Given** repeated reads from the same match state
**When** clients fetch treaty status again
**Then** they receive deterministic ordering and no duplicate side effects.

### Story 13.3: Add alliance create/join/leave endpoints with deterministic status views

As an AI agent developer,
I want to create alliances, apply to them, and inspect membership through the API,
So that coalition structure can evolve through explicit public actions rather than only out-of-band assumptions.

**Acceptance Criteria:**

**Given** a player creates an alliance or changes membership
**When** the alliance API handles the request
**Then** it returns a stable alliance status view with deterministic member ordering, leader identity, and join metadata.

**And Given** alliance membership affects shared vision and shared victory semantics
**When** alliance state changes are exposed through the API
**Then** the resulting read model aligns with the canonical player `alliance_id` state used elsewhere in the engine.

**And Given** invalid alliance actions such as joining an unknown alliance or leaving a match that does not exist
**When** the API rejects the request
**Then** it does so with structured errors and no hidden mutation.

### Story 13.4: Add match join and lightweight agent profile scaffolding

As an AI agent developer,
I want a minimal join/profile surface,
So that Phase 2 API completeness improves without blocking on the full production authentication and billing stack.

**Acceptance Criteria:**

**Given** a lobby or joinable match record
**When** an agent requests to join
**Then** the API exposes a minimal deterministic join contract or a clear not-yet-joinable rejection path consistent with repo conventions.

**And Given** the architecture calls for agent profile visibility
**When** the lightweight profile endpoint is introduced
**Then** it returns a stable placeholder or DB-backed rating/history shape that can evolve later without breaking clients.

**And Given** these surfaces remain early-phase scaffolding
**When** they are implemented
**Then** they stay intentionally narrow, avoid speculative auth/billing complexity, and remain covered by behavior-first tests.

## Epic 14: Agent Authentication and Secured Access

Turn the current join/profile scaffolding into the first production-shaped security boundary for agent clients. Sequence the work so API-key authentication lands before broader match authorization, while keeping the implementation lean, deterministic, and compatible with both the in-memory seeded registry and the DB-backed local runtime.

### Story 14.1: Add X-API-Key authentication and an authenticated current-agent profile endpoint

As an AI agent developer,
I want the server to resolve my identity from the `X-API-Key` header,
So that profile and join flows stop relying on client-supplied agent identifiers.

**Acceptance Criteria:**

**Given** a request to a secured agent endpoint without a valid active API key
**When** the server evaluates authentication
**Then** it rejects the request with a structured `401` response and no domain mutation.

**And Given** a valid API key for a seeded or DB-backed agent identity
**When** the authentication dependency runs
**Then** it resolves a stable authenticated agent context without exposing raw key material in the API surface.

**And Given** the architecture calls for `GET /api/v1/agent/profile`
**When** an authenticated agent requests that endpoint
**Then** the API returns the profile for the caller's key owner with behavior-first coverage plus at least one running-process integration or smoke flow.

### Story 14.2: Bind match joins and match-scoped reads/writes to the authenticated agent identity

As an AI agent developer,
I want match access to derive my playable identity from my authenticated agent,
So that state polling, order submission, and diplomacy actions cannot spoof another player through request payload fields.

**Acceptance Criteria:**

**Given** an authenticated agent joining a match
**When** the join endpoint succeeds
**Then** it assigns or reuses the deterministic match player slot for that authenticated agent without requiring the client to send `agent_id` in the payload.

**And Given** a secured match-scoped API call after join
**When** the endpoint needs player identity for state reads or writes
**Then** it derives that identity from the authenticated agent's join mapping and rejects unjoined or mismatched access with structured errors and no hidden mutation.

**And Given** this access-control layer changes public API behavior
**When** the story is implemented
**Then** the repo includes behavior-first API coverage, real-process verification, and a simplification pass confirming the solution stays KISS and by-the-book.

## Epic 15: Reference Agent SDK and Example Bot

Turn the now-authenticated agent API into a usable developer product by shipping a narrow Python SDK plus a minimal example bot. Sequence the work so the typed client lands before the bot that consumes it, and keep both artifacts focused on the public HTTP contract rather than internal server implementation details.

### Story 15.1: Add a reference Python SDK for authenticated agent workflows

As an AI agent developer,
I want a small Python client for the authenticated Iron Council API,
So that I can list matches, join, poll state, submit orders, and interact with diplomacy endpoints without hand-rolling HTTP glue.

**Acceptance Criteria:**

**Given** a base URL and valid `X-API-Key`
**When** an agent uses the SDK to call profile, match, state, order, message, treaty, or alliance workflows
**Then** the SDK sends the correct authenticated requests and returns stable typed data for the public API contract.

**And Given** the server responds with a structured API error or transport failure
**When** the SDK request fails
**Then** the caller receives one clear exception carrying the HTTP status and repo-style API error details without leaking secrets.

**And Given** the repo requires behavior-first and real-process verification
**When** the SDK story is implemented
**Then** it includes in-process contract tests plus at least one running-app integration or smoke path that uses the SDK against the real local server boundary.

### Story 15.2: Add a minimal example agent and SDK quickstart guide

As an AI agent developer,
I want a minimal runnable example agent and setup guide,
So that I can copy a working loop instead of reverse-engineering the API from tests and docs.

**Acceptance Criteria:**

**Given** the reference Python SDK and a running seeded server
**When** the example agent is executed with the documented environment variables or CLI arguments
**Then** it authenticates, joins a match if needed, fetches visible state, and performs one deterministic decision cycle using only the SDK surface.

**And Given** the example is meant to teach agent authors the public contract
**When** it decides what to do each tick
**Then** it stays intentionally simple, deterministic, and free of internal server imports or implementation-detail shortcuts.

## Epic 16: Complete the Group-Chat Messaging Surface

Close the largest remaining messaging gap between the GDD/architecture and the implemented agent API by adding authenticated group-chat workflows end to end. Sequence the work so the backend contract lands first, then extend the standalone SDK and onboarding docs to consume that public surface.

### Story 16.1: Add authenticated group-chat creation, membership, and message workflows

As an AI agent player,
I want to create and participate in match-scoped group chats,
So that I can coordinate alliances and back-channel negotiations through the same authenticated API surface as direct and world messaging.

**Acceptance Criteria:**

**Given** an authenticated agent joined to a match
**When** it creates a group chat with a name and invited member ids
**Then** the API persists a deterministic group-chat record and returns a stable identifier plus membership.

**And Given** a player is a member of a group chat
**When** that player lists visible group chats or reads group-chat messages
**Then** they only see the chats and messages for groups they belong to in that match.

**And Given** a player is not a member of a group chat
**When** they attempt to read or post messages to that group
**Then** the API rejects the request with a structured authorization or visibility error.

**And Given** existing world and direct message workflows already exist
**When** group-chat support is added
**Then** those existing behaviors continue to pass unchanged through behavior-first API and running-app verification.

### Story 16.2: Extend the Python SDK and example docs for group-chat workflows

As an AI agent developer,
I want the reference Python SDK and docs to cover group-chat workflows,
So that I can use the full public messaging surface without reverse-engineering new HTTP shapes by hand.

**Acceptance Criteria:**

**Given** the authenticated group-chat API exists
**When** an agent uses the Python SDK to create, list, read, and send group-chat messages
**Then** it gets stable typed data matching the public HTTP contract.

**And Given** the SDK must remain a self-contained external-consumer artifact
**When** group-chat support is added
**Then** the SDK still imports and runs without repo-internal `server` package dependencies.

**And Given** developers need a trustworthy onboarding path
**When** the SDK docs/examples describe group-chat usage
**Then** the documented commands and snippets are covered by tests or smoke verification.

## Epic 17: Consolidated Agent Turn Contract

Close the remaining gap between the architecture's per-tick agent payloads and the currently fragmented REST surface by adding a bundled authenticated briefing read and a single-command submission write. Sequence the work so the read-side contract lands first, then add the consolidated command envelope on top of the existing validated order, messaging, treaty, and alliance primitives.

### Story 17.1: Add an authenticated bundled agent briefing endpoint

As an AI agent developer,
I want one authenticated endpoint that returns my current fog-filtered state plus relevant communication and diplomacy context,
So that I can evaluate a turn from one stable contract instead of stitching together multiple HTTP reads.

**Acceptance Criteria:**

**Given** an authenticated agent joined to a match
**When** it requests the bundled agent briefing for that match
**Then** the response includes the existing fog-filtered state projection, visible alliance status, visible treaties, visible group chats, and message buckets shaped for direct, group, and world consumption.

**And Given** agents need an incremental polling loop instead of replaying the entire communication history every tick
**When** the client passes a deterministic since-tick cursor
**Then** the bundled briefing only includes messages and diplomacy events at or after that tick while keeping the current state snapshot authoritative.

**And Given** the bundled contract is meant to reduce integration risk for external agents
**When** the endpoint is documented and tested
**Then** behavior-first API tests, running-app checks, and SDK-facing contract smoke coverage verify the exact public JSON shape without depending on repo-internal server imports.

### Story 17.2: Add a consolidated authenticated agent command endpoint

As an AI agent developer,
I want to submit orders, outgoing messages, and diplomacy actions in one authenticated command envelope,
So that my turn loop can write one public contract per tick instead of coordinating multiple mutation endpoints by hand.

**Acceptance Criteria:**

**Given** an authenticated agent joined to a match
**When** it posts a consolidated command envelope for the current tick
**Then** the server validates the match/tick identity once, applies accepted orders through the existing validation pipeline, records outgoing messages, applies requested treaty or alliance actions, and returns a stable acceptance summary.

**And Given** any contained action is invalid for the authenticated player or match
**When** the command endpoint validates the envelope
**Then** it returns structured errors without partially mutating unrelated side effects.

**And Given** the consolidated command endpoint is only a public-contract convenience layer
**When** it is implemented
**Then** the underlying focused REST endpoints remain available and keep their existing behavior-first tests passing unchanged.

## Epic 18: Live Match Runtime Loop

Close the biggest remaining architecture gap between the deterministic engine and a shippable multiplayer service by teaching the running FastAPI app to advance active matches on its own clock. Sequence the work so the server can first advance active matches in-process against the existing registry and APIs, then add durable tick persistence/logging, then layer human/spectator realtime delivery on top of that moving runtime.

### Story 18.1: Launch an in-process async tick loop for active matches

As a game server operator,
I want active matches to advance on their configured interval without an HTTP trigger,
So that the running service behaves like a real tick-based simulation instead of a static contract mock.

**Acceptance Criteria:**

**Given** the FastAPI app starts with one or more active matches in the registry
**When** the server lifespan begins
**Then** it launches one background loop per active match that sleeps by the match tick interval and advances only that match state on schedule.

**And Given** agents have already submitted validated orders for the current tick
**When** the loop advances the match
**Then** it resolves the next tick from the existing pure-function engine, consumes the queued submissions for that tick, increments the canonical match tick, and leaves later ticks' submissions untouched.

**And Given** developers need confidence at the public boundary
**When** the story ships
**Then** behavior-first tests cover lifecycle startup/shutdown plus a small real-process API smoke proving an active match tick advances without any manual endpoint call.

### Story 18.2: Persist live tick advancement and write tick-log history

As a game server operator,
I want runtime tick advancement to update the database durably,
So that active matches can resume after a restart and expose auditable tick history.

**Acceptance Criteria:**

**Given** the app runs against the database-backed registry
**When** an active match advances a tick
**Then** the latest match state and current tick are persisted back to the `matches` table.

**And Given** debugging and replay require historical state
**When** each runtime tick completes
**Then** the server writes a `tick_log` row containing the resolved tick number, state snapshot, accepted orders, and emitted events.

**And Given** runtime durability should not break local workflows
**When** the persistence path is verified
**Then** running-app tests exercise the real service boundary against migrated seeded data and confirm the persisted state survives a registry reload.

### Story 18.3: Broadcast live match updates over WebSockets for human clients and spectators

As a human player or spectator,
I want the running match to push updates over WebSockets,
So that the client can watch the war unfold in real time instead of polling ad hoc REST reads.

**Acceptance Criteria:**

**Given** a human player or spectator connects to the match WebSocket
**When** the server accepts the connection
**Then** it sends an initial state payload shaped to the documented protocol and keeps the connection registered for future broadcasts.

**And Given** an active match advances or a chat-visible event occurs
**When** the runtime loop completes the tick
**Then** the server broadcasts the post-tick payload to subscribed clients, using fog-filtered state for players and full visibility for spectators.

**And Given** the realtime protocol is a public client contract
**When** the feature ships
**Then** tests cover connection lifecycle, initial payload shape, and at least one real-process tick-driven broadcast for both a player and a spectator role.

## Epic 19: Match Replay and Public Read Models

Turn the newly persisted runtime state into consumable read models for replay tooling, spectator surfaces, and future web-client pre-game/history pages. Sequence the work so the server first exposes auditable tick history and replay snapshots from the existing `tick_log`, then layers lightweight public leaderboard and completed-match summary reads on top of the same persisted database foundation.

### Story 19.1: Expose persisted tick history and replay snapshots

As a spectator client or debugging tool,
I want to list recorded match ticks and fetch one persisted snapshot by tick,
So that replay and audit flows can inspect the authoritative history written by the live runtime.

**Acceptance Criteria:**

**Given** the DB-backed server has persisted `tick_log` rows for a match
**When** a client requests the match history route
**Then** the API returns deterministic tick entries for that match in ascending order, together with enough match metadata to drive a replay picker.

**And Given** a client requests one specific persisted tick
**When** the replay snapshot route is called with an existing tick number
**Then** the API returns the persisted state snapshot, accepted orders, and emitted events for that tick.

**And Given** replay depends on durable runtime history rather than in-memory state
**When** the feature ships
**Then** behavior-first tests cover unknown match/tick failures plus a real-process DB-backed smoke proving the running app serves the persisted history contract.

### Story 19.2: Add public leaderboard and completed-match summary reads

As a human player or spectator,
I want lightweight leaderboard and completed-match summary endpoints,
So that pre-game browsing can show who is strong and what happened in finished matches without requiring private agent credentials.

**Acceptance Criteria:**

**Given** persisted player and match records in the database
**When** a client requests the public leaderboard route
**Then** the API returns deterministic agent/player ranking summaries ordered by visible rating fields.

**And Given** completed matches exist in the database
**When** a client requests match-history summaries
**Then** the API returns compact completed-match metadata suitable for browse/list views without dumping full tick snapshots.

**And Given** these are public read models
**When** the story ships
**Then** tests verify stable ordering, minimal response shape, and real-process coverage against the running DB-backed app.

## Epic 20: Public Match Browse and Lobby Read Models

Turn the existing public `GET /api/v1/matches` route into a durable browse surface for human pre-game and spectator entry flows. Sequence the work so the server first returns DB-backed compact match browse summaries for lobby/active/paused matches, then layers a dedicated public match-detail read for one selected lobby without exposing private fogged state.

### Story 20.1: Add DB-backed public match browse summaries

As a human player or spectator,
I want the public matches route to return compact browse metadata for joinable and live matches,
So that pre-game browsing can distinguish lobbies, running games, and spectator candidates without relying on private agent APIs.

**Acceptance Criteria:**

**Given** persisted non-completed matches exist in the database
**When** a client requests `GET /api/v1/matches`
**Then** the API returns deterministic compact browse summaries ordered by public status and recency rather than replay-sized state payloads.

**And Given** match browse needs to support lobby and live entry decisions
**When** the response is returned
**Then** each summary includes only public metadata needed for browsing, such as match identity, status, map, current tick, tick interval, current player count, max player count, and open slot count.

**And Given** completed matches already have a dedicated browse route
**When** the public matches route is called in DB-backed mode
**Then** completed matches are excluded and behavior-first tests plus a real-process smoke prove the running app serves the DB-backed browse contract.

### Story 20.2: Add a public match lobby detail read

As a human player or spectator,
I want one compact public match-detail endpoint for a selected match,
So that pre-game and spectator surfaces can inspect lobby configuration and visible roster metadata before joining or watching.

**Acceptance Criteria:**

**Given** a lobby, paused, or active match exists
**When** a client requests the public match-detail route
**Then** the API returns compact public metadata for that one match, including configuration and a visible roster summary, without exposing fog-filtered state or private agent credentials.

**And Given** a completed match or unknown match is requested
**When** the public detail route is called
**Then** the server returns a structured response aligned with the browse-surface contract and does not leak replay/history payloads through this endpoint.

**And Given** this endpoint is a public read model
**When** the story ships
**Then** tests cover route success, structured not-found handling, stable ordering of visible roster rows, and real-process coverage against the DB-backed app.

## Epic 21: Authenticated Match Lobby Creation

Turn the now-public browse and detail surfaces into a usable lobby funnel by letting authenticated agent competitors create new browseable lobbies with validated config and canonical starting state. Sequence the work so the first story adds a narrow API for creating one lobby with creator membership in DB-backed mode, reusing the existing public browse/detail contracts instead of inventing a separate admin or seed-only path.

### Story 21.1: Add an authenticated match lobby creation endpoint

As an authenticated agent competitor,
I want to create a new match lobby through the API,
So that I can spin up a browseable game with valid public settings and immediately occupy the creator slot without relying on seeded fixtures.

**Acceptance Criteria:**

**Given** an authenticated caller submits a supported lobby configuration
**When** `POST /api/v1/matches` is called
**Then** the server creates a new lobby with validated public config, canonical initialized state, and creator membership.

**And Given** DB-backed mode is active
**When** the lobby is created
**Then** the server persists the `matches` row and creator `players` row in one coherent transaction and returns compact lobby metadata suitable for browse/detail surfaces.

**And Given** the new lobby is public and joinable
**When** the existing browse or detail routes are called
**Then** the lobby appears immediately with correct slot counts and without leaking private auth material.

**And Given** invalid config or unsupported map input
**When** the create route is called
**Then** the server returns structured validation/domain errors and does not persist a partial lobby.

**And Given** the story ships
**When** focused unit/API/e2e and SDK checks run
**Then** the authenticated creation contract is proven from the public boundary and the repo quality gate passes.

## Epic 22: Lobby Activation and Match Start

Turn the authenticated lobby funnel into an actually playable DB-backed flow by letting a lobby creator start a created lobby once enough competitors have joined, switching the match into the active runtime path without relying on seeded active matches.

### Story 22.1: Add an authenticated lobby start endpoint

As an authenticated lobby creator,
I want to start a ready lobby through the API,
So that a DB-created match can transition from browseable lobby state into a live active match with the real runtime loop.

**Acceptance Criteria:**

**Given** an authenticated creator has a lobby with enough joined players
**When** `POST /api/v1/matches/{id}/start` is called
**Then** the server validates creator ownership and readiness rules, transitions the match status from `lobby` to `active`, and returns compact post-start metadata.

**And Given** DB-backed mode is active
**When** the lobby start succeeds
**Then** the status transition and any required persisted match metadata updates are stored durably and the running app can observe the match as active without reseeding fixtures.

**And Given** a lobby is not ready, the caller is not the creator, or the match is already active/completed
**When** the start route is called
**Then** the server returns structured domain errors and does not partially transition the match.

**And Given** the newly started match enters the runtime flow
**When** the real-process app is running
**Then** a focused smoke proves the match becomes active and is eligible for the existing tick/runtime path without regressing public browse/detail reads.

## Epic 23: Authenticated Lobby Lifecycle SDK and Quickstart

Carry the newly shipped authenticated lobby creation/start funnel through the reference Python SDK and runnable example so an external agent can create, fill, and start a lobby without dropping down to handwritten HTTP calls. Sequence the work so the first story adds a narrow start-lobby SDK method and then updates the example/README to demonstrate the DB-backed pregame lifecycle from the public boundary.

### Story 23.1: Extend the Python SDK and example quickstart for authenticated lobby lifecycle flows

As an external agent developer,
I want the Python SDK and runnable example to cover create/join/start lobby workflows,
So that I can drive the new DB-backed pregame lifecycle from a stable public client surface instead of custom HTTP code.

**Acceptance Criteria:**

**Given** the server now supports authenticated lobby creation and creator-only start
**When** the Python SDK is used from outside the server package
**Then** it exposes narrow typed helpers for `POST /api/v1/matches` and `POST /api/v1/matches/{id}/start` without importing repo-internal server modules.

**And Given** a creator client plus another authenticated competitor
**When** they use the SDK against the DB-backed app to create a lobby, join it, and start it
**Then** the returned typed responses prove compact metadata, creator-only start behavior, and transition to `active` from the public boundary.

**And Given** the runnable example and README quickstart
**When** an implementer follows the documented command path
**Then** they can either target an existing match or create a lobby, optionally auto-start it after enough agents join, and see a concise JSON summary describing the lifecycle actions taken.

**And Given** the story ships
**When** focused SDK/unit/real-process smoke checks and the repo quality gate run
**Then** the client contract, example flow, and docs are all verified from the consumer boundary.

## Epic 24: Web Client Foundation and Human Access

Open the next product lane beyond the server and agent SDK by introducing the first Next.js client scaffold and the missing human-access foundation. Sequence the work so the client can first ship a public read-only match browser against the existing public API, then tighten the human authentication boundary on HTTP and WebSocket paths, then add client-side session/bootstrap plumbing without overreaching into full gameplay UI.

### Story 24.1: Scaffold a Next.js client and public match browser

As a spectator or prospective player,
I want a web page that lists public matches from the running server,
So that I can discover lobbies and active games without using agent tooling or private credentials.

**Acceptance Criteria:**

**Given** the FastAPI server is running
**When** a user opens the new client app's public matches route
**Then** the page renders data from `GET /api/v1/matches` using the existing compact public browse contract.

**And Given** the match browser is intended as the first human-facing entry point
**When** rows are shown
**Then** each row includes only public browse metadata such as match id, status, map, tick, tick interval, current player count, max players, and open slots.

**And Given** the client is the first new runtime in the repo
**When** the story ships
**Then** the repository contains a minimal Next.js + TypeScript scaffold, documented local run commands, and automated client verification integrated into the repo quality workflow.

**And Given** the server is unavailable or returns no public matches
**When** the route loads
**Then** the client shows deterministic empty/error states without exposing stack traces or raw transport details.

### Story 24.2: Add real human JWT authentication for HTTP and WebSocket paths

As a human player,
I want the server to authenticate me with a real user token instead of agent credentials,
So that the browser can join future player-only flows through the public architecture boundary.

**Acceptance Criteria:**

**Given** the architecture requires Supabase-issued JWTs for human users
**When** an authenticated browser calls a protected HTTP route or player WebSocket path
**Then** the server validates the JWT, resolves the human identity, and rejects invalid or missing tokens with structured auth errors.

**And Given** agent auth and spectator access already exist
**When** human auth is introduced
**Then** the implementation preserves agent API-key flows and unauthenticated spectator reads without widening privileges or conflating identities.

**And Given** WebSocket auth is a public contract
**When** a player socket connects with a valid human token
**Then** the server registers the viewer as a human player and sends the same initial realtime envelope shape already documented for player viewers.

**And Given** the story ships
**When** focused HTTP/WebSocket tests plus the repo quality gate run
**Then** the new human auth path is verified from the public boundary and the docs stay aligned with the shipped contract.

### Story 24.3: Add client-side auth/session bootstrap for future human flows

As a returning human player,
I want the web client to remember my configured server/auth context,
So that later browse, lobby, and live-match pages can reuse one simple session shell instead of ad hoc per-page wiring.

**Acceptance Criteria:**

**Given** the client has a public browser page and the server can validate human JWTs
**When** a user configures the client runtime
**Then** the app provides a small session/bootstrap layer for server base URL, auth state, and guarded navigation.

**And Given** some pages remain public while later pages require auth
**When** navigation occurs
**Then** the client clearly distinguishes public routes from authenticated routes without duplicating connection/bootstrap logic.

**And Given** the story ships
**When** local run docs and automated checks are executed
**Then** the client session shell is documented, tested, and ready for authenticated lobby/gameplay stories.

## Epic 25: Human Pregame and Spectator Entry

Turn the new client foundation into a usable human-facing entry funnel by adding public match detail, a read-only spectator live view, and the first authenticated lobby actions for humans. Sequence the work so read-only discovery lands before live spectator delivery, and live spectator delivery lands before authenticated lobby mutation flows.

### Story 25.1: Add a public match-detail page in the web client

As a spectator or prospective player,
I want a web detail page for one public match,
So that I can inspect a lobby or running match before deciding to watch or join.

**Acceptance Criteria:**

**Given** the server already exposes a compact public match-detail route
**When** a user opens the client detail page for a valid lobby, paused, or active match
**Then** the page renders configuration and visible roster metadata without exposing fog-filtered state or private credentials.

**And Given** an unknown or completed match id is requested
**When** the route resolves
**Then** the page shows deterministic not-found or unsupported-state handling aligned with the public API contract.

### Story 25.2: Add a read-only spectator live match page over WebSockets

As a spectator,
I want to watch the live match state update in the browser,
So that I can observe the war unfold without polling APIs manually.

**Acceptance Criteria:**

**Given** the running server already broadcasts spectator-safe WebSocket updates
**When** a user opens the spectator live page for an active match
**Then** the client connects to the spectator WebSocket path, renders the initial payload, and updates the view when new tick broadcasts arrive.

**And Given** the socket disconnects or the match is not active
**When** the client handles the condition
**Then** it shows a deterministic reconnect or inactive-state message without silently freezing stale state.

### Story 25.3: Add authenticated human lobby create/join/start flows in the web client

As a human player,
I want to create, join, and start a lobby from the browser,
So that I can enter matches through the same product surface instead of relying on agent SDK tools.

**Acceptance Criteria:**

**Given** the browser has authenticated human access and the server already supports lobby lifecycle mutations
**When** a player uses the client lobby actions
**Then** the UI calls the existing public routes for create, join, and creator-only start without inventing a parallel backend path.

**And Given** domain errors occur such as invalid auth, not-ready, or forbidden start
**When** the action fails
**Then** the client surfaces the structured error clearly and does not leave optimistic state that disagrees with the server.

## Epic 26: Authenticated Human Live Match Operations

Carry the authenticated human browser lane from pregame into the active-match surface by connecting the client to the already-shipped player websocket contract first, then layering in the smallest practical read/write gameplay affordances. Sequence the work so the first story proves the browser can receive fog-filtered player state plus messaging/diplomacy summaries over the real player websocket before adding any order-entry UI.

### Story 26.1: Add an authenticated human live match page over the player websocket

As an authenticated human player,
I want a browser page for my live match feed,
So that I can observe my fog-filtered state, chat/diplomacy summaries, and tick updates through the same shipped player websocket contract used by the backend.

**Acceptance Criteria:**

**Given** a joined authenticated human and an active match
**When** the player opens the live match page in the client
**Then** the UI connects to the existing `/ws/match/{id}?viewer=player&token=*** websocket path, renders the initial fog-filtered player envelope, and updates as new tick broadcasts arrive without inventing a parallel backend route.

**And Given** the websocket payload includes player-safe state plus world/direct/group/treaty/alliance collections
**When** the client renders the live page
**Then** it shows concise player-facing summaries derived from that existing contract and clearly identifies the authenticated player id currently being viewed.

**And Given** auth is missing/invalid, the user is not joined to the match, the match is not active, or the socket disconnects
**When** the client handles the condition
**Then** it surfaces a deterministic guard/error/reconnect state and preserves the last confirmed live snapshot instead of silently freezing or showing stale optimistic UI.

**And Given** the story ships
**When** focused client behavior tests plus the repo quality gate run
**Then** the human live page is verified from the public browser boundary and the docs/BMAD artifacts stay aligned with the shipped route and contract.

### Story 26.2: Add authenticated human order submission controls in the live web client

As an authenticated human player,
I want to queue and submit my orders from the browser live page,
So that I can actually play an active match through the shipped web client without falling back to agent-only tooling.

**Acceptance Criteria:**

**Given** a joined authenticated human on the live match page and the server already supports the authenticated command envelope
**When** the player drafts movement, recruitment, upgrade, or transfer orders and submits them
**Then** the client posts the existing `/api/v1/matches/{id}/commands` route using the current live tick and the shipped order payload shape without inventing a new backend route.

**And Given** the command request fails because auth is missing, the player is not joined, the tick is stale, or validation/domain rules reject the order
**When** the client handles the failure
**Then** it surfaces the structured error clearly, keeps the player's draft intact for correction, and does not pretend the live state already changed.

**And Given** the command request succeeds
**When** the server accepts the order envelope
**Then** the client shows a deterministic accepted-for-tick confirmation from the public response while still relying on the websocket for authoritative state updates.

**And Given** the story ships
**When** focused client behavior tests plus the repo quality gate run
**Then** the order controls are verified from the browser boundary and the docs/BMAD artifacts stay aligned with the shipped command route and payload contract.

## Epic 27: Human Live Match Diplomacy and Communication Writes

Finish the first genuinely playable human browser lane by layering the smallest practical chat and diplomacy write controls onto the authenticated live page. Keep the scope deliberately text-first and route-faithful: reuse the existing live websocket for authoritative refreshes, but send writes through the already-shipped authenticated HTTP API contracts for world/direct/group chat, treaties, and alliance management.

### Story 27.1: Add authenticated human live messaging controls in the web client

As an authenticated human player,
I want to send world, direct, and group-chat messages from the live browser page,
So that I can participate in the same diplomacy and communication loop as agents without leaving the shipped web client.

**Acceptance Criteria:**

**Given** a joined authenticated human on the live match page and the server already supports authenticated message routes
**When** the player drafts a world message, a direct message to another visible player, or a group-chat message to a visible group chat and submits it
**Then** the client posts only the existing `/api/v1/matches/{id}/messages` or `/api/v1/matches/{id}/group-chats/{group_chat_id}/messages` routes using the current live tick and the shipped payload contracts without inventing a parallel backend mutation path.

**And Given** auth is missing, the user is not joined, the tick is stale, the message content is invalid, or the target chat/player is rejected by the domain rules
**When** the client handles the failure
**Then** it surfaces the structured error clearly, preserves the player's draft for correction, and does not optimistically append a fake message to the live feed.

**And Given** a message submission succeeds
**When** the server returns the accepted response
**Then** the client shows a deterministic accepted-for-tick confirmation while continuing to rely on the websocket for the authoritative live message timeline.

**And Given** the story ships
**When** focused client behavior tests plus the repo quality gate run
**Then** the human live messaging controls are verified from the browser/API boundary and the docs/BMAD artifacts stay aligned with the shipped message routes and payloads.

### Story 27.2: Add authenticated human treaty and alliance controls in the live web client

As an authenticated human player,
I want to manage treaties and alliances from the live browser page,
So that the browser supports the core diplomatic actions needed for real human multiplayer matches.

**Acceptance Criteria:**

**Given** a joined authenticated human on the live match page and the server already supports treaty and alliance routes
**When** the player proposes or withdraws a treaty, creates an alliance, joins an alliance, or leaves their current alliance from the client
**Then** the UI calls only the shipped authenticated treaty/alliance HTTP routes or existing command-envelope surface already defined by the backend, using the current live tick and existing payload contracts without inventing a browser-only mutation API.

**And Given** domain errors occur such as invalid auth, invalid counterparty, duplicate treaty/alliance membership, creator/leader restrictions, or tick mismatch
**When** the action fails
**Then** the client surfaces the structured error clearly, preserves the current draft/selection state for correction, and does not fabricate optimistic diplomatic state.

**And Given** a treaty or alliance action succeeds
**When** the server accepts the request
**Then** the client shows deterministic acceptance metadata while relying on the websocket refresh as the source of truth for the updated diplomatic state.

**And Given** the story ships
**When** focused client behavior tests plus the repo quality gate run
**Then** treaty/alliance controls are verified from the public browser/API boundary and the docs/BMAD artifacts stay aligned with the shipped route and payload contracts.

## Epic 28: Human Live Group Chat Creation and Invite Controls

Close the last obvious human diplomacy parity gap in the live browser lane by letting authenticated human players create new match-scoped group chats from the existing `/play` page. Keep the work deliberately narrow: reuse the shipped authenticated `/api/v1/matches/{id}/group-chats` route, derive invite candidates from the authoritative websocket snapshot, and rely on the websocket as the source of truth for visible group-chat state after accepted writes.

### Story 28.1: Add authenticated human live group-chat creation controls in the web client

As an authenticated human player,
I want to create a new group chat and invite visible players from the live browser page,
So that I can start new private coalition conversations without leaving the shipped web client or relying on agent-only tooling.

**Acceptance Criteria:**

**Given** a joined authenticated human on the live match page and the server already supports authenticated group-chat creation
**When** the player enters a group-chat name, selects one or more visible other players, and submits the form
**Then** the client posts only the existing `/api/v1/matches/{id}/group-chats` route with the current live tick and the shipped payload contract without inventing a browser-only mutation API or extra discovery route.

**And Given** auth is missing, the player is not joined, the tick is stale, the chat name is invalid, or the invited players are rejected by the existing domain rules
**When** the creation request fails
**Then** the client surfaces the structured error clearly, preserves the drafted name and invited-player selections for correction, and does not fabricate optimistic group-chat state.

**And Given** the server accepts the group-chat creation request
**When** the response returns accepted metadata
**Then** the client shows deterministic acceptance details from the response while continuing to rely on the websocket snapshot as the authoritative source for the visible group-chat list and subsequent message targets.

**And Given** the story ships
**When** focused client behavior tests plus the repo quality gate run
**Then** the human group-chat creation controls are verified from the public browser/API boundary and the docs/BMAD artifacts stay aligned with the shipped route and payload contract.

## Epic 29: Public Web Read Models for Ranking and Replay

Turn the already-shipped public read APIs for leaderboard standings, completed matches, and persisted replay history into browser-accessible pages so spectators and prospective players can understand who is strong and what happened in finished games without agent tooling. Keep the implementation boring: reuse the existing `/api/v1/leaderboard`, `/api/v1/matches/completed`, and `/api/v1/matches/{id}/history` routes, render compact read-only summaries, and avoid inventing browser-only aggregation endpoints.

### Story 29.1: Add public leaderboard and completed-match browse pages in the web client

As a prospective player or spectator,
I want browser pages for leaderboard standings and completed-match summaries,
So that I can discover strong competitors and recent finished games before joining a live match.

**Acceptance Criteria:**

**Given** the DB-backed server already exposes public leaderboard and completed-match summary routes
**When** the browser loads the new read-only pages
**Then** the client fetches only the shipped `/api/v1/leaderboard` and `/api/v1/matches/completed` contracts, renders deterministic rankings and compact completed-match cards, and does not invent any browser-only aggregation API.

**And Given** the server reports unavailable or malformed public-read payloads
**When** the page request fails
**Then** the client surfaces a clear read-only error state without crashing and preserves obvious navigation back to the rest of the public browser.

**And Given** a completed-match card is rendered
**When** a user wants deeper inspection
**Then** the page exposes a stable link into the match-specific replay/history surface rather than embedding replay payloads directly into the browse response.

**And Given** the story ships
**When** focused client behavior tests plus the repo quality gate run
**Then** the leaderboard and completed-match browse flows are verified from the public browser/API boundary and the docs/BMAD artifacts stay aligned with the shipped route contracts.

### Story 29.2: Add public completed-match history and replay inspection pages in the web client

As a spectator or debugging user,
I want a browser replay inspector for one completed match,
So that I can review persisted tick history and inspect one authoritative replay snapshot at a time from the shipped public history APIs.

**Acceptance Criteria:**

**Given** a completed match with persisted `tick_log` history
**When** the browser opens the replay page and selects a tick
**Then** the client fetches only the shipped `/api/v1/matches/{id}/history` and `/api/v1/matches/{id}/history/{tick}` routes, renders deterministic tick-picker metadata, and shows the selected persisted snapshot/orders/events without inventing a websocket or browser-only replay API.

**And Given** the match or tick is unknown, or the DB-backed history API is unavailable
**When** the browser loads the replay surface
**Then** the client shows structured read-only error states with stable navigation back to completed-match browse pages.

**And Given** the story ships
**When** focused client behavior tests plus the repo quality gate run
**Then** the replay/history inspector is verified from the public browser/API boundary and the docs/BMAD artifacts stay aligned with the shipped route contracts.

## Epic 30: Spectator Situation Awareness and Live Context

Turn the existing public live spectator page into a more legible watch surface so observers can understand what is happening politically, not just that ticks are arriving. Reuse the shipped public match-detail read and spectator websocket contracts, keep the UI read-only and text-first, and prefer small deterministic readability wins over flashy presentation.

### Story 30.1: Add a spectator situation room to the live web client

As a spectator,
I want the live match page to show readable chat, treaty, and alliance context,
So that I can understand the political state of a live match without decoding raw player IDs or switching tools.

**Acceptance Criteria:**

**Given** the public live spectator page already fetches `/api/v1/matches/{id}` before opening the websocket
**When** the page renders roster metadata
**Then** the public match-detail contract includes stable public `player_id` values alongside `display_name` and `competitor_kind` so the client can map live-event actor IDs to readable labels without inventing a second lookup API.

**And Given** the spectator websocket delivers world messages, treaties, and alliances
**When** the live page renders a tick update
**Then** it shows text-first read-only panels for recent world chat, treaty status, and alliance membership using roster display names where possible and deterministic raw-ID fallback otherwise.

**And Given** those public panels have no data or the page is disconnected
**When** the user views the spectator page
**Then** the UI shows explicit empty/not-live states rather than stale or fabricated diplomacy/chat context.

**And Given** the story ships
**When** focused server/client checks plus the repo quality gate run
**Then** the enriched spectator live surface is verified from the public API/browser boundary and the docs/BMAD artifacts stay aligned with the shipped contracts.

### Story 30.2: Add territory pressure and victory context to the spectator live page

As a spectator,
I want a compact territory and victory summary on the live page,
So that I can see who is leading and why the current political situation matters.

**Acceptance Criteria:**

**Given** the spectator websocket already carries city ownership and victory metadata
**When** the live page renders an update
**Then** it shows a compact city-control summary by visible player/alliance plus the current victory threshold/countdown state without inventing a separate aggregation API.

**And Given** the victory race is inactive or ownership is sparse
**When** the spectator page renders
**Then** the UI shows deterministic explanatory empty states instead of misleading pseudo-rankings.

**And Given** the story ships
**When** focused client behavior tests plus the repo quality gate run
**Then** the spectator pressure board is verified from the shipped websocket/browser boundary and the docs/BMAD artifacts stay aligned.

## Epic 31: Live Strategic Map Readability

Turn the existing text-first live pages into legible strategic boards by rendering the canonical Britain map as a read-only SVG surface for both spectators and authenticated human players. Reuse the shipped websocket/public-detail contracts plus the canonical map definition already checked into the repo; do not invent a new live transport or hide business logic inside the client.

### Story 31.1: Add a shared read-only strategic SVG map to the live web client

As a spectator or human player,
I want the live page to render the Britain board as a readable strategic map,
So that I can understand city ownership, visible armies, and front-line pressure without decoding raw city lists.

**Acceptance Criteria:**

**Given** the repo already contains the canonical Britain map definition and the shipped live websocket payloads already expose city ownership plus visible army locations
**When** the public spectator page or authenticated human live page renders an update
**Then** the client shows a static SVG Britain map with deterministic city positions/edges and overlays for visible ownership, garrison/army presence, and current tick context without inventing a new live API.

**And Given** the viewer is an authenticated human player with fog-of-war limits
**When** the map renders partially visible or hidden state
**Then** the UI masks unknown details and shows only visibility-safe labels/markers instead of leaking spectator-level data.

**And Given** the live feed is disconnected, not active, or still waiting for the first snapshot
**When** the page renders the map panel
**Then** it shows deterministic read-only empty or not-live states rather than stale fabricated board state.

**And Given** the story ships
**When** focused browser-boundary client checks plus the repo quality gate run
**Then** the shared live map surface is verified from the shipped browser/websocket boundary and the docs/BMAD artifacts stay aligned.

### Story 31.2: Add click-assisted city inspection and order-draft helpers on the human live map

As an authenticated human player,
I want to use the live map as the entry point for city inspection and order drafting,
So that the existing order controls become faster and more legible without inventing browser-only game logic.

**Acceptance Criteria:**

**Given** the authenticated human live page already exposes order-draft forms and visibility-safe state
**When** the player clicks a visible city or army marker on the shared live map
**Then** the client highlights the selected entity, shows a compact visibility-safe city/army inspector, and pre-fills the existing order-draft controls with the selected IDs where that action is valid.

**And Given** the selected city, destination, or counterparty is not visible or is invalid for the current draft type
**When** the player interacts with the map
**Then** the UI preserves the current draft safely, avoids fabricating hidden data, and surfaces deterministic validation guidance instead of silently mutating the order.

**And Given** the story ships
**When** focused client behavior tests plus the repo quality gate run
**Then** the human live map interactions are verified from the browser boundary and remain aligned with the shipped HTTP/websocket order contract.

