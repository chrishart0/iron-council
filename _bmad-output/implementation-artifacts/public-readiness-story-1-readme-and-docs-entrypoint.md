# Story: Public readiness Story 1 - README and docs entrypoint overhaul

Status: done

## Story

As a public visitor,
I want the repository README and top-level docs entrypoint to explain Iron Council quickly and honestly,
So that I can understand what the project is, what works today, and how to try it locally.

## Acceptance Criteria

1. `README.md` opens with a clear product summary and core pillars.
2. `README.md` explains what works today versus what is still planned.
3. `README.md` includes a 5-minute quickstart for server, client, and example agent / SDK flows.
4. `README.md` surfaces the quality story (`make quality`, CI parity, coverage/smoke guidance) and links to deeper docs/governance pages.
5. `docs/index.md` exists as a curated public docs entrypoint.
6. Public-facing planning docs remove or contextualize obviously private/confidential wording while staying honest about roadmap status.

## Tasks / Subtasks

- [x] Rewrite `README.md` as a public landing page. (AC: 1, 2, 3, 4)
- [x] Create `docs/index.md` as a start-here entrypoint. (AC: 5)
- [x] Mirror the public-context wording update in `core-plan.md` and `_bmad-output/planning-artifacts/gdd.md`. (AC: 6)
- [x] Verify README still satisfies the tested local-dev docs contract. (AC: 3, 4)

## Dev Notes

- This slice is anchored to `docs/plans/2026-04-01-public-repo-readiness.md` Story 1 and `docs/plans/2026-04-01-public-readiness-execution.md` Task 2.
- The README intentionally keeps the stronger public first-impression framing while preserving the operational details enforced by `tests/test_local_dev_docs.py`.
- The planning-doc wording was softened to a public planning snapshot note rather than stripped entirely, so the docs remain honest about exploratory roadmap content.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `git diff --stat`
- `make help`
- `uv run pytest -q -o addopts='' tests/test_local_dev_docs.py`
- spec review: PASS
- quality review: REQUEST_CHANGES then APPROVED after follow-up refinement

### Completion Notes List

- Reframed `README.md` around product summary, pillars, current status, quickstart, quality story, and architecture-at-a-glance.
- Added `docs/index.md` so external readers have a curated docs entrypoint before diving into BMAD artifacts.
- Preserved required local-dev guidance such as `make db-setup`, `make db-reset`, `IRON_COUNCIL_DB_LANE`, focused `--no-cov` pytest usage, and public client route examples.
- Added README links to SDK docs plus the new public governance files (`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `LICENSE`).
- Updated `core-plan.md` and `_bmad-output/planning-artifacts/gdd.md` to describe the document as a public planning snapshot whose roadmap details remain exploratory.

### File List

- `README.md`
- `docs/index.md`
- `core-plan.md`
- `_bmad-output/planning-artifacts/gdd.md`
- `agent-sdk/README.md`
- `_bmad-output/implementation-artifacts/public-readiness-story-1-readme-and-docs-entrypoint.md`
