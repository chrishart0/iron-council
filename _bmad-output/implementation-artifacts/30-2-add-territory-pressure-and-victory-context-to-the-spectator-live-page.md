# Story 30.2: Add territory pressure and victory context to the spectator live page

Status: done

## Story

As a spectator,
I want a compact territory and victory summary on the live page,
So that I can see who is leading and why the current political situation matters.

## Acceptance Criteria

1. Given the spectator websocket already carries city ownership and victory metadata, when the live page renders an update, then it shows a compact city-control summary by visible player/alliance plus the current victory threshold/countdown state without inventing a separate aggregation API.
2. Given the victory race is inactive or ownership is sparse, when the spectator page renders, then the UI shows deterministic explanatory empty states instead of misleading pseudo-rankings.
3. Given the story ships, when focused client behavior tests plus the repo quality gate run, then the spectator pressure board is verified from the shipped websocket/browser boundary and the docs/BMAD artifacts stay aligned.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add focused browser-boundary tests for territory-control summaries, alliance-aware labeling, and inactive victory-race empty states. (AC: 1, 2)
- [x] Implement a compact spectator pressure board in the existing live view by aggregating city owners from the shipped websocket payload and mapping player/alliance IDs through the already-fetched public roster plus alliance metadata. (AC: 1)
- [x] Render deterministic victory-context copy for active countdowns, inactive races, and sparse/no-territory states without inventing new rankings or write controls. (AC: 1, 2)
- [x] Re-run focused client verification plus the repo quality gate, then close docs/BMAD artifacts. (AC: 3)

## Dev Notes

- Keep this story sequential in one worktree. It should remain a narrow enhancement to the existing spectator live surface.
- Reuse only the shipped spectator websocket payload and the already-fetched public match roster. Do not add a new spectator aggregation endpoint.
- Keep the UI text-first and read-only. This story is about spectator comprehension, not map rendering or animation.
- Prefer deterministic ordering. Sort city-control summaries by owned-city count descending, then by resolved public label ascending as a stable tie-breaker.
- Treat `leading_alliance` as an opaque public identifier. When it matches a visible alliance record, render the alliance name; otherwise fall back deterministically to the raw ID or a neutral explanatory label.
- Avoid misleading “leaderboard” framing when the websocket snapshot is sparse. If no owned cities are visible, say so explicitly.

### References

- `core-plan.md#1.2 Design Pillars`
- `core-plan.md#8.1 Coalition Victory`
- `core-plan.md#Appendix: Design Principles`
- `core-architecture.md#2.2 Web Client (Next.js)`
- `core-architecture.md#5.3 WebSocket Protocol (Human Client)`
- `_bmad-output/planning-artifacts/epics.md#Story 30.2: Add territory pressure and victory context to the spectator live page`
- `_bmad-output/implementation-artifacts/30-1-add-a-spectator-situation-room-to-the-live-web-client.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Debug Log References

- `cd client && npm test -- --run src/components/matches/match-live-view.test.tsx src/components/matches/public-match-live-page.test.tsx`
- `cd client && npm run build`
- `make quality`

## Completion Notes

- Added a text-first spectator `Territory pressure` panel that groups visible city ownership by public alliance name when available, otherwise by the shipped public player label or raw ID, with deterministic ordering by cities held desc then label asc.
- Added a companion `Victory context` panel that explains active countdowns, inactive victory races, and sparse/no-territory snapshots without inventing a leaderboard or adding a new API.
- Kept the implementation client-only by deriving all summaries from the existing spectator websocket envelope plus the already-fetched public roster.
- Follow-up review fix: territory aggregation now keys by stable owner identity (`alliance:<id>` or `player:<id>`) while storing display labels separately, so unrelated owners with the same visible label do not merge.
- Follow-up review fix: inactive victory states no longer render `leads the victory race` copy, and the focused browser-boundary tests now scope territory and empty-state assertions to the relevant sections instead of relying on page-wide counts.

## Files

- `client/src/components/matches/match-live-view.tsx`
- `client/src/components/matches/match-live-view.test.tsx`
- `client/src/components/matches/public-match-live-page.test.tsx`
- `README.md`
- `core-architecture.md`
- `_bmad-output/implementation-artifacts/30-2-add-territory-pressure-and-victory-context-to-the-spectator-live-page.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
