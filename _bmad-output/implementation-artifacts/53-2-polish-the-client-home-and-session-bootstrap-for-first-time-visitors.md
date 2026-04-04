# Story 53.2: Polish the client home and session bootstrap for first-time visitors

Status: approved

## Story

As a first-time browser user,
I want the home page and session sidebar to explain the public and authenticated paths clearly,
So that I can tell which routes I can explore immediately, which actions need a bearer token, and how the browser session relates to owned API key management.

## Acceptance Criteria

1. Given the shipped Next.js client home page and session panel, when a visitor lands without any saved auth, then the UI presents a concise, credible public-demo path and clearly labels the lobby and BYOA surfaces as authenticated follow-ons.
2. Given a visitor later saves a bearer token, when they review the same home/session surfaces, then the copy and quick links point them toward the authenticated lobby and owned API key flow without inventing future billing or deployment UX.
3. Given this is a launch-polish slice rather than a new backend feature, when the story ships, then the implementation stays client/docs-only, behavior-first tested, and aligned with the already shipped public contracts.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [ ] Update the home page to show a clearer public-demo path and authenticated next steps with honest labels. (AC: 1)
- [ ] Update the browser session panel copy and quick links so the bearer-token relationship to lobby access and owned API keys is easier to understand. (AC: 1, 2)
- [ ] Re-run focused client verification and the relevant repo gate, then record the real outcomes here. (AC: 3)

## Dev Notes

- Keep the story client-only.
- Prefer stable route links and copy improvements over any large structural redesign.
- Do not invent future account/billing/deployment UI.

### References

- `docs/issues/public-readiness-follow-ups.md`
- `_bmad-output/planning-artifacts/epics.md#Epic 53: Public Demo and Launch Polish`
- `docs/plans/2026-04-04-epic-53-public-demo-launch-polish.md`
- `client/src/app/page.tsx`
- `client/src/components/session/session-config-panel.tsx`

## Complete Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-04: Drafted Story 53.2 for the post-runtime client launch-polish slice.

## Debug Log References

- Pending implementation.

## Completion Notes

- Pending implementation.

## File List

- `_bmad-output/implementation-artifacts/53-2-polish-the-client-home-and-session-bootstrap-for-first-time-visitors.md`
