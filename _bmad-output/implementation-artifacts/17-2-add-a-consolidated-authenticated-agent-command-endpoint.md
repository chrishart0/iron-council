# Story 17.2: Add a consolidated authenticated agent command endpoint

Status: done

## Story

As an AI agent developer,
I want to submit orders, outgoing messages, and diplomacy actions in one authenticated command envelope,
So that my turn loop can write one public contract per tick instead of coordinating multiple mutation endpoints by hand.

## Acceptance Criteria

1. Given an authenticated agent joined to a match, when it posts a consolidated command envelope for the current tick, then the server validates the match/tick identity once, applies accepted orders through the existing validation pipeline, records outgoing messages, applies requested treaty or alliance actions, and returns a stable acceptance summary.
2. Given any contained action is invalid for the authenticated player or match, when the command endpoint validates the envelope, then it returns structured errors without partially mutating unrelated side effects.
3. Given the consolidated command endpoint is only a public-contract convenience layer, when it is implemented, then the underlying focused REST endpoints remain available and keep their existing behavior-first tests passing unchanged.

## Tasks / Subtasks

- [x] Define the public command-envelope request/response models. (AC: 1, 2)
- [x] Add a transactional orchestration layer over existing focused order/message/diplomacy primitives. (AC: 1, 2)
- [x] Add the authenticated command endpoint and structured error mapping. (AC: 1, 2)
- [x] Add behavior-first API, running-app, and SDK contract coverage. (AC: 1, 2, 3)
- [x] Update docs/BMAD tracking artifacts and completion notes when the story ships. (AC: 3)

## Dev Notes

- Sequence after Story 17.1 so the read-side contract is stable first.
- Preserve the existing focused endpoints as the underlying public building blocks.
- Favor all-or-nothing validation before side effects to avoid partial turn writes.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py tests/agent_sdk/test_python_client.py`
- `uv run pytest --override-ini addopts='' tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py`
- `make quality`

### Completion Notes List

- Switched the canonical authenticated convenience endpoint to `/api/v1/matches/{match_id}/command` and kept the plural `/commands` route as a hidden backward-compatible alias.
- Extended the command envelope to cover world, direct, and group-chat outgoing messages by reusing the existing group-chat message primitives and validating group-chat visibility during the scratch-registry preflight.
- Preserved all-or-nothing command execution by preflighting the full envelope against a scratch registry before mutating the live match registry, including invalid bundled group-chat messages.
- Preserved the existing focused mutation endpoints and kept their behavior-first tests passing unchanged.
- Extended the Python SDK with typed command-envelope request models, a canonical `submit_command()` helper, and a backward-compatible `submit_command_envelope()` alias.
- Improved nested command validation mapping for later message items plus invalid treaty action/type literals, and added explicit `401` OpenAPI metadata for the authenticated routes in this contract surface.
- Added API-boundary, running-app, smoke, and SDK tests for successful bundled group-chat flows, structured validation errors, and no-partial-mutation failures.

### File List

- _bmad-output/implementation-artifacts/17-2-add-a-consolidated-authenticated-agent-command-endpoint.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- agent-sdk/python/iron_council_client.py
- server/agent_registry.py
- server/main.py
- server/models/api.py
- tests/agent_sdk/test_python_client.py
- tests/api/test_agent_api.py
- tests/api/test_agent_process_api.py
- tests/e2e/test_api_smoke.py

### Change Log

- 2026-03-29 19:25 UTC: Drafted Story 17.2 as the follow-on consolidated command envelope.
- 2026-03-29 21:17 UTC: Implemented the consolidated authenticated command endpoint, SDK helper, and transactional coverage.
- 2026-03-29 21:32 UTC: Patched the command contract to cover bundled group-chat messages, restored the singular canonical route, tightened nested validation errors, and refreshed authenticated route metadata.
