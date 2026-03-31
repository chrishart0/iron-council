# Story 25.3: Add authenticated human lobby create/join/start flows in the web client

Status: done

## Story

As a human player,
I want to create, join, and start a lobby from the browser,
So that I can enter matches through the same product surface instead of relying on agent SDK tools.

## Acceptance Criteria

1. Given the browser has authenticated human access and the server already supports lobby lifecycle mutations, when a player uses the client lobby actions, then the UI calls the existing public routes for create, join, and creator-only start without inventing a parallel backend path.
2. Given domain errors occur such as invalid auth, not-ready, or forbidden start, when the action fails, then the client surfaces the structured error clearly and does not leave optimistic state that disagrees with the server.

## Tasks / Subtasks

- [x] Add typed authenticated lobby lifecycle HTTP helpers in the client. (AC: 1, 2)
- [x] Replace the authenticated placeholder route with create/join/start lobby flows. (AC: 1)
- [x] Add behavior-first tests for success and structured error handling. (AC: 2)
- [x] Re-run client checks plus the repo quality gate after the story lands.

## Dev Notes

- Reuse the existing session bootstrap shell and bearer-token session state from Story 24.3.
- Consume existing server routes only; do not add new backend API surface in this story unless review finds a real contract gap.
- Keep mutation flows boring and deterministic. Avoid optimistic state that can drift from the server.
- Expect overlap with the match browser/detail pages; sequence after Story 25.2 unless implementation review shows safe parallel isolation.

### References

- `core-architecture.md#2.2 Web Client (Next.js)`
- `_bmad-output/planning-artifacts/epics.md#Story 25.3: Add authenticated human lobby create/join/start flows in the web client`
- `_bmad-output/implementation-artifacts/21-1-add-an-authenticated-match-lobby-creation-endpoint.md`
- `_bmad-output/implementation-artifacts/22-1-add-an-authenticated-lobby-start-endpoint.md`
- `_bmad-output/implementation-artifacts/24-3-add-client-side-auth-session-bootstrap-for-future-human-flows.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'human and (lobby or start or join)'`
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -q`
- `cd client && npm test -- --run src/components/lobby/human-lobby-page.test.tsx src/components/navigation/protected-route.test.tsx src/lib/api.test.ts`
- `uv run pytest tests/api/test_agent_process_api.py::test_running_app_requires_authenticated_join_and_match_scoped_reads tests/test_db_registry.py::test_start_match_lobby_rejects_invalid_api_key_missing_match_and_paused_match -q`
- `make quality`

### Completion Notes List

- Follow-up fix preserved create/start auth error ordering so memory-mode requests without auth still return the historical auth failure instead of short-circuiting to service unavailable.
- Lobby page now renders structured lobby action failures with message, stable code, and status when available, while keeping last confirmed server state unchanged on failure.
- Added a page-level success test for the create-then-start lobby flow through the shipped start route.
- Regression follow-up restored the legacy unauthenticated `/matches/{id}/join` error contract for non-lobby seeded matches while keeping DB-backed human lobby joins on the mixed-auth path.
- Regression follow-up reordered DB lobby-start validation so invalid API keys fail before missing-match checks, preserving the historical `invalid_api_key` contract.

### File List

- `README.md`
- `_bmad-output/implementation-artifacts/25-3-add-authenticated-human-lobby-create-join-start-flows-in-the-web-client.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `client/src/app/globals.css`
- `client/src/app/lobby/page.tsx`
- `client/src/app/page.tsx`
- `client/src/components/lobby/human-lobby-page.tsx`
- `client/src/components/lobby/human-lobby-page.test.tsx`
- `client/src/lib/api.ts`
- `client/src/lib/api.test.ts`
- `client/src/lib/types.ts`
- `server/agent_registry.py`
- `server/db/registry.py`
- `server/main.py`
- `tests/api/test_agent_api.py`
- `tests/e2e/test_api_smoke.py`
- `tests/support.py`
