# Story 15.2: Add a minimal example agent and SDK quickstart guide

Status: done

## Story

As an AI agent developer,
I want a minimal runnable example agent and setup guide,
So that I can copy a working loop instead of reverse-engineering the API from tests and docs.

## Acceptance Criteria

1. Given the reference Python SDK and a running seeded server, when the example agent is executed with the documented environment variables or CLI arguments, then it authenticates, joins a match if needed, fetches visible state, and performs one deterministic decision cycle using only the SDK surface.
2. Given the example is meant to teach agent authors the public contract, when it decides what to do each tick, then it stays intentionally simple, deterministic, and free of internal server imports or implementation-detail shortcuts.
3. Given new developers need an onboarding path, when the quickstart documentation is read and exercised, then it documents installation, configuration, and run commands that are covered by tests or smoke verification.

## Tasks / Subtasks

- [x] Add a minimal runnable example agent script. (AC: 1, 2)
- [x] Document SDK setup and example-agent usage in `agent-sdk/README.md`. (AC: 3)
- [x] Add smoke or contract coverage proving the documented commands work. (AC: 1, 3)
- [x] Update BMAD status, completion notes, and debug references when shipped. (AC: 3)

## Dev Notes

- Keep this story downstream of Story 15.1 so the example consumes the public SDK instead of duplicating HTTP code.
- Favor one deterministic cycle over a complicated autonomous loop.
- Use the same real app boundary and seeded dev environment already exercised elsewhere in the repo.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest -o addopts='' tests/agent_sdk/test_example_agent.py` (red: failed because `agent-sdk/python/example_agent.py` did not exist; green: passed after implementation)
- `uv run pytest --no-cov tests/e2e/test_example_agent_smoke.py` (red: failed because repo pytest config injects coverage args without `pytest-cov`; replaced with `-o addopts=''` for execution in this repo)
- `uv run pytest -o addopts='' tests/e2e/test_example_agent_smoke.py`
- `make quality`

### Completion Notes List

- Added `agent-sdk/python/example_agent.py` as a minimal deterministic one-shot agent that accepts CLI or env configuration, joins a match, fetches visible state, submits an empty order batch, and prints a concise JSON summary.
- Added `agent-sdk/README.md` with copyable setup, configuration, run commands, and the documented no-op decision cycle.
- Added behavior-first coverage for CLI/env configuration, first-match selection, structured JSON output, and standalone import without server internals.
- Added a real subprocess smoke test that runs the documented example command against the seeded app.
- Promoted `httpx` and `pydantic` to runtime dependencies in `pyproject.toml` so `uv run python agent-sdk/python/example_agent.py ...` works without extra dependency flags.

### File List

- `agent-sdk/python/example_agent.py`
- `agent-sdk/README.md`
- `tests/agent_sdk/test_example_agent.py`
- `tests/e2e/test_example_agent_smoke.py`
- `pyproject.toml`
- `uv.lock`
- `_bmad-output/implementation-artifacts/15-2-add-a-minimal-example-agent-and-sdk-quickstart-guide.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-29 17:55 UTC: Drafted Story 15.2 for the example agent and quickstart.
- 2026-03-29 17:27 UTC: Implemented the minimal example agent, added quickstart docs and smoke coverage, and updated BMAD tracking artifacts.
