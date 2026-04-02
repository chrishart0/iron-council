# Story 37.1 Match-Record Assembly Extraction Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extract the duplicated `MatchRecord` composition logic out of `server/db/hydration.py` into focused helper functions while preserving the existing hydration import surface, DB-backed reload semantics, and caller-visible behavior.

**Architecture:** Keep `server.db.hydration` as the stable caller-facing module, but move the repeated assembly details behind explicit helper functions inside the same module or a tiny adjacent helper module only if that is clearly simpler. Preserve the current row-loading split between whole-registry reload and session-scoped single-match reload, and keep the refactor boring: plain functions, explicit inputs, no new service layer, and no behavior changes to auth, API, websocket, runtime, or gameplay paths.

**Tech Stack:** Python 3.12, FastAPI server package, SQLAlchemy, Pydantic, pytest, uv, make quality.

---

## Parallelism Assessment

- **Implementation:** Keep Story 37.1 sequential. It centers on `server/db/hydration.py` plus the DB hydration/registry regression surface, so multiple Codex workers would collide on the same files and create merge noise.
- **Safe parallel work:** Spec-compliance and code-quality review passes can run after implementation because they are read-only.
- **Next increment:** After 37.1 lands, draft the next hydration decomposition slice from the remaining concentration in `server/db/hydration.py` rather than spawning a second implementation worker now.

### Task 1: Pin the current hydration composition contract with focused regressions

**Objective:** Lock the current `MatchRecord` assembly behavior before moving code.

**Files:**
- Modify: `tests/test_db_registry.py`
- Modify if needed: `tests/api/test_agent_api.py`
- Modify if needed: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing test**

Add or tighten behavior-first coverage for the composition seam that Story 37.1 could accidentally drift:
- registry reload keeps joined-agent, joined-human, authenticated-agent-key, alliance, and public-competitor metadata attached to hydrated records
- session-scoped `load_match_record_from_session(...)` produces the same joinability/current-player-count semantics as registry reload for the same persisted match
- the stable `server.db.registry` facade still points at the hydration entrypoints after the refactor

Example addition:

```python
def test_load_match_record_from_session_matches_registry_reload_joinability(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'hydration-joinability.db'}"
    provision_seeded_database(database_url=database_url, reset=True)

    registry = load_match_registry_from_database(database_url)
    reloaded = registry.get_match("00000000-0000-0000-0000-000000000101")
    assert reloaded is not None

    engine = create_engine(database_url)
    with Session(engine) as session:
        match = session.scalar(select(Match).where(Match.id == UUID("00000000-0000-0000-0000-000000000101")))
        assert match is not None
        single = load_match_record_from_session(session=session, match=match)

    assert single.joinable_player_ids == reloaded.joinable_player_ids
    assert single.current_player_count == reloaded.current_player_count
    assert single.joined_agents == reloaded.joined_agents
    assert single.joined_humans == reloaded.joined_humans
```

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'load_match_record_from_session or load_match_registry_from_database or hydration'`
Expected: PASS if the seam is already covered, or FAIL in a way that defines the missing contract test.

**Step 3: Write minimal implementation**

Only add/adjust regression tests that pin the current behavior. Do not refactor production code yet.

**Step 4: Run test to verify baseline**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'load_match_record_from_session or load_match_registry_from_database or hydration'`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_db_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
git commit -m "test: pin db hydration match-record contract"
```

### Task 2: Extract focused match-record composition helpers in `server/db/hydration.py`

**Objective:** Remove duplicated `MatchRecord(...)` assembly without changing hydration behavior.

**Files:**
- Modify: `server/db/hydration.py`
- Modify if needed: `tests/test_db_registry.py`

**Step 1: Write failing test**

Reuse the Task 1 regression slice as the contract.

**Step 2: Run test to verify failure**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'load_match_record_from_session or load_match_registry_from_database or hydration'`
Expected: FAIL while the extraction is mid-edit.

**Step 3: Write minimal implementation**

Refactor toward plain helper functions with explicit inputs, for example:

```python
def _build_joinable_player_ids(
    *,
    state: MatchState,
    joined_agents: dict[str, str],
    joined_humans: dict[str, str],
    status: MatchStatus,
) -> list[str]:
    if status not in {MatchStatus.LOBBY, MatchStatus.PAUSED}:
        return []
    return sorted(
        player_id
        for player_id in state.players
        if player_id not in joined_agents.values() and player_id not in joined_humans.values()
    )


def _build_match_record(
    *,
    match_id: str,
    match_status: MatchStatus,
    match_config: dict[str, object],
    state: MatchState,
    joined_agents: dict[str, str],
    joined_humans: dict[str, str],
    agent_profiles: list[AgentProfileResponse],
    authenticated_agent_keys: list[AuthenticatedAgentKeyRecord],
    public_competitor_kinds: dict[str, Literal['agent', 'human']],
    alliances: list[MatchAlliance] | None = None,
) -> MatchRecord:
    ...
```

