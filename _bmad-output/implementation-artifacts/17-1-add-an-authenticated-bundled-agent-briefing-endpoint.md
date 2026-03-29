# Story 17.1: Add an authenticated bundled agent briefing endpoint

Status: done

## Story

As an AI agent developer,
I want one authenticated endpoint that returns my current fog-filtered state plus relevant communication and diplomacy context,
So that I can evaluate a turn from one stable contract instead of stitching together multiple HTTP reads.

## Acceptance Criteria

1. Given an authenticated agent joined to a match, when it requests the bundled agent briefing for that match, then the response includes the existing fog-filtered state projection, visible alliance status, visible treaties, visible group chats, and message buckets shaped for direct, group, and world consumption.
2. Given agents need an incremental polling loop instead of replaying the entire communication history every tick, when the client passes a deterministic since-tick cursor, then the bundled briefing only includes messages and diplomacy events at or after that tick while keeping the current state snapshot authoritative.
3. Given the bundled contract is meant to reduce integration risk for external agents, when the endpoint is documented and tested, then behavior-first API tests, running-app checks, and SDK-facing contract smoke coverage verify the exact public JSON shape without depending on repo-internal server imports.

## Tasks / Subtasks

- [x] Define the public briefing models and query contract in `server/models/api.py`. (AC: 1, 2)
- [x] Add registry helpers for since-tick filtering of visible messages and diplomacy records. (AC: 1, 2)
- [x] Add the authenticated bundled read endpoint plus validation/error handling in `server/main.py`. (AC: 1, 2)
- [x] Add behavior-first API, running-app, and SDK smoke coverage for the exact contract. (AC: 1, 2, 3)
- [x] Update README/BMAD tracking artifacts and completion notes when the story ships. (AC: 3)

## Dev Notes

- Prefer a boring composition layer over new abstractions: build the response from existing fog, message, group-chat, treaty, and alliance primitives.
- Keep the current focused endpoints unchanged; this story adds a convenience read contract, not a replacement.
- Use an explicit `since_tick` query parameter instead of implicit server-side cursors so the contract stays deterministic and stateless.
- Return only data visible to the authenticated joined player.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Red phase: `uv run pytest -o addopts='' tests/api/test_agent_api.py -k 'briefing or openapi_declares_secured_match_route_contracts'`
- Contract verification: `uv run pytest -o addopts='' tests/api/test_agent_api.py tests/e2e/test_api_smoke.py tests/e2e/test_agent_sdk_smoke.py -k 'briefing or openapi_declares_secured_match_route_contracts'`
- Follow-up focused verification: `uv run pytest -o addopts='' tests/agent_sdk/test_python_client.py -k briefing` and `uv run pytest -o addopts='' tests/e2e/test_api_smoke.py -k agent_briefing`
- Repo gate: `make quality`

### Completion Notes List

- Added authenticated `GET /api/v1/matches/{match_id}/agent-briefing` as a bundled polling contract over the existing fog, alliance, treaty, group-chat, and message primitives.
- Kept the fog-filtered `state` and alliance status current-authoritative while making treaty records and direct/group/world message buckets deterministically filter on optional `since_tick`.
- Extended the standalone Python SDK with typed briefing models plus `get_agent_briefing(...)`, and documented the new workflow in `agent-sdk/README.md`.
- Added in-process API coverage, real-process smoke coverage, and SDK smoke coverage for the new public JSON contract.
- Followed up with focused SDK unit coverage for `get_agent_briefing(...)`, plus a leaner real-process assertion that the bundled endpoint surfaces public treaty and group-chat artifacts through the live HTTP boundary.

### File List

- _bmad-output/implementation-artifacts/17-1-add-an-authenticated-bundled-agent-briefing-endpoint.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- agent-sdk/README.md
- agent-sdk/python/iron_council_client.py
- server/agent_registry.py
- server/main.py
- server/models/api.py
- tests/api/test_agent_api.py
- tests/e2e/test_agent_sdk_smoke.py
- tests/e2e/test_api_smoke.py

### Change Log

- 2026-03-29 19:25 UTC: Drafted Story 17.1 for a consolidated authenticated agent briefing endpoint.
- 2026-03-29 19:58 UTC: Implemented the bundled authenticated agent briefing endpoint, added deterministic `since_tick` filtering for treaty/message buckets, extended SDK/docs, and completed targeted verification plus the repo quality gate.
- 2026-03-29 19:38 UTC: Added focused SDK unit coverage for `get_agent_briefing(...)`, tightened SDK wording around public treaty records, and extended the live smoke path to assert treaty and group-chat artifacts in the bundled briefing response.
