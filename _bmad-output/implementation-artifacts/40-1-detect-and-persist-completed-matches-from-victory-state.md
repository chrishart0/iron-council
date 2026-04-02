# Story: 40.1 Detect and persist completed matches from victory state

Status: completed

## Story

As a server maintainer,
I want the runtime and persistence layers to mark a match completed when the victory countdown fully expires,
So that completed-match browse, replay/history, and future rating settlement all read from one authoritative terminal match record.

## Acceptance Criteria

1. When an `AdvancedMatchTick` reaches a terminal victory state, the persistence path updates the `matches` row atomically with the terminal `current_tick`, final canonical `state`, `status=completed`, and `winner_alliance` while still appending the matching tick log entry.
2. The in-memory/runtime path transitions the completed match to `MatchStatus.COMPLETED` exactly once, stops future scheduled ticks for that match, and still allows the terminal tick to be persisted and broadcast without duplication.
3. Existing public read surfaces behave correctly after completion: `/api/v1/matches` excludes the completed match, `/api/v1/matches/completed` can include it, and history/replay reads still serve the terminal tick/state from persisted data.
4. Persistence failure semantics remain safe: if the terminal tick cannot be persisted, the in-memory match state is restored and the match is not left half-completed.
5. Focused runtime/DB/API/e2e regression coverage passes, plus the strongest practical repo-managed verification for the touched seam.

## Tasks / Subtasks

- [x] Audit the current runtime loop, tick persistence path, and completed-match public-read assumptions to identify the smallest compatibility-safe completion seam. (AC: 1, 2, 4)
- [x] Add focused failing tests for terminal victory persistence, runtime stop behavior, and completed-match public visibility before implementing the change. (AC: 1, 2, 3, 4)
- [x] Implement the terminal victory completion transition in the persistence and runtime layers without changing non-terminal behavior. (AC: 1, 2, 4)
- [x] Add or tighten focused regressions around completed browse visibility and terminal replay/history fidelity if needed. (AC: 3, 5)
- [x] Run focused verification plus the strongest practical repo-managed checks. (AC: 5)

## Dev Notes

- Source of truth: `core-plan.md` section 8.1 defines coalition victory as maintaining 50% city control until the countdown expires; `core-plan.md` section 8.2 makes post-match rating settlement dependent on that final outcome.
- The resolver already computes victory countdown state; this story is about authoritative completion handoff through runtime and persistence, not new gameplay rules.
- Current likely touchpoints: `server/runtime.py`, `server/db/tick_persistence.py`, `server/agent_registry.py` / `server/agent_registry_types.py`, `server/db/public_reads.py`, and focused tests under `tests/test_db_registry.py`, `tests/test_runtime.py` if created, `tests/api/test_agent_api.py`, and `tests/e2e/test_api_smoke.py`.
- Prefer explicit helper functions and local transaction-safe logic over a new service abstraction.
- Preserve terminal tick persistence and broadcast ordering carefully so the last tick is durable and visible exactly once.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted after Epic 39 closed. This is the first story in the new match-completion / rating-finalization phase.
- 2026-04-02: Implemented terminal completion persistence and runtime stop behavior, then tightened follow-up review coverage for `updated_at`-backed completed ordering and unresolved persisted-winner rollback semantics.
- 2026-04-02: Re-ran the focused Story 40.1 terminal regressions plus static checks after the review fixes.

### Completion Notes

- Terminal completed ticks now persist `matches.status=completed`, the final `winner_alliance`, and a fresh `matches.updated_at` timestamp in the same transaction as the terminal tick log append, so completed browse ordering and `completed_at` no longer reuse the seeded active-match timestamp.
- Terminal winner persistence no longer degrades silently when persisted alliance membership drifts. If the winner alliance cannot be resolved from the current persisted player/alliance rows, persistence raises and the runtime rollback path preserves the pre-tick in-memory match instead of storing a winnerless completed record.
- Runtime terminal handling now uses a local `is_terminal` flag to keep the completion/broadcast/stop flow explicit without changing non-terminal behavior.
- Focused regression coverage now locks in the `updated_at` contract, the unresolved terminal-winner failure semantics, the runtime rollback path, and the DB-backed public completed/history visibility after a terminal tick.
- Verification: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'terminal'`; `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'completed_terminal_tick_is_excluded'`; `uv run ruff check server/agent_registry.py server/db/tick_persistence.py server/runtime.py tests/test_db_registry.py tests/api/test_agent_api.py`; `uv run mypy server/agent_registry.py server/db/tick_persistence.py server/runtime.py tests/test_db_registry.py tests/api/test_agent_api.py`; `make quality`.

### File List

- `_bmad-output/implementation-artifacts/40-1-detect-and-persist-completed-matches-from-victory-state.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/agent_registry.py`
- `server/db/tick_persistence.py`
- `server/runtime.py`
- `tests/api/test_agent_api.py`
- `tests/test_db_registry.py`

### Change Log

- 2026-04-02: Drafted Story 40.1 to move Iron Council from provisional live-only victory state into persisted completed-match finalization.
- 2026-04-02: Completed Story 40.1 with terminal completion persistence, runtime stop/rollback handling, and focused DB/API/runtime regressions.
