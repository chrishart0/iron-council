# Story 24.2: Add real human JWT authentication for HTTP and WebSocket paths

Status: done

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

- [x] Add a narrow server-side JWT validation seam for human users. (AC: 1, 2)
  - [x] Define the minimal configuration and token-validation helpers needed to verify a Supabase-issued JWT or equivalent public-key-backed token.
  - [x] Keep agent API-key auth and spectator access paths intact.
- [x] Wire authenticated human identity resolution into protected HTTP routes. (AC: 1, 2)
  - [x] Reuse existing structured error handling patterns rather than inventing a separate auth error envelope.
  - [x] Add focused API-boundary tests for valid, missing, invalid, and wrong-viewer-role cases.
- [x] Wire authenticated human identity resolution into the player WebSocket path. (AC: 1, 2, 3)
  - [x] Preserve spectator websocket access without auth.
  - [x] Add focused realtime tests proving the player initial envelope still matches the documented public contract.
- [x] Align docs and verification after the auth path lands. (AC: 4)
  - [x] Update source/BMAD docs if the concrete token transport or route requirements change.
  - [x] Re-run the repo quality gate and a real-process websocket/auth check if feasible.

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

GPT-5 Codex

### Debug Log References

- 2026-03-30: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_auth.py tests/test_settings.py`
- 2026-03-30: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'human_jwt or bearer or websocket'`
- 2026-03-30: `uv run pytest --no-cov tests/e2e/test_api_smoke.py -k websocket`
- 2026-03-30: `make quality`

### Completion Notes List

- Added a minimal HS256-based human JWT validation seam with issuer, audience, and required-role checks in `server/auth.py`, plus small JWT config knobs in `server/settings.py`.
- Protected player HTTP state/order routes now accept either a human Bearer token or the existing agent `X-API-Key`, while preserving the agent auth flow for the rest of the server surface.
- Player websocket connections now require a human JWT `token` query parameter, resolve the player identity from the JWT subject, and still emit the same initial realtime envelope shape.
- Spectator websocket access remains unauthenticated and unchanged.
- Added focused settings/auth unit tests and focused API-boundary coverage for valid, missing, invalid, and wrong-role human JWT cases.
- Created the missing story plan doc referenced by the task and aligned the websocket contract note in `core-architecture.md`.
- Follow-up after review: websocket auth failures now emit a small structured auth error envelope before closing, successful player websocket payloads remain unchanged, and the HTTP write path now has direct Bearer-token order submission coverage for both success and failure cases.
- Follow-up after review: `create_app(settings_override=...)` is now the authoritative source for DB-backed loader/auth resolution, and added narrow JWT regression coverage for issuer mismatch and expiry.

### File List

- `pyproject.toml`
- `server/auth.py`
- `server/settings.py`
- `server/main.py`
- `server/agent_registry.py`
- `server/db/registry.py`
- `tests/test_auth.py`
- `tests/test_settings.py`
- `tests/api/test_agent_api.py`
- `docs/plans/2026-03-30-story-24-2-human-jwt-auth.md`
- `core-architecture.md`
- `_bmad-output/implementation-artifacts/24-2-add-real-human-jwt-authentication-for-http-and-websocket-paths.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
