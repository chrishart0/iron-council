# Story 39.3 Public History Route Extraction Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extract the persisted public match history and replay route handlers out of `server/api/public_routes.py` into a focused compatibility-safe module without changing the shipped HTTP or OpenAPI contract.

**Architecture:** Keep `server/api/public_routes.py` as the public composition layer for metadata plus public route-family wiring. Move only the `/api/v1/matches/{match_id}/history` and `/api/v1/matches/{match_id}/history/{tick}` handlers and their tiny DB-availability helper into a new `server/api/public_history_routes.py` router-builder module, mirroring the already-extracted `public_summary_routes` and `public_match_routes` patterns.

**Tech Stack:** FastAPI, Pydantic response models, pytest/httpx AsyncClient API tests, real-process e2e smoke tests, uv-managed Python toolchain.

---

### Task 1: Add the extracted public history router module

**Objective:** Create the smallest dedicated router-builder module for persisted history/replay routes while preserving current error translation and DB-backed-only behavior.

**Files:**
- Create: `server/api/public_history_routes.py`
- Modify: `server/api/public_routes.py`
- Test: `tests/api/test_agent_api.py`

**Step 1: Write/adjust failing seam test**

Add the extracted-module exposure assertion to `tests/api/test_agent_api.py` near `test_server_api_modules_expose_extracted_route_seams`:

```python
public_history_routes = importlib.import_module("server.api.public_history_routes")
assert hasattr(public_history_routes, "build_public_history_router")
```

**Step 2: Run focused test to verify failure**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k extracted_route_seams
```

Expected: FAIL because `server.api.public_history_routes` does not exist yet.

**Step 3: Write minimal implementation**

Create `server/api/public_history_routes.py` with a plain builder:

```python
from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter

from server.db.registry import (
    MatchHistoryNotFoundError,
    TickHistoryNotFoundError,
    get_match_history,
    get_match_replay_tick,
)
from server.models.api import MatchHistoryResponse, MatchReplayTickResponse

from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError


def build_public_history_router(*, history_database_url: str | None) -> APIRouter:
    router = APIRouter()

    def require_history_database_url() -> str:
        if history_database_url is None:
            raise ApiError(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="match_history_unavailable",
                message="Persisted match history is only available in DB-backed mode.",
            )
        return history_database_url

    @router.get(...)
    async def get_persisted_match_history(match_id: str) -> MatchHistoryResponse:
        ...

    @router.get(...)
    async def get_persisted_match_replay_tick(match_id: str, tick: int) -> MatchReplayTickResponse:
        ...

    return router
```

Then simplify `server/api/public_routes.py` to import and include the new router:

```python
from .public_history_routes import build_public_history_router
...
router.include_router(build_public_history_router(history_database_url=history_database_url))
```

**Step 4: Run focused tests to verify pass**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'extracted_route_seams or match_history_routes or openapi_declares_public_read_contracts'
```

Expected: PASS.

**Step 5: Commit**

```bash
git add server/api/public_history_routes.py server/api/public_routes.py tests/api/test_agent_api.py
git commit -m "refactor: extract public history routes"
```

### Task 2: Prove the public contract is unchanged at API and smoke boundaries

**Objective:** Re-run the strongest focused verification for persisted history/replay routes, including real-process behavior.

**Files:**
- Test: `tests/api/test_agent_api.py`
- Test: `tests/e2e/test_api_smoke.py`

**Step 1: Run focused API regressions**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'match_history_routes or openapi_declares_public_read_contracts'
```

Expected: PASS.

**Step 2: Run real-process smoke regression**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k match_history_and_replay_smoke_flow_runs_through_real_process
```

Expected: PASS.

**Step 3: Run repo-managed quality gate for touched seam**

Run:

```bash
source .venv/bin/activate && make quality
```

Expected: PASS.

**Step 4: Inspect simplification outcome**

Check:

```bash
git diff --stat
uv run python - <<'PY'
from pathlib import Path
for path in [Path('server/api/public_routes.py'), Path('server/api/public_history_routes.py')]:
    print(path, sum(1 for _ in path.open()))
PY
```

Expected: `server/api/public_routes.py` is reduced to composition concerns only, and the new module is narrowly scoped to persisted history/replay behavior.

**Step 5: Commit or amend**

```bash
git add server/api/public_history_routes.py server/api/public_routes.py tests/api/test_agent_api.py
git commit --amend --no-edit
```

### Task 3: Close out BMAD artifacts after verification

**Objective:** Mark Story 39.3 complete and prepare the next planning handoff.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/39-3-extract-public-history-and-replay-routes-out-of-server-api-public_routes-py.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Update story record**

Add completion notes with exact verification commands/results and final file list.

**Step 2: Advance sprint status**

Set Story 39.3 to `done`. If Epic 39 is complete, mark the epic done and set the next story to the highest-value drafted follow-on item.

**Step 3: Verify BMAD artifacts are valid**

Run:

```bash
python - <<'PY'
from pathlib import Path
import yaml
yaml.safe_load(Path('_bmad-output/implementation-artifacts/sprint-status.yaml').read_text())
print('sprint-status.yaml OK')
PY
```

Expected: `sprint-status.yaml OK`.

**Step 4: Final commit**

```bash
git add _bmad-output/implementation-artifacts/39-3-extract-public-history-and-replay-routes-out-of-server-api-public_routes-py.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "docs: close story 39.3"
```

## Parallelism / sequencing note

This run should stay sequential for implementation because Story 39.3 touches the same public-route composition surface and test seam that any adjacent public-route cleanup would also modify. Parallelism is appropriate later only after Epic 39 is closed and the next story family lands on non-overlapping files.

## Validation summary

Primary commands:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'extracted_route_seams or match_history_routes or openapi_declares_public_read_contracts'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k match_history_and_replay_smoke_flow_runs_through_real_process
source .venv/bin/activate && make quality
```

## Risks / pitfalls

- Keep `/matches/completed` ordering comments and route wiring intact; do not accidentally change dynamic/static route behavior while editing the composition file.
- Preserve exact `match_not_found`, `tick_not_found`, and `match_history_unavailable` error payloads.
- Do not add a service class or route registry abstraction; plain router-builder functions are enough.
- Re-check OpenAPI schema declarations after extraction so the new builder still contributes the same public contract.
