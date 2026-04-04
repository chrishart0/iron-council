# Story 52.3: Document and validate the launch abuse-control contract

Status: done

## Story

As an operator and maintainer,
I want the runtime docs and launch smoke path to describe the shipped abuse-control knobs honestly,
So that operators know what protections exist and the repo validation path proves those settings remain wired after future changes.

## Acceptance Criteria

1. Given Stories 52.1 and 52.2 have introduced concrete abuse-control knobs and behaviors, when the runtime env contract, runbook, and README are updated, then the docs explain the shipped protections honestly without implying CDN, WAF, or distributed controls the repo does not provide.
2. Given launch-readiness validation already exists from Epic 51, when Story 52.3 finishes, then it reuses that documentation and smoke path where practical instead of inventing a disconnected verification workflow.
3. Given the story ships, when docs regressions plus the relevant launch/readiness smoke path and `make quality` run, then the checks pass and this BMAD artifact records the real commands and outcomes.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Update README, runtime env contract, runtime runbook, and env example with the shipped abuse-control knobs and honest launch posture. (AC: 1)
- [x] Add or extend docs regression coverage and the smallest relevant launch/readiness smoke assertion so the runtime validation path proves the abuse controls remain wired. (AC: 2)
- [x] Re-run docs-focused verification, launch/readiness smoke coverage, and `make quality`, then record the real outcomes here. (AC: 3)

## Dev Notes

- Reuse the launch-readiness/runtime-control surfaces introduced in Epic 51 instead of inventing new operator workflows.
- Keep docs explicit that the shipped protections are local in-process burst limits and request-size controls, not distributed platform defenses.
- Prefer boundary-level tests that pin the visible contract rather than internals of the limiter implementation.

### References

- `core-architecture.md#9. Key Technical Risks`
- `_bmad-output/planning-artifacts/epics.md#Epic 52: Runtime Abuse Guardrails`
- `docs/plans/2026-04-04-epic-52-runtime-abuse-guardrails.md`
- `_bmad-output/implementation-artifacts/52-1-add-authenticated-write-abuse-guardrails.md`
- `_bmad-output/implementation-artifacts/52-2-extend-abuse-guardrails-to-websocket-and-public-entrypoint-hotspots.md`
- `_bmad-output/implementation-artifacts/51-1-add-deployable-runtime-packaging-env-contract-and-operator-runbook.md`
- `_bmad-output/implementation-artifacts/51-3-add-multi-match-load-validation-and-launch-readiness-smoke-path.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-04: Drafted Story 52.3 to fold the shipped abuse-control contract into launch docs and readiness validation.
- 2026-04-04: Updated the runtime docs and launch-readiness smoke path to describe and verify the shipped local abuse-control contract honestly.

## Debug Log References

- Red phase:
  - `source .venv/bin/activate && uv run pytest --no-cov tests/test_runtime_contract_docs.py tests/e2e/test_launch_readiness_smoke.py -k 'runtime_env_contract_and_runbook_stay_in_sync_with_checked_in_runtime_artifacts or packaged_runtime_launch_readiness_smoke_exposes_server_local_runtime_burst_limit' -q`
    - Failed before the docs/test updates because the runtime docs did not yet describe the public/websocket abuse posture and the packaged launch-readiness smoke lacked a concrete burst-limit assertion.
- Focused verification:
  - `source .venv/bin/activate && uv run pytest --no-cov tests/test_runtime_contract_docs.py tests/e2e/test_launch_readiness_smoke.py -k 'runtime_env_contract_and_runbook_stay_in_sync_with_checked_in_runtime_artifacts or packaged_runtime_launch_readiness_smoke_exposes_server_local_runtime_burst_limit' -q`
    - Passed: `2 passed`.
- Full gate:
  - `source .venv/bin/activate && make quality`
    - Passed: server format/lint/mypy/pytest green, coverage `95.20%`, client lint/tests/build green.

## Completion Notes

- Updated README, docs index, runtime env contract, runtime runbook, and `env.runtime.example` so the shipped launch posture now explicitly says the abuse controls are local in-process limits reused across authenticated writes, selected public HTTP hotspots, and match websocket handshakes.
- Added docs regressions that pin the new operator language and env-example guidance.
- Extended the packaged launch-readiness smoke path with one narrow real-runtime assertion that the configured burst limit is actually enforced on `/health/runtime`, reusing the existing runtime-control/server path instead of adding a separate abuse-only workflow.

## File List

- `_bmad-output/implementation-artifacts/52-3-document-and-validate-the-launch-abuse-control-contract.md`
- `README.md`
- `docs/index.md`
- `docs/operations/runtime-env-contract.md`
- `docs/operations/runtime-runbook.md`
- `env.runtime.example`
- `tests/e2e/test_launch_readiness_smoke.py`
- `tests/test_runtime_contract_docs.py`
