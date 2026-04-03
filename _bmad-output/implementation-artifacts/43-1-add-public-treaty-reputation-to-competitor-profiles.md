# Story: 43.1 Add public treaty reputation to competitor profiles

Status: done

## Story

As a player or spectator,
I want public competitor profiles to show treaty reputation and history,
So that betrayals, withdrawals, and honored agreements remain visible when I inspect agents and humans outside the live match UI.

## Acceptance Criteria

1. Public agent and human profile response contracts add an explicit treaty-reputation section with deterministic counts for signed, currently active, honored, withdrawn, broken-by-self, and broken-by-counterparty treaties.
2. DB-backed profile assembly maps persisted treaty rows onto persistent agent/human identities and exposes a deterministic read-only treaty-history list with match id, counterparty display name, treaty type, final status, signed tick, and break/withdraw tick when present.
3. Honest empty treaty-reputation payloads are returned when no treaty history exists; existing not-found and DB-unavailable profile contracts remain unchanged.
4. Public agent and human profile pages render a stable read-only treaty-reputation summary and treaty-history section with deterministic empty-state copy.
5. Focused API/DB/client verification passes, followed by the strongest practical repo-managed quality checks for the touched seam.

## Tasks / Subtasks

- [x] Add additive treaty-reputation models to the shared public profile contract and keep non-DB/empty-history behavior explicit. (AC: 1, 3)
- [x] Aggregate persisted treaty rows by public competitor identity for DB-backed agent/human profile responses without inventing provenance fields. (AC: 1, 2, 3)
- [x] Render treaty-reputation summary/history on the public agent and human profile pages. (AC: 4)
- [x] Add focused API/DB/client tests plus repo-managed verification and a simplification pass. (AC: 5)

## Dev Notes

- Reuse the existing public profile routes instead of creating match-specific profile endpoints in this story.
- Keep the contract additive and honest: empty arrays/counts are acceptable; fabricated treaty history is not.
- Treat `broken_by_a` / `broken_by_b` as identity-relative reputation in the profile response, exposing whether the profiled competitor broke the treaty or had it broken by the counterparty.
- Preserve the existing human-profile `503 human_profile_unavailable` behavior when no DB is configured.
- Prefer a small helper in `server/db/identity_hydration.py` or a tightly scoped sibling module over broad new abstractions.

## Dev Agent Record

### Debug Log

- 2026-04-03: Drafted as the first post-Epic-42 story so the newly honest treaty lifecycle data becomes visible on the shipped public profile surfaces.
- 2026-04-03: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'public_and_authenticated_agent_profile_routes_return_stable_shapes or human_profile_route_returns_structured_unavailable_error_without_db_backing or db_backed_agent_profile_routes_return_finalized_settlement_results'`
- 2026-04-03: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'get_human_profile_from_db_returns_settled_public_profile_without_agent_only_fields or get_agent_profile_from_db_aggregates_identity_relative_treaty_reputation'`
- 2026-04-03: `cd client && npm test -- --run src/lib/api.test.ts src/components/public/public-agent-profile-page.test.tsx src/components/public/public-human-profile-page.test.tsx`
- 2026-04-03: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'public_and_authenticated_agent_profile_routes_return_stable_shapes or human_profile or automatic_treaty_breaks_surface_through_authenticated_reads or db_backed_agent_profile_routes_return_finalized_settlement_results'`
- 2026-04-03: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'human_profile or agent_profile or treaty_reputation'`
- 2026-04-03: `uv run pytest -o addopts='' tests/agent_sdk/test_python_client.py -k 'sdk_profile_and_match_methods_return_typed_authenticated_contracts'`
- 2026-04-03: `uv run pytest -o addopts='' tests/api/test_agent_process_api.py -k 'running_app_serves_authenticated_current_agent_profile_from_db_registry'`
- 2026-04-03: `uv run pytest -o addopts='' tests/e2e/test_agent_sdk_smoke.py -k 'agent_sdk_smoke_flow_runs_through_real_process or agent_sdk_example_lobby_lifecycle_command_runs_through_real_process'`
- 2026-04-03: `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'completion_to_leaderboard_smoke_flow_runs_through_real_process or agent_join_and_profile_smoke_flow_runs_through_real_process or authenticated_current_agent_profile_smoke_flow_runs_through_real_process'`
- 2026-04-03: `uv run pytest -o addopts='' tests/test_agent_registry.py -k 'get_agent_profile_returns_stable_seeded_placeholder_shape'`
- 2026-04-03: `source .venv/bin/activate && make quality`
- 2026-04-03: Follow-up fix for the honored-history visibility gap: `source .venv/bin/activate && pytest -o addopts='' tests/test_db_registry.py -k 'get_human_profile_from_db_returns_settled_public_profile_without_agent_only_fields or get_agent_profile_from_db_aggregates_identity_relative_treaty_reputation'`
- 2026-04-03: Follow-up fix for the honored-history visibility gap: `source .venv/bin/activate && pytest -o addopts='' tests/api/test_agent_api.py -k 'db_backed_human_profile_route_returns_stable_public_contract or db_backed_agent_profile_routes_return_finalized_settlement_results'`
- 2026-04-03: Follow-up fix for the honored-history visibility gap: `cd client && npm test -- --run src/lib/api.test.ts src/components/public/public-agent-profile-page.test.tsx src/components/public/public-human-profile-page.test.tsx`
- 2026-04-03: Follow-up fix for the honored-history visibility gap: `source .venv/bin/activate && make quality`

### Completion Notes

- Added explicit treaty-reputation summary/history models to the public agent profile contract, DB-backed human profile contract, TypeScript client types, and the Python SDK.
- Aggregated persisted treaty rows onto stable public identities in `server/db/identity_hydration.py`, keeping empty treaty payloads explicit for seeded, in-memory, lobby-creator, and no-history profiles.
- Rendered read-only treaty reputation and treaty history sections on the public agent and human profile pages with deterministic empty-state copy.
- Updated API, DB, client, smoke, and SDK tests to cover the additive contract and completed the full repo quality gate successfully.
- Follow-up fix: completed-match treaties that persisted with final DB status `active` now surface as `honored` in public treaty history visibility as well as summary counts, while identity-relative `broken_by_self` behavior remains unchanged for broken treaties.
- Removed local prompt/review scratch files that were used during the story follow-up and should not ship.

### File List

- `_bmad-output/implementation-artifacts/43-1-add-public-treaty-reputation-to-competitor-profiles.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `agent-sdk/python/iron_council_client.py`
- `client/src/components/public/public-agent-profile-page.test.tsx`
- `client/src/components/public/public-agent-profile-page.tsx`
- `client/src/components/public/public-human-profile-page.test.tsx`
- `client/src/components/public/public-human-profile-page.tsx`
- `client/src/lib/api.test.ts`
- `client/src/lib/api.ts`
- `client/src/lib/types.ts`
- `server/db/hydration.py`
- `server/db/identity_hydration.py`
- `server/db/lobby_registry.py`
- `server/models/api.py`
- `server/registry_seed_data.py`
- `tests/agent_sdk/test_python_client.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/e2e/test_api_smoke.py`
- `tests/test_agent_registry.py`
- `tests/test_db_registry.py`

### Change Log

- 2026-04-03: Drafted Story 43.1 and advanced BMAD tracking past the completed treaty-break story.
- 2026-04-03: Implemented public treaty reputation on server, client, and SDK profile surfaces and verified the full repo quality gate.
- 2026-04-03: Corrected the honored-history visibility contract so completed-match treaties no longer render as still active on public profile history surfaces.
