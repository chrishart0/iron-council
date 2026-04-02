# Story 38.3 Public-Read History/Replay Extraction Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extract match-history and replay response assembly out of `server/db/public_reads.py` into focused helper functions while preserving the stable `server.db.public_reads` / `server.db.registry` behavior seen by routes and smoke tests.

**Architecture:** Keep `server.db.public_reads` as the caller-facing orchestration module that owns SQLAlchemy queries and not-found branching. Move only response-building detail for `MatchHistoryResponse` and `MatchReplayTickResponse` into plain helper functions in `server/db/public_read_assembly.py` unless a tiny adjacent helper module is clearly simpler. Preserve persisted tick ordering, payload fidelity, and error semantics exactly; do not introduce services, classes, or framework abstractions.

**Tech Stack:** Python 3.12, FastAPI server package, SQLAlchemy, Pydantic, pytest, uv, make quality.

---

## Parallelism Assessment

- **Implementation:** Keep Story 38.3 sequential. It centers on `server/db/public_reads.py`, `server/db/public_read_assembly.py`, and a shared DB public-read regression seam, so multiple implementation workers would collide.
- **Safe parallel work:** After implementation, run spec-compliance review and code-quality/simplification review in parallel because they are read-only.
- **Expected closeout:** If 38.3 lands cleanly, Epic 38 should be ready to close rather than spawning another decomposition story.

### Task 1: Pin the history/replay contract with focused regressions

**Objective:** Lock the current history/replay behavior before moving production code.

**Files:**
- Modify: `tests/test_db_registry.py`
- Modify if needed: `tests/api/test_agent_api.py`
- Modify if needed: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing test**

Add or tighten behavior-first coverage for:
- `get_match_history(...)` preserving tick ordering and top-level metadata.
- `get_match_replay_tick(...)` preserving `state_snapshot`, `orders`, and `events` payload fidelity.
- not-found behavior staying unchanged for missing match / missing tick paths.

**Step 2: Run test to verify baseline/failure shape**

Run:
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'match_history or replay_tick'`

Expected: PASS if the seam is already covered, or FAIL in a way that clearly defines the missing contract test.

**Step 3: Write minimal implementation**

Only add/adjust regression tests that pin current behavior. Do not refactor production code yet.

**Step 4: Run test to verify baseline**

Run the same command again and expect PASS.

**Step 5: Commit**

```bash
git add tests/test_db_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
git commit -m "test: pin db public history replay contract"
```

### Task 2: Extract focused history/replay assembly helpers

**Objective:** Remove history/replay response-building detail from `server/db/public_reads.py` without changing behavior.

**Files:**
- Modify: `server/db/public_reads.py`
- Modify: `server/db/public_read_assembly.py`
- Modify if needed: `tests/test_db_registry.py`

**Step 1: Use the pinned regression slice as the contract**

Reuse Task 1 tests as the red/green guardrail.

**Step 2: Run tests during the refactor**

Run:
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'match_history or replay_tick'`

Expected: FAIL while the extraction is mid-edit, then PASS when complete.

**Step 3: Write minimal implementation**

Refactor toward plain helpers with explicit inputs, for example:

```python
def build_match_history_response(*, match: Match, ticks: Sequence[int]) -> MatchHistoryResponse:
    return MatchHistoryResponse(
        match_id=str(match.id),
        status=MatchStatus(match.status),
        current_tick=int(match.current_tick),
        tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
        history=[MatchHistoryEntry(tick=int(tick)) for tick in ticks],
    )


def build_match_replay_tick_response(*, match: Match, tick_row: TickLog) -> MatchReplayTickResponse:
    return MatchReplayTickResponse(
        match_id=str(match.id),
        tick=int(tick_row.tick),
        state_snapshot=tick_row.state_snapshot,
        orders=tick_row.orders,
        events=tick_row.events,
    )
```

Guardrails:
- keep top-level query orchestration and not-found branching explicit in `server/db/public_reads.py`
- preserve `__all__` and current caller imports
- preserve tick ordering exactly (`TickLog.tick`, then `TickLog.id`)
- preserve replay payload fields exactly
- do not add classes, registries, or generalized read-service abstractions

**Step 4: Run tests to verify pass**

Run the same focused registry command again and expect PASS.

**Step 5: Commit**

```bash
git add server/db/public_reads.py server/db/public_read_assembly.py tests/test_db_registry.py
git commit -m "refactor: extract public history replay helpers"
```

### Task 3: Verify compatibility callers and simplify the result

**Objective:** Confirm the refactor stays contract-safe and simpler than before.

**Files:**
- Modify if needed: `server/db/public_reads.py`
- Modify if needed: `server/db/public_read_assembly.py`
- Modify if needed: `server/db/registry.py`
- Modify if needed: `tests/test_db_registry.py`
- Modify if needed: `tests/api/test_agent_api.py`
- Modify if needed: `tests/e2e/test_api_smoke.py`

**Step 1: Run focused verification**

Run:
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'match_history or replay_tick or public_leaderboard or completed_match_summaries'`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'history or replay'`
- `uv run pytest --no-cov tests/e2e/test_api_smoke.py -k 'history or replay'`

Expected: PASS.

**Step 2: Simplification pass**

Review the diff for:
- remaining inline response assembly that still obscures orchestration
- helper signatures with hidden coupling instead of explicit inputs
- any new abstraction that makes `server/db/public_reads.py` less obvious
- accidental drift in tick ordering or replay payload shape

**Step 3: Commit**

```bash
git add server/db/public_reads.py server/db/public_read_assembly.py server/db/registry.py tests/test_db_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
git commit -m "refactor: simplify public history replay orchestration"
```

### Task 4: Full verification, review, and BMAD closeout

**Objective:** Finish the story with verification, review, and artifact updates.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/38-3-extract-public-history-and-replay-assembly-helpers-out-of-server-db-public_reads-py.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify if needed: `_bmad-output/planning-artifacts/epics.md`
- Modify: `docs/plans/2026-04-02-story-38-3-public-read-history-replay-extraction.md`

**Step 1: Run repo-managed quality gate**

Run:
- `make quality`

Expected: PASS.

**Step 2: Review passes**

Run explicit spec-compliance review first, then code-quality/simplification review. Fix any issues before merge.

**Step 3: Update BMAD artifacts**

- Mark Story 38.3 done in `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Add completion notes, checks run, and final file list to the Story 38.3 artifact
- Close Epic 38 if no meaningful decomposition remains

**Step 4: Commit and push**

```bash
git add server/db/public_reads.py server/db/public_read_assembly.py tests/test_db_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py \
  _bmad-output/implementation-artifacts/38-3-extract-public-history-and-replay-assembly-helpers-out-of-server-db-public_reads-py.md \
  _bmad-output/implementation-artifacts/sprint-status.yaml \
  _bmad-output/planning-artifacts/epics.md \
  docs/plans/2026-04-02-story-38-3-public-read-history-replay-extraction.md
git commit -m "docs: close epic 38 planning"
git push
```
