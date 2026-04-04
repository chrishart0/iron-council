# Story 51.2: Add runtime observability for tick drift, websocket fanout, and restart recovery

Status: drafted

## Story

As an operator of the live runtime,
I want narrow observability around tick timing, websocket fanout, and restart recovery,
So that the first public launch can detect the most meaningful runtime-failure signals before they turn into silent gameplay drift.

## Acceptance Criteria

1. Given Story 51.1 has already defined the runtime package and environment contract, when the runtime is exercised under normal live-match behavior, then operators can see boring, trustworthy signals for tick drift, websocket connection or fanout behavior, and whether an active match resumed cleanly after restart without reading private implementation details.
2. Given this story is about exposing observability rather than proving launch scale, when the change ships, then it adds one narrow operator-facing signal surface that Story 51.3 can consume instead of inventing separate success criteria.
3. Given the story ships, when focused observability validation and the repo quality gate run, then the new checks pass and this BMAD artifact records the real commands and outcomes.

## Ready Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Tasks / Subtasks

- [ ] Add focused failing expectations for tick-drift, websocket-fanout, and restart-recovery signals at the operator boundary. (AC: 1)
- [ ] Expose one narrow signal surface for those runtime events without introducing a heavy observability framework. (AC: 1, 2)
- [ ] Verify Story 51.3 can consume the same signal surface rather than redefining observability semantics. (AC: 2)
- [ ] Run focused validation plus `make quality`, then update this artifact with the real results. (AC: 3)

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

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-04: Drafted Story 51.2 as the operator-observability follow-on once Story 51.1 defines the packaged runtime contract.

## Debug Log References

- None yet. Story not started.

## Completion Notes

- Pending implementation.

## File List

- `_bmad-output/implementation-artifacts/51-2-add-runtime-observability-for-tick-drift-websocket-fanout-and-restart-recovery.md`