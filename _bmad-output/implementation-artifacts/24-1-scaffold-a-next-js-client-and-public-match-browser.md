# Story 24.1: Scaffold a Next.js client and public match browser

Status: done

## Story

As a spectator or prospective player,
I want a web page that lists public matches from the running server,
So that I can discover lobbies and active games without using agent tooling or private credentials.

## Acceptance Criteria

1. Given the FastAPI server is running, when a user opens the new client app's public matches route, then the page renders data from `GET /api/v1/matches` using the existing compact public browse contract.
2. Given the match browser is intended as the first human-facing entry point, when rows are shown, then each row includes only public browse metadata such as match id, status, map, tick, tick interval, current player count, max players, and open slots.
3. Given the client is the first new runtime in the repo, when the story ships, then the repository contains a minimal Next.js + TypeScript scaffold, documented local run commands, and automated client verification integrated into the repo quality workflow.
4. Given the server is unavailable or returns no public matches, when the route loads, then the client shows deterministic empty/error states without exposing stack traces or raw transport details.

## Tasks / Subtasks

- [x] Create the initial `client/` Next.js + TypeScript scaffold with a minimal app shell and shared API types. (AC: 1, 3)
  - [x] Add `client/package.json`, TypeScript config, and the smallest working app-router layout.
  - [x] Add a typed API helper for the public matches route and mirror only the compact browse fields already exposed by the server.
- [x] Build a read-only public matches page against `GET /api/v1/matches`. (AC: 1, 2, 4)
  - [x] Render deterministic loading, empty, success, and error states.
  - [x] Keep the page public and read-only; do not add auth, lobby mutation, or websocket behavior in this story.
- [x] Integrate the new client into local docs and repo verification paths. (AC: 3)
  - [x] Add local install/run commands to `README.md`.
  - [x] Add client verification commands to `Makefile` and CI in the simplest coherent way.
- [x] Add automated coverage for the public match browser and close the story with review/simplification. (AC: 1, 3, 4)
  - [x] Add at least one client-side automated check for successful load plus one failure/empty-path check.
  - [x] Re-run the repo quality gate after client integration.

## Dev Notes

- Start with the narrowest valuable surface: a public browser page only. Do not pull in human auth, spectator sockets, map rendering, or gameplay controls yet.
- Prefer stable consumer-boundary contracts over sharing Python code with the frontend. The client should define its own small TypeScript types that mirror the public HTTP response shape.
- Keep the first client runtime boring and easy to run locally. Avoid introducing a complex state library or design system in this story.
- The server already exposes the needed public browse route, so this story should not require backend behavior changes unless a small docs/ergonomics adjustment is unavoidable.

### Project Structure Notes

- New top-level app root should be `client/` to match `core-architecture.md`.
- Keep client code under `client/src/` with an app-router entrypoint plus a small `lib/` area for fetch/types.
- Do not move or rename existing Python server paths as part of this story.

### References

- `core-architecture.md#2.2 Web Client (Next.js)`
- `core-architecture.md#5.2 HTTP API Surface`
- `core-architecture.md#7. Project Structure`
- `_bmad-output/planning-artifacts/epics.md#Epic 24: Web Client Foundation and Human Access`
- `_bmad-output/implementation-artifacts/20-1-add-db-backed-public-match-browse-summaries.md`
- `README.md#Server quality harness`

## Dev Agent Record

### Agent Model Used

OpenAI Codex CLI via `codex --yolo exec`, followed by Hermes Agent review/verification on `gpt-5.4`.

### Debug Log References

- `npm test`
- `npm run lint`
- `npm run build`
- `make quality`
- `make ci`

### Completion Notes List

- Added a minimal `client/` Next.js + TypeScript workspace with a public `/matches` route.
- Kept the first human-facing client surface read-only and limited to the existing compact browse contract from `GET /api/v1/matches`.
- Added deterministic loading, empty, and error states without exposing raw transport details.
- Integrated the client into repo commands, CI, and git-hook verification with the smallest coherent `client-install` / `client-lint` / `client-test` / `client-build` workflow.
- Added client behavior tests for the rendered browser states plus API helper contract/error handling.
- Updated README documentation for the new local client workflow.

### File List

- `.github/workflows/quality.yml`
- `.pre-commit-config.yaml`
- `Makefile`
- `README.md`
- `tests/test_local_dev_docs.py`
- `client/.env.example`
- `client/.gitignore`
- `client/next.config.ts`
- `client/package-lock.json`
- `client/package.json`
- `client/src/app/globals.css`
- `client/src/app/layout.tsx`
- `client/src/app/matches/loading.tsx`
- `client/src/app/matches/page.tsx`
- `client/src/app/page.tsx`
- `client/src/components/matches/match-browser.test.tsx`
- `client/src/components/matches/match-browser.tsx`
- `client/src/lib/api.test.ts`
- `client/src/lib/api.ts`
- `client/src/lib/types.ts`
- `client/tsconfig.json`
- `client/vitest.config.ts`
- `client/vitest.setup.ts`
