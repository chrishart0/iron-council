# Story 24.2: Add real human JWT authentication for HTTP and WebSocket paths

Status: ready-for-dev

## Story

As a human player,
I want the server to authenticate me with a real user token instead of agent credentials,
So that the browser can join future player-only flows through the public architecture boundary.

## Acceptance Criteria

1. Given the architecture requires Supabase-issued JWTs for human users, when an authenticated browser calls a protected HTTP route or player WebSocket path, then the server validates the JWT, resolves the human identity, and rejects invalid or missing tokens with structured auth errors.
2. Given agent auth and spectator access already exist, when human auth is introduced, then the implementation preserves agent API-key flows and unauthenticated spectator reads without widening privileges or conflating identities.
3. Given WebSocket auth is a public contract, when a player socket connects with a valid human token, then the server registers the viewer as a human player and sends the same initial realtime envelope shape already documented for player viewers.
4. Given the story ships, when focused HTTP/WebSocket tests plus the repo quality gate run, then the new human auth path is verified from the public boundary and the docs stay aligned with the shipped contract.

## Tasks / Subtasks

- [ ] Add a narrow server-side JWT validation seam for human users. (AC: 1, 2)
  - [ ] Define the minimal configuration and token-validation helpers needed to verify a Supabase-issued JWT or equivalent public-key-backed token.
  - [ ] Keep agent API-key auth and spectator access paths intact.
- [ ] Wire authenticated human identity resolution into protected HTTP routes. (AC: 1, 2)
  - [ ] Reuse existing structured error handling patterns rather than inventing a separate auth error envelope.
  - [ ] Add focused API-boundary tests for valid, missing, invalid, and wrong-viewer-role cases.
- [ ] Wire authenticated human identity resolution into the player WebSocket path. (AC: 1, 2, 3)
  - [ ] Preserve spectator websocket access without auth.
  - [ ] Add focused realtime tests proving the player initial envelope still matches the documented public contract.
- [ ] Align docs and verification after the auth path lands. (AC: 4)
  - [ ] Update source/BMAD docs if the concrete token transport or route requirements change.
  - [ ] Re-run the repo quality gate and a real-process websocket/auth check if feasible.

## Dev Notes

- This story is intentionally server-only. Do not couple it to a full browser auth UX; Story 24.3 can consume the new boundary afterward.
- The goal is parity with the architecture: human JWT auth for human paths, API keys for agent paths, unauthenticated spectator access where already public.
- Prefer the smallest validation surface that can be tested locally. Avoid prematurely adding a full Supabase client dependency to the browser or server if public-key JWT verification is sufficient.
- Be especially careful not to leave compatibility aliases or optional legacy token fields that still undermine the intended public contract.

### Project Structure Notes

- Primary implementation is expected in existing server auth/websocket route paths.
- Keep auth logic centralized and small rather than scattering JWT parsing through route handlers.
- Any settings additions should follow the existing repo configuration patterns and stay easy to test.

### References

- `core-architecture.md#2.1 Game Server (FastAPI)`
- `core-architecture.md#5.1 Authentication`
- `core-architecture.md#5.3 WebSocket Protocol (Human Client)`
- `_bmad-output/planning-artifacts/epics.md#Epic 24: Web Client Foundation and Human Access`
- `_bmad-output/implementation-artifacts/18-3-broadcast-live-match-updates-over-websockets-for-human-clients-and-spectators.md`
- `_bmad-output/implementation-artifacts/14-1-add-x-api-key-authentication-and-an-authenticated-current-agent-profile-endpoint.md`

## Dev Agent Record

### Agent Model Used

_To be filled during implementation._

### Debug Log References

_To be filled during implementation._

### Completion Notes List

_To be filled during implementation._

### File List

_To be filled during implementation._
