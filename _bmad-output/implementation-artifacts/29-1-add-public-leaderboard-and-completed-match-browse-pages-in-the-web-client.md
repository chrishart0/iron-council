# Story 29.1: Add public leaderboard and completed-match browse pages in the web client

Status: done

## Story

As a prospective player or spectator,
I want browser pages for leaderboard standings and completed-match summaries,
So that I can discover strong competitors and recent finished games before joining a live match.

## Acceptance Criteria

1. Given the DB-backed server already exposes public leaderboard and completed-match summary routes, when the browser loads the new read-only pages, then the client fetches only the shipped `/api/v1/leaderboard` and `/api/v1/matches/completed` contracts, renders deterministic rankings and compact completed-match cards, and does not invent any browser-only aggregation API.
2. Given the server reports unavailable or malformed public-read payloads, when the page request fails, then the client surfaces a clear read-only error state without crashing and preserves obvious navigation back to the rest of the public browser.
3. Given a completed-match card is rendered, when a user wants deeper inspection, then the page exposes a stable link into the match-specific replay/history surface rather than embedding replay payloads directly into the browse response.
4. Given the story ships, when focused client behavior tests plus the repo quality gate run, then the leaderboard and completed-match browse flows are verified from the public browser/API boundary and the docs/BMAD artifacts stay aligned with the shipped route contracts.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add typed public client request/response helpers for leaderboard and completed-match reads. (AC: 1, 2)
- [x] Add read-only browser pages/components that render deterministic standings and compact completed-match cards. (AC: 1, 2, 3)
- [x] Add behavior-first tests covering success, malformed/unavailable payload handling, and replay-page linking. (AC: 2, 3)
- [x] Re-run focused client checks and the repo quality gate, then close docs/BMAD artifacts. (AC: 4)

## Dev Notes

- Reuse the existing public browser/session-bootstrap patterns from Stories 24.1, 25.1, and 28.1.
- Keep the UI boring and read-only. No filters, pagination, search, or browser-only derived ranking logic in this story.
- Reuse only the shipped `/api/v1/leaderboard` and `/api/v1/matches/completed` routes.
- Completed-match cards should link toward the replay/history surface; the actual replay inspector belongs to Story 29.2.
- Parallelism assessment: implementation stays sequential because the story touches shared client route, `lib/types.ts`, `lib/api.ts`, and public-navigation surfaces.

### References

- `core-plan.md#8.2 ELO & Ranking`
- `core-plan.md#9.4 Play Modes`
- `core-architecture.md#2.2 Web Client (Next.js)`
- `core-architecture.md#5.2 REST Endpoints (Agent API)`
- `_bmad-output/planning-artifacts/epics.md#Story 29.1: Add public leaderboard and completed-match browse pages in the web client`
- `_bmad-output/implementation-artifacts/19-1-expose-persisted-tick-history-and-replay-snapshots.md`
- `_bmad-output/implementation-artifacts/19-2-add-public-leaderboard-and-completed-match-summary-reads.md`
- `_bmad-output/implementation-artifacts/24-1-scaffold-a-next-js-client-and-public-match-browser.md`
- `_bmad-output/implementation-artifacts/25-1-add-a-public-match-detail-page-in-the-web-client.md`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Dev Agent Record

### Agent Model Used

- GPT-5 Codex

### Debug Log References

- `cd client && npm ci`
- `cd client && npm test -- --run src/lib/api.test.ts`
- `cd client && npm test -- --run src/components/public/public-leaderboard-page.test.tsx src/components/public/completed-matches-page.test.tsx src/app/page.test.tsx`
- `cd client && npm test -- --run src/lib/api.test.ts src/components/public/public-leaderboard-page.test.tsx src/components/public/completed-matches-page.test.tsx src/app/page.test.tsx`
- `cd client && npm test -- --run src/app/matches/[matchId]/history/page.test.tsx`
- `cd client && npm test -- --run src/app/matches/[matchId]/history/page.test.tsx src/components/public/completed-matches-page.test.tsx`
- `cd client && npm run build`
- `make install`
- `make quality`

### Completion Notes List

- Added narrow public client types and fetch helpers for `GET /api/v1/leaderboard` and `GET /api/v1/matches/completed` with deterministic malformed/unavailable error handling.
- Added text-first public `/leaderboard` and `/matches/completed` browser pages that hydrate from the stored session API base URL and keep navigation available in loading and error states.
- Completed-match browse cards now link to the future replay/history route shape at `/matches/<match_id>/history` instead of embedding replay payloads.
- Follow-up fix: added a lightweight read-only client route at `/matches/<match_id>/history` so the shipped completed-match links no longer 404 while keeping replay inspection deferred to Story 29.2.
- Updated the home page, primary navigation, and README so the shipped public browser routes match the Story 29.1 surface area.
- `make quality` passed after syncing the repo dev environment with `make install` because the initial run failed on a missing local `mypy` binary.

### File List

- `README.md`
- `_bmad-output/implementation-artifacts/29-1-add-public-leaderboard-and-completed-match-browse-pages-in-the-web-client.md`
- `client/src/app/page.tsx`
- `client/src/app/page.test.tsx`
- `client/src/app/leaderboard/page.tsx`
- `client/src/app/matches/[matchId]/history/page.tsx`
- `client/src/app/matches/[matchId]/history/page.test.tsx`
- `client/src/app/matches/completed/page.tsx`
- `client/src/components/navigation/app-shell.tsx`
- `client/src/components/public/public-leaderboard-page.tsx`
- `client/src/components/public/public-leaderboard-page.test.tsx`
- `client/src/components/public/completed-matches-page.tsx`
- `client/src/components/public/completed-matches-page.test.tsx`
- `client/src/lib/api.ts`
- `client/src/lib/api.test.ts`
- `client/src/lib/types.ts`
