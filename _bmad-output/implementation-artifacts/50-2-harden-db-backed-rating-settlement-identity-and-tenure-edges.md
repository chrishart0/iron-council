# Story 50.2: Harden DB-backed rating settlement identity and tenure edges

Status: done

## Story

As a maintainer,
I want deterministic DB-backed regressions for rating settlement edge cases,
So that completed-match ELO updates remain honest across solo winners, alliance winners, draws, and identity aggregation reads.

## Acceptance Criteria

1. Given completed matches can settle human and agent ratings from persisted player rows and canonical match state, when focused regressions exercise winner resolution, tenure weighting, zero-territory fallback, and latest-human-ELO lookup edge cases, then settlement stays deterministic, additive, and safe without depending on row-order accidents or hidden defaults.
2. Given V1 is already feature-complete, when this hardening story lands, then the code and tests stay boring: prefer narrow DB/behavior tests and only the smallest production refactor needed to keep the implementation aligned with repo conventions and `make quality`.
3. Given the story ships, when the focused DB test slice and the repo quality gate run, then the new regressions pass and the BMAD artifact records the real verification commands and outcomes.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add focused DB-backed regressions for winner identity resolution, draw handling, and territory/tenure weighting edge cases. (AC: 1)
- [x] Add focused regressions for settlement aggregate and latest-human-ELO lookups so identity grouping stays stable. (AC: 1)
- [x] Make only the smallest implementation cleanup required for any exposed drift. (AC: 2)
- [x] Re-run the focused DB slice plus `make quality`, then close out this BMAD artifact with real outcomes. (AC: 3)

## Dev Notes

- Keep the scope centered on `server/db/rating_settlement.py` and existing DB-backed tests in `tests/test_db_registry.py` or a nearby focused DB test module.
- Prefer real-session SQLite/Postgres-path tests over pure mock tests so the persistence boundary stays honest.
- Do not broaden into leaderboard/profile route rewrites unless a narrow contract bug forces a tiny follow-up fix.
- If production code needs cleanup, prefer a small helper clarification over new abstraction layers.

### References

- `_bmad-output/planning-artifacts/epics.md#Story 50.2: Harden DB-backed rating settlement identity and tenure edges`
- `server/db/rating_settlement.py`
- `server/db/models.py`
- `tests/test_db_registry.py`
- `tests/test_database_migrations.py`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-04: Drafted Story 50.2 to harden completed-match rating settlement semantics after V1 feature completion.
- 2026-04-04: Added DB-backed settlement edge regressions, hardened duplicate-settlement verification, and closed Story 50.2 after controller quality verification.

## Debug Log References

- 2026-04-04: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'settlement or elo or latest_human or aggregate'` (pass)
- 2026-04-04: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py` (pass)
- 2026-04-04: `source .venv/bin/activate && make quality` (pass in controller repo after merge; 471 Python tests, 200 client tests, Next build, and 95.26% total coverage)

## Completion Notes

- Added DB-backed regressions for canonical alliance winner resolution, canonical solo winner fallback, draw handling, zero-territory equal-share fallback, stable identity aggregation, latest-human-ELO tie-breaking, and duplicate-settlement race handling.
- Narrowed settlement recovery so duplicate-settlement races are tolerated only after verifying the durable settlement marker and participant rows already exist.
- Controller verification confirmed the focused DB slice, the broader DB registry suite, and the full repository quality gate all pass on `master`.

## File List

- `_bmad-output/implementation-artifacts/50-2-harden-db-backed-rating-settlement-identity-and-tenure-edges.md`
- `server/db/rating_settlement.py`
- `tests/test_db_registry.py`
