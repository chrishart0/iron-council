Continue Story 41.1 in this SAME worktree. The previous pass already added the backend leaderboard `agent_id` contract and updated related server tests. Do not redo that work; inspect the current diff and build on it.

You must finish the remaining story scope:
1. Add client types/API/validators/tests for public agent profiles and the optional leaderboard `agent_id` contract.
2. Build the new read-only Next.js route `/agents/[agentId]` with deterministic loading, ready, and unavailable states.
3. Update leaderboard UI/tests so agent rows link to `/agents/{agentId}` while human rows remain plain text.
4. Run focused client tests, the focused server/e2e tests, then `source .venv/bin/activate && make quality`.
5. Update `_bmad-output/implementation-artifacts/41-1-add-public-agent-profile-page-in-the-web-client.md` to `Status: done` with real debug log/completion notes/file list/change log.
6. Update `_bmad-output/implementation-artifacts/sprint-status.yaml` so `next_story` points to `41-2-link-completed-match-and-replay-browse-surfaces-to-durable-public-competitor-identities`, story 41.1 is `done`, and epic 41 becomes `in-progress`.
7. Commit all remaining changes in this worktree.

Constraints:
- Keep it KISS.
- Use the existing `/api/v1/agents/{agent_id}/profile` route.
- Do not invent human public profile routes.
- Do not stop until tests pass and a commit exists.
