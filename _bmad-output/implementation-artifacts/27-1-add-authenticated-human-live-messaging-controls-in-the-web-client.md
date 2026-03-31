# Story 27.1: Add authenticated human live messaging controls in the web client

Status: drafted

## Story

As an authenticated human player,
I want to send world, direct, and group-chat messages from the live browser page,
So that I can participate in the same diplomacy and communication loop as agents without leaving the shipped web client.

## Acceptance Criteria

1. Given a joined authenticated human on the live match page and the server already supports authenticated message routes, when the player drafts a world message, a direct message to another visible player, or a group-chat message to a visible group chat and submits it, then the client posts only the existing `/api/v1/matches/{id}/messages` or `/api/v1/matches/{id}/group-chats/{group_chat_id}/messages` routes using the current live tick and the shipped payload contracts without inventing a parallel backend mutation path.
2. Given auth is missing, the user is not joined, the tick is stale, the message content is invalid, or the target chat/player is rejected by the domain rules, when the client handles the failure, then it surfaces the structured error clearly, preserves the player's draft for correction, and does not optimistically append a fake message to the live feed.
3. Given a message submission succeeds, when the server returns the accepted response, then the client shows a deterministic accepted-for-tick confirmation while continuing to rely on the websocket for the authoritative live message timeline.
4. Given the story ships, when focused client behavior tests plus the repo quality gate run, then the human live messaging controls are verified from the browser/API boundary and the docs/BMAD artifacts stay aligned with the shipped message routes and payloads.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [ ] Add typed authenticated client request/response helpers for match-message and group-chat-message submissions. (AC: 1, 2, 3)
- [ ] Add a text-first live-page message composer for world, direct, and group-chat messages using only the shipped routes. (AC: 1, 2, 3)
- [ ] Add behavior-first tests covering success, structured-error handling, and draft preservation at the browser boundary. (AC: 2, 3)
- [ ] Re-run focused client checks and the repo quality gate, then close docs/BMAD artifacts. (AC: 4)

## Dev Notes

- Reuse the existing `/matches/[matchId]/play` route, live websocket snapshot, and session bootstrap from Stories 26.1 and 26.2.
- Keep the UI boring and text-first. Do not add treaty/alliance controls, group-chat creation flows, or map-integrated chat affordances in this story.
- Reuse the websocket snapshot as the authoritative source for visible players and visible group chats, but send writes only through the existing authenticated HTTP routes.
- Preserve message drafts on failure; clear only the successfully accepted draft after a confirmed acceptance response.
- This story should remain sequential with Story 26.2 because it touches the same live-page, API, and client type surfaces.

### References

- `core-plan.md#7.1 Messaging`
- `core-plan.md#9.4 Play Modes`
- `core-architecture.md#2.2 Web Client (Next.js)`
- `_bmad-output/planning-artifacts/epics.md#Story 27.1: Add authenticated human live messaging controls in the web client`
- `_bmad-output/implementation-artifacts/13-1-add-agent-facing-match-message-inbox-and-send-endpoints.md`
- `_bmad-output/implementation-artifacts/16-1-add-authenticated-group-chat-creation-membership-and-message-workflows.md`
- `_bmad-output/implementation-artifacts/26-1-add-an-authenticated-human-live-match-page-over-the-player-websocket.md`
- `_bmad-output/implementation-artifacts/26-2-add-authenticated-human-order-submission-controls-in-the-live-web-client.md`

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
