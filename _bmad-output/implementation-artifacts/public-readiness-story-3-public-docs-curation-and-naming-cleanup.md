# Story: Public readiness Story 3 - public docs curation and naming cleanup

Status: done

## Story

As an external reader,
I want the repo structure and naming to feel intentional,
So that the project feels credible rather than accidental.

## Acceptance Criteria

1. Public naming is aligned across the primary user-visible repo surfaces.
2. Confusing or confidential wording is removed or clearly contextualized for a public audience.
3. `docs/index.md` remains a credible public docs entrypoint.
4. Sprint tracking reflects Story 3 truthfully once verification is complete.

## Tasks / Subtasks

- [x] Update the primary public-facing naming surfaces to `Iron Council` / `iron-council`. (AC: 1)
- [x] Keep compatibility-sensitive internal names stable where they are already the public contract, including the `IRON_COUNCIL_*` env var namespace and the SDK module path. (AC: 1)
- [x] Keep the curated docs entrypoint coherent after the naming cleanup and remove stale public-readiness wording that implied the naming issue was still open. (AC: 2, 3)
- [x] Verify the metadata/settings/docs contract tests first, then pass the full repo quality gate. (AC: 4)
- [x] Update sprint tracking to reflect Story 3 and the overall public-readiness epic as complete. (AC: 4)

## Dev Notes

- This slice is anchored to `docs/plans/2026-04-01-public-repo-readiness.md` Story 3 and `docs/plans/2026-04-01-public-readiness-execution.md` Tasks 2 and 4.
- The Story 3 artifact file was missing when this work started, so this implementation record was added as part of completing the story.
- The change intentionally keeps the internal compatibility-sensitive surfaces stable where a rename would be broader than the public-readiness goal, while aligning the main package/service/local-dev/public strings.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `sed -n '1,240p' docs/plans/2026-04-01-public-repo-readiness.md`
- `sed -n '1,260p' docs/plans/2026-04-01-public-readiness-execution.md`
- `sed -n '1,260p' _bmad-output/implementation-artifacts/sprint-status.yaml`
- `rg -n "iron-counsil|iron counsil|Iron Counsil|confidential|Confidential" README.md docs/index.md pyproject.toml server/main.py tests/api/test_metadata.py env.local.example compose.support-services.yaml server/settings.py tests`
- `uv run pytest -q -o addopts='' tests/api/test_metadata.py tests/test_settings.py tests/test_local_dev_docs.py` (red)
- `uv run pytest -q -o addopts='' tests/api/test_metadata.py tests/test_settings.py tests/test_local_dev_docs.py` (green)
- `make quality`

### Completion Notes List

- Renamed the package metadata, FastAPI title, root metadata contract, and public local-dev defaults from `counsil` to `council`.
- Kept the existing `IRON_COUNCIL_*` environment variable namespace and SDK module path unchanged to avoid broader compatibility churn.
- Updated the public assessment and follow-up backlog so they no longer claim naming cleanup is still unresolved.
- Verified that `docs/index.md` remained a credible public entrypoint and did not require structural changes for this slice.
- Added the missing Story 3 implementation artifact and closed the public-readiness epic in sprint tracking because Story 4 had identified naming cleanup as the last remaining blocker.

### File List

- `pyproject.toml`
- `uv.lock`
- `server/main.py`
- `server/settings.py`
- `README.md`
- `env.local.example`
- `compose.support-services.yaml`
- `tests/api/test_metadata.py`
- `tests/test_settings.py`
- `tests/test_local_dev_docs.py`
- `docs/consulting/public-repo-assessment-2026-04-01.md`
- `docs/issues/public-readiness-follow-ups.md`
- `_bmad-output/implementation-artifacts/public-readiness-story-3-public-docs-curation-and-naming-cleanup.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
