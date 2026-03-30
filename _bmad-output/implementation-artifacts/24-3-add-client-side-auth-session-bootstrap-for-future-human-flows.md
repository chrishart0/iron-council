# Story 24.3: Add client-side auth/session bootstrap for future human flows

Status: done

## Story

As a returning human player,
I want the web client to remember my configured server/auth context,
So that later browse, lobby, and live-match pages can reuse one simple session shell instead of ad hoc per-page wiring.

## Acceptance Criteria

1. Given the client has a public browser page and the server can validate human JWTs, when a user configures the client runtime, then the app provides a small session/bootstrap layer for server base URL, auth state, and guarded navigation.
2. Given some pages remain public while later pages require auth, when navigation occurs, then the client clearly distinguishes public routes from authenticated routes without duplicating connection/bootstrap logic.
3. Given the story ships, when local run docs and automated checks are executed, then the client session shell is documented, tested, and ready for authenticated lobby/gameplay stories.

## Tasks / Subtasks

- [x] Add a narrow client session/bootstrap seam for runtime config and auth state. (AC: 1)
  - [x] Keep the session shape small: API base URL, auth token presence/state, and a minimal signed-in label.
  - [x] Persist the configured browser state in the simplest boring way that survives refreshes.
- [x] Add public vs authenticated navigation and a reusable guard helper. (AC: 1, 2)
  - [x] Keep `/` and `/matches` public.
  - [x] Introduce a clearly-marked authenticated-only route shell for later stories rather than implementing lobby actions now.
- [x] Document and verify the new client bootstrap flow. (AC: 3)
  - [x] Add behavior-first client tests for session persistence/guard behavior.
  - [x] Update local run docs with the exact setup flow.
  - [x] Re-run the repo quality gate after the story lands.

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

GPT-5 Codex

### Debug Log References

- 2026-03-30: `cd client && npm test` (red phase: expected failures for missing session/bootstrap modules and explicit API base URL override behavior)
- 2026-03-30: `cd client && npm test -- --run src/lib/api.test.ts src/components/session/session-provider.test.tsx src/components/navigation/protected-route.test.tsx` (red phase follow-up: expected failures for browser env removal and protected-route hydration gating)
- 2026-03-30: `cd client && npm test -- --run src/components/matches/public-matches-page.test.tsx` (follow-up regression: proves `/matches` waits for session hydration so the first public request uses the stored browser API base URL)
- 2026-03-30: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_local_dev_docs.py` (red phase follow-up: expected README/env contract failure before docs sync)
- 2026-03-30: `make client-install`
- 2026-03-30: `make client-lint`
- 2026-03-30: `make client-test`
- 2026-03-30: `make client-build`
- 2026-03-30: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_local_dev_docs.py`
- 2026-03-30: `make install` (required to sync the locked dev environment before rerunning the full quality gate)
- 2026-03-30: `make quality`

### Completion Notes List

- Added a small localStorage-backed browser session seam for API base URL, optional human bearer token, and derived auth status, exposed through a shared provider/context in the root client layout.
- Kept `/` and `/matches` public while adding a clearly labeled `/lobby` authenticated placeholder route that reuses the same shared session shell instead of page-local auth logic.
- Moved public match loading onto a tiny client component so the stored browser API base URL actually drives the public browse request path.
- Added behavior-first client tests for session rehydration/persistence, protected-route rendering, config form behavior, and the explicit API base URL override path.
- Follow-up fix: removed unsupported browser reads of `IRON_COUNCIL_API_BASE_URL`, so the shipped client now defaults to `http://127.0.0.1:8000` unless the browser session form stores an override.
- Follow-up fix: exposed explicit session hydration state and gated `ProtectedRoute` on it so a stored bearer token no longer flashes the unauthenticated guard during localStorage rehydration.
- Follow-up fix: gated the `/matches` public fetch on session hydration so a saved browser API base URL controls the very first browse request instead of allowing an initial fetch against the baked-in default URL.
- Updated the README and local client env example with the exact browser-session bootstrap flow for public pages and future authenticated human routes, matching the no-browser-env contract exactly.
- Synced the locked Python dev environment with `make install` after the initial `make quality` attempt failed because `mypy` was not yet installed in the worktree `.venv`, then reran `make quality` successfully.

### File List

- `README.md`
- `client/.env.example`
- `client/src/app/globals.css`
- `client/src/app/layout.tsx`
- `client/src/app/lobby/page.tsx`
- `client/src/app/matches/page.tsx`
- `client/src/app/page.tsx`
- `client/src/components/matches/public-matches-page.tsx`
- `client/src/components/matches/public-matches-page.test.tsx`
- `client/src/components/navigation/app-shell.tsx`
- `client/src/components/navigation/protected-route.test.tsx`
- `client/src/components/navigation/protected-route.tsx`
- `client/src/components/session/session-config-panel.test.tsx`
- `client/src/components/session/session-config-panel.tsx`
- `client/src/components/session/session-context.ts`
- `client/src/components/session/session-provider.test.tsx`
- `client/src/components/session/session-provider.tsx`
- `client/src/lib/api.test.ts`
- `client/src/lib/api.ts`
- `client/src/lib/session-storage.ts`
- `tests/test_local_dev_docs.py`
