# Story 11.2: Add realistic scenario-based smoke tests for deterministic gameplay flows

Status: drafted

## Story

As a game engine developer,
I want realistic multi-tick scenario tests,
So that the game rules are validated through meaningful gameplay situations rather than only isolated unit behaviors.

## Acceptance Criteria

1. Given deterministic headless simulation support and the implemented resolver phases, when realistic scenarios are executed across multiple ticks, then the tests cover representative flows including legal movement, invalid order rejection, attrition pressure, combat resolution, occupation/control handoff, build progression, siege degradation, and victory countdown behavior.
2. Given repeated runs of the same scenario fixtures, when the smoke suite executes, then the resulting snapshots, events, and asserted business outcomes are deterministic.
3. Given the scenario assertions, when the suite validates outcomes, then it checks externally meaningful gameplay results and invariants instead of brittle implementation-detail internals.

## Tasks / Subtasks

- [ ] Design a concise but realistic smoke-scenario catalog. (AC: 1)
  - [ ] Include at least one scenario each for movement, invalid orders, attrition, combat, occupation/control handoff, build progression, siege pressure, and victory countdown behavior.
  - [ ] Reuse canonical map and match-state fixtures where possible instead of inventing alternate rulesets.
  - [ ] Keep scenario names and fixtures stable enough for targeted reruns.
- [ ] Implement behavior-first smoke tests at the simulation boundary. (AC: 1, 2, 3)
  - [ ] Assert business outcomes that a game designer or agent client would care about.
  - [ ] Avoid helper-only or implementation-detail assertions unless required to explain a business outcome.
  - [ ] Verify repeated runs from the same inputs produce identical snapshots or equivalent externally visible outcomes.
- [ ] Add a practical smoke-test execution path for local and CI use. (AC: 2, 3)
  - [ ] Keep runtime modest enough to remain part of a normal quality workflow.
  - [ ] Document or encode a stable command target for rerunning the smoke suite.
  - [ ] Re-run the repository quality gate after the smoke suite lands.

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

_TBD_

### Debug Log References

- _TBD_

### Completion Notes List

- _TBD_

### File List

- _TBD_

### Change Log

- 2026-03-28 14:40 UTC: Drafted Story 11.2 for realistic deterministic gameplay smoke scenarios.
