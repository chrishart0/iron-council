# Story: 35.4 Extract authenticated command and messaging routes out of `server/api/authenticated_match_routes.py`

Status: done

## Story

As a server maintainer,
I want the authenticated command envelope and match/group messaging routes moved into focused route modules,
So that command and collaboration changes do not require one oversized authenticated match router to own every write surface.

## Acceptance Criteria

1. `server/api/authenticated_match_routes.py` delegates authenticated command-envelope and messaging route registration to focused modules while preserving the existing route paths, request/response models, auth dependencies, status codes, broadcast behavior, and compatibility behavior for current imports/callers.
2. Command-envelope behavior remains unchanged: `/api/v1/matches/{match_id}/command` plus the hidden `/commands` alias preserve match-id validation, joined-player resolution, tick mismatch handling, structured error/status mapping, and the current “broadcast only when messages/treaties/alliance payloads are present” behavior.
3. Messaging behavior remains unchanged for inbox reads, world/direct message writes, group-chat listing/creation, and group-chat message listing/writes, including membership/visibility checks, structured validation errors, not-found/forbidden mappings, tick mismatch handling, and realtime broadcast side effects.
4. The story remains refactor-only: no HTTP/OpenAPI contract, auth semantics, websocket behavior, DB schema, runtime-loop behavior, or gameplay/messaging semantics change.
5. Focused authenticated API/process regressions covering command and messaging surfaces pass, along with the repo quality gate or the strongest repo-managed equivalent that can run in the worker environment.
6. The resulting structure is simpler than the starting point: command and messaging routes live behind clearly named route-builder modules and `server/api/authenticated_match_routes.py` shrinks into a thinner composition module.

## Tasks / Subtasks

- [ ] Pin current authenticated command and messaging behavior with focused regressions. (AC: 2, 3, 5)
- [ ] Extract command-envelope routes into a focused router module. (AC: 1, 2, 6)
- [ ] Extract messaging and group-chat routes into a focused router module. (AC: 1, 3, 6)
- [ ] Rewire `server/api/authenticated_match_routes.py` to compose the extracted routers without contract drift. (AC: 1, 6)
- [ ] Run focused verification, simplification review, and the repo quality gate. (AC: 5, 6)
- [ ] Update sprint tracking and completion notes after merge. (AC: 5)

## Dev Notes

- This is the fourth delivery slice for Epic 35 in `_bmad-output/planning-artifacts/epics.md`.
- Treat this as a route-surface refactor only. Do not broaden into auth redesign, registry behavior changes, DB workflow changes, runtime-loop changes, or websocket payload changes beyond what is required to preserve existing behavior.
- Keep the route surface boring: prefer small explicit route-builder modules and narrow helper reuse over new abstractions, base classes, or dependency-injection layers.
- Pay special attention to the authenticated command envelope endpoints plus the match/group messaging surfaces in `server/api/authenticated_match_routes.py`, including structured validation/error mapping and broadcast side effects.
- Story 35.5 should remain sequential after this work because it still needs to extract treaty/alliance routes from the same parent module.

## Dev Agent Record

### Debug Log

- `uv sync --extra dev --frozen`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'post_command_envelope or command_envelope or post_messages or group_chat or secured_match_route_contracts or phase_one_seams or orders_only_command_envelope_does_not_broadcast_match_refresh'`
- `uv run pytest --no-cov tests/api/test_agent_process_api.py -k 'command_envelope or messages'`
- `make quality`
- Spec-compliance review: PASS
- Code-quality/simplification review: APPROVED

### Completion Notes

- Extracted authenticated command-envelope registration into `server/api/authenticated_match_command_routes.py` and messaging/group-chat registration into `server/api/authenticated_match_messaging_routes.py` while preserving route paths, response models, auth dependencies, structured errors, and broadcast semantics.
- Reduced `server/api/authenticated_match_routes.py` to a thinner composition module that now delegates command and messaging surfaces while leaving treaty/alliance routes in place for the next Epic 35 slice.
- Added focused regressions proving the hidden `/commands` alias stays out of OpenAPI and that order-only command envelopes do not trigger a realtime match refresh broadcast.
- Focused authenticated API regressions, real-process message/command regressions, and the full repo quality gate all passed in the worker worktree.
- Minor review-only follow-up for Story 35.5: consider whether the duplicated `_authenticated_route_responses()` helper should be centralized once the remaining treaty/alliance extraction settles.

### File List

- `_bmad-output/implementation-artifacts/35-4-extract-authenticated-command-and-messaging-routes-out-of-server-api-authenticated_match_routes-py.md`
- `server/api/authenticated_match_command_routes.py`
- `server/api/authenticated_match_messaging_routes.py`
- `server/api/authenticated_match_routes.py`
- `tests/api/test_agent_api.py`

### Change Log

- 2026-04-01: Drafted Story 35.4 as the next Epic 35 authenticated match-route extraction slice after completing Story 35.3.
- 2026-04-01: Completed the authenticated command and messaging route extraction into focused router modules, added contract/broadcast regressions, and passed the repo quality gate.
