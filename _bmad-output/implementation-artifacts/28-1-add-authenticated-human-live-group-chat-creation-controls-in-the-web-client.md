# Story 28.1: Add authenticated human live group-chat creation controls in the web client

Status: done

## Story

As an authenticated human player,
I want to create a new group chat and invite visible players from the live browser page,
So that I can start new private coalition conversations without leaving the shipped web client or relying on agent-only tooling.

## Acceptance Criteria

1. Given a joined authenticated human on the live match page and the server already supports authenticated group-chat creation, when the player enters a group-chat name, selects one or more visible other players, and submits the form, then the client posts only the existing `/api/v1/matches/{id}/group-chats` route with the current live tick and the shipped payload contract without inventing a browser-only mutation API or extra discovery route.
2. Given auth is missing, the player is not joined, the tick is stale, the chat name is invalid, or the invited players are rejected by the existing domain rules, when the creation request fails, then the client surfaces the structured error clearly, preserves the drafted name and invited-player selections for correction, and does not fabricate optimistic group-chat state.
3. Given the server accepts the group-chat creation request, when the response returns accepted metadata, then the client shows deterministic acceptance details from the response while continuing to rely on the websocket snapshot as the authoritative source for the visible group-chat list and subsequent message targets.
4. Given the story ships, when focused client behavior tests plus the repo quality gate run, then the human group-chat creation controls are verified from the public browser/API boundary and the docs/BMAD artifacts stay aligned with the shipped route and payload contract.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add typed authenticated client request/response helpers for group-chat creation submissions. (AC: 1, 2, 3)
- [x] Add a text-first live-page group-chat creation form using only the shipped route and websocket-derived invite candidates. (AC: 1, 2, 3)
- [x] Add behavior-first tests covering success, structured-error handling, draft preservation, and websocket-source-of-truth semantics. (AC: 2, 3)
- [x] Re-run focused client checks and the repo quality gate, then close docs/BMAD artifacts. (AC: 4)

## Dev Notes

- Reuse the existing `/matches/[matchId]/play` route, live websocket snapshot, and session bootstrap from Stories 26.1, 26.2, 27.1, and 27.2.
- Keep the UI boring and text-first. Do not add group-chat membership editing, player-profile lookups, or any extra backend reads in this story.
- Reuse the websocket snapshot as the authoritative source for visible players and visible group chats, but send writes only through the existing authenticated HTTP route.
- Preserve the chat name and selected invitees on failure; clear only the accepted creation draft after a confirmed acceptance response.
- This story should remain sequential because it touches the same live-page, API, and client type surfaces as the recent human live stories.

### References

- `core-plan.md#7.1 Messaging`
- `core-plan.md#9.4 Play Modes`
- `core-architecture.md#2.2 Web Client (Next.js)`
- `_bmad-output/planning-artifacts/epics.md#Story 28.1: Add authenticated human live group-chat creation controls in the web client`
- `_bmad-output/implementation-artifacts/16-1-add-authenticated-group-chat-creation-membership-and-message-workflows.md`
- `_bmad-output/implementation-artifacts/26-1-add-an-authenticated-human-live-match-page-over-the-player-websocket.md`
- `_bmad-output/implementation-artifacts/27-1-add-authenticated-human-live-messaging-controls-in-the-web-client.md`
- `_bmad-output/implementation-artifacts/27-2-add-authenticated-human-treaty-and-alliance-controls-in-the-live-web-client.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Dev Agent Record

### Agent Model Used

- GPT-5 Codex

### Debug Log References

- `cd client && npm test -- --run src/lib/api.test.ts src/components/matches/human-match-live-page.test.tsx`
- `cd client && npm run build`
- `make quality` (initially failed because `mypy` was missing in the fresh worktree environment)
- `uv sync --extra dev --frozen`
- `make quality`
- `2026-03-31 follow-up: cd client && npm test -- --run src/lib/api.test.ts src/components/matches/human-match-live-page.test.tsx`
- `2026-03-31 follow-up: cd client && npm run build`

### Completion Notes List

- Added a typed authenticated `submitGroupChatCreate()` helper that posts only to `/api/v1/matches/{id}/group-chats` and now uses a dedicated `GroupChatCreateError` path for transport/validation fallback handling.
- Added a text-first group-chat creation form to the authenticated live match page that derives invite candidates from the websocket snapshot, excludes the current player, and preserves the draft on submission errors.
- Successful submissions now show accepted `group_chat` metadata from the response while the visible group-chat list remains websocket-authoritative until a later snapshot includes the new chat.
- Updated client tests and README live-page docs to cover shipped group-chat creation behavior.
- Follow-up corrected the client/server tick-mismatch expectation to the shipped backend contract: HTTP 400 with `Group chat payload tick '<tick>' does not match current match tick '<tick>'.`
- Follow-up introduced a dedicated `GroupChatCreateError` path so group-chat creation fallback copy is specific to creation failures instead of message sending.
- Follow-up added explicit `apiBaseUrl` override coverage for `submitGroupChatCreate()`.

### File List

- `client/src/lib/types.ts`
- `client/src/lib/api.ts`
- `client/src/lib/api.test.ts`
- `client/src/components/matches/human-match-live-page.tsx`
- `client/src/components/matches/human-match-live-page.test.tsx`
- `README.md`
- `_bmad-output/implementation-artifacts/28-1-add-authenticated-human-live-group-chat-creation-controls-in-the-web-client.md`
