# Story 31.1: Add a shared read-only strategic SVG map to the live web client

Status: done

## Story

As a spectator or human player,
I want the live page to render the Britain board as a readable strategic map,
So that I can understand city ownership, visible armies, and front-line pressure without decoding raw city lists.

## Acceptance Criteria

1. Given the repo already contains the canonical Britain map definition and the shipped live websocket payloads already expose city ownership plus visible army locations, when the public spectator page or authenticated human live page renders an update, then the client shows a static SVG Britain map with deterministic city positions/edges and overlays for visible ownership, garrison/army presence, and current tick context without inventing a new live API.
2. Given the viewer is an authenticated human player with fog-of-war limits, when the map renders partially visible or hidden state, then the UI masks unknown details and shows only visibility-safe labels/markers instead of leaking spectator-level data.
3. Given the live feed is disconnected, not active, or still waiting for the first snapshot, when the page renders the map panel, then it shows deterministic read-only empty or not-live states rather than stale fabricated board state.
4. Given the story ships, when focused browser-boundary client checks plus the repo quality gate run, then the shared live map surface is verified from the shipped browser/websocket boundary and the docs/BMAD artifacts stay aligned.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add focused client tests that pin a shared Britain SVG map surface on both the spectator and human live pages, including ownership labels, visibility-safe masking, and not-live empty states. (AC: 1, 2, 3)
- [x] Implement a shared read-only live map component that derives deterministic city positions/edges from the canonical Britain map definition already in the repo and overlays visibility-safe city/army markers from the shipped websocket payloads. (AC: 1, 2)
- [x] Wire the new map panel into both live pages without inventing a new transport surface or browser-only state source. (AC: 1, 3)
- [x] Re-run focused client verification plus the repo quality gate, then close docs/BMAD artifacts. (AC: 4)

## Dev Notes

- Keep this story sequential in one worktree. It touches shared client map rendering primitives plus both live-page shells.
- Reuse the canonical Britain map definition already committed in the repo. If the client needs build configuration to import the shared map artifact safely, keep that change minimal and documented.
- Keep the UI read-only. This story is about board readability, not clickable order input, animation, or a spectator-only aggregation API.
- Prefer deterministic ordering and deterministic SVG identifiers so browser tests remain stable.
- For authenticated human players, use only `visibility`, `owner`, visible army fields, and other shipped player-safe data. Unknown fields must render as explicit masked or unavailable state, not guessed values.
- Treat disconnected or not-yet-live states as first-class UX states inside the map panel rather than leaving a blank box.

### References

- `core-plan.md#3. Map & Territory`
- `core-plan.md#6.4 Fog of War`
- `core-architecture.md#2.2 Web Client (Next.js)`
- `core-architecture.md#3.2 Match State (JSONB)`
- `core-architecture.md#5.3 WebSocket Protocol (Human Client)`
- `server/data/map_uk_1900.json`
- `_bmad-output/planning-artifacts/epics.md#Story 31.1: Add a shared read-only strategic SVG map to the live web client`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Debug Log References

- `cd client && npm test -- --run src/components/matches/match-live-map.test.tsx src/components/matches/match-live-view.test.tsx src/components/matches/public-match-live-page.test.tsx src/components/matches/human-match-live-page.test.tsx`
- `cd client && npm run build`
- `make quality`
- Story 31.1 follow-up (2026-03-31): reproduced the public spectator disconnect regression where a post-snapshot socket error cleared the last envelope and showed the generic unavailable state; fixed `PublicMatchLivePage` to preserve the last spectator snapshot on websocket failure and keep the generic unavailable state only before the first valid payload.

## Completion Notes

- Added a shared read-only `MatchLiveMap` SVG panel for both spectator and authenticated player live pages, rendering the canonical Britain board from the checked-in `server/data/map_uk_1900.json` artifact through a small server-side layout loader.
- Spectator live updates now project readable ownership, garrison, and visible army overlays onto the shared board without adding a new live API.
- Human live updates reuse the same map surface while masking partial fog-of-war data as `Owner hidden`, `Garrison hidden`, and partial-army summaries instead of leaking spectator detail.
- Added focused browser-boundary tests for the shared map component plus both live-page shells, then verified `npm run build` and the full `make quality` gate in a fresh worktree after bootstrapping dev dependencies with `uv sync --extra dev --frozen`.
- Follow-up fix: preserved the last spectator websocket envelope when the live page disconnects after at least one valid payload, so the page now keeps the last map snapshot and renders the explicit `Live connection lost` recovery message instead of falling back to the generic unavailable state.

## Files

- `client/src/components/matches/match-live-map.tsx`
- `client/src/components/matches/match-live-map.test.tsx`
- `client/src/components/matches/match-live-view.tsx`
- `client/src/components/matches/public-match-live-page.tsx`
- `client/src/components/matches/public-match-live-page.test.tsx`
- `client/src/components/matches/human-match-live-page.tsx`
- `client/src/components/matches/human-match-live-page.test.tsx`
- `client/src/app/matches/[matchId]/live/page.tsx`
- `client/src/app/matches/[matchId]/play/page.tsx`
- `client/src/lib/britain-map.ts`
- `README.md`
- `_bmad-output/implementation-artifacts/31-1-add-a-shared-read-only-strategic-svg-map-to-the-live-web-client.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
