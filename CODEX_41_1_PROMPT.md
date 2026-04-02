Implement Iron Council Story 41.1 in this worktree.

Repo: /tmp/ic-41-1-public-agent-profile
Base branch already includes the planning commit `docs: plan public agent profile surfacing`.

You are implementing:
- `_bmad-output/implementation-artifacts/41-1-add-public-agent-profile-page-in-the-web-client.md`
- `docs/plans/2026-04-02-story-41-1-public-agent-profile-page.md`

Goal:
Add a public web-client agent profile page and wire leaderboard agent rows to it using a durable backend `agent_id` contract.

Hard requirements:
1. Follow TDD.
2. Keep the solution boring/KISS.
3. Reuse the existing shipped server route `/api/v1/agents/{agent_id}/profile`.
4. Do NOT invent human public profile routes.
5. Add only the smallest backend contract extension needed so leaderboard agent rows can link to profiles.
6. Run the relevant focused tests in this worktree before finishing.
7. Then run the repo quality gate (`source .venv/bin/activate && make quality`).
8. Update the Story 41.1 artifact with real debug log/completion notes/file list/change log and set status to done.
9. Update `_bmad-output/implementation-artifacts/sprint-status.yaml` so:
   - `41-1-add-public-agent-profile-page-in-the-web-client: done`
   - `epic-41` advances appropriately (likely `in-progress` unless you also finish all of Epic 41)
   - `next_story: 41-2-link-completed-match-and-replay-browse-surfaces-to-durable-public-competitor-identities`
10. Commit all implementation changes in this worktree with a clear commit message.

Expected implementation surface:
- Server contract/model/read assembly/tests for optional leaderboard `agent_id` on agent rows only.
- Client API/types/tests for public agent profiles and explicit leaderboard validation.
- New Next.js route/page/component/tests for `/agents/[agentId]`.
- Leaderboard page links agent rows to `/agents/{agentId}` and leaves human rows non-clickable.

Suggested verification commands from the plan:
- `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'public_leaderboard_and_completed_match_routes_return_compact_db_backed_reads or public_and_authenticated_agent_profile_reads_expose_finalized_settlement_results or openapi_declares_public_read_contracts'`
- `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'public_leaderboard_and_completed_match_smoke_flow_runs_through_real_process or completion_to_leaderboard_smoke_flow_runs_through_real_process'`
- `cd client && npm test -- --run src/lib/api.test.ts src/components/public/public-agent-profile-page.test.tsx src/components/public/public-leaderboard-page.test.tsx src/app/page.test.tsx`
- `source .venv/bin/activate && make quality`

Guardrails:
- Behavior-first tests, not implementation-detail tests.
- Keep route/model names aligned with existing conventions.
- Inspect actual files/tests; do not trust assumptions.
- Do not stop until code is implemented, tests pass, artifacts updated, and a commit is created.
