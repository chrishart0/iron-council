# Story: 47.1 Sync canonical architecture and public entrypoint docs

## Status
Draft

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
- [ ] Refresh `core-architecture.md` to describe the real shipped HTTP/websocket surface. (AC: 1, 2)
- [ ] Refresh `README.md` and `docs/index.md` so public readers can discover the shipped public pages/contracts first. (AC: 2)
- [ ] Add a small docs regression guard in the existing pytest doc checks. (AC: 3)
- [ ] Re-run focused docs verification and the repo-managed quality gate after merge. (AC: 4)
- [ ] Update this story artifact and sprint status with real outcomes. (AC: 4)

## Dev Notes
- Keep this story narrow and truthful. The goal is sync, not a full architecture rewrite.
- Prior review found concrete drift around the REST section framing, websocket/auth docs, env var naming, and the public profile/history surfaces.
- Favor small stable assertions in docs tests rather than brittle full-document snapshots.

## Testing
- `source .venv/bin/activate && uv run pytest --no-cov tests/test_local_dev_docs.py -q`
- `source .venv/bin/activate && make quality`

## Change Log
- 2026-04-03: Drafted Story 47.1 after post-46 review found the canonical/public docs lagging the shipped public browse/profile/history/runtime surfaces.
