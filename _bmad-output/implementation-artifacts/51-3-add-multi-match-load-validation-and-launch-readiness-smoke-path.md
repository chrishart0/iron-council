# Story 51.3: Add multi-match/load validation and launch-readiness smoke path

Status: done

## Story

As a maintainer preparing for public launch,
I want a small multi-match/load validation slice and one launch-readiness smoke path,
So that the packaged runtime is proven against realistic concurrent-match and restart scenarios instead of only single-match happy paths.

## Acceptance Criteria

1. Given Story 51.1 has defined the deployable runtime and environment contract, when the packaged server is exercised with multiple active matches, websocket subscribers, and restart or resume conditions, then the repo contains a focused validation path that proves the launch-critical behavior honestly without claiming large-scale benchmarking coverage.
2. Given Story 51.2 may already expose runtime signals, when this story validates restart, websocket, or concurrent-match behavior, then it consumes those same signals where available instead of inventing a second observability contract.
3. Given the story ships, when the launch-readiness validation path and repo quality gate run, then the checks pass and this BMAD artifact records the real commands and outcomes.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Define one small launch-readiness smoke path against the packaged runtime from Story 51.1. (AC: 1)
- [x] Add focused validation for a few concurrent active matches and websocket subscribers without drifting into large-scale performance benchmarking. (AC: 1)
- [x] Reuse Story 51.2 runtime signals when validating restart or websocket behavior, if those signals already exist. (AC: 2)
- [x] Run the launch-readiness slice plus `make quality`, then update this artifact with the real outcomes. (AC: 3)

## Dev Notes

- Keep the scope launch-confidence sized, not platform-benchmark sized.
- Prefer deterministic or tightly bounded smoke/load checks over noisy stress tests.
- This story validates the runtime contract; it should not redefine packaging or operator env assumptions from Story 51.1.
- If Story 51.2 is not complete yet, keep any temporary validation seams minimal and converge onto the shared signal surface later.

### References

- `core-architecture.md`
- `_bmad-output/planning-artifacts/epics.md#Story 51.3: Add multi-match/load validation and launch-readiness smoke path`
- `docs/plans/2026-04-04-epic-51-production-readiness-and-launch-hardening.md`
- `_bmad-output/implementation-artifacts/51-1-add-deployable-runtime-packaging-env-contract-and-operator-runbook.md`
- `_bmad-output/implementation-artifacts/51-2-add-runtime-observability-for-tick-drift-websocket-fanout-and-restart-recovery.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-04: Drafted Story 51.3 as the launch-readiness validation slice that can run after Story 51.1 and alongside Story 51.2.
- 2026-04-04: Added a packaged-runtime launch-readiness smoke path, a narrow `make launch-readiness-smoke` entrypoint, and runbook/README references that reuse `/health/runtime` instead of adding a second status contract.

## Debug Log References

- `uv run pytest --no-cov tests/e2e/test_launch_readiness_smoke.py tests/test_runtime_contract_docs.py -q` failed before test execution because the repo `pytest` addopts still expected the dev coverage extras in the fresh `uv run` environment.
- `uv run --extra dev pytest --override-ini "addopts= -q --strict-config --strict-markers" tests/e2e/test_launch_readiness_smoke.py tests/test_runtime_contract_docs.py` first failed with a bad patch artifact (`tests/test_runtime_contract_docs.py` had an accidental `++ /tmp/...` first line), then failed as intended on the missing `make launch-readiness-smoke` README/runbook wiring, and then passed (`3 passed`) after the target/docs landed.
- `make launch-readiness-smoke` passed (`1 passed`).
- `make quality` first failed on `ruff format --check` for `tests/e2e/test_launch_readiness_smoke.py`, then failed on one Ruff `E501` line-length error, then failed on mypy websocket/JSON typing in the new smoke test, and finally passed after those fixes (`480 passed, 1 skipped`, coverage `95.32%`, client lint/test/build green).

## Completion Notes

- Added one deterministic real-process smoke path at `tests/e2e/test_launch_readiness_smoke.py` that boots the checked-in `./scripts/runtime-control.sh server` entrypoint against a DB-backed runtime, promotes two seeded matches to active 1-second ticks, attaches websocket spectators to both, verifies `/health/runtime` startup recovery and fanout signals, and proves restart/resume against the same database.
- Added the narrow developer command `make launch-readiness-smoke` instead of expanding the quality workflow with a separate benchmark harness.
- Updated the README and runtime runbook so the operator/developer path for this story points at the packaged runtime entrypoint plus the shared `/health/runtime` contract from Story 51.2.

## File List

- `_bmad-output/implementation-artifacts/51-3-add-multi-match-load-validation-and-launch-readiness-smoke-path.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `Makefile`
- `README.md`
- `docs/operations/runtime-runbook.md`
- `tests/e2e/test_launch_readiness_smoke.py`
- `tests/test_runtime_contract_docs.py`
