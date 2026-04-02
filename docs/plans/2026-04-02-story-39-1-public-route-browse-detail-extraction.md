# Story 39.1 Public Browse/Detail Route Extraction Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extract the `/api/v1/matches` and `/api/v1/matches/{match_id}` public route handlers out of `server/api/public_routes.py` into a focused compatibility-safe module while preserving the shipped API contract, fallback semantics, and caller surface.

**Architecture:** Keep `server/api/public_routes.py` as the stable public-router composition module that still owns root/health registration plus the broader public router assembly. Move only the browse/detail route construction and its tiny helper seams into a neighboring route module with plain functions and explicit injected dependencies. Preserve both DB-backed and in-memory fallback behavior exactly; do not introduce service classes, registries, or abstractions added only for test convenience.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, uv, make quality.

---

## Parallelism Assessment

- **Implementation:** Keep Story 39.1 sequential. It centers on `server/api/public_routes.py`, likely a new neighboring route module, and the shared public API regression surface, so multiple implementation workers would collide on the same files.
- **Safe parallel work:** After implementation, run spec-compliance review and code-quality/simplification review in parallel because they are read-only.
- **Next increment:** If 39.1 lands cleanly, the next safe story is another `server/api/public_routes.py` decomposition slice (leaderboard/completed/history routes), but not in parallel with this extraction because the file overlap is too high.

### Task 1: Pin the browse/detail route contract before moving code

**Objective:** Lock the public browse/detail route behavior at the API boundary so the extraction has a stable red/green contract.

**Files:**
- Modify if needed: `tests/api/test_agent_api.py`
- Modify if needed: `tests/e2e/test_api_smoke.py`

**Step 1: Write failing test**

Add or tighten behavior-first coverage for the Story 39.1 seam:
- `/api/v1/matches` keeps DB-backed vs in-memory fallback behavior, excludes completed DB matches, and preserves compact browse row ordering.
- `/api/v1/matches/{match_id}` keeps DB-backed vs in-memory fallback behavior, preserves public roster ordering and compact payload shape, and maps unknown/completed matches to the same structured not-found error.
- `server.api.public_routes` keeps exporting `build_public_api_router` for current callers.

Example contract assertion to keep or strengthen:

```python
@pytest.mark.asyncio
async def test_public_match_detail_route_rejects_unknown_and_completed_in_memory() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    completed_record = build_seeded_match_records(primary_match_id="match-gamma")[0]
    completed_record.status = MatchStatus.COMPLETED
    registry.seed_match(completed_record)

    app = create_app(match_registry=registry)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        missing_response = await client.get("/api/v1/matches/unknown-match")
        completed_response = await client.get("/api/v1/matches/match-gamma")

    assert missing_response.json() == {
        "error": {"code": "match_not_found", "message": "Match 'unknown-match' was not found."}
    }
    assert completed_response.json() == {
        "error": {"code": "match_not_found", "message": "Match 'match-gamma' was not found."}
    }
```

**Step 2: Run tests to verify baseline**

Run:
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'list_matches_returns_stable_json_summaries or list_matches_returns_compact_db_backed_public_browse_rows_and_excludes_completed or public_match_detail_route'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'db_backed_public_match_browse_smoke or public_match_detail_smoke_flow'`

Expected: PASS if the seam is already covered, or FAIL in a way that clearly defines the missing contract test.

**Step 3: Write minimal implementation**

Only add or tighten the regression tests needed to pin the current behavior. Do not refactor production code yet.

**Step 4: Re-run the focused slice**

Run the same commands from Step 2.

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
git commit -m "test: pin public browse route contract"
```

### Task 2: Extract the public browse/detail route builders

**Objective:** Remove browse/detail route-construction detail from `server/api/public_routes.py` without changing API behavior.

**Files:**
- Modify: `server/api/public_routes.py`
- Create if clearly simpler: `server/api/public_match_routes.py`
- Modify if needed: `tests/api/test_agent_api.py`

**Step 1: Use the pinned tests as the contract**

Reuse Task 1 tests as the red/green guardrail.

**Step 2: Run focused tests during refactor**

