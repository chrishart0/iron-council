# Story: 35.5 Extract authenticated treaty and alliance routes plus shared match-route helpers out of `server/api/authenticated_match_routes.py`

Status: done

## Story

As a server maintainer,
I want treaty/alliance route handlers and shared authenticated-match helper logic split into focused modules,
So that diplomacy and route-level validation can change without one remaining composition file owning the authenticated match write surface.

## Acceptance Criteria

1. `server/api/authenticated_match_routes.py` delegates authenticated treaty and alliance route registration to focused modules while preserving existing route paths, request/response models, auth dependencies, status codes, error mapping, and compatibility behavior for current imports/callers.
2. Treaty behavior remains unchanged: list/read access rules, joined-player gating, match-id validation, counterparty existence validation, self-target rejection, structured transition errors, and realtime broadcast side effects all stay the same.
3. Alliance behavior remains unchanged: list/read access rules, joined-player gating, match-id validation, structured transition errors, accepted response shape, and realtime broadcast side effects all stay the same.
4. Shared authenticated-match helper seams are simplified rather than fragmented: any shared response-schema helper or match-record/dependency plumbing introduced by the Epic 35 route splits is consolidated only where it reduces duplication without changing contracts or introducing new abstraction layers.
5. The story remains refactor-only: no HTTP/OpenAPI contract, auth semantics, websocket behavior, DB schema, runtime-loop behavior, or gameplay/diplomacy semantics change.
6. Focused authenticated API/process regressions covering treaty/alliance surfaces pass, along with the repo quality gate or the strongest repo-managed equivalent that can run in the worker environment.
7. The resulting structure is simpler than the starting point: `server/api/authenticated_match_routes.py` becomes a thin composition module (or disappears entirely if composition can move into a clearer stable surface without import drift), and duplicated helper seams are reduced rather than spread further.

## Tasks / Subtasks

- [ ] Pin current authenticated treaty/alliance behavior with focused regressions. (AC: 2, 3, 6)
- [ ] Extract treaty routes into a focused router module. (AC: 1, 2, 7)
- [ ] Extract alliance routes into a focused router module. (AC: 1, 3, 7)
- [ ] Reconcile shared authenticated-match helper seams so the final composition stays simpler, not more fragmented. (AC: 4, 7)
- [ ] Rewire `server/api/authenticated_match_routes.py` (or its stable export surface) to compose the extracted routes without contract drift. (AC: 1, 7)
- [ ] Run focused verification, simplification review, and the repo quality gate. (AC: 6, 7)
- [ ] Update sprint tracking and completion notes after merge. (AC: 6)

## Dev Notes

- This is the fifth and likely final delivery slice for Epic 35 in `_bmad-output/planning-artifacts/epics.md`.
- Treat this as a route-surface refactor only. Do not broaden into registry behavior changes, diplomacy-rule redesign, DB workflow changes, runtime-loop changes, or websocket payload changes beyond what is required to preserve current behavior.
- Keep the route surface boring: prefer small explicit route-builder modules and one obvious helper seam over generic factories or dependency-injection frameworks.
- Story 35.4 left a review-only note about duplicated `_authenticated_route_responses()` helpers across the authenticated match route modules; handle that here only if the consolidation is clearly simpler and contract-preserving.

## Dev Agent Record

### Debug Log

- `uv sync --all-extras --dev`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'openapi_declares_secured_match_route_contracts or treaty_lifecycle_reads_are_deterministic_and_world_announcements_are_public or treaty_actions_reject_invalid_authenticated_requests or alliance_lifecycle_reads_are_deterministic_and_update_membership or alliance_actions_reject_invalid_authenticated_requests'`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'briefing or treaty'`
- `make quality`
- Spec-compliance review: PASS
- Code-quality/simplification review: APPROVED

### Completion Notes

- Extracted treaty route registration into `server/api/authenticated_match_treaty_routes.py` and alliance route registration into `server/api/authenticated_match_alliance_routes.py` while preserving route paths, response models, auth dependencies, structured errors, and realtime broadcast semantics.
- Reduced `server/api/authenticated_match_routes.py` to a thin composition surface that now wires command, messaging, treaty, and alliance routers around one local match-record/auth dependency seam.
- Centralized the shared authenticated route response schema helper and callable aliases in `server/api/authenticated_match_route_helpers.py`, removing duplicated helper plumbing from the command and messaging route modules without adding new abstraction layers.
- Added focused OpenAPI regression coverage proving the treaty/alliance route schemas remain exposed on the secured authenticated match surface.
- Focused authenticated API regressions, focused real-process smoke coverage, full spec/quality review passes, and the full repo quality gate all passed.

### File List

- `_bmad-output/implementation-artifacts/35-5-extract-authenticated-treaty-and-alliance-routes-plus-shared-match-route-helpers-out-of-server-api-authenticated_match_routes-py.md`
- `server/api/authenticated_match_alliance_routes.py`
- `server/api/authenticated_match_command_routes.py`
- `server/api/authenticated_match_messaging_routes.py`
- `server/api/authenticated_match_route_helpers.py`
- `server/api/authenticated_match_routes.py`
- `server/api/authenticated_match_treaty_routes.py`
- `tests/api/test_agent_api.py`

### Change Log

- 2026-04-01: Drafted Story 35.5 as the next Epic 35 cleanup slice after completing Story 35.4.
- 2026-04-01: Completed the authenticated treaty/alliance route extraction, consolidated shared match-route helper plumbing, and passed focused regressions plus the full quality gate.
