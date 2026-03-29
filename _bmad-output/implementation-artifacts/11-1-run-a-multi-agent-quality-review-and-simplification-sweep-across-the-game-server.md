# Story 11.1: Run a multi-agent quality review and simplification sweep across the game server

Status: done

## Story

As a delivery lead,
I want multiple focused review agents to inspect the codebase in parallel,
So that correctness gaps, overcomplexity, weak tests, and convention drift are found and fixed before broader validation work proceeds.

## Acceptance Criteria

1. Given the current server, engine, API, and test suite, when multiple review agents inspect bounded slices of the codebase in parallel, then each review lane reports concrete findings for correctness, test quality, and maintainability without overlapping ownership chaotically.
2. Given critical or important findings from those review lanes, when remediation work is completed, then the affected code and tests are updated, the relevant verification commands pass, and the repo remains in a coherent shippable state.
3. Given the final review pass for the story, when the quality sweep is closed out, then it explicitly confirms overcomplexity, KISS, and by-the-book convention checks were performed and no unresolved high-severity issues remain.

## Tasks / Subtasks

- [x] Define parallel review lanes and ownership boundaries before dispatching implementers/reviewers. (AC: 1)
  - [x] Split review ownership into at least engine/resolver logic, API/contract boundaries, and test-quality/simplicity lanes.
  - [x] Keep each review lane in a separate worktree or isolated execution thread to avoid diff collisions.
  - [x] Record the review plan and expected verification commands for each lane.
- [x] Run focused review agents and collect actionable findings. (AC: 1, 3)
  - [x] Require each lane to report correctness risks, missing/weak tests, and simplification opportunities.
  - [x] Require explicit overcomplexity, KISS, and by-the-book convention checks in every review output.
  - [x] De-duplicate overlapping findings into a single remediation queue.
- [x] Fix accepted findings and re-verify the affected slices. (AC: 2, 3)
  - [x] Apply the smallest coherent fixes needed to address critical and important issues.
  - [x] Re-run relevant focused tests in the responsible lane before merge.
  - [x] Re-run the repository quality gate after the merged fix set lands.

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
- 2026-03-29 04:36 UTC: Planned three parallel review lanes (engine/resolver, API/persistence boundary, and test-quality/simplicity) and ran the full-quality gate baseline.
- 2026-03-29 04:38 UTC: Collected multi-agent review findings; identified a transfer-resolution correctness gap, local DB workflow/docs drift, and one implementation-detail-coupled simulation test.
- 2026-03-29 04:44 UTC: Remediated accepted transfer-order resolution via a dedicated Codex worktree and added behavior-first resolver coverage.
- 2026-03-29 04:42 UTC: Tightened local Postgres workflow documentation and added sync tests for README/default settings guidance.
- 2026-03-29 04:49 UTC: Replaced the brittle simulation import-topology assertion by removing the implementation-detail test during the simplification pass.
- 2026-03-29 04:50 UTC: Verified the remediation slice with `PYTHONPATH=. uv run --extra dev pytest --no-cov tests/test_resolver.py tests/test_order_validation.py tests/test_simulation.py tests/test_settings.py tests/test_local_dev_docs.py`.
- 2026-03-29 04:50 UTC: Re-ran `make quality` successfully after merging the remediation set.

### Completion Notes List

- Completed the planned three-lane quality sweep across engine/resolver logic, API/persistence boundaries, and overall test quality, then de-duplicated the findings into a focused remediation queue.
- Remediated the critical engine gap where accepted transfer orders were validated but never applied by the resolver, while preserving the next-tick-only recruitment budget behavior through build-phase ordering and validation.
- Tightened the local Postgres developer workflow so the documented default DSN, `.env.local` example, and README guidance align with the support-services stack, and documented the focused-test `--no-cov` escape hatch for the repo coverage gate.
- Removed a brittle simulation import-topology test because it locked in implementation details instead of public behavior, improving alignment with `AGENTS.md` behavior-first testing doctrine.
- Explicitly performed the closeout refinement checks required by Story 11.1: no unresolved high-severity findings remain, no overcomplexity or unnecessary abstraction was added, the final state is KISS/simple, and the changes remain by-the-book with repo conventions.

### File List

- `README.md`
- `env.local.example`
- `server/models/orders.py`
- `server/order_validation.py`
- `server/resolver.py`
- `server/settings.py`
- `tests/test_local_dev_docs.py`
- `tests/test_resolver.py`
- `tests/test_settings.py`
- `tests/test_simulation.py`

### Change Log

- 2026-03-28 14:40 UTC: Drafted Story 11.1 for parallel quality review and simplification hardening.
- 2026-03-28 15:46 UTC: Remediated the custom-map resolver/simulation hardcoding finding and added custom-map regression tests.
- 2026-03-29 04:50 UTC: Closed Story 11.1 after parallel review-lane remediation for transfer resolution, local DB workflow/docs alignment, and test-suite simplification.
