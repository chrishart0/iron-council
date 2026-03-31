# Story 30.1: Add a spectator situation room to the live web client

Status: in-progress

## Story

As a spectator,
I want the live match page to show readable chat, treaty, and alliance context,
So that I can understand the political state of a live match without decoding raw player IDs or switching tools.

## Acceptance Criteria

1. Given the public live spectator page already fetches `/api/v1/matches/{match_id}` before opening the websocket, when the page renders roster metadata, then the public match-detail contract includes stable public `player_id` values alongside `display_name` and `competitor_kind` so the client can map live-event actor IDs to readable labels without inventing a second lookup API.
2. Given the spectator websocket delivers world messages, treaties, and alliances, when the live page renders a tick update, then it shows text-first read-only panels for recent world chat, treaty status, and alliance membership using roster display names where possible and deterministic raw-ID fallback otherwise.
3. Given those public panels have no data or the page is disconnected, when the user views the spectator page, then the UI shows explicit empty/not-live states rather than stale or fabricated diplomacy/chat context.
4. Given the story ships, when focused server/client checks plus the repo quality gate run, then the enriched spectator live surface is verified from the public API/browser boundary and the docs/BMAD artifacts stay aligned with the shipped contracts.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [ ] Extend the compact public match-detail roster contract with stable `player_id` values and update the server/API tests. (AC: 1)
- [ ] Reuse the fetched public roster map inside the spectator live page to render readable world-chat, treaty, and alliance panels from the shipped websocket payload. (AC: 2, 3)
- [ ] Add focused browser-boundary tests for readable label resolution, empty states, and disconnected-state behavior. (AC: 2, 3)
- [ ] Re-run focused verification plus the repo quality gate, then close docs/BMAD artifacts. (AC: 4)

## Dev Notes

- Reuse the already-shipped `/api/v1/matches/{match_id}` and `/ws/match/{match_id}?viewer=spectator` contracts. Do not add a spectator-only lookup endpoint.
- Keep the view boring and text-first. This story is about readability, not map rendering or animation.
- Maintain deterministic fallback behavior: if a roster row is missing for some actor ID, render the raw ID rather than hiding the event.
- Parallelism assessment: keep this story sequential in one worktree because it touches the shared public match-detail contract, client types, and the existing spectator live page.

### References

- `core-plan.md#1.1 Vision`
- `core-plan.md#4 Core Gameplay Loop`
- `core-architecture.md#2.2 Web Client (Next.js)`
- `core-architecture.md#5.2 REST Endpoints (Agent API)`
- `core-architecture.md#5.3 WebSocket Protocol (Human Client)`
- `_bmad-output/planning-artifacts/epics.md#Story 30.1: Add a spectator situation room to the live web client`
- `_bmad-output/implementation-artifacts/25-2-add-a-read-only-spectator-live-match-page-over-websockets.md`
- `docs/plans/2026-03-31-story-30-1-spectator-situation-room.md`

## Complete Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner
