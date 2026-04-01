# Story: Public readiness Story 2 - add OSS governance files

Status: done

## Story

As a potential user or contributor,
I want clear usage, contribution, conduct, and security guidance,
So that I can engage with the public Iron Council repository with confidence.

## Acceptance Criteria

1. Add `LICENSE` at the repository root using a low-friction open-source license that fits the current repo posture.
2. Add `CONTRIBUTING.md` with repo-specific setup and workflow guidance, including `uv sync --extra dev --frozen`, `make quality`, client checks under `client/`, BMAD-driven story execution, and behavior-first testing expectations.
3. Add `CODE_OF_CONDUCT.md` with a concise Contributor Covenant style policy adapted to this repository's current public GitHub workflow.
4. Add `SECURITY.md` with an honest disclosure path for a public GitHub repository that does not promise unsupported private channels.

## Tasks / Subtasks

- [x] Add a root `LICENSE`. (AC: 1)
- [x] Add a root `CONTRIBUTING.md`. (AC: 2)
- [x] Add a root `CODE_OF_CONDUCT.md`. (AC: 3)
- [x] Add a root `SECURITY.md`. (AC: 4)
- [x] Verify the docs against the repo workflow and update BMAD tracking. (AC: 2, 3, 4)

## Dev Notes

- This slice is anchored to `docs/plans/2026-04-01-public-repo-readiness.md` Story 2 and `docs/plans/2026-04-01-public-readiness-execution.md` Task 3.
- Scope intentionally excludes `README.md` and runtime code.
- This is a documentation/governance slice, so no runtime behavior changed and no new failing test was required.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `git status --short && git branch --show-current && git log --oneline -5`
- `make help`
- `git diff --stat`
- `make quality` (initial run failed because `uv run mypy` could not find `mypy` in the local project environment)
- `uv sync --extra dev --frozen`
- `make quality`
- `sed -n '1,220p' CONTRIBUTING.md`
- `sed -n '1,240p' CODE_OF_CONDUCT.md`
- `make help`
- `git diff --stat`
- `make quality`

### Completion Notes List

- Added a root MIT `LICENSE` to establish clear public-use terms.
- Added a concise `CONTRIBUTING.md` aligned with the repo's `uv`, `make`, BMAD, and behavior-first testing workflow.
- Added a concise `CODE_OF_CONDUCT.md` adapted from Contributor Covenant and matched to the current public GitHub moderation reality.
- Added a `SECURITY.md` that routes sensitive disclosures through GitHub private vulnerability tooling when available and otherwise avoids unsafe public disclosure details.
- Verified the repo workflow with `make help` and passed `make quality` after syncing the locked dev dependencies into `.venv`.
- Kept the change set limited to governance/trust documentation and BMAD tracking artifacts.
- Tightened `CONTRIBUTING.md` so `make setup` is the primary onboarding path while preserving the explicit `uv sync --extra dev --frozen` reference and the BMAD/testing expectations from the original acceptance criteria.
- Refined `CODE_OF_CONDUCT.md` so conduct issues are routed through GitHub-native reporting and moderation paths without implying that sensitive details should be posted publicly or inventing an unsupported private contact.

### File List

- `LICENSE`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `_bmad-output/implementation-artifacts/public-readiness-story-2-add-oss-governance-files.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