Run:
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'list_matches_returns_stable_json_summaries or list_matches_returns_compact_db_backed_public_browse_rows_and_excludes_completed or public_match_detail_route'`

Expected: FAIL while the extraction is mid-edit, then PASS when the refactor is complete.

**Step 3: Write minimal implementation**

Refactor toward plain helper functions with explicit dependencies, for example:

```python
def register_public_match_routes(
    router: APIRouter,
    *,
    registry_dependency: object,
    history_database_url: str | None,
    public_match_status_priority: PublicStatusPriority,
    build_in_memory_public_match_roster: PublicRosterBuilder,
) -> None:
    @router.get("/matches", response_model=MatchListResponse)
    async def list_matches(
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> MatchListResponse:
        ...

    @router.get("/matches/{match_id}", response_model=PublicMatchDetailResponse)
    async def get_public_match_detail_route(
        match_id: str,
        registry: InMemoryMatchRegistry = registry_dependency,
    ) -> PublicMatchDetailResponse:
        ...
```

Guardrails:
- keep `build_public_api_router(...)` in `server/api/public_routes.py`
- keep root/health metadata registration in `server/api/public_routes.py`
- preserve `/api/v1/matches` and `/api/v1/matches/{match_id}` paths exactly
- preserve DB-backed browse/detail delegation exactly
- preserve in-memory browse ordering and detail roster construction exactly
- preserve `match_not_found` mapping for unknown and completed matches exactly
- avoid classes, framework abstractions, or generic route registries

**Step 4: Run focused tests to verify pass**

Run:
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'list_matches_returns_stable_json_summaries or list_matches_returns_compact_db_backed_public_browse_rows_and_excludes_completed or public_match_detail_route'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'db_backed_public_match_browse_smoke or public_match_detail_smoke_flow'`

Expected: PASS.

**Step 5: Commit**

```bash
git add server/api/public_routes.py server/api/public_match_routes.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
git commit -m "refactor: extract public browse detail routes"
```

### Task 3: Verify compatibility and simplify the resulting structure

**Objective:** Confirm the refactor remains caller-safe and simpler than the pre-story baseline.

**Files:**
- Modify if needed: `server/api/public_routes.py`
- Modify if created: `server/api/public_match_routes.py`
- Modify if needed: `tests/api/test_agent_api.py`
- Modify if needed: `tests/e2e/test_api_smoke.py`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'api_schema_lists_public_match_and_history_routes or list_matches_returns_stable_json_summaries or public_match_detail_route'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'db_backed_public_match_browse_smoke or public_match_detail_smoke_flow'`

Expected: PASS.

**Step 2: Simplification pass**

Review the diff for:
- remaining inline browse/detail route logic still cluttering `server/api/public_routes.py`
- helper signatures with hidden coupling rather than explicit inputs
- any new abstraction that makes the route surface harder to follow
- accidental drift in fallback semantics, path names, response models, or error mapping

**Step 3: Commit**

```bash
git add server/api/public_routes.py server/api/public_match_routes.py tests/api/test_agent_api.py tests/e2e/test_api_smoke.py
git commit -m "refactor: simplify public route composition"
```

### Task 4: Full verification, review, and BMAD closeout

**Objective:** Finish the story with verification, review, and artifact updates.

**Files:**
- Modify if needed: `server/api/public_routes.py`
- Modify if created: `server/api/public_match_routes.py`
- Modify: `_bmad-output/implementation-artifacts/39-1-extract-public-browse-and-detail-route-handlers-out-of-server-api-public_routes-py.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Create if needed: `_bmad-output/implementation-artifacts/39-2-*.md`
- Modify: `docs/plans/2026-04-02-story-39-1-public-route-browse-detail-extraction.md`

**Step 1: Run focused verification**

Run:
- `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'api_schema_lists_public_match_and_history_routes or list_matches_returns_stable_json_summaries or public_match_detail_route'`
- `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k 'db_backed_public_match_browse_smoke or public_match_detail_smoke_flow'`

Expected: PASS.

**Step 2: Run repo-managed quality gate**

Run:
- `source .venv/bin/activate && make quality`

Expected: PASS.

**Step 3: Review passes**

Run explicit spec-compliance review first, then code-quality / simplification review. Fix any issues before merge.

**Step 4: Update BMAD artifacts**

- Mark Story 39.1 done in `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Add completion notes, checks run, and final file list to the Story 39.1 artifact
- Draft the next practical public-route decomposition story if Epic 39 continues

**Step 5: Commit**

```bash
git add _bmad-output/implementation-artifacts/39-1-extract-public-browse-and-detail-route-handlers-out-of-server-api-public_routes-py.md \
        _bmad-output/implementation-artifacts/sprint-status.yaml \
        docs/plans/2026-04-02-story-39-1-public-route-browse-detail-extraction.md
git commit -m "docs: close story 39.1 and draft 39.2"
```
