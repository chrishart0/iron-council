# Story 27.2: Add authenticated human treaty and alliance controls in the live web client

Status: drafted

## Story

As an authenticated human player,
I want to manage treaties and alliances from the live browser page,
So that the browser supports the core diplomatic actions needed for real human multiplayer matches.

## Acceptance Criteria

1. Given a joined authenticated human on the live match page and the server already supports treaty and alliance routes, when the player proposes or withdraws a treaty, creates an alliance, joins an alliance, or leaves their current alliance from the client, then the UI calls only the shipped authenticated treaty/alliance HTTP routes or existing command-envelope surface already defined by the backend, using the current live tick and existing payload contracts without inventing a browser-only mutation API.
2. Given domain errors occur such as invalid auth, invalid counterparty, duplicate treaty/alliance membership, creator/leader restrictions, or tick mismatch, when the action fails, then the client surfaces the structured error clearly, preserves the current draft/selection state for correction, and does not fabricate optimistic diplomatic state.
3. Given a treaty or alliance action succeeds, when the server accepts the request, then the client shows deterministic acceptance metadata while relying on the websocket refresh as the source of truth for the updated diplomatic state.
4. Given the story ships, when focused client behavior tests plus the repo quality gate run, then treaty/alliance controls are verified from the public browser/API boundary and the docs/BMAD artifacts stay aligned with the shipped route and payload contracts.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [ ] Add typed authenticated client helpers for treaty and alliance actions. (AC: 1, 2, 3)
- [ ] Extend the live page with text-first treaty/alliance action controls using only the shipped routes/contracts. (AC: 1, 2, 3)
- [ ] Add behavior-first tests covering success, structured-error handling, and websocket-source-of-truth semantics. (AC: 2, 3)
- [ ] Re-run focused client checks and the repo quality gate, then close docs/BMAD artifacts. (AC: 4)

## Dev Notes

- Follow Story 27.1; do not start until the live messaging surface is stable.
- Keep the UI deterministic and boring: no drag-and-drop diplomacy widgets, no speculative state, no extra backend routes.
- Prefer public player/alliance information already present in the websocket snapshot instead of adding extra background reads unless a real shipped contract gap is discovered.

### References

- `core-plan.md#7.2 Treaties`
- `core-plan.md#7.3 Alliances`
- `core-architecture.md#2.2 Web Client (Next.js)`
- `_bmad-output/planning-artifacts/epics.md#Story 27.2: Add authenticated human treaty and alliance controls in the live web client`
- `_bmad-output/implementation-artifacts/13-2-add-public-treaty-status-and-lifecycle-endpoints.md`
- `_bmad-output/implementation-artifacts/13-3-add-alliance-create-join-leave-endpoints-with-deterministic-status-views.md`
- `_bmad-output/implementation-artifacts/26-1-add-an-authenticated-human-live-match-page-over-the-player-websocket.md`
- `_bmad-output/implementation-artifacts/27-1-add-authenticated-human-live-messaging-controls-in-the-web-client.md`

## Complete Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Dev Agent Record

### Agent Model Used

Pending implementation.

### Debug Log References

- Pending.

### Completion Notes List

- Pending.

### File List

- Pending.
