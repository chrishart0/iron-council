# Story 11.1: Run a multi-agent quality review and simplification sweep across the game server

Status: in-progress

## Story

As a delivery lead,
I want multiple focused review agents to inspect the codebase in parallel,
So that correctness gaps, overcomplexity, weak tests, and convention drift are found and fixed before broader validation work proceeds.

## Acceptance Criteria

1. Given the current server, engine, API, and test suite, when multiple review agents inspect bounded slices of the codebase in parallel, then each review lane reports concrete findings for correctness, test quality, and maintainability without overlapping ownership chaotically.
2. Given critical or important findings from those review lanes, when remediation work is completed, then the affected code and tests are updated, the relevant verification commands pass, and the repo remains in a coherent shippable state.
3. Given the final review pass for the story, when the quality sweep is closed out, then it explicitly confirms overcomplexity, KISS, and by-the-book convention checks were performed and no unresolved high-severity issues remain.

## Tasks / Subtasks

- [ ] Define parallel review lanes and ownership boundaries before dispatching implementers/reviewers. (AC: 1)
  - [ ] Split review ownership into at least engine/resolver logic, API/contract boundaries, and test-quality/simplicity lanes.
  - [ ] Keep each review lane in a separate worktree or isolated execution thread to avoid diff collisions.
  - [ ] Record the review plan and expected verification commands for each lane.
- [ ] Run focused review agents and collect actionable findings. (AC: 1, 3)
  - [ ] Require each lane to report correctness risks, missing/weak tests, and simplification opportunities.
  - [ ] Require explicit overcomplexity, KISS, and by-the-book convention checks in every review output.
  - [ ] De-duplicate overlapping findings into a single remediation queue.
- [ ] Fix accepted findings and re-verify the affected slices. (AC: 2, 3)
  - [ ] Apply the smallest coherent fixes needed to address critical and important issues.
  - [ ] Re-run relevant focused tests in the responsible lane before merge.
  - [ ] Re-run the repository quality gate after the merged fix set lands.

## Dev Notes

- Treat this story as a structured QA hardening pass, not a pretext for uncontrolled refactoring.
- Favor simplification and clarity over architectural churn.
- Keep findings tied to user-visible behavior, domain correctness, or durable maintainability concerns.

### References

- `AGENTS.md` test pyramid and TDD guidance.
- `_bmad-output/planning-artifacts/epics.md` Story 11.1 acceptance criteria.
- Existing review/simplification expectations from the autonomous BMAD workflow.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-03-28 15:39 UTC: Added red-phase custom-map regression coverage for resolver and headless simulation.
- 2026-03-28 15:42 UTC: Updated resolver and simulation contracts to accept an explicit `MapDefinition`, defaulting to the UK map when omitted.
- 2026-03-28 15:45 UTC: Verified remediation with `PYTHONPATH=. uv run --extra dev pytest --no-cov tests/test_resolver.py tests/test_simulation.py`.
- 2026-03-28 15:46 UTC: Ran `make quality` successfully.

### Completion Notes List

- Remediated the critical review finding where resolver movement distance and siege adjacency implicitly loaded the UK map even when upstream initialization and order validation used a custom map.
- Preserved backward compatibility by keeping the public resolver and simulation APIs optional-map based and defaulting to `load_uk_1900_map()` when no map is supplied.
- Added behavior-first regression coverage proving a custom non-UK map can validate movement orders and then resolve/simulate them correctly, including siege adjacency for fortification degradation.
- Story remains in progress because this turn addressed a specific remediation item within the broader quality-sweep scope.

### File List

- `server/resolver.py`
- `server/simulation.py`
- `tests/test_resolver.py`
- `tests/test_simulation.py`

### Change Log

- 2026-03-28 14:40 UTC: Drafted Story 11.1 for parallel quality review and simplification hardening.
- 2026-03-28 15:46 UTC: Remediated the custom-map resolver/simulation hardcoding finding and added custom-map regression tests.
