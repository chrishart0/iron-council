# Story 26.1: Add an authenticated human live match page over the player websocket

Status: done

## Story

As an authenticated human player,
I want a browser page for my live match feed,
So that I can observe my fog-filtered state, chat/diplomacy summaries, and tick updates through the same shipped player websocket contract used by the backend.

## Acceptance Criteria

1. Given a joined authenticated human and an active match, when the player opens the live match page in the client, then the UI connects to the existing `/ws/match/{id}?viewer=player&token=***` websocket path, renders the initial fog-filtered player envelope, and updates as new tick broadcasts arrive without inventing a parallel backend route.
2. Given the websocket payload includes player-safe state plus world/direct/group/treaty/alliance collections, when the client renders the live page, then it shows concise player-facing summaries derived from that existing contract and clearly identifies the authenticated player id currently being viewed.
3. Given auth is missing/invalid, the user is not joined to the match, the match is not active, or the socket disconnects, when the client handles the condition, then it surfaces a deterministic guard/error/reconnect state and preserves the last confirmed live snapshot instead of silently freezing or showing stale optimistic UI.
4. Given the story ships, when focused client behavior tests plus the repo quality gate run, then the human live page is verified from the public browser boundary and the docs/BMAD artifacts stay aligned with the shipped route and contract.

## Tasks / Subtasks

- [x] Add typed player websocket contracts and URL/parser helpers in the client API layer. (AC: 1, 2, 3)
- [x] Add the authenticated live match route/page and a player-oriented live view component. (AC: 1, 2, 3)
- [x] Add behavior-first tests covering happy path, auth/join guards, inactive match, and disconnect fallback. (AC: 1, 2, 3)
- [x] Re-run focused client checks and the repo quality gate, then close out docs/BMAD artifacts. (AC: 4)

## Dev Notes

- Reuse the existing session bootstrap shell and stored bearer-token session from Story 24.3.
- Reuse the already-shipped player websocket contract only; do not add a new backend transport or alternate player-live API in this story.
- Keep the live page text-first and boring. Do not overreach into interactive order-entry, map rendering, or message sending yet.
- Preserve the last confirmed live snapshot on disconnect/error rather than clearing the screen.
- This story should remain sequential after Story 25.3 because it touches the same client API/types/live-view surface as the spectator page and authenticated session flow.

### References

- `core-plan.md#1.3 Target Experience`
- `core-plan.md#7.1 Messaging`
- `core-plan.md#9.4 Play Modes`
- `core-architecture.md#2.2 Web Client (Next.js)`
- `core-architecture.md#5.2 WebSocket Flow`
- `_bmad-output/planning-artifacts/epics.md#Story 26.1: Add an authenticated human live match page over the player websocket`
- `_bmad-output/implementation-artifacts/24-2-add-real-human-jwt-authentication-for-http-and-websocket-paths.md`
- `_bmad-output/implementation-artifacts/24-3-add-client-side-auth-session-bootstrap-for-future-human-flows.md`
- `_bmad-output/implementation-artifacts/25-2-add-a-read-only-spectator-live-match-page-over-websockets.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `cd client && npm test -- --run src/lib/api.test.ts src/components/matches/human-match-live-page.test.tsx src/components/matches/match-detail.test.tsx`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_local_dev_docs.py`
- `cd client && npm run build`
- `make quality`

### Completion Notes List

- Added a typed player websocket contract plus player websocket URL/parser helpers alongside the existing spectator helpers.
- Added the authenticated `/matches/[matchId]/play` route and a text-first human live page that renders player-safe summaries for visible state, resources, movement, chat, treaties, and alliances.
- The live page now surfaces deterministic missing-auth, inactive-match, websocket auth-envelope, and known close-reason states including `human_not_joined`, while preserving the last confirmed snapshot on disconnect or malformed payloads.
- Added behavior-first regression coverage for hydration, happy-path live updates, missing token, inactive match, malformed payloads, websocket auth error envelopes, and not-joined close handling.
- Updated the public match detail page and README so the authenticated live page is discoverable from the shipped browser flow.

### File List

- `README.md`
- `client/src/app/matches/[matchId]/play/page.tsx`
- `client/src/components/matches/human-match-live-page.tsx`
- `client/src/components/matches/human-match-live-page.test.tsx`
- `client/src/components/matches/match-detail.tsx`
- `client/src/components/matches/match-detail.test.tsx`
- `client/src/lib/api.ts`
- `client/src/lib/api.test.ts`
- `client/src/lib/types.ts`
- `tests/test_local_dev_docs.py`
