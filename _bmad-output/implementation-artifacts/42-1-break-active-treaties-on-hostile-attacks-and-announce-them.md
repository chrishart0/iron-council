# Story: 42.1 Break active treaties on hostile attacks and announce them

Status: done

## Story

As a player or spectator,
I want active treaties to break automatically when one side attacks the other,
So that diplomacy history, world chat, and match reputation reflect actual betrayals instead of only manual withdrawals.

## Acceptance Criteria

1. An active treaty automatically transitions to `broken_by_a` or `broken_by_b` when one side launches a hostile accepted attack against the treaty partner during tick advancement.
2. The automatic break records the break tick and stops surfacing the treaty as active.
3. World chat receives one deterministic treaty-break announcement for each automatic break.
4. Authenticated/read/realtime treaty payloads serialize the broken statuses honestly.
5. Focused registry/API/process verification passes.

## Tasks / Subtasks

- [x] Extend the treaty status contract to include `broken_by_a` and `broken_by_b`. (AC: 1, 2, 4)
- [x] Detect hostile treaty violations during match tick advancement using the pre-resolution state plus accepted hostile movement orders. (AC: 1, 2)
- [x] Record a deterministic world-chat treaty-break announcement exactly once per break. (AC: 3)
- [x] Verify the new statuses flow through registry/API/process payloads without regressing existing diplomacy actions. (AC: 4, 5)
- [x] Run focused verification and a simplification pass. (AC: 5)

## Dev Notes

- Keep the resolver pure over `MatchState`; implement treaty-break reconciliation in the match-registry tick path where `MatchRecord` already owns treaties and messages.
- Prefer the smallest explicit helper surface over a new diplomacy framework.
- Use the treaty pair ordering already established in `agent_registry_diplomacy.py` so broken statuses are deterministic and reviewable.
- Honor the DB/source-doc direction that treaty history distinguishes formal withdrawals from actual breaks.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted Story 42.1 to close Epic 41.
- 2026-04-03: Added regression coverage for hostile attacks into neutral cities already occupied by a treaty partner, confirmed the red phase, then widened registry-side detection to honor that case without changing resolver purity.
- `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'attacking_partner_in_neutral_city or broken_by_b or treaty_record_accepts_broken_statuses'`
- `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'automatic_treaty_breaks_surface_through_authenticated_reads'`
- `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'treaty'`
- `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'treaty'`
- `source .venv/bin/activate && uv run pytest --no-cov tests/api/test_agent_process_api.py -k treaty`
- `source .venv/bin/activate && uv run pytest --no-cov tests/test_db_registry.py -k persisted_treaties -vv`
- `source .venv/bin/activate && uv run pytest --no-cov tests/api/test_agent_process_api.py -k treaty -vv`
- `source .venv/bin/activate && uv run ruff check server/db/hydration.py tests/api/test_agent_process_api.py tests/test_db_registry.py`
- `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py -k 'treaty'`
- `source .venv/bin/activate && uv run ruff check server tests agent-sdk/python`
- `source .venv/bin/activate && uv run mypy server tests agent-sdk/python`
- Spec-compliance review: PASS
- Code-quality/simplification review: APPROVED

### Completion Notes

- Kept treaty-break detection in the registry tick path by extending the accepted-movement scan to treat a move into a neutral city already occupied by a treaty partner as a hostile attack that breaks active treaties.
- Preserved the pure resolver contract and avoided new abstraction layers by reusing the existing diplomacy helper while deriving defenders from pre-resolution city ownership plus occupying stationary armies.
- Added behavior-first regression coverage for hostile attacks into neutral occupied cities, plus an explicit `broken_by_b` registry regression, so the public contract now stays honest across both directional treaty-break statuses.
- Closed the DB-backed hydration gap by loading persisted treaty rows into `MatchRecord` deterministically, mapping persisted player IDs back to canonical player IDs, and deriving the minimal compatibility fields needed for current authenticated treaty reads without a migration.
- Documented that legacy DB treaty rows do not store proposal provenance, so DB-backed reads preserve truthful status/break metadata while reconstructing compatibility values for `proposed_by` / `proposed_tick` until a future schema expansion exists.
- Requested focused treaty regressions plus `ruff` and `mypy` all passed.

### File List

- `_bmad-output/implementation-artifacts/42-1-break-active-treaties-on-hostile-attacks-and-announce-them.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/plans/2026-04-02-story-42-1-treaty-breaks.md`
- `server/agent_registry_commands.py`
- `server/agent_registry_diplomacy.py`
- `server/models/api.py`
- `server/db/hydration.py`
- `agent-sdk/python/iron_council_client.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/agent_sdk/test_python_client.py`
- `tests/test_db_registry.py`
- `tests/test_agent_registry.py`

### Change Log

- 2026-04-02: Drafted Story 42.1 to close the treaty-break gap left after Epic 41.
- 2026-04-03: Implemented neutral-city occupied-defender treaty breaking in the registry tick path, added behavior-first regressions including `broken_by_b`, and passed the requested focused checks.
- 2026-04-03: Hydrated persisted treaties for DB-backed match loads, fixed the running-app broken-treaty regression/expectation mismatch, and re-ran focused DB and process treaty checks.
