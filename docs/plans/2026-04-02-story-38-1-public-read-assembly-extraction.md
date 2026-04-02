# Story 38.1 Public-Read Assembly Extraction Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extract the public match browse/detail payload assembly and roster-row construction out of `server/db/public_reads.py` into focused helper functions while preserving the stable `server.db.public_reads` and `server.db.registry` behavior seen by routes and tests.

**Architecture:** Keep `server.db.public_reads` as the stable caller-facing orchestration module that owns the SQLAlchemy queries and response entrypoints. Move only the browse/detail payload-building details into plain helper functions in a tiny adjacent helper module if that is clearly simpler, or into tightly scoped helpers in the same area if that keeps ownership clearer. Preserve canonical player-id mapping, roster ordering, public visibility filtering, and open-slot calculations exactly; do not introduce service layers, classes, or framework abstractions.

**Tech Stack:** Python 3.12, FastAPI server package, SQLAlchemy, Pydantic, pytest, uv, make quality.

---

## Parallelism Assessment

- **Implementation:** Keep Story 38.1 sequential. It centers on `server/db/public_reads.py`, likely a new neighboring helper module, and the shared DB registry regression surface, so multiple implementation workers would collide on the same files.
- **Safe parallel work:** After implementation, run spec-compliance review and code-quality/simplification review in parallel because they are read-only.
- **Next increment:** If 38.1 lands cleanly, draft the next DB-public-read decomposition slice from the remaining concentration in `server/db/public_reads.py` rather than forcing a second implementation worker into the same seam during this run.

### Task 1: Pin the browse/detail assembly contract with focused regressions

**Objective:** Lock the current public browse/detail and roster-mapping behavior before moving production code.

**Files:**
- Modify: `tests/test_db_registry.py`
- Modify if needed: `tests/api/test_agent_api.py`

**Step 1: Write failing test**

Add or tighten behavior-first coverage for the Story 38.1 seam:
- `get_public_match_summaries(...)` keeps current-player-count, max-player-count, open-slot-count, status, and browse ordering stable.
- `get_public_match_detail(...)` keeps roster ordering and canonical `player_id` mapping stable when persisted player row order differs from canonical `state.players` order.
- `server.db.registry` still re-exports the same public-read entrypoints from `server.db.public_reads`.

Example addition:

```python
def test_public_match_detail_preserves_canonical_player_ids_when_persisted_rows_are_out_of_order(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'public-read-detail.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    detail = get_public_match_detail(
        database_url=database_url,
        match_id="00000000-0000-0000-0000-000000000101",
    )

    assert [row.model_dump(mode="json") for row in detail.roster] == [
        {"player_id": "player-2", "display_name": "Arthur", "competitor_kind": "human"},
        {"player_id": "player-3", "display_name": "Lancelot", "competitor_kind": "agent"},
        {"player_id": "player-1", "display_name": "Merlin", "competitor_kind": "agent"},
    ]
```

**Step 2: Run test to verify baseline/failure shape**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'public_match_detail or public_match_summaries or registry_facade_re_exports_stable_module_surfaces'`

Expected: PASS if the seam is already covered, or FAIL in a way that clearly defines the missing contract test.

**Step 3: Write minimal implementation**

Only add/adjust regression tests that pin the current behavior. Do not refactor production code yet.

**Step 4: Run test to verify baseline**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'public_match_detail or public_match_summaries or registry_facade_re_exports_stable_module_surfaces'`

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_db_registry.py tests/api/test_agent_api.py
git commit -m "test: pin db public read assembly contract"
```

### Task 2: Extract focused public browse/detail assembly helpers

**Objective:** Remove browse/detail payload-building detail from `server/db/public_reads.py` without changing behavior.

**Files:**
- Modify: `server/db/public_reads.py`
- Create if clearly simpler: `server/db/public_read_assembly.py`
- Modify if needed: `tests/test_db_registry.py`

**Step 1: Use the pinned regression slice as the contract**

Reuse Task 1 tests as the red/green guardrail.

**Step 2: Run tests during the refactor**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'public_match_detail or public_match_summaries or registry_facade_re_exports_stable_module_surfaces'`

Expected: FAIL while the extraction is mid-edit, then PASS when the refactor is complete.

**Step 3: Write minimal implementation**

Refactor toward plain helper functions with explicit inputs, for example:

