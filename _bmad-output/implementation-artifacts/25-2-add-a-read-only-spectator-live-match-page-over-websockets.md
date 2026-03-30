# Story 25.2: Add a read-only spectator live match page over WebSockets

Status: done

## Story

As a spectator,
I want to watch the live match state update in the browser,
So that I can observe the war unfold without polling APIs manually.

## Acceptance Criteria

1. Given the running server already broadcasts spectator-safe WebSocket updates, when a user opens the spectator live page for an active match, then the client connects to the spectator WebSocket path, renders the initial payload, and updates the view when new tick broadcasts arrive.
2. Given the socket disconnects or the match is not active, when the client handles the condition, then it shows a deterministic reconnect or inactive-state message without silently freezing stale state.

## Tasks / Subtasks

- [x] Add typed spectator WebSocket payload parsing and connection helpers in the client. (AC: 1, 2)
  - [x] Mirror only the shipped spectator-safe envelope from `/ws/match/{match_id}?viewer=spectator`.
  - [x] Surface deterministic connection, inactive, and disconnect states.
- [x] Build a read-only live spectator page linked from the public match detail view. (AC: 1)
  - [x] Reuse the existing session bootstrap shell without requiring auth.
  - [x] Render a text-first live state summary from the spectator envelope and update it on each tick.
- [x] Add behavior-first tests and verification for reconnect/inactive handling. (AC: 2)
  - [x] Cover initial render, tick updates, disconnect/error messaging, and inactive-match affordances.
  - [x] Re-run client checks plus the repo quality gate after the story lands.

## Dev Notes

- Consume the already-shipped server WebSocket contract; do not invent a parallel polling endpoint.
- Keep the spectator view read-only and text-first. No map rendering or player-only controls in this story.
- Treat lobby/paused/completed matches as unsupported for the live spectator page unless the shipped runtime behavior proves otherwise.
- Link from Story 25.1's public match detail page so the discovery funnel remains public-first.

### Project Structure Notes

- Likely paths: `client/src/app/matches/[matchId]/live/page.tsx`, `client/src/components/matches/`, and `client/src/lib/`.
- The existing `/matches/[matchId]` page should gain the smallest coherent affordance into the live spectator route.

### References

- `core-architecture.md#2.2 Web Client (Next.js)`
- `core-architecture.md#2.1 Game Server (FastAPI)`
- `_bmad-output/planning-artifacts/epics.md#Story 25.2: Add a read-only spectator live match page over WebSockets`
- `_bmad-output/implementation-artifacts/18-3-broadcast-live-match-updates-over-websockets-for-human-clients-and-spectators.md`
- `_bmad-output/implementation-artifacts/25-1-add-a-public-match-detail-page-in-the-web-client.md`

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

- `cd client && npm test -- --run src/lib/api.test.ts` (red, then green)
- `cd client && npm test -- --run src/components/matches/match-live-view.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/match-detail.test.tsx` (red, then green)
- `cd client && npm run build`
- `make client-lint`
- `make client-test`
- `make client-build`

### Completion Notes List

- Added narrow typed spectator websocket helpers in the client for `/ws/match/{match_id}?viewer=spectator`, including deterministic payload parsing and URL building from the configured public session base URL.
- Added a public `/matches/[matchId]/live` route that waits for session hydration, fetches the existing public match detail to gate on active status, and only then opens the spectator websocket.
- Rendered the spectator live page as a small text-first public view that shows the latest tick snapshot and clearly marks the page as `Not live` after disconnect/error instead of silently freezing stale data.
- Linked the existing public match detail page to the new live spectator route.
- Verified the story with focused client tests plus `make client-lint`, `make client-test`, and `make client-build`.

### File List

- `_bmad-output/implementation-artifacts/25-2-add-a-read-only-spectator-live-match-page-over-websockets.md`
- `client/src/app/matches/[matchId]/live/page.tsx`
- `client/src/components/matches/match-detail.test.tsx`
- `client/src/components/matches/match-detail.tsx`
- `client/src/components/matches/match-live-view.test.tsx`
- `client/src/components/matches/match-live-view.tsx`
- `client/src/components/matches/public-match-live-page.test.tsx`
- `client/src/components/matches/public-match-live-page.tsx`
- `client/src/lib/api.test.ts`
- `client/src/lib/api.ts`
- `client/src/lib/types.ts`
