# Story 11.3: Add a large-batch simulation regression harness with invariant checks

Status: drafted

## Story

As a game engine developer,
I want a batch-oriented simulation regression harness,
So that many deterministic scenarios can be exercised quickly to catch invalid states and rule regressions that single examples may miss.

## Acceptance Criteria

1. Given a collection of seeded or fixture-driven simulation inputs, when the regression harness executes a large batch of runs, then it completes within CI-friendly limits while checking for crashes, invalid references, impossible negative values, ownership/resource inconsistencies, and other documented state invariants.
2. Given a failing regression scenario, when the harness reports the failure, then it identifies the exact scenario or seed and the violated invariant clearly enough for reproduction.
3. Given repeated executions with the same batch inputs, when the harness runs again, then the pass/fail outcomes remain deterministic.

## Tasks / Subtasks

- [ ] Define the invariant set and batch input strategy. (AC: 1, 2, 3)
  - [ ] Document the invariants that should always hold for match state, orders, ownership, resources, and references.
  - [ ] Choose a stable mix of curated fixtures and generated/sequenced inputs.
  - [ ] Keep seeds or fixture identifiers explicit so failures are reproducible.
- [ ] Implement the regression harness and failure reporting. (AC: 1, 2)
  - [ ] Ensure each batch run reports which scenario/seed failed and which invariant was violated.
  - [ ] Keep the harness deterministic and independent of external services.
  - [ ] Avoid overbuilding a full fuzzing framework if a narrower deterministic harness is sufficient.
- [ ] Integrate the harness into local and CI-quality workflows. (AC: 1, 3)
  - [ ] Add a stable command path for running the regression batch alone.
  - [ ] Verify runtime stays practical for repeated execution.
  - [ ] Re-run the repository quality gate after the harness lands.

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

_TBD_

### Debug Log References

- _TBD_

### Completion Notes List

- _TBD_

### File List

- _TBD_

### Change Log

- 2026-03-28 14:40 UTC: Drafted Story 11.3 for deterministic batch regression and invariant validation.
