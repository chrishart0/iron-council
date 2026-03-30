# Story 25.1: Add a public match-detail page in the web client

Status: done

## Story

As a spectator or prospective player,
I want a web detail page for one public match,
So that I can inspect a lobby or running match before deciding to watch or join.

## Acceptance Criteria

1. Given the server already exposes a compact public match-detail route, when a user opens the client detail page for a valid lobby, paused, or active match, then the page renders configuration and visible roster metadata without exposing fog-filtered state or private credentials.
2. Given an unknown or completed match id is requested, when the route resolves, then the page shows deterministic not-found or unsupported-state handling aligned with the public API contract.

## Tasks / Subtasks

- [x] Add typed client access to the existing public match-detail API contract. (AC: 1, 2)
  - [x] Mirror only the public fields already exposed by `GET /api/v1/matches/{match_id}`.
  - [x] Preserve deterministic parsing and transport-safe error handling.
- [x] Build a public match detail page and link into it from the existing browser. (AC: 1)
  - [x] Show match metadata and roster entries with competitor-kind labels.
  - [x] Keep the route public and read-only.
- [x] Add deterministic empty/error/not-found handling and verification. (AC: 2)
  - [x] Add behavior-first client tests for success and not-found/error states.
  - [x] Re-run client checks plus the repo quality gate after the story lands.

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

GPT-5 Codex

### Debug Log References

- RED: `cd client && npm test` failed before implementation because `fetchPublicMatchDetail`, `match-detail`, `public-match-detail-page`, and browse-to-detail links did not exist yet.
- Follow-up RED/GREEN: `cd client && npm test -- --run src/components/matches/match-detail.test.tsx`
- Verification: `make client-lint`
- Verification: `make client-test`
- Verification: `make client-build`
- Verification: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_local_dev_docs.py`
- Verification: `make quality`

### Completion Notes List

- Added a typed public match-detail client contract and fetch helper that consume only `GET /api/v1/matches/{match_id}` and map `match_not_found` into deterministic public not-found messaging.
- Added a public read-only `/matches/[matchId]` page that reuses the existing client session/bootstrap shell without requiring auth.
- Linked the existing public match browser rows into the new detail page and kept the UI text-first with visible roster metadata only.
- Added behavior-first client coverage for detail parsing, detail rendering, not-found/error handling, hydration behavior, and browse-to-detail linking.
- Follow-up fix: wrapped match metadata in a semantic `<dl>` matching the existing app-shell pattern and made public roster row keys collision-safe for duplicate display names and competitor kinds.
- Updated local-dev docs to mention navigating from `/matches` into `/matches/<match_id>`.

### File List

- `client/src/app/matches/[matchId]/page.tsx`
- `client/src/app/globals.css`
- `client/src/components/matches/match-browser.tsx`
- `client/src/components/matches/match-browser.test.tsx`
- `client/src/components/matches/match-detail.tsx`
- `client/src/components/matches/match-detail.test.tsx`
- `client/src/components/matches/public-match-detail-page.tsx`
- `client/src/lib/api.ts`
- `client/src/lib/api.test.ts`
- `client/src/lib/types.ts`
- `README.md`
- `tests/test_local_dev_docs.py`
- `_bmad-output/implementation-artifacts/25-1-add-a-public-match-detail-page-in-the-web-client.md`
