# Story 21.1 Plan: Authenticated Match Lobby Creation

Date: 2026-03-30
Story: `21-1-add-an-authenticated-match-lobby-creation-endpoint`

## Objective

Add an authenticated lobby-creation API so an agent can create a new browseable match lobby with validated public config, persisted canonical starting state, and deterministic creator membership without relying on seed-only fixtures.

## Acceptance Focus

1. Authenticated callers can create a new lobby through one public API contract that validates map, max players, tick interval, and starting-city/victory settings.
2. Lobby creation persists a canonical `matches` row plus the creator's `players` row in DB-backed mode, and returns compact public lobby metadata with creator membership included.
3. The new lobby immediately appears on the public browse/detail surfaces and supports the existing join flow without leaking private credentials.
4. Focused unit/API/real-process tests plus the repo quality gate prove the contract from the public boundary.

## Implementation Approach

1. Add narrow request/response models for authenticated lobby creation in `server/models/api.py`.
2. Add a small creation helper in `server/db/registry.py` that:
   - validates supported map/config values
   - initializes a canonical state via `server.match_initialization`
   - inserts a `matches` row and the creator `players` row in one transaction
   - returns a compact public detail response plus creator `player_id`
3. Wire `POST /api/v1/matches` in `server/main.py` behind existing agent API-key auth.
4. Add focused DB/API/e2e coverage, SDK support if the public contract is meant for external agents, and update BMAD/source docs.

## TDD / Verification

- RED:
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'create_match_lobby'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'create_match_lobby'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'create_match_lobby'`
- GREEN / focused:
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'create_match_lobby or public_match_detail or match_browse'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'create_match_lobby or public_match_detail or match_browse or join_match'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'create_match_lobby or public_match_detail or match_browse'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py -k 'create_match_lobby'`
- Final gate:
  - `make quality`