```python
def build_match_summary(*, match: Match, current_player_count: int) -> MatchSummary:
    max_player_count = max(int(match.config.get("max_players", 0)), 0)
    return MatchSummary(
        match_id=str(match.id),
        status=MatchStatus(match.status),
        map=str(match.config.get("map", "")),
        tick=int(match.current_tick),
        tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
        current_player_count=current_player_count,
        max_player_count=max_player_count,
        open_slot_count=max(max_player_count - current_player_count, 0),
    )


def build_public_match_roster(
    *,
    players: list[Player],
    persisted_player_mapping: dict[str, str],
) -> list[PublicMatchRosterRow]:
    return [
        PublicMatchRosterRow(
            player_id=canonical_player_id,
            display_name=player.display_name,
            competitor_kind="agent" if player.is_agent else "human",
        )
        for player in sorted(players, key=public_match_roster_sort_key)
        if (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
    ]
```

Guardrails:
- keep top-level query orchestration explicit in `server/db/public_reads.py`
- preserve `get_public_match_summaries`, `get_public_match_detail`, and current `__all__`
- preserve browse filtering (`status != COMPLETED`) exactly
- preserve canonical player-id mapping via `build_persisted_player_mapping(...)`
- preserve roster ordering, compact roster rows, and open-slot calculations exactly
- do not add classes, registries, callback hooks, or generalized read-service abstractions

**Step 4: Run tests to verify pass**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'public_match_detail or public_match_summaries or registry_facade_re_exports_stable_module_surfaces'`

Expected: PASS.

**Step 5: Commit**

```bash
git add server/db/public_reads.py server/db/public_read_assembly.py tests/test_db_registry.py
git commit -m "refactor: extract db public read assembly helpers"
```

### Task 3: Verify compatibility callers and simplify the resulting structure

**Objective:** Confirm the refactor stays contract-safe and simpler than before.

**Files:**
- Modify if needed: `server/db/public_reads.py`
- Modify if created: `server/db/public_read_assembly.py`
- Modify if needed: `server/db/registry.py`
- Modify if needed: `tests/test_db_registry.py`
- Modify if needed: `tests/api/test_agent_api.py`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/test_db_registry.py -k 'public_match_detail or public_match_summaries or public_leaderboard or completed_match_summaries or registry_facade_re_exports_stable_module_surfaces'`
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'api_schema_lists_public_match_and_history_routes or public match'`

Expected: PASS.

**Step 2: Simplification pass**

Review the diff for:
- remaining inline `MatchSummary(...)` / `PublicMatchDetailResponse(...)` assembly that still obscures orchestration
- helper signatures with hidden coupling instead of explicit inputs
- any new abstraction that makes `server/db/public_reads.py` less obvious than before
- accidental drift in roster ordering, open-slot math, or canonical player-id mapping

**Step 3: Commit**

```bash
git add server/db/public_reads.py server/db/public_read_assembly.py server/db/registry.py tests/test_db_registry.py tests/api/test_agent_api.py
git commit -m "refactor: simplify db public read orchestration"
```

### Task 4: Full verification, review, and BMAD closeout

**Objective:** Finish the story with verification, review, and artifact updates.

**Files:**
- Modify if needed: `server/db/public_reads.py`
- Modify if created: `server/db/public_read_assembly.py`
- Modify: `_bmad-output/implementation-artifacts/38-1-extract-public-browse-and-roster-assembly-helpers-out-of-server-db-public_reads-py.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Create if needed: `_bmad-output/implementation-artifacts/38-2-*.md`
- Modify: `docs/plans/2026-04-02-story-38-1-public-read-assembly-extraction.md`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/test_db_registry.py -k 'public_match_detail or public_match_summaries or public_leaderboard or completed_match_summaries or registry_facade_re_exports_stable_module_surfaces'`
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'api_schema_lists_public_match_and_history_routes or public match'`

Expected: PASS.

**Step 2: Run repo-managed quality gate**

Run:
- `source .venv/bin/activate && make quality`

Expected: PASS.

**Step 3: Review passes**

Run explicit spec-compliance review first, then code-quality / simplification review. Fix any issues before merge.

**Step 4: Update BMAD artifacts**

- Mark Story 38.1 done in `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Add completion notes, checks run, and final file list to the Story 38.1 artifact
- Draft the next practical decomposition story if the epic continues

**Step 5: Commit and push**

```bash
git add server/db/public_reads.py server/db/public_read_assembly.py tests/test_db_registry.py tests/api/test_agent_api.py \
  _bmad-output/implementation-artifacts/38-1-extract-public-browse-and-roster-assembly-helpers-out-of-server-db-public_reads-py.md \
  _bmad-output/implementation-artifacts/sprint-status.yaml \
  docs/plans/2026-04-02-story-38-1-public-read-assembly-extraction.md
git commit -m "refactor: extract db public read browse helpers"
git push
```
