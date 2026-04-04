# Epic 51 Production Readiness and Launch Hardening Implementation Plan

> **For Hermes:** keep this epic boring, contract-first, and launch-focused. Do not broaden into platform automation, autoscaling, or paid infrastructure work.

**Goal:** Add the smallest credible production-readiness slice after Epics 1-50: define one concrete deployable runtime packaging path and explicit environment contract, then harden runtime observability and launch-readiness validation around the shipped FastAPI, Next.js, and Postgres stack.

**Architecture:** Treat Epic 51 as operator-facing hardening, not product expansion. The server remains the source of truth for match runtime, websocket fanout, and restart recovery; the client remains a separately deployable Next.js surface; the database remains the durable persistence layer. The first story must add one concrete packaging or entrypoint shape plus the documented environment and operator contract before later stories add runtime metrics or heavier validation against that contract.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, asyncio runtime loop, Next.js 14, TypeScript, Supabase/Postgres, pytest smoke tests, repo Make quality harness, deployment docs/runbooks, environment-variable contracts.

---

## Parallelism and dependency notes

- **Must go first:** Story 51.1. Epic 51 should not guess at observability names, smoke commands, or operator actions before the runtime package and environment contract exist in one documented place.
- **Safe to run in parallel after 51.1:** Story 51.2 and Story 51.3. They both depend on the defined runtime/env contract, but they primarily touch different validation seams: observability/metrics vs. load/restart/smoke verification.
- **Must stay sequential inside each story:** define failing doc/test expectations first, verify the gap honestly, make the smallest change, rerun the focused slice, then rerun `make quality`.
- **Controller responsibility:** keep all three stories launch-scoped. Reject scope creep into autoscaling, billing, fleet orchestration, or major runtime redesign.

## Epic sequencing

1. **Story 51.1:** add deployable runtime packaging, env contract, and operator runbook.
2. **Story 51.2:** add runtime observability for tick drift, websocket fanout, and restart recovery.
3. **Story 51.3:** add multi-match/load validation and launch-readiness smoke path.

## Story breakdown

### Story 51.1: Add deployable runtime packaging, env contract, and operator runbook

**Objective:** Define one boring, reproducible way to run the shipped server, client, and local support services with an explicit environment contract and operator runbook.

**Why first:** Epic 51 needs one source of truth for deployable shape, required environment variables, local-vs-hosted assumptions, startup order, health checks, and rollback/recovery basics before any instrumentation or validation work can be trusted.

**Bite-sized tasks:**

1. Inventory the current real runtime pieces already implied by `core-architecture.md`, local support tooling, and shipped dev scripts.
2. Define the minimum deployable packaging shape and at least one checked-in runnable packaging or startup artifact for:
   - server runtime
   - client runtime
   - runtime dependencies
   - local support services or dev-only helpers
3. Write one explicit environment contract covering required, optional, local-only, and hosted-only variables without claiming secrets management or infra automation the repo does not ship.
4. Add an operator runbook covering startup order, health verification, websocket/runtime expectations, restart behavior, and basic failure triage.
5. Add narrow docs or docs tests that pin the most important contract promises, then record the real verification commands and outcomes in the story artifact.

**Implementation guardrail:** Story 51.1 is not complete if it only writes prose. It must leave behind at least one checked-in runnable packaging/startup artifact or operator entrypoint alongside the env contract and runbook.

### Story 51.2: Add runtime observability for tick drift, websocket fanout, and restart recovery

**Objective:** Make the running server honest about its most important launch-time failure modes by exposing operator-facing signals for tick scheduling drift, live websocket fanout behavior, and what happened after a process restart.

**Depends on:** Story 51.1 defining the runtime package, health surfaces, and environment names.

**Bite-sized tasks:**

1. Add focused failing regressions or smoke expectations for exposed observability signals rather than private helper behavior.
2. Surface boring runtime metrics/logging around:
   - scheduled tick vs. actual tick drift
   - per-match websocket connection or fanout counts
   - restart recovery and resumed active-match state
3. Keep the signal surface small and operator-readable; prefer one narrow status/metric seam over a broad observability framework.
4. Prove the signals through focused tests or running-app validation tied to the packaged runtime shape from 51.1 so Story 51.3 can consume those same signals rather than inventing separate success criteria.

### Story 51.3: Add multi-match/load validation and launch-readiness smoke path

**Objective:** Prove the packaged runtime can survive a small but honest launch-readiness scenario: multiple active matches, websocket subscribers, and restart/resume validation without inventing a full performance lab.

**Depends on:** Story 51.1 for the runtime/env contract. Can run in parallel with 51.2 once that contract exists.

**Bite-sized tasks:**

1. Define one small launch-readiness smoke path that exercises the packaged server/client/runtime shape.
2. Add focused validation for a few concurrent active matches rather than theoretical scale claims.
3. Include websocket and restart/recovery checks in the smoke path by consuming the signals exposed in Story 51.2 when available, rather than redefining observability surfaces here.
4. Keep the scope bounded to launch confidence, not long-haul benchmarking or distributed systems work.

## Expected deliverables

- One deployable runtime packaging path with an explicit environment contract and operator runbook.
- One small runtime observability seam that makes tick drift, websocket fanout, and restart recovery visible.
- One launch-readiness smoke path plus small multi-match/load validation aligned with the packaged runtime.

## Out of scope

- Autoscaling or multi-region deployment design
- Managed observability platform integration
- Full SRE incident tooling
- Large-scale load testing beyond a small launch-confidence slice
- Product feature expansion unrelated to runtime readiness
