# Story 24.3: Add client-side auth/session bootstrap for future human flows

Status: ready-for-dev

## Story

As a returning human player,
I want the web client to remember my configured server/auth context,
So that later browse, lobby, and live-match pages can reuse one simple session shell instead of ad hoc per-page wiring.

## Acceptance Criteria

1. Given the client has a public browser page and the server can validate human JWTs, when a user configures the client runtime, then the app provides a small session/bootstrap layer for server base URL, auth state, and guarded navigation.
2. Given some pages remain public while later pages require auth, when navigation occurs, then the client clearly distinguishes public routes from authenticated routes without duplicating connection/bootstrap logic.
3. Given the story ships, when local run docs and automated checks are executed, then the client session shell is documented, tested, and ready for authenticated lobby/gameplay stories.

## Tasks / Subtasks

- [ ] Add a narrow client session/bootstrap seam for runtime config and auth state. (AC: 1)
  - [ ] Keep the session shape small: API base URL, auth token presence/state, and a minimal signed-in label.
  - [ ] Persist the configured browser state in the simplest boring way that survives refreshes.
- [ ] Add public vs authenticated navigation and a reusable guard helper. (AC: 1, 2)
  - [ ] Keep `/` and `/matches` public.
  - [ ] Introduce a clearly-marked authenticated-only route shell for later stories rather than implementing lobby actions now.
- [ ] Document and verify the new client bootstrap flow. (AC: 3)
  - [ ] Add behavior-first client tests for session persistence/guard behavior.
  - [ ] Update local run docs with the exact setup flow.
  - [ ] Re-run the repo quality gate after the story lands.

## Dev Notes

- Keep this story entirely client-side unless a tiny docs/config touch is unavoidable.
- Do not add Supabase SDK coupling, full login/signup UX, or server mutations yet.
- Prefer a tiny React context + localStorage seam over introducing a broad state library.
- Guarded navigation should be explicit and deterministic, not hidden behind complex middleware.
- Preserve the existing public match browser flow and boring local developer ergonomics.

### Project Structure Notes

- Expected primary paths live under `client/src/app/`, `client/src/components/`, and `client/src/lib/`.
- If a provider is added, keep it in a small reusable client-side module and wire it through the root layout.
- Authenticated route placeholders should make future Story 25.3 easier without widening scope today.

### References

- `core-architecture.md#2.2 Web Client (Next.js)`
- `core-architecture.md#5.1 Authentication`
- `_bmad-output/planning-artifacts/epics.md#Story 24.3: Add client-side auth/session bootstrap for future human flows`
- `_bmad-output/implementation-artifacts/24-1-scaffold-a-next-js-client-and-public-match-browser.md`
- `_bmad-output/implementation-artifacts/24-2-add-real-human-jwt-authentication-for-http-and-websocket-paths.md`

## Dev Agent Record

### Agent Model Used

Pending

### Debug Log References

- Pending

### Completion Notes List

- Pending

### File List

- Pending
