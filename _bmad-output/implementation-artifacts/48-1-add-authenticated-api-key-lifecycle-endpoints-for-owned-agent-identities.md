# Story 48.1: Add authenticated API key lifecycle endpoints for owned agent identities

Status: ready-for-dev

## Story

As an authenticated human player,
I want to create, list, and revoke my own agent API keys through the shipped API,
So that I can onboard and manage my own agents without relying on seeded local fixtures or direct database edits.

## Acceptance Criteria

1. Given an authenticated human bearer token, when the caller requests their owned agent API keys, then the server returns a compact list of owned key summaries that includes stable key ids, rating metadata, active state, and created timestamps without exposing raw key material.
2. Given the same authenticated human wants to create a new agent key, when the creation route succeeds, then the response returns a one-time raw secret plus the persisted key summary while the database stores only the hashed secret and future reads never reveal it again.
3. Given an owned key is revoked, when that key is later presented through the existing `X-API-Key` contract, then agent-authenticated routes reject it as inactive and the lifecycle endpoints continue to show the key as inactive rather than deleting history.
4. Given this is the first self-serve BYOA slice, when the story ships, then focused API/process/docs verification plus the repo quality gate pass and the README/BMAD artifacts explain the new onboarding path honestly.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [ ] Add behavior-first API tests for listing, creating, and revoking owned agent API keys from the authenticated human boundary, including one-time secret reveal and revoked-key auth rejection. (AC: 1, 2, 3)
- [ ] Add the smallest DB-backed service/model helpers needed to persist and return owned API key summaries without exposing raw secrets on reads. (AC: 1, 2)
- [ ] Add authenticated HTTP routes for key lifecycle management and keep the public/authenticated contract surfaces narrow and typed. (AC: 1, 2, 3)
- [ ] Refresh the minimal BYOA entrypoint docs so the new lifecycle contract is discoverable from the shipped product surface without requiring client UI work yet. (AC: 4)
- [ ] Re-run focused verification plus the repo quality gate, then update BMAD/docs artifacts with real outcomes. (AC: 4)

## Dev Notes

- Keep this story server-first and narrow. Do not couple it to Stripe, entitlements, match occupancy rules, or guided-agent gameplay semantics yet.
- Prefer extending the existing authenticated human Bearer-token surface rather than inventing a separate admin or setup auth flow.
- The `api_keys` table already exists with `id`, `user_id`, `key_hash`, `elo_rating`, `is_active`, and `created_at`; prefer the smallest additive change set that supports one-time secret reveal and compact list responses.
- Reads must never echo the raw API key after creation. Revoke should mark the key inactive rather than deleting the row so historical profile/rating references remain stable.
- Review existing agent-auth and human-auth tests before implementation so the new routes preserve the current `invalid_api_key` / mixed-auth error conventions where they overlap.
- Keep docs honest: the product doc may still mention future paid keys, but this story only establishes self-serve lifecycle management and manual BYOA onboarding.

### References

- `core-plan.md#9.1 Bring Your Own Agent`
- `core-plan.md#9.3 Agent Access & Pricing`
- `core-architecture.md#2.1 Game Server (FastAPI)`
- `core-architecture.md#3.1 Core Tables`
- `core-architecture.md#5.2 REST API`
- `server/db/models.py`
- `server/api/authenticated_read_routes.py`
- `server/api/authenticated_lobby_routes.py`
- `server/api/authenticated_write_routes.py`
- `_bmad-output/planning-artifacts/epics.md#Story 48.1: Add authenticated API key lifecycle endpoints for owned agent identities`

## Complete Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Testing

- `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'api_key and (lifecycle or current_agent_profile or invalid)'`
- `source .venv/bin/activate && uv run pytest --no-cov tests/api/test_agent_process_api.py -k 'api_key and (profile or lifecycle or invalid)' -q`
- `source .venv/bin/activate && uv run pytest --no-cov tests/test_local_dev_docs.py -q`
- `source .venv/bin/activate && make quality`

## Change Log

- 2026-04-03: Drafted Story 48.1 to start the self-serve BYOA onboarding phase after Epic 47 completed and BMAD planning reached the end of the current roadmap.
