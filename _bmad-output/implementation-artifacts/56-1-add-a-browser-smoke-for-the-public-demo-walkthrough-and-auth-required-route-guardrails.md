# Story 56.1: Add a browser smoke for the public demo walkthrough and auth-required route guardrails

Status: ready-for-dev

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

- [ ] Add one focused browser smoke harness over the packaged local runtime and seeded demo data. (AC: 1, 4)
- [ ] Cover public browse, match detail/history/live navigation, and the auth-required guardrail routes in the same high-value smoke. (AC: 1, 2)
- [ ] Persist the API base URL through the browser session panel and prove the saved value is reused. (AC: 3)
- [ ] Wire the smoke into a simple repo command path and document any required browser/test bootstrap honestly. (AC: 4)
- [ ] Run focused verification plus the full repo quality gate, then record the real outcomes here. (AC: 5)

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

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-04: Drafted Story 56.1 as the next post-Epic-55 launch-confidence slice.

## Debug Log References

- Pending implementation.

## Completion Notes

- Pending implementation.

## File List

- `_bmad-output/implementation-artifacts/56-1-add-a-browser-smoke-for-the-public-demo-walkthrough-and-auth-required-route-guardrails.md`
