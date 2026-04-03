# Story: 45.1 Stabilize Next.js client dev root and generated types

## Status
Done

## Story
**As a** local developer,
**I want** `client/npm run dev` to use the real client workspace without warning noise or generated-file drift,
**so that** local browser work starts cleanly and does not dirty the repo with avoidable `next-env.d.ts` changes.

## Acceptance Criteria
1. `client/next.config.ts` explicitly anchors the Next.js/Turbopack root to the client workspace so `npm run dev` no longer emits the inferred-workspace-root warning in this repo.
2. A focused automated test proves the config exports the explicit client root rather than relying on implicit discovery.
3. A repo-level subprocess smoke test boots `npm run dev` from `client/`, captures startup output, and proves both that the workspace-root warning is absent and `client/next-env.d.ts` stays unchanged before/after the boot.
4. Focused client/test commands and the strongest practical related repo-managed checks pass.

## Tasks / Subtasks
- [x] Add explicit client-root config in `client/next.config.ts`. (AC: 1)
- [x] Add a focused config test in the client test suite. (AC: 2)
- [x] Add a subprocess smoke regression for `npm run dev` startup output plus `next-env.d.ts` stability. (AC: 3)
- [x] Run focused client + pytest checks and the relevant broader client verification. (AC: 4)
- [x] Update this story artifact and sprint status with real verification outcomes. (AC: 4)

## Dev Notes
- This follows the observed local-dev issue from 2026-04-03 QA: `npm run dev` warned that Next.js inferred the workspace root from `/home/hermes/.hermes/hermes-agent/package-lock.json`, and the run rewrote tracked `client/next-env.d.ts` from `./.next/types/routes.d.ts` to `./.next/dev/types/routes.d.ts`.
- Keep the solution narrow: explicit client workspace root plus a tiny `next-env.d.ts` normalization seam, with no broader app-container/runtime changes.
- Prefer one small config seam and boring tests over new helper abstractions.

## Testing
- `cd client && npm test -- --run src/next-config.test.ts`
- `uv run pytest --no-cov tests/test_client_dev_smoke.py -q`
- `make client-lint`
- `make client-test`
- `make client-build`
- `uv run pytest --no-cov tests/test_local_dev_docs.py tests/test_client_dev_smoke.py -q`
- `make quality`

## Change Log
- 2026-04-03: Drafted Story 45.1 after local QA reproduced the Next.js workspace-root warning and `client/next-env.d.ts` drift.
- 2026-04-03: Completed Story 45.1 with an explicit Turbopack client root, a tiny `next-env.d.ts` normalizer for dev/build shutdown paths, and a repo-level `next dev` smoke test anchored to the canonical tracked file.

## Dev Agent Record
### Agent Model Used
- GPT-5 Codex

### Debug Log References
- RED: `cd client && npm test -- --run src/next-config.test.ts` failed because `nextConfig.turbopack?.root` was `undefined`.
- RED nuance: the first draft of `uv run pytest --no-cov tests/test_client_dev_smoke.py -q` passed while `client/next-env.d.ts` was already pre-drifted to `./.next/dev/types/routes.d.ts`; the test was tightened to assert the canonical tracked `./.next/types/routes.d.ts` import before the dev boot.
- Probe: `cd client && npm run dev -- --hostname 127.0.0.1 --port 3901` confirmed the inferred-workspace-root warning was gone after adding `turbopack.root`, and showed Next.js 16 still generates the dev route-types import during `next dev`.
- Design decision: treat `client/next-env.d.ts` with `import "./.next/types/routes.d.ts";` as the canonical tracked repo state because `next build` already regenerates that form.
- Implementation note: `client/scripts/run-next-dev.mjs` now wraps `next dev`, forwards developer interrupts, and normalizes `client/next-env.d.ts` back to the canonical build-style import on shutdown; `client/scripts/normalize-next-env.mjs` is also wired through `postbuild`.
- GREEN: `cd client && npm test -- --run src/next-config.test.ts`
- GREEN: `uv run pytest --no-cov tests/test_client_dev_smoke.py -q`
- GREEN: `make client-lint`
- GREEN: `make client-test`
- GREEN: `make client-build`
- GREEN: `uv run pytest --no-cov tests/test_local_dev_docs.py tests/test_client_dev_smoke.py -q`
- GREEN: `make quality`

### Completion Notes List
- Added a single explicit config seam in `client/next.config.ts` that pins `turbopack.root` to the absolute `client/` workspace path.
- Added `client/src/next-config.test.ts` to prove the exported config does not rely on implicit workspace discovery.
- Added `client/scripts/normalize-next-env.mjs` and `client/scripts/run-next-dev.mjs` so both `npm run dev` shutdowns and `npm run build` converge the repo back to one canonical tracked `client/next-env.d.ts` form.
- Updated `client/package.json` so `npm run dev` uses the wrapper and `postbuild` reasserts the canonical tracked import after `next build`.
- Updated `tests/test_client_dev_smoke.py` to start from the canonical tracked build-style import, boot `npm run dev`, stop it with a developer-style interrupt, and assert the repo returns to the same file state with no workspace-root warning.
- Left `client/next-env.d.ts` in the stable tracked `import "./.next/types/routes.d.ts";` form.

### File List
- `client/package.json`
- `client/next.config.ts`
- `client/next-env.d.ts`
- `client/scripts/normalize-next-env.mjs`
- `client/scripts/run-next-dev.mjs`
- `client/src/next-config.test.ts`
- `tests/test_client_dev_smoke.py`
- `docs/plans/2026-04-03-story-45-1-nextjs-dev-root-stability.md`
- `_bmad-output/implementation-artifacts/45-1-stabilize-nextjs-client-dev-root-and-generated-types.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## QA Results
- PASS: AC1. `client/next.config.ts` now exports `turbopack.root` as the absolute `client/` workspace path.
- PASS: AC2. Focused Vitest coverage locks that explicit root in `client/src/next-config.test.ts`.
- PASS: AC3. The repo-level subprocess smoke test proves `npm run dev` startup output no longer includes the inferred-workspace-root warning and that `client/next-env.d.ts` returns to the canonical tracked `./.next/types/routes.d.ts` import after a developer-style interrupt.
- PASS: AC4. Required focused and broader related checks passed:
  - `cd client && npm test -- --run src/next-config.test.ts`
  - `uv run pytest --no-cov tests/test_client_dev_smoke.py -q`
  - `make client-lint`
  - `make client-test`
  - `make client-build`
  - `uv run pytest --no-cov tests/test_local_dev_docs.py tests/test_client_dev_smoke.py -q`
  - `make quality`
