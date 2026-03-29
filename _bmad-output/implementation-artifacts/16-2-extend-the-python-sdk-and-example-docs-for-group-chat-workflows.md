# Story 16.2: Extend the Python SDK and example docs for group-chat workflows

Status: done

## Story

As an AI agent developer,
I want the reference Python SDK and docs to cover group-chat workflows,
So that I can use the full public messaging surface without reverse-engineering new HTTP shapes by hand.

## Acceptance Criteria

1. Given the authenticated group-chat API exists, when an agent uses the Python SDK to create, list, read, and send group-chat messages, then it gets stable typed data matching the public HTTP contract.
2. Given the SDK must remain a self-contained external-consumer artifact, when group-chat support is added, then the SDK still imports and runs without repo-internal `server` package dependencies.
3. Given developers need a trustworthy onboarding path, when the SDK docs/examples describe group-chat usage, then the documented commands and snippets are covered by tests or smoke verification.

## Tasks / Subtasks

- [x] Add typed SDK models and methods for group-chat workflows. (AC: 1, 2)
- [x] Add SDK behavior tests plus standalone-import protection. (AC: 1, 2)
- [x] Update docs/examples and smoke coverage for the public group-chat workflow. (AC: 3)
- [x] Update BMAD tracking artifacts and completion notes when shipped. (AC: 3)

## Dev Notes

- Keep this story downstream of Story 16.1 so the SDK reflects the real public contract rather than a speculative one.
- Prefer boring, symmetric SDK method names that match the existing message/treaty/alliance client surface.
- Only expand the example agent if it improves onboarding without complicating the intentionally minimal example loop.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-03-29: `uv run pytest -o addopts='' tests/agent_sdk/test_python_client.py` (red: missing `create_group_chat` on `IronCouncilClient`)
- 2026-03-29: `uv run pytest -o addopts='' tests/agent_sdk/test_python_client.py`
- 2026-03-29: `uv run pytest -o addopts='' tests/e2e/test_agent_sdk_smoke.py tests/e2e/test_example_agent_smoke.py`
- 2026-03-29: `make quality`

### Completion Notes List

- Added self-contained typed SDK models and symmetric client methods for group-chat create, list, read, and send workflows without introducing any `server` imports.
- Added behavior-first SDK coverage for typed group-chat workflows and extended the real-process SDK smoke test to exercise the documented public contract.
- Updated the public SDK quickstart with a copyable standalone group-chat example and kept `example_agent.py` unchanged to preserve the minimal onboarding loop.
- Kept the implementation deliberately boring: direct Pydantic models plus four client methods, with no extra abstraction layer.

### File List

- agent-sdk/python/iron_council_client.py
- agent-sdk/README.md
- tests/agent_sdk/test_python_client.py
- tests/e2e/test_agent_sdk_smoke.py
- _bmad-output/implementation-artifacts/16-2-extend-the-python-sdk-and-example-docs-for-group-chat-workflows.md
- _bmad-output/implementation-artifacts/sprint-status.yaml

### Change Log

- 2026-03-29 18:15 UTC: Drafted Story 16.2 for SDK and doc support of group-chat workflows.
- 2026-03-29 18:35 UTC: Added standalone SDK group-chat workflows, updated public docs, extended SDK smoke coverage, and completed Story 16.2.
