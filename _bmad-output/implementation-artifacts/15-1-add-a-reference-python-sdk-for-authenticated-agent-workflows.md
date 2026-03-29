# Story 15.1: Add a reference Python SDK for authenticated agent workflows

Status: in-progress

## Story

As an AI agent developer,
I want a small Python client for the authenticated Iron Council API,
So that I can list matches, join, poll state, submit orders, and interact with diplomacy endpoints without hand-rolling HTTP glue.

## Acceptance Criteria

1. Given a base URL and valid `X-API-Key`, when an agent uses the SDK to call profile, match, state, order, message, treaty, or alliance workflows, then the SDK sends the correct authenticated requests and returns stable typed data for the public API contract.
2. Given the server responds with a structured API error or transport failure, when the SDK request fails, then the caller receives one clear exception carrying the HTTP status and repo-style API error details without leaking secrets.
3. Given the repo requires behavior-first and real-process verification, when the SDK story is implemented, then it includes in-process contract tests plus at least one running-app integration or smoke path that uses the SDK against the real local server boundary.

## Tasks / Subtasks

- [ ] Create the minimal SDK surface for authenticated agent workflows. (AC: 1, 2)
  - [ ] Add a narrow client module under `agent-sdk/python/` with one shared request helper and stable methods for the current REST surface.
  - [ ] Add one repo-style exception carrying `status_code`, `error_code`, and `message` for API failures.
  - [ ] Keep secrets out of `repr`/error text and avoid coupling the SDK to internal server objects beyond public response parsing.
- [ ] Add behavior-first SDK contract tests. (AC: 1, 2)
  - [ ] Cover happy-path match/profile/state/order/message/treaty/alliance calls against the in-process FastAPI app.
  - [ ] Cover structured API-error propagation and transport-failure handling.
  - [ ] Keep tests focused on public behavior, not internal helper sequencing.
- [ ] Add real-running-app verification and keep the harness simple. (AC: 3)
  - [ ] Exercise at least one join → state → submit or diplomacy flow through `running_seeded_app` using the SDK.
  - [ ] Extend lint/type/test config so the new SDK files are included in the standard quality gate.
  - [ ] Run the full repository quality gate after the SDK lands.
- [ ] Update BMAD and docs artifacts. (AC: 3)
  - [ ] Record debug commands and completion notes in this story file.
  - [ ] Update the implementation plan and sprint status when the story is complete.

## Dev Notes

- Anchor to `core-architecture.md` sections 5.2, 7, and 8 Phase 2, plus the project-structure note for `agent-sdk/python/iron_council_client.py`.
- Keep the SDK intentionally narrow and by-the-book: synchronous `httpx` is sufficient for the reference client today.
- Favor typed parsing of existing API response models where practical, but do not introduce a large packaging abstraction or a publish/install workflow in this story.
- The SDK should teach the public contract; it must not bypass it by importing registries, fixtures, or internal route helpers.

### Candidate Implementation Surface

- `agent-sdk/python/iron_council_client.py`
- `tests/agent_sdk/test_python_client.py`
- `tests/e2e/test_agent_sdk_smoke.py`
- `pyproject.toml`
- `Makefile`
- `docs/plans/2026-03-29-story-15-1-python-agent-sdk.md`
- `_bmad-output/implementation-artifacts/15-1-add-a-reference-python-sdk-for-authenticated-agent-workflows.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### References

- `core-plan.md` sections 9.1, 9.2, and 9.4
- `core-architecture.md` sections 5.2, 7, and 8 Phase 2
- `_bmad-output/planning-artifacts/epics.md` Story 15.1 acceptance criteria
- `AGENTS.md` guidance favoring behavior-first API tests, real-process verification, and KISS-by-default changes

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Pending implementation.

### Completion Notes List

- Pending implementation.

### File List

- Pending implementation.

### Change Log

- 2026-03-29 17:55 UTC: Drafted Story 15.1 for the reference Python SDK.
