# Story 56.1: Add a browser smoke for the public demo walkthrough and auth-required route guardrails

Status: ready-for-review

## Story

As a delivery lead,
I want one real-browser smoke that follows the documented local demo path against the packaged runtime,
So that launch confidence no longer depends only on API/process tests and component-level client checks.

## Acceptance Criteria

1. The repo gains one small browser-driven smoke that starts the checked-in local runtime, opens the client in a real browser, and verifies the shipped public browse/detail/history/live walkthrough against the running API.
2. The same smoke proves `/lobby` and `/matches/<match_id>/play` show the existing auth-required guardrail state when no bearer token is saved.
3. The smoke saves the browser session panel API base URL and proves that setting persists for subsequent navigation or reloads.
4. The story adds the smallest honest browser harness and command path possible, keeps existing public/auth contracts unchanged, and remains easy to run locally.
5. Story-focused verification passes together with the repo-managed quality gate.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add one focused browser smoke harness over the packaged local runtime and seeded demo data. (AC: 1, 4)
- [x] Cover public browse, match detail/history/live navigation, and the auth-required guardrail routes in the same high-value smoke. (AC: 1, 2)
- [x] Persist the API base URL through the browser session panel and prove the saved value is reused. (AC: 3)
- [x] Wire the smoke into a simple repo command path and document any required browser/test bootstrap honestly. (AC: 4)
- [x] Run focused verification plus the full repo quality gate, then record the real outcomes here. (AC: 5)

## Dev Notes

- Follow `docs/plans/2026-04-04-epic-56-browser-launch-confidence-and-human-live-maintainability.md`.
- Keep the story behavior-first and browser-boundary focused; do not replace it with component-only mocks.
- Reuse the existing runtime-control entrypoints and seeded database flow rather than inventing a second demo harness.
- Keep assertions coarse and stable enough to avoid websocket/browser flake.
- Do not widen scope into human login automation, payments, or new backend endpoints.

### References

- `docs/guides/public-demo-walkthrough.md`
- `docs/operations/runtime-runbook.md`
- `tests/e2e/test_launch_readiness_smoke.py`
- `scripts/runtime-control.sh`
- `_bmad-output/planning-artifacts/epics.md#Epic-56-browser-launch-confidence-and-human-live-maintainability`

## Complete Signoff

- [x] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-04: Drafted Story 56.1 as the next post-Epic-55 launch-confidence slice.
- 2026-04-04: Added a Playwright browser smoke over the packaged runtime plus repo command wiring for the public demo walkthrough and auth guardrails.

## Debug Log References

- 2026-04-04: `make browser-smoke` red run failed because the temporary smoke runtime env only allowed the default browser origin (`http://127.0.0.1:3000`), so the browser client at `http://127.0.0.1:3100` could not load `/api/v1/matches`.
- 2026-04-04: Updated the generated smoke env in `client/playwright.config.ts` to set `IRON_COUNCIL_BROWSER_ORIGINS=http://127.0.0.1:3100`, then reran `make browser-smoke` successfully.
- 2026-04-04: `make launch-readiness-smoke` initially failed because the worktree `.venv` was missing `pytest-cov`; ran `uv sync --extra dev --frozen`, reran the smoke, and it passed.
- 2026-04-04: `make quality` initially failed because Vitest was collecting the new Playwright spec and package-provided tests from `node_modules`; constrained `client/vitest.config.ts` to the client `src/**` test set and excluded `tests/e2e/**`, then reran `make quality` successfully.
- 2026-04-04: Review follow-up found the first Playwright `webServer` bootstrap command only appeared to apply `set -euo pipefail`; switched it to `bash -euo pipefail -c` over one chained bootstrap command so `db-reset` and server startup failures stay controller-visible, then reran `make browser-smoke` and `source .venv/bin/activate && make quality` successfully.

## Completion Notes

- Added `client/tests/e2e/public-demo-smoke.spec.ts` as one coarse Playwright smoke that saves the browser session API base URL, walks `/matches` -> detail -> history -> live, verifies `/lobby` protected-route copy, and verifies the existing no-token guard on `/matches/<match_id>/play`.
- Added `client/playwright.config.ts` to start the checked-in packaged runtime through `scripts/runtime-control.sh`, reseed a deterministic SQLite database with `db-reset`, and run the production-style client with `client-start`.
- Added `make browser-smoke`, `make client-browser-install`, and the `client` `test:e2e` script so the browser smoke has one small repo-managed command path.
- Tightened the smoke follow-up by asserting the session summary through the labeled `API` row instead of the first `.session-summary dd`, and made the browser smoke bootstrap command honestly strict.
- Verified with `make browser-smoke`, `source .venv/bin/activate && make launch-readiness-smoke`, and `source .venv/bin/activate && make quality`.

## File List

- `_bmad-output/implementation-artifacts/56-1-add-a-browser-smoke-for-the-public-demo-walkthrough-and-auth-required-route-guardrails.md`
- `.gitignore`
- `Makefile`
- `client/package.json`
- `client/package-lock.json`
- `client/playwright.config.ts`
- `client/tests/e2e/public-demo-smoke.spec.ts`
- `client/vitest.config.ts`
