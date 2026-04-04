# Story 51.2: Add runtime observability for tick drift, websocket fanout, and restart recovery

Status: done

## Story

As an operator of the live runtime,
I want narrow observability around tick timing, websocket fanout, and restart recovery,
So that the first public launch can detect the most meaningful runtime-failure signals before they turn into silent gameplay drift.

## Acceptance Criteria

1. Given Story 51.1 has already defined the runtime package and environment contract, when the runtime is exercised under normal live-match behavior, then operators can see boring, trustworthy signals for tick drift, websocket connection or fanout behavior, and whether an active match resumed cleanly after restart without reading private implementation details.
2. Given this story is about exposing observability rather than proving launch scale, when the change ships, then it adds one narrow operator-facing signal surface that Story 51.3 can consume instead of inventing separate success criteria.
3. Given the story ships, when focused observability validation and the repo quality gate run, then the new checks pass and this BMAD artifact records the real commands and outcomes.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add focused failing expectations for tick-drift, websocket-fanout, and restart-recovery signals at the operator boundary. (AC: 1)
- [x] Expose one narrow signal surface for those runtime events without introducing a heavy observability framework. (AC: 1, 2)
- [x] Verify Story 51.3 can consume the same signal surface rather than redefining observability semantics. (AC: 2)
- [x] Run focused validation plus `make quality`, then update this artifact with the real results. (AC: 3)

## Dev Notes

- Keep the scope centered on operator-readable runtime signals, not dashboards or vendor integrations.
- Build on the packaged runtime and env contract from Story 51.1.
- Prefer one boring status or metrics seam over multiple partially overlapping surfaces.
- Do not broaden this story into multi-match/load harness work; that belongs in Story 51.3.

### References

- `core-architecture.md`
- `_bmad-output/planning-artifacts/epics.md#Story 51.2: Add runtime observability for tick drift, websocket fanout, and restart recovery`
- `docs/plans/2026-04-04-epic-51-production-readiness-and-launch-hardening.md`
- `_bmad-output/implementation-artifacts/51-1-add-deployable-runtime-packaging-env-contract-and-operator-runbook.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-04: Drafted Story 51.2 as the operator-observability follow-on once Story 51.1 defines the packaged runtime contract.
- 2026-04-04: Fixed review findings so `/health/runtime` keeps a narrow operator surface while reporting honest tick scheduling, websocket fanout, and startup recovery signals.

## Debug Log References

- `uv run pytest tests/api/test_runtime_observability.py -q` failed before test execution because the repo `pytest` addopts included `--cov` flags but the current `uv run` environment had not loaded the dev extras yet.
- `uv run --extra dev pytest --no-cov tests/api/test_runtime_observability.py -q` passed (`5 passed`).
- `uv run --extra dev pytest --no-cov tests/api/test_runtime_observability.py tests/test_runtime_contract_docs.py tests/e2e/test_api_smoke.py -k 'runtime_observability or runtime_status or runtime_contract or runtime_control or runtime_env_contract' -q` passed (`8 passed`).
- `make quality` passed after formatting/lint cleanup (`479 passed, 1 skipped`, coverage `95.32%`, client lint/test/build green).

## Completion Notes

- `server/runtime.py` now schedules against the next tick deadline instead of sleeping a full interval after each loop body, so `/health/runtime` drift stays tied to scheduler lateness while processing time remains a separate signal.
- `server/websocket.py` now lets payload-construction bugs fail as server errors instead of unregistering sockets and inflating dropped-connection counts.
- Focused coverage now proves startup recovery against a DB-backed resumed active match, plus the healthy-processing-time drift regression and payload-construction fanout honesty.
- `docs/operations/runtime-runbook.md` now reflects that Story 51.2 signals exist at `/health/runtime`.

## File List

- `_bmad-output/implementation-artifacts/51-2-add-runtime-observability-for-tick-drift-websocket-fanout-and-restart-recovery.md`
- `docs/operations/runtime-runbook.md`
- `server/main.py`
- `server/models/api.py`
- `server/runtime.py`
- `server/runtime_observability.py`
- `server/websocket.py`
- `server/api/public_routes.py`
- `tests/api/test_runtime_observability.py`
- `tests/e2e/test_api_smoke.py`
- `tests/test_runtime_contract_docs.py`
