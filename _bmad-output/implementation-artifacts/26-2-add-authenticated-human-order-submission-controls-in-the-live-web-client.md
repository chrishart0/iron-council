# Story 26.2: Add authenticated human order submission controls in the live web client

Status: ready

## Story

As an authenticated human player,
I want to queue and submit my orders from the browser live page,
So that I can actually play an active match through the shipped web client without falling back to agent-only tooling.

## Acceptance Criteria

1. Given a joined authenticated human on the live match page and the server already supports the authenticated command envelope, when the player drafts movement, recruitment, upgrade, or transfer orders and submits them, then the client posts the existing `/api/v1/matches/{id}/commands` route using the current live tick and the shipped order payload shape without inventing a new backend route.
2. Given the command request fails because auth is missing, the player is not joined, the tick is stale, or validation/domain rules reject the order, when the client handles the failure, then it surfaces the structured error clearly, keeps the player's draft intact for correction, and does not pretend the live state already changed.
3. Given the command request succeeds, when the server accepts the order envelope, then the client shows a deterministic accepted-for-tick confirmation from the public response while still relying on the websocket for authoritative state updates.
4. Given the story ships, when focused client behavior tests plus the repo quality gate run, then the order controls are verified from the browser boundary and the docs/BMAD artifacts stay aligned with the shipped command route and payload contract.

## Ready Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Tasks / Subtasks

- [ ] Add typed authenticated command-envelope request/response models plus a client helper for posting order-only command payloads. (AC: 1, 2, 3)
- [ ] Add a text-first order draft composer to the authenticated live page for movement, recruitment, upgrade, and transfer orders. (AC: 1, 2, 3)
- [ ] Add behavior-first tests covering success, stale-tick / structured-error handling, and auth guards. (AC: 2, 3)
- [ ] Re-run focused client checks and the repo quality gate, then close out docs/BMAD artifacts. (AC: 4)

## Dev Notes

- Reuse the existing session bootstrap shell and authenticated `/matches/[matchId]/play` route from Story 26.1.
- Consume only the shipped `/api/v1/matches/{id}/commands` route and existing order payload contracts; do not add a parallel backend route in this story.
- Keep the order UI boring and text-first. Do not overreach into SVG map interactions, drag-and-drop movement planning, or message/diplomacy writing yet.
- Preserve draft entries on failure, but prefer resetting the successfully accepted draft back to an empty slate after a confirmed acceptance response.
- This story must stay sequential after Story 26.1 because it touches the same client live-page, session, API, and type surfaces.

### References

- `core-plan.md#1.3 Target Experience`
- `core-plan.md#9.4 Play Modes`
- `core-architecture.md#2.2 Web Client (Next.js)`
- `core-architecture.md#3.4 Agent Order Payload`
- `core-architecture.md#4.2 Order Validation`
- `_bmad-output/planning-artifacts/epics.md#Story 26.2: Add authenticated human order submission controls in the live web client`
- `_bmad-output/implementation-artifacts/17-2-add-a-consolidated-authenticated-agent-command-endpoint.md`
- `_bmad-output/implementation-artifacts/26-1-add-an-authenticated-human-live-match-page-over-the-player-websocket.md`

## Complete Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Dev Agent Record

### Agent Model Used

TBD

### Debug Log References

- TBD

### Completion Notes List

- TBD

### File List

- TBD
