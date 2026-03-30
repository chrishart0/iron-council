# Story 24.1: Scaffold a Next.js client and public match browser

Status: ready-for-dev

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

- [ ] Create the initial `client/` Next.js + TypeScript scaffold with a minimal app shell and shared API types. (AC: 1, 3)
  - [ ] Add `client/package.json`, TypeScript config, and the smallest working app-router layout.
  - [ ] Add a typed API helper for the public matches route and mirror only the compact browse fields already exposed by the server.
- [ ] Build a read-only public matches page against `GET /api/v1/matches`. (AC: 1, 2, 4)
  - [ ] Render deterministic loading, empty, success, and error states.
  - [ ] Keep the page public and read-only; do not add auth, lobby mutation, or websocket behavior in this story.
- [ ] Integrate the new client into local docs and repo verification paths. (AC: 3)
  - [ ] Add local install/run commands to `README.md`.
  - [ ] Add client verification commands to `Makefile` and CI in the simplest coherent way.
- [ ] Add automated coverage for the public match browser and close the story with review/simplification. (AC: 1, 3, 4)
  - [ ] Add at least one client-side automated check for successful load plus one failure/empty-path check.
  - [ ] Re-run the repo quality gate after client integration.

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

_To be filled during implementation._

### Debug Log References

_To be filled during implementation._

### Completion Notes List

_To be filled during implementation._

### File List

_To be filled during implementation._
