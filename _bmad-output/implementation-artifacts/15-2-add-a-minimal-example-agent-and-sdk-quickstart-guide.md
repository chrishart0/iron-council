# Story 15.2: Add a minimal example agent and SDK quickstart guide

Status: drafted

## Story

As an AI agent developer,
I want a minimal runnable example agent and setup guide,
So that I can copy a working loop instead of reverse-engineering the API from tests and docs.

## Acceptance Criteria

1. Given the reference Python SDK and a running seeded server, when the example agent is executed with the documented environment variables or CLI arguments, then it authenticates, joins a match if needed, fetches visible state, and performs one deterministic decision cycle using only the SDK surface.
2. Given the example is meant to teach agent authors the public contract, when it decides what to do each tick, then it stays intentionally simple, deterministic, and free of internal server imports or implementation-detail shortcuts.
3. Given new developers need an onboarding path, when the quickstart documentation is read and exercised, then it documents installation, configuration, and run commands that are covered by tests or smoke verification.

## Tasks / Subtasks

- [ ] Add a minimal runnable example agent script. (AC: 1, 2)
- [ ] Document SDK setup and example-agent usage in `agent-sdk/README.md`. (AC: 3)
- [ ] Add smoke or contract coverage proving the documented commands work. (AC: 1, 3)
- [ ] Update BMAD status, completion notes, and debug references when shipped. (AC: 3)

## Dev Notes

- Keep this story downstream of Story 15.1 so the example consumes the public SDK instead of duplicating HTTP code.
- Favor one deterministic cycle over a complicated autonomous loop.
- Use the same real app boundary and seeded dev environment already exercised elsewhere in the repo.

## Dev Agent Record

### Agent Model Used

Pending.

### Debug Log References

- Pending implementation.

### Completion Notes List

- Pending implementation.

### File List

- Pending implementation.

### Change Log

- 2026-03-29 17:55 UTC: Drafted Story 15.2 for the example agent and quickstart.
