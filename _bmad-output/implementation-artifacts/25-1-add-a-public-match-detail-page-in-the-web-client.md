# Story 25.1: Add a public match-detail page in the web client

Status: ready-for-dev

## Story

As a spectator or prospective player,
I want a web detail page for one public match,
So that I can inspect a lobby or running match before deciding to watch or join.

## Acceptance Criteria

1. Given the server already exposes a compact public match-detail route, when a user opens the client detail page for a valid lobby, paused, or active match, then the page renders configuration and visible roster metadata without exposing fog-filtered state or private credentials.
2. Given an unknown or completed match id is requested, when the route resolves, then the page shows deterministic not-found or unsupported-state handling aligned with the public API contract.

## Tasks / Subtasks

- [ ] Add typed client access to the existing public match-detail API contract. (AC: 1, 2)
  - [ ] Mirror only the public fields already exposed by `GET /api/v1/matches/{match_id}`.
  - [ ] Preserve deterministic parsing and transport-safe error handling.
- [ ] Build a public match detail page and link into it from the existing browser. (AC: 1)
  - [ ] Show match metadata and roster entries with competitor-kind labels.
  - [ ] Keep the route public and read-only.
- [ ] Add deterministic empty/error/not-found handling and verification. (AC: 2)
  - [ ] Add behavior-first client tests for success and not-found/error states.
  - [ ] Re-run client checks plus the repo quality gate after the story lands.

## Dev Notes

- This story should consume the already-shipped public HTTP contract rather than inventing a new backend route.
- Keep the detail view boring and text-first; do not add a live WebSocket spectator pane yet.
- Unknown and completed matches should align with the server's current `match_not_found` public error behavior.
- Reuse the client session/bootstrap shell from Story 24.3 where helpful, but do not require auth for this route.

### Project Structure Notes

- Likely paths: `client/src/app/matches/[matchId]/page.tsx`, `client/src/components/matches/`, and `client/src/lib/`.
- The existing `/matches` page should gain links into the new detail view with the smallest coherent UI change.

### References

- `core-architecture.md#2.2 Web Client (Next.js)`
- `core-architecture.md#5.2 HTTP API Surface`
- `_bmad-output/planning-artifacts/epics.md#Story 25.1: Add a public match-detail page in the web client`
- `_bmad-output/implementation-artifacts/20-2-add-a-public-match-lobby-detail-read.md`
- `_bmad-output/implementation-artifacts/24-1-scaffold-a-next-js-client-and-public-match-browser.md`

## Dev Agent Record

### Agent Model Used

Pending

### Debug Log References

- Pending

### Completion Notes List

- Pending

### File List

- Pending
