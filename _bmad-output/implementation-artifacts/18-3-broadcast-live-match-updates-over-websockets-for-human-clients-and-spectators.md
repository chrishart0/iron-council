# Story 18.3: Broadcast live match updates over WebSockets for human clients and spectators

Status: done

## Story

As a human player or spectator,
I want the running match to push updates over WebSockets,
So that the client can watch the war unfold in real time instead of polling ad hoc REST reads.

## Acceptance Criteria

1. Given a human player or spectator connects to the match WebSocket, when the server accepts the connection, then it sends an initial state payload shaped to the documented protocol and keeps the connection registered for future broadcasts.
2. Given an active match advances or a chat-visible event occurs, when the runtime loop completes the tick, then the server broadcasts the post-tick payload to subscribed clients, using fog-filtered state for players and full visibility for spectators.
3. Given the realtime protocol is a public client contract, when the feature ships, then tests cover connection lifecycle, initial payload shape, and at least one real-process tick-driven broadcast for both a player and a spectator role.

## Tasks / Subtasks

- [x] Add a small explicit WebSocket connection manager and realtime payload contract for per-match subscriptions. (AC: 1)
- [x] Expose a match WebSocket route that accepts player and spectator viewers, sends an initial payload, and cleans up registrations on disconnect. (AC: 1)
- [x] Broadcast post-tick realtime payloads from the runtime/app path with fog-filtered player state and full spectator visibility, and include chat-visible/public diplomacy context needed by the client contract. (AC: 2)
- [x] Add behavior-first API/WebSocket tests plus a real-process smoke covering one player connection and one spectator connection through a live tick. (AC: 3)
- [x] Run simplification/review and refresh BMAD completion notes when the story ships. (AC: 3)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'websocket or realtime'`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'registers_player_connection_and_sends_initial_fog_filtered_payload or registers_spectator_connection_and_sends_full_visibility_payload or world_message_broadcasts_refresh or private_chat_events_broadcast or command_envelope_message_writes_broadcast'`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k websocket`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'match_websocket or websocket_manager_drops_failed_and_slow_connections_and_realtime_builder_requires_match or private_chat_events_broadcast_refresh_with_full_spectator_visibility or command_envelope_message_writes_broadcast_private_chat_refresh or runtime_broadcasts_post_tick_payload_to_connected_player_and_spectator or world_message_broadcasts_refresh_to_connected_player_and_spectator'`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'canonical_token_without_player_id or match_websocket_accepts_legacy_path_and_api_key_alias'`
- `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k websocket`
- `make format`
- `uv sync --extra dev`
- `make quality`

### Completion Notes List

- Added a minimal realtime contract in `server/models/realtime.py` and one boring per-match websocket manager in `server/websocket.py`, reusing `project_agent_state()` for player fog filtering and a direct full-state spectator projection.
- Added `/ws/matches/{match_id}` with outbound-only behavior: the server accepts a player or spectator subscription, sends one initial `tick_update` payload immediately, and keeps the connection registered until disconnect.
- Chose the narrowest auth contract that fits current repo reality: spectator websockets are open, while player websockets authenticate with the existing active API key via websocket query params plus an explicit `player_id`. This keeps the route shape stable for later JWT replacement without introducing a broader auth system in Story 18.3.
- Wired runtime tick broadcasts after successful tick persistence, preserving Story 18.2's durability/rollback path. The runtime does not broadcast a post-tick payload until the authoritative state advance and optional persistence step have succeeded.
- Reused the same realtime payload builder for initial sends and live fanout, and triggered refresh broadcasts for public world-message, treaty, and alliance writes so browser clients do not need to reconnect to observe public/chat-visible changes.
- Follow-up fix: expanded player websocket payloads to include direct messages, visible group chats, and visible group-chat messages, while keeping spectator payloads public-only with empty private-chat fields.
- Follow-up fix: triggered websocket refresh broadcasts for direct message writes, group-chat creation, group-chat message writes, and command-envelope message writes so connected players stay current without REST polling after chat-visible events.
- Follow-up fix: added the documented canonical websocket route `/ws/match/{match_id}` and `token` query support while preserving `/ws/matches/{match_id}` and `api_key` as compatibility aliases; player identity now resolves from the auth token and only uses `player_id` as an optional consistency check.
- Follow-up fix: aligned spectator payloads with the source architecture by exposing full map visibility and all chat channels, including direct messages, group-chat metadata, and group-chat messages.
- Follow-up fix: changed websocket fanout from sequential awaits to bounded concurrent sends with per-socket timeout-based laggard eviction so one slow client does not stall the runtime broadcast path.
- Added API-level websocket tests for initial payload shape, connection lifecycle, invalid viewer/auth cases, and public-event refresh, plus a real-process websocket smoke that proves both a player and a spectator receive a live tick-driven update.
- Added API-level regressions that prove private direct/group chat refresh reaches connected player viewers, remains fully visible to spectators per the architecture docs, and keeps legacy websocket compatibility working.

### File List

- _bmad-output/implementation-artifacts/18-3-broadcast-live-match-updates-over-websockets-for-human-clients-and-spectators.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- _bmad-output/planning-artifacts/architecture.md
- core-architecture.md
- server/main.py
- server/websocket.py
- tests/api/test_agent_api.py
- tests/e2e/test_api_smoke.py

## Dev Notes

- Keep the implementation intentionally narrow: one boring per-match connection registry, one documented outbound payload shape, and one broadcast path reused by both initial sends and live updates.
- Reuse existing registry/projector helpers where possible instead of introducing a second projection stack.
- Do not broaden scope into full bidirectional WebSocket command handling yet; this story only needs server-to-client live updates.
- Human JWT auth is not implemented elsewhere in the repo yet, so choose the narrowest connection authentication contract that fits the current server state and keeps the public protocol easy to evolve.

## Implementation Plan

- Plan file: `docs/plans/2026-03-30-story-18-3-live-websocket-broadcasts.md`
- Parallelism assessment: sequential implementation because `server/main.py`, runtime broadcast wiring, new realtime models/manager, and websocket tests all share one public-contract seam; independent spec and quality review can run after implementation.
- Verification target: focused API/WebSocket tests, real-process websocket smoke for player + spectator, then `make quality`.
