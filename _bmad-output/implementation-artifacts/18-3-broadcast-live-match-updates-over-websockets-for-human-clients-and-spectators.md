# Story 18.3: Broadcast live match updates over WebSockets for human clients and spectators

Status: backlog

## Story

As a human player or spectator,
I want the running match to push updates over WebSockets,
So that the client can watch the war unfold in real time instead of polling ad hoc REST reads.

## Acceptance Criteria

1. Given a human player or spectator connects to the match WebSocket, when the server accepts the connection, then it sends an initial state payload shaped to the documented protocol and keeps the connection registered for future broadcasts.
2. Given an active match advances or a chat-visible event occurs, when the runtime loop completes the tick, then the server broadcasts the post-tick payload to subscribed clients, using fog-filtered state for players and full visibility for spectators.
3. Given the realtime protocol is a public client contract, when the feature ships, then tests cover connection lifecycle, initial payload shape, and at least one real-process tick-driven broadcast for both a player and a spectator role.

## Tasks / Subtasks

- [ ] Add a small explicit WebSocket connection manager and realtime payload contract for per-match subscriptions. (AC: 1)
- [ ] Expose a match WebSocket route that accepts player and spectator viewers, sends an initial payload, and cleans up registrations on disconnect. (AC: 1)
- [ ] Broadcast post-tick realtime payloads from the runtime/app path with fog-filtered player state and full spectator visibility, and include chat-visible/public diplomacy context needed by the client contract. (AC: 2)
- [ ] Add behavior-first API/WebSocket tests plus a real-process smoke covering one player connection and one spectator connection through a live tick. (AC: 3)
- [ ] Run simplification/review and refresh BMAD completion notes when the story ships. (AC: 3)

## Dev Notes

- Keep the implementation intentionally narrow: one boring per-match connection registry, one documented outbound payload shape, and one broadcast path reused by both initial sends and live updates.
- Reuse existing registry/projector helpers where possible instead of introducing a second projection stack.
- Do not broaden scope into full bidirectional WebSocket command handling yet; this story only needs server-to-client live updates.
- Human JWT auth is not implemented elsewhere in the repo yet, so choose the narrowest connection authentication contract that fits the current server state and keeps the public protocol easy to evolve.

## Implementation Plan

- Plan file: `docs/plans/2026-03-30-story-18-3-live-websocket-broadcasts.md`
- Parallelism assessment: sequential implementation because `server/main.py`, runtime broadcast wiring, new realtime models/manager, and websocket tests all share one public-contract seam; independent spec and quality review can run after implementation.
- Verification target: focused API/WebSocket tests, real-process websocket smoke for player + spectator, then `make quality`.
