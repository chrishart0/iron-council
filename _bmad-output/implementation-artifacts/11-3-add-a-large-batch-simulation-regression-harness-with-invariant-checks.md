# Story 11.3: Add a large-batch simulation regression harness with invariant checks

Status: done

## Story

As a game engine developer,
I want a batch-oriented simulation regression harness,
So that many deterministic scenarios can be exercised quickly to catch invalid states and rule regressions that single examples may miss.

## Acceptance Criteria

1. Given a collection of seeded or fixture-driven simulation inputs, when the regression harness executes a large batch of runs, then it completes within CI-friendly limits while checking for crashes, invalid references, impossible negative values, ownership/resource inconsistencies, and other documented state invariants.
2. Given a failing regression scenario, when the harness reports the failure, then it identifies the exact scenario or seed and the violated invariant clearly enough for reproduction.
3. Given repeated executions with the same batch inputs, when the harness runs again, then the pass/fail outcomes remain deterministic.

## Tasks / Subtasks

- [x] Define the invariant set and batch input strategy. (AC: 1, 2, 3)
  - [x] Document the invariants that should always hold for match state, orders, ownership, resources, and references.
  - [x] Choose a stable mix of curated fixtures and generated/sequenced inputs.
  - [x] Keep seeds or fixture identifiers explicit so failures are reproducible.
- [x] Implement the regression harness and failure reporting. (AC: 1, 2)
  - [x] Ensure each batch run reports which scenario/seed failed and which invariant was violated.
  - [x] Keep the harness deterministic and independent of external services.
  - [x] Avoid overbuilding a full fuzzing framework if a narrower deterministic harness is sufficient.
- [x] Integrate the harness into local and CI-quality workflows. (AC: 1, 3)
  - [x] Add a stable command path for running the regression batch alone.
  - [x] Verify runtime stays practical for repeated execution.
  - [x] Re-run the repository quality gate after the harness lands.

## Dev Notes

- Prefer deterministic breadth over probabilistic randomness for the first regression harness.
- Capture failures in a form that a developer or Codex worker can rerun immediately.
- Keep the implementation simple: this is a confidence harness, not a new subsystem.

### References

- `tests/test_simulation.py` and resolver-focused tests for current deterministic assumptions.
- `AGENTS.md` guidance favoring stable, behavior-oriented tests.
- `_bmad-output/planning-artifacts/epics.md` Story 11.3 acceptance criteria.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv sync --extra dev --frozen`
- `uv run pytest --no-cov tests/test_simulation_regression.py::test_regression_harness_executes_declared_batch`
- `uv run pytest --no-cov tests/test_simulation_regression.py::test_regression_harness_is_deterministic_across_repeated_runs`
- `uv run pytest --no-cov tests/test_simulation_regression.py -q`
- `make regression-test`
- `make format`
- `make quality`

### Completion Notes List

- Added `server/simulation_regression.py` with a deterministic 12-scenario batch harness, invariant checks, failure records, and stable outcome digests.
- Added `tests/test_simulation_regression.py` covering batch execution, reproducible invariant reporting, repeated-run determinism, and malformed-state failure formatting.
- Tightened Story 11.3 regression assertions to pin the exact scenario ID list and expected `outcome_digest` values so deterministic but behaviorally wrong gameplay changes fail the suite.
- Added `make regression-test` as the stable targeted command path for rerunning only the regression harness.
- Kept the harness deterministic and CI-friendly by reusing `simulate_ticks` with validated per-tick orders and modest curated scenario families instead of fuzzing.

### File List

- `server/simulation_regression.py`
- `tests/test_simulation_regression.py`
- `Makefile`
- `_bmad-output/implementation-artifacts/11-3-add-a-large-batch-simulation-regression-harness-with-invariant-checks.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-28 14:40 UTC: Drafted Story 11.3 for deterministic batch regression and invariant validation.
- 2026-03-29 08:31 UTC: Marked story in progress for deterministic regression harness implementation.
- 2026-03-29 08:31 UTC: Implemented the deterministic batch regression harness, added invariant-focused tests and `make regression-test`, reran `make quality`, and marked the story done.
- 2026-03-29 09:05 UTC: Strengthened regression expectations to assert the exact scenario result set and pinned outcome digests from the public harness output.
