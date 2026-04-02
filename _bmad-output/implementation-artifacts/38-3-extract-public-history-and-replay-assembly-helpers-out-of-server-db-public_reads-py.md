# Story: 38.3 Extract public history and replay assembly helpers out of `server/db/public_reads.py`

Status: completed

## Story

As a server maintainer,
I want the match-history and replay response assembly logic grouped behind focused helpers,
So that `server/db/public_reads.py` can finish Epic 38 as a thin orchestration surface for public DB reads instead of mixing SQL query flow with every response-construction detail.

## Acceptance Criteria

1. The inline history/replay response-construction responsibilities in `server/db/public_reads.py` (at minimum `MatchHistoryResponse` and `MatchReplayTickResponse` assembly) move behind a focused compatibility-safe helper surface while preserving stable caller behavior from `server.db.public_reads` and `server.db.registry`.
2. Persisted tick ordering, status/current-tick metadata, replay `state_snapshot` / `orders` / `events` payload fidelity, and not-found behavior remain unchanged at the registry, route, and real-process smoke-test boundary.
3. `server/db/public_reads.py` keeps explicit top-level DB query orchestration and does not gain a framework/service abstraction.
4. Focused DB public-read / registry regression coverage passes, along with the strongest practical repo-managed verification for the touched seam.
5. The final structure is simpler than the post-38.2 starting point: fewer mixed responsibilities in `server/db/public_reads.py`, clearer ownership for history/replay assembly helpers, and no abstraction added only for test convenience.

## Tasks / Subtasks

- [x] Audit the remaining history/replay assembly seams in `server/db/public_reads.py` and identify the tightest extraction that preserves current behavior. (AC: 1, 5)
- [x] Extract focused helper(s) or a compatibility-safe helper module surface for history/replay response construction. (AC: 1, 2, 3, 5)
- [x] Keep `server.db.public_reads` and `server.db.registry` import behavior stable for current callers. (AC: 1, 2)
- [x] Add or tighten focused regression coverage around history ordering, replay payload fidelity, and not-found behavior. (AC: 2, 4)
- [x] Run focused verification plus the strongest practical repo-managed checks. (AC: 4, 5)

## Dev Notes

- This is the next pragmatic Epic 38 slice after Story 38.2 moved leaderboard and completed-match aggregation into `server/db/public_read_assembly.py`.
- Treat this as refactor-only work; do not broaden into new public routes, API shape changes, DB schema changes, or UI work.
- Prefer plain functions and explicit inputs over classes, registries, or generalized read-service frameworks.
- Preserve the current tick ordering, payload field contents, and not-found error semantics exactly.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the next Epic 38 slice after completing Story 38.2.
- 2026-04-02: Confirmed the existing history/replay regression seam in `tests/test_db_registry.py` before refactoring so the extraction stayed contract-first instead of helper-first.
- 2026-04-02: Extracted `MatchHistoryResponse` and `MatchReplayTickResponse` assembly into plain helper functions in `server/db/public_read_assembly.py`, leaving `server/db/public_reads.py` responsible only for SQL query orchestration and not-found branching.
- 2026-04-02: Verified the touched seam in `master` with:
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'match_history or replay_tick or public_leaderboard or completed_match_summaries'`
  - `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'history or replay'`
  - `uv run pytest --override-ini addopts='' tests/e2e/test_api_smoke.py -k 'history or replay'`
  - `make quality`
- 2026-04-02: Completed explicit post-implementation review passes: spec compliance PASS and code quality APPROVED with no blocking issues.

### Completion Notes

- Extracted the remaining history/replay response construction out of `server/db/public_reads.py` into focused plain-function helpers in `server/db/public_read_assembly.py`.
- Preserved registry and route contracts exactly: history tick ordering, status/current-tick metadata, replay `state_snapshot` / `orders` / `events` payloads, and match/tick not-found semantics all remained unchanged at the public boundary.
- Left `server/db/public_reads.py` as a thin, explicit orchestration module over the public DB read queries with no service object or framework abstraction added.
- Re-ran the strongest practical repo-managed verification in `master`; the full quality gate passed after integration.
- Epic 38 is now complete and ready to close.

### File List

- `server/db/public_read_assembly.py`
- `server/db/public_reads.py`
- `_bmad-output/implementation-artifacts/38-3-extract-public-history-and-replay-assembly-helpers-out-of-server-db-public_reads-py.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/39-1-extract-public-browse-and-detail-route-handlers-out-of-server-api-public_routes-py.md`

### Change Log

- 2026-04-02: Drafted Story 38.3 to finish decomposing `server/db/public_reads.py` by extracting history/replay response assembly helpers.
- 2026-04-02: Completed Story 38.3 by moving history/replay response assembly into `server/db/public_read_assembly.py`, re-verifying focused registry/API/e2e seams plus `make quality`, and closing Epic 38.
