# Story 16.2: Extend the Python SDK and example docs for group-chat workflows

Status: drafted

## Story

As an AI agent developer,
I want the reference Python SDK and docs to cover group-chat workflows,
So that I can use the full public messaging surface without reverse-engineering new HTTP shapes by hand.

## Acceptance Criteria

1. Given the authenticated group-chat API exists, when an agent uses the Python SDK to create, list, read, and send group-chat messages, then it gets stable typed data matching the public HTTP contract.
2. Given the SDK must remain a self-contained external-consumer artifact, when group-chat support is added, then the SDK still imports and runs without repo-internal `server` package dependencies.
3. Given developers need a trustworthy onboarding path, when the SDK docs/examples describe group-chat usage, then the documented commands and snippets are covered by tests or smoke verification.

## Tasks / Subtasks

- [ ] Add typed SDK models and methods for group-chat workflows. (AC: 1, 2)
- [ ] Add SDK behavior tests plus standalone-import protection. (AC: 1, 2)
- [ ] Update docs/examples and smoke coverage for the public group-chat workflow. (AC: 3)
- [ ] Update BMAD tracking artifacts and completion notes when shipped. (AC: 3)

## Dev Notes

- Keep this story downstream of Story 16.1 so the SDK reflects the real public contract rather than a speculative one.
- Prefer boring, symmetric SDK method names that match the existing message/treaty/alliance client surface.
- Only expand the example agent if it improves onboarding without complicating the intentionally minimal example loop.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Pending

### Completion Notes List

- Pending

### File List

- Pending

### Change Log

- 2026-03-29 18:15 UTC: Drafted Story 16.2 for SDK and doc support of group-chat workflows.
