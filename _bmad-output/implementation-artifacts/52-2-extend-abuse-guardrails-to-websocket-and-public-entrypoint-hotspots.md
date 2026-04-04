# Story 52.2: Extend abuse guardrails to websocket and public-entrypoint hotspots

Status: done

## Story

As an operator of the public runtime,
I want the same abuse-control seam to cover websocket and public-entrypoint hotspots,
So that launch protection is not limited to authenticated writes while still staying small and local to the shipped server.

## Acceptance Criteria

1. Given Story 52.1 has already defined the settings-backed abuse-control seam, when repeated websocket handshake requests exceed the configured burst policy, then the server closes the connection with the existing close semantics instead of inventing a second limiter implementation.
2. Given Story 52.1 has already defined the settings-backed abuse-control seam, when selected public-entrypoint requests exceed the configured burst policy, then the server returns a structured `429` API error using the same local limiter semantics instead of introducing a second policy path.
3. Given this remains a launch-scope hardening slice, when the story ships, then it keeps the implementation boring, repo-convention aligned, and verified through focused boundary tests plus the smallest relevant smoke coverage.
4. Given the story ships, when focused verification and `make quality` run, then the checks pass and this BMAD artifact records the real commands and outcomes.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add focused public-boundary regressions for websocket handshake bursts and selected public-entrypoint throttling. (AC: 1, 2)
- [x] Extend the existing settings-backed abuse seam so websocket/public hotspots reuse the same local limiter behavior rather than adding a second implementation. (AC: 1, 2)
- [x] Apply the guardrail seam to the chosen public hotspots and websocket handshake path while preserving existing auth and close semantics. (AC: 1, 2, 3)
- [x] Re-run focused verification, a small real-process smoke path, and `make quality`, then record the real outcomes here. (AC: 3, 4)

## Dev Notes

- Keep the scope narrow: prefer the match websocket handshake plus the smallest honest set of public browse/runtime entrypoints that are real launch hotspots.
- Reuse the existing `ApiError` contract for HTTP throttling and preserve current websocket close behavior for non-throttling auth failures.
- Do not add distributed rate limiting, vendor middleware, or infra-scale load tooling.

### References

- `core-architecture.md#9. Key Technical Risks`
- `_bmad-output/planning-artifacts/epics.md#Epic 52: Runtime Abuse Guardrails`
- `docs/plans/2026-04-04-epic-52-runtime-abuse-guardrails.md`
- `_bmad-output/implementation-artifacts/52-1-add-authenticated-write-abuse-guardrails.md`
- `_bmad-output/implementation-artifacts/51-3-add-multi-match-load-validation-and-launch-readiness-smoke-path.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-04: Drafted Story 52.2 to extend the existing abuse seam to websocket handshakes and selected public runtime hotspots.
- 2026-04-04: Implemented shared public/websocket abuse throttling on `/api/v1/matches`, `/health/runtime`, and the shared match websocket handshake path while reusing the Story 52.1 limiter.

## Debug Log References

- Red phase:
  - `uv run --extra dev pytest -o addopts='' tests/api/test_authenticated_write_abuse.py -k 'public_match_list_route_rate_limits or runtime_health_route_rate_limits'`
    - Failed as expected before implementation: both new public hotspot tests returned `200` instead of `429`.
  - `uv run --extra dev pytest -o addopts='' tests/api/test_agent_api.py -k 'match_websocket_rate_limit_is_shared_by_canonical_and_legacy_routes'`
    - Failed as expected before implementation: second websocket handshake did not disconnect.
  - `uv run --extra dev pytest -o addopts='' tests/api/test_authenticated_write_abuse.py -k 'public_entrypoint_rate_limit_uses_direct_client_identity_over_forwarded_for'`
    - Failed as expected during review follow-up: the second `/api/v1/matches` request returned `200` when only `X-Forwarded-For` changed, proving the limiter still trusted spoofable forwarded identity.
  - `uv run --extra dev pytest -o addopts='' tests/api/test_agent_api.py -k 'match_websocket_rate_limit_applies_before_unknown_match_lookup'`
    - Failed as expected during review follow-up: an unknown-match websocket disconnect did not consume the burst allowance, so the next valid handshake still connected.
- Focused verification:
  - `uv run --extra dev pytest -o addopts='' tests/api/test_authenticated_write_abuse.py`
    - Passed: `7 passed in 1.58s`
  - `uv run --extra dev pytest -o addopts='' tests/api/test_agent_api.py -k 'list_matches_returns_stable_json_summaries or match_websocket_rejects_invalid_and_wrong_role_human_tokens or match_websocket_rejects_invalid_viewer_and_unknown_match or match_websocket_rate_limit_is_shared_by_canonical_and_legacy_routes or match_websocket_rate_limit_applies_before_unknown_match_lookup'`
    - Passed: `5 passed, 131 deselected in 0.73s`
- Neighboring real-process smoke:
  - `uv run --extra dev pytest --no-cov tests/e2e/test_api_smoke.py -k 'runtime_observability_status_smoke_reports_recovery_and_match_runtime_signals or match_websocket_smoke_broadcasts_initial_and_tick_updates_for_player_and_spectator'`
    - Passed: `2 passed, 17 deselected in 3.14s`
- Full gate:
  - `make quality`
    - Passed: server format/lint/mypy/pytest green, coverage `95.12%`, client lint/tests/build green.

## Completion Notes

- Reused the existing `AuthenticatedWriteAbuseGuard` limiter instead of creating a second abuse-control system.
- Added narrow public-read throttling for `/api/v1/matches` and `/health/runtime`, both returning structured `429` `ApiError` responses.
- Added websocket handshake throttling on the shared match websocket handler and normalized the legacy `/ws/matches/{match_id}` alias to the canonical route key so both paths share the same burst window.
- Preserved existing websocket auth and non-throttling close behavior by keeping the new check inside the existing websocket `ApiError` path.
- Tightened public/websocket network identity resolution to the direct socket client host for this repo instead of trusting spoofable `X-Forwarded-For`.
- Moved websocket handshake throttling ahead of match existence lookup so bursts against unknown match IDs consume the same limiter window.

## File List

- `_bmad-output/implementation-artifacts/52-2-extend-abuse-guardrails-to-websocket-and-public-entrypoint-hotspots.md`
- `server/api/abuse.py`
- `server/api/public_match_routes.py`
- `server/api/public_routes.py`
- `server/api/realtime_routes.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_authenticated_write_abuse.py`
