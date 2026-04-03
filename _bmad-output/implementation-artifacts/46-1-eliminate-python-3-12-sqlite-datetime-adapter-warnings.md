# Story: 46.1 Eliminate Python 3.12 sqlite datetime adapter warnings

## Status
Done

## Story
**As a** local developer and CI maintainer,
**I want** the sqlite-backed persistence and test paths to stop emitting Python 3.12 datetime adapter deprecation warnings,
**so that** the quality harness stays future-proof and real persistence regressions are not buried under avoidable warning noise.

## Acceptance Criteria
1. The shared DB timestamp persistence seam avoids the Python 3.12 sqlite default datetime adapter path while preserving timezone-aware UTC round-trips for the existing ORM models.
2. Focused tests prove representative sqlite-backed timestamp writes/reads succeed without the prior adapter deprecation warning text.
3. Relevant DB-backed API/runtime regressions still pass without contract drift in serialized datetime fields.
4. The strongest practical repo-managed quality verification passes, and the prior sqlite adapter warning spam is removed from the affected test output.

## Tasks / Subtasks
- [x] Add focused regression coverage that captures the current sqlite datetime warning behavior. (AC: 2)
- [x] Implement one shared sqlite-safe UTC datetime persistence seam in the DB metadata/models layer. (AC: 1)
- [x] Re-run focused DB/API verification and fix only real compatibility drift. (AC: 2, 3)
- [x] Run the strongest practical repo-managed quality gate and record results. (AC: 4)
- [x] Update this story artifact and sprint status with real outcomes. (AC: 4)

## Dev Notes
- `make quality` is currently green, but the Python test portion emits 1000+ warnings from the Python 3.12 sqlite datetime adapter deprecation path inside SQLAlchemy's sqlite driver.
- Keep the fix narrow and honest: do not paper over the warnings with global filters if one explicit persistence seam can remove the root cause.
- Prefer a shared boring type/helper over repeated per-call conversions.
- Verify both sqlite round-trip behavior and broader public API serialization remain stable.

## Testing
- `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_database_migrations.py -k datetime`
- `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'tick or settlement or datetime'`
- `source .venv/bin/activate && uv run pytest --no-cov tests/api/test_agent_api.py -k 'completed or settlement or history' -q`
- `source .venv/bin/activate && uv run pytest --no-cov tests/e2e/test_api_smoke.py -k 'completed or history or treaty' -q`
- `source .venv/bin/activate && make quality`

## Change Log
- 2026-04-03: Drafted Story 46.1 after baseline `make quality` confirmed the repo is green but still emits heavy sqlite datetime adapter deprecation warning noise under Python 3.12.
- 2026-04-03: Completed Story 46.1 with a shared sqlite-safe UTC datetime SQLAlchemy seam, raw seed-SQL datetime bind typing, and focused regression coverage for seeded and terminal persistence paths.

## Dev Agent Record
### Agent Model Used
- GPT-5 Codex

### Debug Log References
- RED: `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_database_migrations.py -k datetime` initially failed because `provision_seeded_database(...)` still emitted the Python 3.12 sqlite default datetime adapter deprecation warning.
- RED: `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'tick or settlement or datetime'` initially failed in the new warning-focused persistence regression for the same adapter path.
- Worktree bootstrap nuance: the first `make quality` in the fresh worker worktree failed in `tests/test_client_dev_smoke.py` because `client/node_modules` was absent and `npm run dev` could not resolve `next/dist/bin/next`; rerunning after `make client-install` confirmed this was an environment bootstrap issue, not a product regression.
- GREEN: `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_database_migrations.py -k datetime`
- GREEN: `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'tick or settlement or datetime'`
- GREEN: `source .venv/bin/activate && uv run pytest --no-cov tests/api/test_agent_api.py -k 'completed or settlement or history' -q`
- GREEN: `source .venv/bin/activate && uv run pytest --no-cov tests/e2e/test_api_smoke.py -k 'completed or history or treaty' -q`
- GREEN after bootstrap: `source .venv/bin/activate && make client-install && source .venv/bin/activate && make quality`

### Completion Notes List
- Added `UTCDateTime` plus `bind_utc_datetime_params(...)` in `server/db/metadata.py` so sqlite persists aware UTC timestamps as explicit ISO strings while other dialects keep normal timezone-aware `DateTime` behavior.
- Switched the ORM timestamp columns in `server/db/models.py` to the shared UTC datetime type instead of raw `sa.DateTime(timezone=True)` declarations.
- Updated seeded raw SQL inserts in `server/db/testing.py` to use typed datetime bind params for sqlite-backed fixture provisioning, removing the remaining adapter-warning path outside the ORM.
- Added focused regression coverage in `tests/test_database_migrations.py` and `tests/test_db_registry.py` to prove seeded provisioning and terminal tick persistence round-trip UTC timestamps without the prior deprecation warning text.
- Verified the broader DB-backed API/e2e history and completion surfaces still behave the same, and the repo quality gate now runs without the earlier sqlite adapter warning spam in the Python test stage.

### File List
- `server/db/metadata.py`
- `server/db/models.py`
- `server/db/testing.py`
- `tests/test_database_migrations.py`
- `tests/test_db_registry.py`
- `docs/plans/2026-04-03-story-46-1-sqlite-datetime-warning-hardening.md`
- `_bmad-output/implementation-artifacts/46-1-eliminate-python-3-12-sqlite-datetime-adapter-warnings.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## QA Results
- PASS: AC1. Shared DB timestamp persistence now goes through one explicit UTC-aware seam that avoids sqlite's deprecated default datetime adapter while preserving UTC round-trips.
- PASS: AC2. Focused seeded-database and terminal-persistence regressions both prove the prior adapter deprecation warning text is absent.
- PASS: AC3. Focused API and e2e history/completion checks stayed green without datetime contract drift.
- PASS: AC4. After bootstrapping client dependencies in the fresh worker worktree, `make quality` passed and the Python test stage no longer emitted the earlier sqlite datetime adapter warning flood.
