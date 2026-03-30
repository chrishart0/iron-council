# Story 20.2 Plan: Public Match Lobby Detail Read

Date: 2026-03-30
Story: `20-2-add-a-public-match-lobby-detail-read`

## Objective

Add a compact public detail route at `GET /api/v1/matches/{match_id}` that returns one non-completed match's public browse metadata plus a visible roster summary, reusing the existing DB-backed public read-model style while preserving a lightweight in-memory seeded/dev fallback.

## Acceptance Focus

1. Return compact public metadata for one lobby, paused, or active match, including configuration and visible roster rows without leaking fog-filtered state or private credentials.
2. Treat completed or unknown matches as not found for this public browse surface and do not leak replay/history payloads.
3. Add focused DB, API, and real-process coverage for success, stable roster ordering, and structured not-found handling.

## Implementation Approach

1. Add compact API models for a public match-detail response and public roster rows.
2. Add a DB-backed `get_public_match_detail` helper in `server/db/registry.py` that:
   - reads one non-completed match
   - derives compact browse fields from persisted match config/current tick
   - reads players for that match
   - returns roster rows with only `display_name` and `competitor_kind`
   - orders roster rows deterministically for stable public rendering
3. Wire `GET /api/v1/matches/{match_id}` in `server/main.py`:
   - DB-backed mode uses the new read helper directly
   - in-memory mode returns the same compact public shape from seeded registry data
   - completed and unknown matches map to the structured `match_not_found` error
4. Update architecture docs and BMAD artifacts to explicitly mention the new public detail contract.

## TDD / Verification

- RED:
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'public_match_detail'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'public_match_detail'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'public_match_detail'`
- GREEN / focused:
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'public_match_detail or match_browse or leaderboard or completed_match'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'public_match_detail or match_browse or leaderboard or completed_match or list_matches'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'public_match_detail or match_browse or leaderboard or completed_match or list_matches'`
- Final gate:
  - `make quality`