Guardrails:
- preserve the existing public function names and imports: `load_match_registry_from_database`, `load_match_record_from_session`, and current `__all__`
- keep row loading explicit in each caller; only share `MatchRecord` composition and derived-field helpers
- preserve seeded fallback agent profiles for whole-registry reloads if no persisted agent profiles are present
- preserve joinability/current-player-count semantics exactly
- do not introduce classes, registries, callback hooks, or generic hydration frameworks

**Step 4: Run tests to verify pass**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'load_match_record_from_session or load_match_registry_from_database or hydration'`
Expected: PASS.

**Step 5: Commit**

```bash
git add server/db/hydration.py tests/test_db_registry.py
git commit -m "refactor: extract hydration match record assembly"
```

### Task 3: Verify compatibility callers and simplify the resulting structure

**Objective:** Confirm the refactor remains contract-safe and simpler than before.

**Files:**
- Modify if needed: `server/db/hydration.py`
- Modify if needed: `server/db/registry.py`
- Modify if needed: `tests/test_db_registry.py`
- Modify if needed: `tests/api/test_agent_api.py`
- Modify if needed: `tests/e2e/test_api_smoke.py`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/test_db_registry.py -k 'load_match_record_from_session or load_match_registry_from_database or hydration or registry_facade_re_exports_stable_module_surfaces'`
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'current_agent_profile or join_match or bundled_agent_briefing'`
- `uv run pytest --no-cov tests/e2e/test_api_smoke.py -k 'reloaded_registry or create_match_lobby'`

Expected: PASS.

**Step 2: Simplification pass**

Review the diff for:
- remaining duplicated `MatchRecord(...)` assembly blocks
- helper signatures that carry hidden coupling instead of explicit inputs
- any new abstraction that makes hydration less obvious than before
- accidental drift in `alliances`, seeded profile fallback, or `__all__` exports

**Step 3: Commit**

```bash
git add server/db/hydration.py server/db/registry.py tests/test_db_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
git commit -m "refactor: simplify db hydration composition"
```

### Task 4: Full verification, review, and BMAD closeout

**Objective:** Finish the story with verification, review, and artifact updates.

**Files:**
- Modify if needed: `server/db/hydration.py`
- Modify: `_bmad-output/implementation-artifacts/37-1-extract-match-record-assembly-helpers-out-of-server-db-hydration-py.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify if needed: `_bmad-output/planning-artifacts/epics.md`
- Create if needed: `_bmad-output/implementation-artifacts/37-2-*.md`
- Modify: `docs/plans/2026-04-02-story-37-1-match-record-assembly-extraction.md`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/test_db_registry.py -k 'load_match_record_from_session or load_match_registry_from_database or hydration or registry_facade_re_exports_stable_module_surfaces'`
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'current_agent_profile or join_match or bundled_agent_briefing'`
- `uv run pytest --no-cov tests/e2e/test_api_smoke.py -k 'reloaded_registry or create_match_lobby'`

Expected: PASS.

**Step 2: Run repo-managed quality gate**

Run:
- `source .venv/bin/activate && make quality`

Expected: PASS.

**Step 3: Review passes**

Run explicit spec-compliance review first, then code-quality / simplification review, then fix any issues before merge.

**Step 4: Update BMAD artifacts**

Mark Story 37.1 done, capture actual debug commands/completion notes/file list, update `sprint-status.yaml`, and draft the next pragmatic hydration decomposition story if it is not already present.

**Step 5: Commit**

```bash
git add server/db/hydration.py \
  tests/test_db_registry.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py \
  _bmad-output/implementation-artifacts/37-1-extract-match-record-assembly-helpers-out-of-server-db-hydration-py.md \
  _bmad-output/implementation-artifacts/sprint-status.yaml \
  _bmad-output/planning-artifacts/epics.md \
  _bmad-output/implementation-artifacts/37-2-*.md \
  docs/plans/2026-04-02-story-37-1-match-record-assembly-extraction.md

git commit -m "refactor: extract hydration match record helpers"
```
