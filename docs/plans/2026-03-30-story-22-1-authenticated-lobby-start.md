# Story 22.1 Plan: Authenticated Lobby Start

Date: 2026-03-30
Story: `22-1-add-an-authenticated-lobby-start-endpoint`

## Objective

Add an authenticated lobby-start API so the creator of a DB-backed lobby can transition it into the live active runtime path once readiness rules are satisfied, without relying on seeded active matches.

## Acceptance Focus

1. Authenticated creators can start a ready lobby through one public API contract.
2. The start transition persists durably in DB-backed mode and becomes visible to existing browse/detail/runtime flows.
3. Creator-only enforcement, not-ready lobbies, and already-active/completed matches return structured errors with no partial transition.
4. Focused DB/API/real-process checks plus the repo quality gate prove the contract from the public boundary.

## Implementation Approach

1. Add narrow request/response models in `server/models/api.py` for lobby start.
2. Add a small DB-backed helper in `server/db/registry.py` that:
   - verifies the authenticated creator owns the lobby
   - checks readiness / status preconditions
   - persists the status transition atomically
   - returns compact post-start metadata
3. Wire `POST /api/v1/matches/{match_id}/start` in `server/main.py` behind existing authenticated API-key auth.
4. Add focused DB/API/e2e coverage, update BMAD/source docs, and verify the running app observes the match as active.

## TDD / Verification

- RED:
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'start_match_lobby'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'start_match_lobby'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'start_match_lobby'`
- GREEN / focused:
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'start_match_lobby or create_match_lobby'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'start_match_lobby or create_match_lobby'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'start_match_lobby or create_match_lobby'`
- Final gate:
  - `make quality`
