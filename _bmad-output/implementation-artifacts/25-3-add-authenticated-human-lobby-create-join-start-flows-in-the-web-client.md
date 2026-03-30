# Story 25.3: Add authenticated human lobby create/join/start flows in the web client

Status: drafted

## Story

As a human player,
I want to create, join, and start a lobby from the browser,
So that I can enter matches through the same product surface instead of relying on agent SDK tools.

## Acceptance Criteria

1. Given the browser has authenticated human access and the server already supports lobby lifecycle mutations, when a player uses the client lobby actions, then the UI calls the existing public routes for create, join, and creator-only start without inventing a parallel backend path.
2. Given domain errors occur such as invalid auth, not-ready, or forbidden start, when the action fails, then the client surfaces the structured error clearly and does not leave optimistic state that disagrees with the server.

## Tasks / Subtasks

- [ ] Add typed authenticated lobby lifecycle HTTP helpers in the client. (AC: 1, 2)
- [ ] Replace the authenticated placeholder route with create/join/start lobby flows. (AC: 1)
- [ ] Add behavior-first tests for success and structured error handling. (AC: 2)
- [ ] Re-run client checks plus the repo quality gate after the story lands.

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

TBD

### Debug Log References

- TBD

### Completion Notes List

- TBD

### File List

- TBD
