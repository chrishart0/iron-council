# Story 29.2: Add public completed-match history and replay inspection pages in the web client

Status: drafted

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

- [ ] Add typed public client request/response helpers for match history and single-tick replay reads. (AC: 1, 2)
- [ ] Add a read-only completed-match replay page with tick picker, snapshot metadata, and stable back-navigation. (AC: 1, 2)
- [ ] Add behavior-first tests covering successful history/replay reads plus not-found/unavailable states. (AC: 2)
- [ ] Re-run focused client checks and the repo quality gate, then close docs/BMAD artifacts. (AC: 3)

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

- [ ] Engineering / Architecture
- [ ] Product Owner
