# Story: 41.1 Add a public agent profile page in the web client

Status: ready-for-dev

## Story

As a player or spectator,
I want to open a public agent profile page from the leaderboard,
So that I can inspect an agent's settled rating and match history instead of only seeing a one-line leaderboard row.

## Acceptance Criteria

1. The web client ships a public `/agents/{agentId}` route that loads the existing `/api/v1/agents/{agent_id}/profile` contract and renders display name, seeded status, rating, and history in a stable read-only UI.
2. Public leaderboard rows for agents expose a durable link target into `/agents/{agentId}`; human rows remain plain text with no invented profile route.
3. The leaderboard/public profile contract stays explicit and type-safe: the client receives a durable `agent_id` only where the backend can provide one honestly, and invalid/unknown agent ids render a deterministic unavailable state.
4. Focused server/client verification passes, followed by the strongest practical repo-managed quality checks for the touched seam.

## Tasks / Subtasks

- [ ] Add the smallest public leaderboard contract extension needed to carry durable agent profile ids without inventing human-profile destinations. (AC: 2, 3)
- [ ] Add client API/types for the public agent profile route and a read-only `/agents/{agentId}` page. (AC: 1, 3)
- [ ] Wire leaderboard agent rows to the new profile route and keep human rows non-clickable. (AC: 2)
- [ ] Add focused API/client tests plus repo-managed verification. (AC: 4)

## Dev Notes

- Reuse the already-shipped `/api/v1/agents/{agent_id}/profile` route; do not build a parallel client-only profile abstraction.
- Keep this story agent-only. Public human profile pages are out of scope until the backend defines a stable public identity contract for them.
- Prefer optional `agent_id` on leaderboard rows over any display-name heuristics.
- Keep the UI boring and read-only; no social features, follow actions, or new write paths.

## Dev Agent Record

### Debug Log

- 2026-04-02: Drafted as the first Epic 41 slice after Epic 40 finalized rating/profile reads server-side but the public web client still lacked a profile destination.

### Completion Notes

- Pending implementation.

### File List

- `_bmad-output/implementation-artifacts/41-1-add-public-agent-profile-page-in-the-web-client.md`

### Change Log

- 2026-04-02: Drafted Story 41.1 for public agent profile surfacing in the web client.
