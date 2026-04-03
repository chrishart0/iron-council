# Story: 46.1 Eliminate Python 3.12 sqlite datetime adapter warnings

## Status
Drafted

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
- [ ] Add focused regression coverage that captures the current sqlite datetime warning behavior. (AC: 2)
- [ ] Implement one shared sqlite-safe UTC datetime persistence seam in the DB metadata/models layer. (AC: 1)
- [ ] Re-run focused DB/API verification and fix only real compatibility drift. (AC: 2, 3)
- [ ] Run the strongest practical repo-managed quality gate and record results. (AC: 4)
- [ ] Update this story artifact and sprint status with real outcomes. (AC: 4)

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

## Dev Agent Record
### Agent Model Used
- GPT-5 Codex

### Debug Log References
- Pending implementation.

### Completion Notes List
- Pending implementation.

### File List
- `docs/plans/2026-04-03-story-46-1-sqlite-datetime-warning-hardening.md`
- `_bmad-output/implementation-artifacts/46-1-eliminate-python-3-12-sqlite-datetime-adapter-warnings.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## QA Results
- Pending implementation.
