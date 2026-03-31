# Story 29.2: Add public completed-match history and replay inspection pages in the web client

Status: done

## Story

As a spectator or debugging user,
I want a browser replay inspector for one completed match,
So that I can review persisted tick history and inspect one authoritative replay snapshot at a time from the shipped public history APIs.

## Acceptance Criteria

1. Given a completed match with persisted `tick_log` history, when the browser opens the replay page and selects a tick, then the client fetches only the shipped `/api/v1/matches/{id}/history` and `/api/v1/matches/{id}/history/{tick}` routes, renders deterministic tick-picker metadata, and shows the selected persisted snapshot, orders, and events without inventing a websocket or browser-only replay API.
2. Given the match or tick is unknown, or the DB-backed history API is unavailable, when the browser loads the replay surface, then the client shows structured read-only error states with stable navigation back to completed-match browse pages.
3. Given the story ships, when focused client behavior tests plus the repo quality gate run, then the replay/history inspector is verified from the public browser/API boundary and the docs/BMAD artifacts stay aligned with the shipped route contracts.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add typed public client request/response helpers for match history and single-tick replay reads. (AC: 1, 2)
- [x] Add a read-only completed-match replay page with tick picker, snapshot metadata, and stable back-navigation. (AC: 1, 2)
- [x] Add behavior-first tests covering successful history/replay reads plus not-found/unavailable states. (AC: 2)
- [x] Re-run focused client checks and the repo quality gate, then close docs/BMAD artifacts. (AC: 3)

## Dev Notes

- Reuse the public completed-match navigation added in Story 29.1.
- Keep the replay viewer boring and text-first. Avoid visual map playback or client-side reconstruction in this story.
- The persisted history API is authoritative; do not blend websocket state into this read-only flow.
- Parallelism assessment: this story should follow Story 29.1 sequentially because both touch shared public navigation, client route structure, and replay-link contracts.

### References

- `core-plan.md#8.2 ELO & Ranking`
- `core-architecture.md#2.2 Web Client (Next.js)`
- `core-architecture.md#5.2 REST Endpoints (Agent API)`
- `_bmad-output/planning-artifacts/epics.md#Story 29.2: Add public completed-match history and replay inspection pages in the web client`
- `_bmad-output/implementation-artifacts/19-1-expose-persisted-tick-history-and-replay-snapshots.md`
- `_bmad-output/implementation-artifacts/19-2-add-public-leaderboard-and-completed-match-summary-reads.md`
- `_bmad-output/implementation-artifacts/29-1-add-public-leaderboard-and-completed-match-browse-pages-in-the-web-client.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Dev Agent Record

### Agent Model Used

- GPT-5 Codex

### Debug Log References

- `cd client && npm test -- --run src/lib/api.test.ts`
- `cd client && npm test -- --run src/components/public/match-history-page.test.tsx src/app/matches/[matchId]/history/page.test.tsx`
- `cd client && npm test -- --run src/lib/api.test.ts src/components/public/match-history-page.test.tsx src/app/matches/[matchId]/history/page.test.tsx src/components/public/completed-matches-page.test.tsx`
- `cd client && npm run build`
- `make quality`

### Completion Notes List

- Added narrow public client types plus read-only fetch helpers for `GET /api/v1/matches/{id}/history` and `GET /api/v1/matches/{id}/history/{tick}` with deterministic malformed/not-found/unavailable error handling.
- Replaced the placeholder `/matches/<match_id>/history` route with a real text-first replay inspector that waits for session hydration, renders persisted match metadata, links deterministic tick selections, and shows one authoritative stored snapshot/orders/events payload at a time.
- Added browser-boundary tests proving the page uses only the shipped public history routes, preserves stable navigation, and degrades cleanly for missing matches, missing ticks, and unavailable DB-backed history responses.
- Updated the README route docs and sprint tracking so the shipped public replay/history contract matches the actual browser surface.
- Simplification pass: kept the inspector boring and read-only—no websocket replay, no client-side playback engine, and no extra abstraction layer beyond narrow helpers plus one page component.

### File List

- `README.md`
- `_bmad-output/implementation-artifacts/29-2-add-public-completed-match-history-and-replay-inspection-pages-in-the-web-client.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `client/src/app/matches/[matchId]/history/page.tsx`
- `client/src/app/matches/[matchId]/history/page.test.tsx`
- `client/src/components/public/match-history-page.tsx`
- `client/src/components/public/match-history-page.test.tsx`
- `client/src/lib/api.ts`
- `client/src/lib/api.test.ts`
- `client/src/lib/types.ts`
- `docs/plans/2026-03-31-story-29-2-public-replay-history-pages.md`
