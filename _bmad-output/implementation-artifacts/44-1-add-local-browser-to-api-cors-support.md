# Story: 44.1 Add local browser-to-API CORS support

Status: done

## Story

As a local developer or reviewer,
I want the Next.js browser app at `http://127.0.0.1:3000` to call the FastAPI API at `http://127.0.0.1:8000` without cross-origin failures,
So that the shipped local public and human browser flows actually work in dev mode against the real server.

## Acceptance Criteria

1. `create_app()` installs an explicit CORS policy that allows the shipped local browser origin(s) to call the HTTP API and receive the expected `Access-Control-Allow-Origin` header on both preflight and normal browser requests.
2. The allowed browser origins come from a small explicit settings seam with a narrow default for the documented local browser workflow and an override for alternate local dev origins.
3. Unlisted origins do not receive the allow-origin echo, so the policy stays explicit rather than wildcard/open-ended.
4. README and local env docs describe the real browser workflow and the optional browser-origin override knob without implying app-containerized runtime changes.
5. Focused API/doc verification passes, followed by the strongest practical repo-managed quality gate for the touched surface.

## Tasks / Subtasks

- [ ] Add a minimal explicit browser-origin settings seam. (AC: 2)
- [ ] Install FastAPI CORS middleware and prove preflight + normal request behavior from the API boundary. (AC: 1, 3)
- [ ] Update README/env docs to match the shipped local browser workflow. (AC: 4)
- [ ] Run focused verification, quality checks, and a simplification pass. (AC: 5)

## Dev Notes

- Keep this story boring and explicit: one settings seam, one middleware install, no speculative deployment policy.
- The source motivation is a real local browser blocker: public/client pages at `http://127.0.0.1:3000` could not fetch `http://127.0.0.1:8000/api/v1/*` because the API emitted no CORS headers.
- Prefer API-boundary tests over framework-internal middleware inspection.
- Preserve the repo's host-run app + real backing services dev model.

## Dev Agent Record

### Debug Log

- 2026-04-03: Drafted after Epic 43 to remove the known local browser blocker and make the shipped Next.js dev workflow actually usable against the FastAPI API.
- 2026-04-03: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'cors'`
- 2026-04-03: `uv run pytest -o addopts='' tests/test_local_dev_docs.py`
- 2026-04-03: `make quality` (initial failure in fresh worktree: `uv run mypy` could not spawn because the worktree dev environment had not been synced yet)
- 2026-04-03: `make install`
- 2026-04-03: `make quality`
- 2026-04-03: Spec review PASS against Story 44.1 acceptance criteria.
- 2026-04-03: Code-quality review APPROVED; reviewer suggested a dedicated settings-unit test as a possible later improvement but found no blocking issues.

### Completion Notes

- Added an explicit `IRON_COUNCIL_BROWSER_ORIGINS` settings seam with narrow local defaults for `http://127.0.0.1:3000` and `http://localhost:3000`.
- Wired FastAPI `CORSMiddleware` in `create_app()` so allowed local browser origins now receive `Access-Control-Allow-Origin` headers on both preflight and normal API requests.
- Added API-boundary regressions for default/override origin settings, allowed-origin preflight/simple requests, and the absence of an allow-origin echo for an unlisted origin.
- Updated the README and `env.local.example` so the documented host-run server + Next.js browser workflow now matches the shipped CORS behavior and optional override knob.
- Fresh-worktree quality initially failed because the worker environment was not synced (`mypy` missing on PATH for `uv run`). Running `make install` in the worktree resolved the bootstrap issue, after which `make quality` passed.

### File List

- `_bmad-output/implementation-artifacts/44-1-add-local-browser-to-api-cors-support.md`
- `README.md`
- `docs/plans/2026-04-03-story-44-1-local-browser-cors.md`
- `env.local.example`
- `server/main.py`
- `server/settings.py`
- `tests/api/test_agent_api.py`
- `tests/test_local_dev_docs.py`

### Change Log

- 2026-04-03: Drafted Story 44.1 for local browser/API cross-origin support.
- 2026-04-03: Implemented local browser CORS settings/middleware, added API/doc regressions, and verified the repo quality gate after bootstrapping the fresh worktree environment.
