# Story 11.2: Add realistic scenario-based smoke tests for deterministic gameplay flows

Status: done

## Story

As a game engine developer,
I want realistic multi-tick scenario tests,
So that the game rules are validated through meaningful gameplay situations rather than only isolated unit behaviors.

## Acceptance Criteria

1. Given deterministic headless simulation support and the implemented resolver phases, when realistic scenarios are executed across multiple ticks, then the tests cover representative flows including legal movement, invalid order rejection, attrition pressure, combat resolution, occupation/control handoff, build progression, siege degradation, and victory countdown behavior.
2. Given repeated runs of the same scenario fixtures, when the smoke suite executes, then the resulting snapshots, events, and asserted business outcomes are deterministic.
3. Given the scenario assertions, when the suite validates outcomes, then it checks externally meaningful gameplay results and invariants instead of brittle implementation-detail internals.

## Tasks / Subtasks

- [x] Design a concise but realistic smoke-scenario catalog. (AC: 1)
  - [x] Include at least one scenario each for movement, invalid orders, attrition, combat, occupation/control handoff, build progression, siege pressure, and victory countdown behavior.
  - [x] Reuse canonical map and match-state fixtures where possible instead of inventing alternate rulesets.
  - [x] Keep scenario names and fixtures stable enough for targeted reruns.
- [x] Implement behavior-first smoke tests at the simulation boundary. (AC: 1, 2, 3)
  - [x] Assert business outcomes that a game designer or agent client would care about.
  - [x] Avoid helper-only or implementation-detail assertions unless required to explain a business outcome.
  - [x] Verify repeated runs from the same inputs produce identical snapshots or equivalent externally visible outcomes.
- [x] Add a practical smoke-test execution path for local and CI use. (AC: 2, 3)
  - [x] Keep runtime modest enough to remain part of a normal quality workflow.
  - [x] Document or encode a stable command target for rerunning the smoke suite.
  - [x] Re-run the repository quality gate after the smoke suite lands.

## Dev Notes

- Prefer realistic state fixtures over synthetic micro-fixtures when they improve confidence without adding brittleness.
- This story is about broad gameplay confidence, not fuzzing or load testing.
- Use the headless engine boundary as the primary test surface unless the scenario truly requires API coverage.

### References

- `tests/test_simulation.py` for the current deterministic simulation boundary.
- `AGENTS.md` test pyramid guidance favoring meaningful boundary tests.
- `_bmad-output/planning-artifacts/epics.md` Story 11.2 acceptance criteria.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest --no-cov tests/test_simulation_smoke.py`
- `make smoke-test`
- `make quality`

### Completion Notes List

- Tightened the smoke assertions around externally visible gameplay outcomes instead of exact per-tick internal troop snapshots.
- Expanded deterministic coverage to include emitted simulation events alongside outcome digests.
- Moved scenario-specific expectations into the scenario catalog and asserted the full rejection set per tick.
- Kept `make smoke-test` as the narrow rerun path while relying on normal `pytest` discovery for `make quality` and `make ci`.

### File List

- `Makefile`
- `tests/test_simulation_smoke.py`
- `_bmad-output/implementation-artifacts/11-2-add-realistic-scenario-based-smoke-tests-for-deterministic-gameplay-flows.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-28 14:40 UTC: Drafted Story 11.2 for realistic deterministic gameplay smoke scenarios.
- 2026-03-29 06:24 UTC: Hardened the smoke suite after review by shifting assertions to gameplay outcomes, including event determinism, and clarifying the normal quality-gate path.
