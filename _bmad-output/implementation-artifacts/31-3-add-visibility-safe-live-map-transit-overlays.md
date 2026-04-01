# Story 31.3: Add visibility-safe live map transit overlays

Status: done

## Story

As a spectator or authenticated human player,
I want the live strategic map to show when visible armies are marching and how long they have left,
So that I can understand frontline motion without decoding raw army lists or leaking hidden route details.

## Acceptance Criteria

1. Given the existing spectator and player websocket payloads already expose in-transit army fields such as `location`, `destination`, `path`, and `ticks_remaining`, when the shared live map renders a visible marching army, then it shows deterministic transit overlays and readable ETA copy derived only from those shipped fields rather than a new API or client-side routefinding.
2. Given an authenticated human player sees a partially visible army or a payload that omits route detail, when the map renders that army, then the UI preserves fog-of-war boundaries by masking exact route/destination geometry while still showing a deterministic marching/ETA indicator when safe.
3. Given no visible transit overlays exist or the live feed is offline, when the map panel renders, then it shows deterministic empty/not-live explanatory states instead of stale or fabricated marching paths.
4. Given the story ships, when focused browser-boundary client checks plus the repo quality gate run, then the marching overlays are verified from the shipped websocket/browser boundary and the docs/BMAD artifacts stay aligned.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add focused browser-boundary tests for visible transit overlays, spectator route/ETA copy, player fog-safe masking, and empty/not-live explanatory states. (AC: 1, 2, 3)
- [x] Extend the shared strategic map surface with read-only transit overlays and marching summaries derived only from existing visible army payload fields. (AC: 1, 3)
- [x] Keep the authenticated human live page visibility-safe by masking route geometry/copy whenever the payload exposes only partial army information while still surfacing safe marching/ETA context. (AC: 2, 3)
- [x] Re-run focused client verification plus the repo quality gate, then close docs/BMAD artifacts. (AC: 4)

## Dev Notes

- Keep this story sequential in one worktree. It touches the shared map component and both live page test surfaces.
- Reuse only the shipped spectator/player websocket payloads and the existing public match preload. Do not add a new route, query, or websocket field.
- Keep the implementation read-only. This story is about map readability, not new control affordances or path submission.
- Prefer deterministic overlay shapes and copy so browser tests stay robust.
- Never infer a hidden destination or reconstruct a path the payload does not expose. Unknown route detail must stay unknown.
- If the player payload exposes a destination or path only partially, prefer generic `march in progress` style copy over a potentially leaky pseudo-route.

### References

- `core-plan.md#3.3 Edges & Movement`
- `core-plan.md#Appendix: Design Principles`
- `core-architecture.md#2.2 Web Client (Next.js)`
- `core-architecture.md#5.3 WebSocket Protocol (Human Client)`
- `_bmad-output/planning-artifacts/epics.md#Epic 31: Live Strategic Map Readability`
- `_bmad-output/implementation-artifacts/31-1-add-a-shared-read-only-strategic-svg-map-to-the-live-web-client.md`
- `_bmad-output/implementation-artifacts/31-2-add-click-assisted-city-inspection-and-order-draft-helpers-on-the-human-live-map.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Debug Log References

- `cd client && npm test -- --run src/components/matches/match-live-map.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/human-match-live-page.test.tsx src/components/matches/match-live-view.test.tsx`
- `cd client && npm run build`
- `make quality`

## Completion Notes

- Extended the shared `MatchLiveMap` surface with deterministic transit overlays plus ETA summaries derived only from existing live websocket army fields (`location`, `destination`, `path`, `ticks_remaining`, `visibility`).
- Kept spectator transit rendering route-aware only when the public payload already exposes the full visible path, while the authenticated player surface falls back to visibility-safe `march in progress` copy whenever route details are partial or hidden.
- Added focused browser-boundary tests for shared-map overlays, spectator transit copy, player fog-safe masking, and the offline/no-transit explanatory states so stale marching paths do not persist after the feed drops.
- Updated the README live-page walkthrough to describe the shipped spectator transit overlays and the player-safe march indicators.

## Files

- `client/src/components/matches/match-live-map.tsx`
- `client/src/components/matches/match-live-map.test.tsx`
- `client/src/components/matches/match-live-view.tsx`
- `client/src/components/matches/match-live-view.test.tsx`
- `client/src/components/matches/human-match-live-page.tsx`
- `client/src/components/matches/human-match-live-page.test.tsx`
- `client/src/components/matches/public-match-live-page.test.tsx`
- `README.md`
- `_bmad-output/implementation-artifacts/31-3-add-visibility-safe-live-map-transit-overlays.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
