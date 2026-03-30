# Story 24.2 Plan: Human JWT Auth for HTTP and WebSocket Paths

Date: 2026-03-30
Story: `24-2-add-real-human-jwt-authentication-for-http-and-websocket-paths`
Status: implemented

## Scope

- Add a minimal server-side human JWT validation seam in `server/auth.py`.
- Add small JWT settings in `server/settings.py`.
- Support human Bearer JWT auth on protected player HTTP state/order routes.
- Require a human JWT `token` query parameter for player websocket connections.
- Preserve existing agent `X-API-Key` HTTP flows and unauthenticated spectator websocket access.

## Shipped Contract

- Protected player HTTP reads/writes accept either:
  - `Authorization: Bearer <jwt>` for human players
  - `X-API-Key: <api-key>` for existing agent callers
- Human JWT validation currently uses a configured shared secret plus issuer, audience, and required role checks.
- Player websocket connections now require `viewer=player&token=<jwt>`.
- Spectator websocket connections remain unauthenticated.

## Config

- `HUMAN_JWT_SECRET`
- `HUMAN_JWT_ISSUER`
- `HUMAN_JWT_AUDIENCE`
- `HUMAN_JWT_REQUIRED_ROLE`

## Verification

1. `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_auth.py tests/test_settings.py`
2. `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'human_jwt or bearer or websocket'`
3. `make quality`
