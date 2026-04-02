# Story: 40.2 Add deterministic post-match rating settlement and profile history updates

Status: done

## Story

As a platform maintainer,
I want completed matches to settle durable rating and history outcomes exactly once,
So that public leaderboard and agent-profile reads reflect real post-match results instead of perpetual provisional snapshots.

## Acceptance Criteria

1. Completed matches with a persisted `winner_alliance` settle deterministic win/loss/draw history updates and durable rating adjustments for every participating human/agent identity.
2. Settlement is idempotent: retries or duplicate triggers for the same completed match do not double-apply rating/history changes.
3. Leaderboard and agent-profile data sources can consume the finalized settlement results without changing unrelated auth, lobby, or replay contracts.
4. Focused DB/API/e2e regressions pass, plus the strongest practical repo-managed verification for the touched seam.

## Tasks / Subtasks

- [x] Define the smallest durable settlement record/guard that prevents double-application. (AC: 1, 2)
- [x] Add failing tests for deterministic rating settlement and idempotent retry behavior. (AC: 1, 2)
- [x] Implement settlement writes and profile-history updates against the persisted completion path. (AC: 1, 2, 3)
- [x] Tighten leaderboard/profile regressions to assert finalized outcomes instead of perpetual provisional snapshots. (AC: 3, 4)
- [x] Run focused verification plus the strongest practical repo-managed checks. (AC: 4)

## Dev Notes

- This story depends on 40.1 providing authoritative completed-match state and a persisted `winner_alliance`.
- Keep settlement logic explicit and idempotent; do not bury it behind a generic ranking framework.
- Re-check `core-plan.md` section 8.2 for intended weighting rules before implementing the actual formula.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the direct follow-on to Story 40.1.
- `uv run pytest -o addopts='' -q tests/test_database_migrations.py -k "alembic_upgrade_creates_persistence_schema_for_an_empty_database"`
- `uv run pytest -o addopts='' -q tests/test_db_registry.py -k "solo_terminal_winner_coherent_across_public_reads or settles_terminal_match_only_once or stable_tiebreakers"`
- `uv run pytest -o addopts='' -q tests/api/test_agent_api.py -k "compact_db_backed_reads or finalized_settlement_results"`
- `uv run pytest -o addopts='' -q tests/api/test_agent_process_api.py -k "current_agent_profile"`
- `uv run pytest -o addopts='' -q tests/e2e/test_api_smoke.py -k "public_leaderboard_and_completed_match_smoke_flow or agent_join_and_profile_smoke_flow"`
- `uv run pytest -o addopts='' -q tests/test_db_registry.py tests/api/test_agent_api.py tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py`
- `uv run pytest -o addopts='' -q tests/test_db_registry.py -k "distinct_user_backed_agent_ids or user_backed_agent_settlement_history or settles_terminal_match_only_once or duplicate_match_settlement_insert_race"`
- `make quality`

### Completion Notes

- Added explicit `match_settlements` and `player_match_settlements` tables so completed matches settle exactly once and durable per-competitor outcomes can be queried without re-deriving history from provisional player rows.
- Wired settlement directly into `persist_advanced_match_tick()` after terminal completion state is persisted, and guarded it by match id so duplicate terminal persistence does not double-apply rating/history changes.
- Kept the settlement formula intentionally local and deterministic: winners gain a base amount plus simple alliance-tenure and territory-share bonuses; losers take a fixed penalty; draws are neutral.
- Updated DB-backed leaderboard aggregation and agent profile reads to prefer finalized settlement rows while preserving provisional in-memory behavior when no DB settlement data exists.
- Added a live DB-backed profile lookup in the API routes so public and authenticated profile reads reflect finalized settlement results even after the app has already started.
- Seeded completed-match fixtures with finalized settlement rows and API-key rating updates so DB, process, and e2e regressions exercise the finalized path rather than provisional placeholders.
- Hardened user-backed agent identity hydration so api-key-less agents now use stable user-based public IDs, session-loaded match records consume their settlement history, and duplicate settlement insert races are treated idempotently.

### File List

- `_bmad-output/implementation-artifacts/40-2-add-deterministic-post-match-rating-settlement-and-profile-history-updates.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `alembic/versions/20260402_1200_match_rating_settlement.py`
- `server/api/authenticated_read_routes.py`
- `server/db/hydration.py`
- `server/db/identity.py`
- `server/db/identity_hydration.py`
- `server/db/models.py`
- `server/db/public_read_assembly.py`
- `server/db/public_reads.py`
- `server/db/rating_settlement.py`
- `server/db/testing.py`
- `server/db/tick_persistence.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/e2e/test_api_smoke.py`
- `tests/support.py`
- `tests/test_database_migrations.py`
- `tests/test_db_registry.py`

### Change Log

- 2026-04-02: Drafted Story 40.2 to convert completed matches into durable rating and profile history outcomes.
- 2026-04-02: Implemented idempotent match settlement persistence, finalized leaderboard/profile reads, focused regressions, and seeded settlement fixtures.
