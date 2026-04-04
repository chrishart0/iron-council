# Story 51.1: Add deployable runtime packaging, env contract, and operator runbook

Status: done

## Story

As an operator and maintainer of Iron Council,
I want one boring deployable runtime package plus an explicit environment contract and runbook,
So that the shipped server, client, and local support services can be started, checked, and recovered consistently outside the current developer-only context.

## Acceptance Criteria

1. Given `core-plan.md` and `core-architecture.md` already define the server, client, websocket, and persistence shape, when the first production-readiness story lands, then the repo contains at least one checked-in runnable packaging or startup artifact plus the required environment variables and startup assumptions for the server, client, and supporting services without overpromising full infra automation.
2. Given launch work will continue in later stories, when the operator runbook is written, then it covers startup order, health verification, websocket/runtime expectations, restart basics, and rollback or recovery guidance clearly enough that Stories 51.2 and 51.3 can build on the same runtime/env contract.
3. Given this story is about deployability rather than a full hosted platform rollout, when the scope is implemented, then it stays focused on boring packaging, documented env surfaces, and operator guidance for the shipped server/client/local-services stack without claiming autoscaling, HA orchestration, or managed observability the repo does not yet provide.
4. Given this story defines the runtime contract for the rest of Epic 51, when focused verification and the repo quality gate run, then the BMAD artifact records the real commands and outcomes and later stories can treat the runtime/env contract as the single source of truth.
5. Given this story is not docs-only, when it completes, then it leaves behind a checked-in runnable packaging or startup artifact rather than only prose about a possible deploy shape.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Inventory the current shipped runtime pieces and operator assumptions already implied by the repo docs, support tooling, and local services. (AC: 1)
- [x] Define one concrete deployable packaging shape and check in at least one runnable packaging or startup artifact for the FastAPI server, Next.js client, and required supporting services, keeping the deployment shape intentionally boring. (AC: 1, 3, 5)
- [x] Document the environment contract, including required vs. optional variables and local-only vs. hosted expectations, without promising secret-management automation the repo does not ship. (AC: 1, 3)
- [x] Write an operator runbook covering startup order, health checks, websocket/runtime expectations, restart behavior, and basic recovery or rollback actions. (AC: 2)
- [x] Add focused docs validation only where it honestly protects the most important runtime/env promises, then run the repo quality gate and update this artifact with the real verification results. (AC: 1, 2, 4)

## Dev Notes

- Keep this story planning-ready and launch-pragmatic. The target is a credible, documented deployment path, not a full production platform design.
- Treat the server runtime, client runtime, and persistence/auth dependency as separate deployable concerns that still need one shared environment contract.
- Prefer one explicit env contract surface over scattered variable references across docs.
- Treat runtime dependencies as the canonical term for external services the packaged server/client rely on.
- The runbook should cover server, client, and local support services used for development/demo operation, but it should not imply the repo ships a one-click cloud environment.
- Do not fold Story 51.2 observability work or Story 51.3 load validation work into this story beyond defining the contract they will rely on.

### References

- `core-plan.md`
- `core-architecture.md`
- `_bmad-output/planning-artifacts/epics.md#Story 51.1: Add deployable runtime packaging, env contract, and operator runbook`
- `docs/plans/2026-04-04-epic-51-production-readiness-and-launch-hardening.md`
- `docs/issues/public-readiness-follow-ups.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-04: Drafted Story 51.1 as the first production-readiness slice after Epic 50 closed, keeping the scope on boring deployable packaging, explicit env contracts, and operator guidance.
- 2026-04-04: Delivered the checked-in runtime launcher, explicit runtime env contract, operator runbook, and focused docs regression coverage; verified with focused pytest plus the full `make quality` gate.

## Debug Log References

- Focused verification: `uv run pytest --override-ini addopts=' -q --strict-config --strict-markers' tests/test_runtime_contract_docs.py tests/test_local_dev_docs.py` -> PASS (11 passed).
- Repo quality gate: `source .venv/bin/activate && make quality` -> PASS after bootstrapping the fresh worktree with `uv sync --all-extras --dev` and `cd client && npm ci` so mypy/client tooling were present on PATH.

## Completion Notes

- Added `scripts/runtime-control.sh` as the checked-in runtime/operator entrypoint for doctor, support-service, DB, server, and client commands without introducing containerized app automation.
- Added `env.runtime.example` plus `docs/operations/runtime-env-contract.md` as the single explicit environment contract for server, client, and runtime dependencies.
- Added `docs/operations/runtime-runbook.md` plus README/docs-index links so startup order, health checks, websocket expectations, restart basics, and rollback/recovery guidance are documented from one boring baseline.
- Added `tests/test_runtime_contract_docs.py` to keep the launcher help, doctor summary, runtime env example, and linked docs aligned with the shipped contract.

## File List

- `README.md`
- `docs/index.md`
- `docs/operations/runtime-env-contract.md`
- `docs/operations/runtime-runbook.md`
- `env.runtime.example`
- `scripts/runtime-control.sh`
- `tests/test_runtime_contract_docs.py`
- `_bmad-output/implementation-artifacts/51-1-add-deployable-runtime-packaging-env-contract-and-operator-runbook.md`
