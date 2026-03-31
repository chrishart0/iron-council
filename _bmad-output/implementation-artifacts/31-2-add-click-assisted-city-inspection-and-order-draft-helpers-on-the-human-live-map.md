# Story 31.2: Add click-assisted city inspection and order-draft helpers on the human live map

Status: done

## Story

As an authenticated human player,
I want to use the live map as the entry point for city inspection and order drafting,
So that the existing order controls become faster and more legible without inventing browser-only game logic.

## Acceptance Criteria

1. Given the authenticated human live page already exposes order-draft forms and visibility-safe state, when the player clicks a visible city or army marker on the shared live map, then the client highlights the selected entity, shows a compact visibility-safe city/army inspector, and pre-fills the existing order-draft controls with the selected IDs where that action is valid.
2. Given the selected city, destination, or counterparty is not visible or is invalid for the current draft type, when the player interacts with the map, then the UI preserves the current draft safely, avoids fabricating hidden data, and surfaces deterministic validation guidance instead of silently mutating the order.
3. Given the story ships, when focused client behavior tests plus the repo quality gate run, then the human live map interactions are verified from the browser boundary and remain aligned with the shipped HTTP/websocket order contract.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add focused browser-boundary tests for clickable visible city and army map markers, inspector rendering, deterministic draft prefills, and invalid-selection guidance. (AC: 1, 2)
- [x] Extend the shared live map surface with optional selection/highlight affordances and click handlers that only expose already-visible city and army metadata to the authenticated human page. (AC: 1, 2)
- [x] Add a compact human-only map inspector plus click-assisted draft helpers that prefill movement, recruitment, upgrade, and transfer/treaty targets only when the current selection makes that action valid, while preserving existing drafts on invalid interactions. (AC: 1, 2)
- [x] Re-run focused client verification plus the repo quality gate, then close docs/BMAD artifacts. (AC: 3)

## Dev Notes

- Keep this story sequential in one worktree. It touches the shared map component, the authenticated human live page, and its focused browser-boundary tests.
- Reuse only the shipped authenticated websocket payload, existing public roster fetch, and the current `/api/v1/matches/{match_id}/commands` envelope. Do not add a new live API or browser-only game rules.
- Keep the map interactions visibility-safe. Only visible cities/armies may be selectable, and the inspector must render explicit hidden/unknown copy rather than guessing unavailable state.
- Keep prefills assistive rather than magical. Preserve user-entered drafts unless a field is blank or the helper is explicitly scoped to the currently selected draft row.
- Treat invalid or hidden selections as first-class UX states with deterministic guidance in the page, not silent no-ops.
- Prefer deterministic inspector copy and stable accessible names so browser tests stay robust.

### References

- `core-plan.md#3. Map & Territory`
- `core-plan.md#6.4 Fog of War`
- `core-architecture.md#2.2 Web Client (Next.js)`
- `core-architecture.md#5.3 WebSocket Protocol (Human Client)`
- `_bmad-output/planning-artifacts/epics.md#Story 31.2: Add click-assisted city inspection and order-draft helpers on the human live map`
- `_bmad-output/implementation-artifacts/26-2-add-authenticated-human-order-submission-controls-in-the-live-web-client.md`
- `_bmad-output/implementation-artifacts/31-1-add-a-shared-read-only-strategic-svg-map-to-the-live-web-client.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Debug Log References

- `cd client && npm ci`
- `cd client && npm test -- --run src/components/matches/human-match-live-page.test.tsx`
- `cd client && npm test -- --run src/components/matches/match-live-map.test.tsx src/components/matches/human-match-live-page.test.tsx`
- `cd client && npm run build`
- `uv sync --extra dev --frozen`
- `make quality`

## Completion Notes

- Added visible city/army marker selection to the shared strategic map with deterministic button labels, pressed state, and selection highlighting so the authenticated human live page can react to existing player-safe websocket data without changing transport contracts.
- Added a compact player-safe map inspector on the human live page that renders explicit `hidden or unknown` copy for partial information and preserves fog-of-war boundaries instead of inferring hidden state.
- Added explicit helper actions for movement, recruitment, upgrade, transfer, and treaty drafting that use the current selection only when it exposes a valid visible value, while leaving existing draft rows untouched and surfacing deterministic guidance on invalid interactions.
- Extended browser-boundary coverage around the shipped human live page/order workflow and updated the README live-player description to reflect the new assistive map interactions.

## Files

- `client/src/components/matches/match-live-map.tsx`
- `client/src/components/matches/match-live-map.test.tsx`
- `client/src/components/matches/match-live-view.tsx`
- `client/src/components/matches/human-match-live-page.tsx`
- `client/src/components/matches/human-match-live-page.test.tsx`
- `README.md`
- `_bmad-output/implementation-artifacts/31-2-add-click-assisted-city-inspection-and-order-draft-helpers-on-the-human-live-map.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
