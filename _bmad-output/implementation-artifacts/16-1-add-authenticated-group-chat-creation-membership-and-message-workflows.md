# Story 16.1: Add authenticated group-chat creation, membership, and message workflows

Status: drafted

## Story

As an AI agent player,
I want to create and participate in match-scoped group chats,
So that I can coordinate alliances and back-channel negotiations through the same authenticated API surface as direct and world messaging.

## Acceptance Criteria

1. Given an authenticated agent joined to a match, when it creates a group chat with a name and invited member ids, then the API persists a deterministic group-chat record and returns a stable identifier plus membership.
2. Given a player is a member of a group chat, when that player lists visible group chats or reads group-chat messages, then they only see the chats and messages for groups they belong to in that match.
3. Given a player is not a member of a group chat, when they attempt to read or post messages to that group, then the API rejects the request with a structured authorization or visibility error.
4. Given existing world and direct message workflows already exist, when group-chat support is added, then those existing behaviors continue to pass unchanged through behavior-first API and running-app verification.

## Tasks / Subtasks

- [ ] Add group-chat API models and match-registry storage. (AC: 1, 2, 3)
- [ ] Add authenticated create/list/read/send group-chat endpoints with membership validation. (AC: 1, 2, 3)
- [ ] Add in-process API coverage plus at least one running-app verification path. (AC: 2, 3, 4)
- [ ] Update BMAD tracking artifacts and completion notes when shipped. (AC: 4)

## Dev Notes

- Ground the contract in the existing GDD/architecture requirement that messaging has direct, group, and world tiers.
- Keep the feature intentionally narrow: create, membership at creation time, list/read/send. Defer renames, kicks, unread state, or moderation.
- Reuse the existing authenticated-agent and joined-player checks instead of inventing a separate auth model.

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

- 2026-03-29 18:15 UTC: Drafted Story 16.1 for authenticated group-chat workflows.
