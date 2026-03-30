# Story 21.1: Add an authenticated match lobby creation endpoint

Status: done

## Story

As an authenticated agent competitor,
I want to create a new match lobby through the API,
So that I can spin up a browseable game with valid public settings and immediately occupy the creator slot without relying on seeded fixtures.

## Acceptance Criteria

1. Given an authenticated caller submits a supported lobby configuration, when `POST /api/v1/matches` is called, then the server creates a new lobby with validated public config, canonical initialized state, and creator membership.
2. Given DB-backed mode is active, when the lobby is created, then the server persists the `matches` row and creator `players` row in one coherent transaction and returns compact lobby metadata suitable for browse/detail surfaces.
3. Given the new lobby is public and joinable, when the existing browse or detail routes are called, then the lobby appears immediately with correct slot counts and without leaking private auth material.
4. Given invalid config or unsupported map input, when the create route is called, then the server returns structured validation/domain errors and does not persist a partial lobby.
5. Given the story ships, when focused unit/API/e2e and SDK checks run, then the authenticated creation contract is proven from the public boundary and the repo quality gate passes.

## Tasks / Subtasks

- [x] Add narrow authenticated create-lobby request/response models and domain validation rules. (AC: 1, 4)
- [x] Add a DB-backed lobby creation helper that initializes canonical state and persists match + creator membership atomically. (AC: 1, 2, 4)
- [x] Expose `POST /api/v1/matches` through the authenticated API, keeping the returned payload compact and public-facing. (AC: 1, 2, 3)
- [x] Add focused DB/API/e2e/SDK coverage for success, validation failures, browse/detail visibility, and creator membership. (AC: 3, 4, 5)
- [x] Update BMAD/source docs, run review + simplification, and pass `make quality`. (AC: 5)

## Dev Notes

- Keep the contract deliberately small: validated map/config inputs, compact public match metadata in the response, and the creator `player_id` for follow-on agent actions.
- Reuse `server.match_initialization` for canonical starting state instead of inventing a second bootstrap path.
- In this repo phase, prefer authenticated agent-driven lobby creation over speculative human-auth flows; do not introduce Supabase JWT plumbing in this story.
- The created lobby must remain compatible with existing public browse/detail reads and the authenticated join flow.

## Implementation Plan

- Plan file: `docs/plans/2026-03-30-story-21-1-authenticated-match-lobby-creation.md`
- Parallelism assessment: sequential implementation because API models, persistence, route wiring, and verification all share one contract seam; spec and quality reviews run after the worker finishes.
- Verification target: focused RED/GREEN DB/API/e2e/SDK commands, then `make quality`.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'create_match_lobby_reload_preserves_authenticated_creator_identity'`
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'test_create_match_lobby_route_creates_browseable_lobby_and_creator_membership'`
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'create_match_lobby or public_match_detail or match_browse'`
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'create_match_lobby or public_match_detail or match_browse or join_match'`
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'create_match_lobby or public_match_detail or match_browse'`
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py -k 'create_match_lobby'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'create_match_lobby_reload_preserves_authenticated_creator_identity'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'test_create_match_lobby_route_creates_browseable_lobby_and_creator_membership'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'create_match_lobby or public_match_detail or match_browse'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'create_match_lobby or public_match_detail or match_browse or join_match'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'create_match_lobby or public_match_detail or match_browse'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py -k 'create_match_lobby'`
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'create_match_lobby_reload_preserves_non_seeded_authenticated_creator_identity'`
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'test_create_match_lobby_route_allows_first_time_valid_db_api_key'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'create_match_lobby_reload_preserves_non_seeded_authenticated_creator_identity'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'test_create_match_lobby_route_allows_first_time_valid_db_api_key'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_process_api.py -k 'non_agent_public_profile_and_non_agent_api_key_join_attempt'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'create_match_lobby'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'create_match_lobby'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'create_match_lobby'`
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py -k 'create_match_lobby'`
- GREEN: `make quality`

### Completion Notes List

- Finished the authenticated `POST /api/v1/matches` contract with compact request/response models and structured validation handling for unsupported map and invalid lobby configuration.
- Kept lobby initialization on the existing canonical `server.match_initialization` path so created lobbies start with validated canonical state instead of a second bootstrap flow.
- Persisted the new `matches` row and creator `players` row coherently in DB-backed mode, then seeded the in-memory registry with the matching creator membership and authenticated agent metadata for immediate follow-on calls.
- Fixed the `load_match_registry_from_database` regression by passing `api_key_rows` into `_load_agent_profiles_by_match` and restoring seeded-agent profile reconstruction from persisted API-key hashes.
- Fixed the follow-up reload regression by deriving DB-backed joined-agent mappings and authenticated key ownership from the persisted API key identity instead of canonical player slots, so a lobby created by `agent-player-2` still reloads as `agent-player-2` after app/registry restart.
- Added a focused regression that proves `create lobby -> reload from DB -> same authenticated agent reads state as player-1` and confirms the reloaded profile and join mapping stay coherent.
- Final review fix: added a DB-backed auth fallback for `get_authenticated_agent()` so a valid active API key that exists only in `api_keys` can authenticate and create its first lobby before any registry or match membership exists.
- Final review fix: made non-seeded authenticated identity deterministic from persisted `api_keys.id`, using `agent-api-key-{api_key_id}` for `agent_id` and `Agent {api_key_id[:8]}` as the stable fallback display name when no persisted agent row exists yet.
- Final review fix: reused the same DB identity resolver in route auth, lobby creation, and DB reload so non-seeded create, profile lookup, joined-player mapping, and reload all preserve the same authenticated identity.
- Tightened DB fallback auth so persisted non-agent ownership still rejects agent-only routes even if the key string matches the seeded API-key format.
- Added regressions for first-time DB-backed lobby creation by a non-seeded key and for non-seeded identity preservation across persistence/reload.
- Preserved browse/detail behavior by leaving public reads DB-backed and compact, with new lobbies appearing immediately with correct slot counts and no auth leakage.
- Updated the source and BMAD architecture docs so the REST endpoint list now includes the authenticated `POST /api/v1/matches` route with its compact lobby-metadata contract wording.
- Added focused DB, API, e2e, and SDK coverage for creation success, invalid config rejection without partial persistence, browse/detail visibility, and creator state access.

### File List

- _bmad-output/implementation-artifacts/21-1-add-an-authenticated-match-lobby-creation-endpoint.md
- _bmad-output/planning-artifacts/architecture.md
- agent-sdk/python/iron_council_client.py
- core-architecture.md
- server/db/registry.py
- server/main.py
- server/models/api.py
- tests/agent_sdk/test_python_client.py
- tests/api/test_agent_api.py
- tests/api/test_agent_process_api.py
- tests/e2e/test_api_smoke.py
- tests/test_db_registry.py
