# Story: 47.1 Sync canonical architecture and public entrypoint docs

## Status
Done

## Story
**As a** public reader and contributor,
**I want** the canonical architecture and public entrypoint docs to match the shipped Iron Council surfaces,
**so that** the repo's source-of-truth documents explain the real browse/profile/history/runtime contract instead of stale pre-extraction assumptions.

## Acceptance Criteria
1. `core-architecture.md` accurately distinguishes public HTTP reads, authenticated human/agent HTTP routes, and the public spectator vs authenticated player websocket paths.
2. The canonical/public entrypoint docs enumerate the shipped public browse/profile/history surfaces and use the current config names (for example `IRON_COUNCIL_BROWSER_ORIGINS`) instead of stale env or route names.
3. A lightweight docs regression test pins the most important route/env-name promises so this drift does not quietly return.
4. Focused docs verification passes, and the repo remains in a simple coherent state without a giant architecture rewrite.

## Tasks / Subtasks
- [x] Refresh `core-architecture.md` to describe the real shipped HTTP/websocket surface. (AC: 1, 2)
- [x] Refresh `README.md` and `docs/index.md` so public readers can discover the shipped public pages/contracts first. (AC: 2)
- [x] Add a small docs regression guard in the existing pytest doc checks. (AC: 3)
- [x] Re-run focused docs verification and the strongest practical repo-managed quality gate in this worktree. (AC: 4)
- [x] Update this story artifact and sprint status with real outcomes. (AC: 4)

## Dev Notes
- Keep this story narrow and truthful. The goal is sync, not a full architecture rewrite.
- Prior review found concrete drift around the REST section framing, websocket/auth docs, env var naming, and the public profile/history surfaces.
- Favor small stable assertions in docs tests rather than brittle full-document snapshots.

## Testing
- `source .venv/bin/activate && uv run pytest --no-cov tests/test_local_dev_docs.py -q`
- `source .venv/bin/activate && make quality`

## Change Log
- 2026-04-03: Drafted Story 47.1 after post-46 review found the canonical/public docs lagging the shipped public browse/profile/history/runtime surfaces.
- 2026-04-03: Completed Story 47.1 with a narrow canonical-doc sync for public/authenticated API and websocket surfaces plus a lightweight regression guard in `tests/test_local_dev_docs.py`.

## Dev Agent Record
### Agent Model Used
- GPT-5 Codex

### Debug Log References
- RED harness nuance: `source .venv/bin/activate && uv run pytest --no-cov tests/test_local_dev_docs.py -q` could not run as written because `.venv/bin/activate` did not exist yet in the fresh worktree.
- RED harness nuance: `uv run pytest --no-cov tests/test_local_dev_docs.py -q` failed before collection because the repo pytest config injected coverage flags that were unavailable in this environment.
- RED: `uv run pytest -q -o addopts='' tests/test_local_dev_docs.py` initially failed because `core-architecture.md` did not mention `/api/v1/agents/{agent_id}/profile`, and the public entrypoint docs did not surface the shipped `/leaderboard` and related public routes.
- GREEN: `uv run pytest -q -o addopts='' tests/test_local_dev_docs.py`
- GREEN within `make quality`: `uv run ruff format --check server tests agent-sdk/python`
- GREEN within `make quality`: `uv run ruff check server tests agent-sdk/python`
- QUALITY-GATE BLOCKER: `make quality` stopped at `uv run mypy server tests agent-sdk/python` with `Failed to spawn: mypy` because `mypy` was not available in this environment.

### Completion Notes List
- Updated `core-architecture.md` section 5.2 so it now describes the shipped mixed public/authenticated HTTP surface instead of framing the API as agent-only.
- Clarified the websocket contract so the public spectator path is read-only and unauthenticated, while the player websocket is tied to a human JWT token plus optional matching `player_id`.
- Replaced the stale `CORS_ORIGINS` naming in the canonical architecture doc with the current `IRON_COUNCIL_BROWSER_ORIGINS` configuration and refreshed the high-level project structure to match the extracted `server/api`, `server/db`, and current client route layout.
- Expanded `README.md` and `docs/index.md` just enough to make the shipped public leaderboard, completed-match summaries, match history/replay, and public human/agent profile pages easier to discover.
- Added a small docs regression guard in `tests/test_local_dev_docs.py` that pins the most important route/env/websocket promises without introducing brittle full-document snapshots.
- Performed a simplification pass after the edits and kept the architecture changes limited to drift correction rather than rewriting the whole document.

### File List
- `core-architecture.md`
- `README.md`
- `docs/index.md`
- `tests/test_local_dev_docs.py`
- `_bmad-output/implementation-artifacts/47-1-sync-canonical-architecture-and-public-entrypoint-docs.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## QA Results
- PASS: AC1. `core-architecture.md` now distinguishes public HTTP reads, authenticated HTTP/player routes, and the public spectator versus authenticated player websocket usage.
- PASS: AC2. The canonical/public entrypoint docs now enumerate the shipped public leaderboard, completed-match, history/replay, and public profile surfaces and use `IRON_COUNCIL_BROWSER_ORIGINS`.
- PASS: AC3. `tests/test_local_dev_docs.py` now contains a lightweight regression guard for the critical route/env/websocket promises.
- PARTIAL: AC4. Focused docs verification passed with `uv run pytest -q -o addopts='' tests/test_local_dev_docs.py`, and the repo quality gate advanced through Ruff formatting/lint checks, but `make quality` was blocked by missing `mypy` in this environment rather than by a product regression in this story.
