# Story 14.2: Bind match joins and match-scoped reads/writes to the authenticated agent identity

Status: done

## Story

As an AI agent developer,
I want match access to derive my playable identity from my authenticated agent,
So that state polling, order submission, and diplomacy actions cannot spoof another player through request payload fields.

## Acceptance Criteria

1. Given an authenticated agent joining a match, when the join endpoint succeeds, then it assigns or reuses the deterministic match player slot for that authenticated agent without requiring the client to send `agent_id` in the payload.
2. Given a secured match-scoped API call after join, when the endpoint needs player identity for state reads or writes, then it derives that identity from the authenticated agent's join mapping and rejects unjoined or mismatched access with structured errors and no hidden mutation.
3. Given this access-control layer changes public API behavior, when the story is implemented, then the repo includes behavior-first API coverage, real-process verification, and a simplification pass confirming the solution stays KISS and by-the-book.

## Tasks / Subtasks

- [x] Narrow authenticated match contracts to remove spoofable identity inputs. (AC: 1, 2, 3)
  - [x] Remove `agent_id` from the authenticated join request contract.
  - [x] Remove or stop trusting match-scoped `player_id` / `sender_id` request inputs where the acting identity should come from auth.
  - [x] Keep response payloads stable enough for clients to understand the derived identity and acceptance result.
- [x] Add a registry helper for authenticated-match player resolution. (AC: 1, 2)
  - [x] Resolve the joined player slot for a `(match_id, agent_id)` pair in both in-memory and DB-backed registries.
  - [x] Raise structured domain errors for unjoined access instead of silently defaulting or mutating.
  - [x] Reuse existing deterministic join-slot assignment behavior for repeat joins.
- [x] Secure match-scoped REST handlers with the authenticated agent context. (AC: 1, 2)
  - [x] Require valid `X-API-Key` auth for join and match-scoped state/message/treaty/alliance/order flows.
  - [x] Derive player identity from auth + join mapping rather than trusting payload/query identity.
  - [x] Reject unjoined access or route/body mismatch with repo-consistent structured errors.
- [x] Extend verification and simplify the finished solution. (AC: 3)
  - [x] Add behavior-first API tests for authenticated happy-path and rejection flows.
  - [x] Add or update running-process smoke coverage against the real app command path.
  - [x] Re-run the repository quality gate and do an explicit simplification/KISS pass before closing the story.

## Dev Notes

- Follow `core-architecture.md` sections 5.1 and 5.2: AI agents authenticate via `X-API-Key`, and match access should derive the caller's playable identity from the authenticated agent rather than client-supplied identity fields.
- Keep this story focused on agent match authorization only. Do not broaden scope into human JWT auth, billing, spectator mode, or generalized RBAC.
- Prefer the smallest deterministic solution: one join mapping source of truth, one helper for deriving the joined player, and straightforward route guards.
- Behavior-first tests should assert visible HTTP outcomes and domain mutations/non-mutations, not helper implementation details.

### Candidate Implementation Surface

- `server/models/api.py`
- `server/agent_registry.py`
- `server/db/registry.py`
- `server/main.py`
- `tests/test_agent_registry.py`
- `tests/test_db_registry.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/e2e/test_api_smoke.py`
- `docs/plans/2026-03-29-story-14-2-authenticated-match-access.md`
- `_bmad-output/implementation-artifacts/14-2-bind-match-joins-and-match-scoped-reads-writes-to-the-authenticated-agent-identity.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### References

- `core-plan.md` sections 8.2, 9.1, 9.2, and 9.3
- `core-architecture.md` sections 2.1, 5.1, and 5.2
- `_bmad-output/planning-artifacts/epics.md` Story 14.2 acceptance criteria
- `AGENTS.md` guidance favoring behavior-first API tests, real-process verification, and KISS-by-default changes

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-03-29: `uv run pytest -o addopts='' tests/test_agent_registry.py tests/test_db_registry.py`
- 2026-03-29: `uv run pytest -o addopts='' tests/api/test_agent_api.py tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py`
- 2026-03-29: `uv sync --extra dev --frozen`
- 2026-03-29: `make quality`

### Completion Notes List

- Authenticated join and match-scoped state/order/message/treaty/alliance flows now derive the acting player from `X-API-Key` auth plus the registry join mapping, while still returning the resolved player identity in accepted responses.
- Authenticated request and query contracts no longer expose spoofable `agent_id`, `player_id`, or `sender_id` inputs; handlers derive the acting identity only from auth plus the join mapping, and accepted responses remain self-describing with derived ids.
- Added `require_joined_player_id` parity in both in-memory and DB-backed registries and surfaced structured `agent_not_joined` API errors without mutating match state on rejected requests.
- Extended behavior-first API, process-backed integration, smoke, and registry coverage to verify derived identity happy paths, unjoined rejections, validation mapping, and a real-process DB-backed authenticated-but-unjoined negative path.
- Simplified the implementation by removing compatibility mismatch branches from `server.main`, passing resolved acting ids into registry commands explicitly, and dropping implementation-detail tests that only pinned exact internal `ValueError` strings.

### File List

- `server/models/api.py`
- `server/agent_registry.py`
- `server/db/registry.py`
- `server/main.py`
- `tests/test_agent_registry.py`
- `tests/test_db_registry.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/e2e/test_api_smoke.py`
- `docs/plans/2026-03-29-story-14-2-authenticated-match-access.md`
- `_bmad-output/implementation-artifacts/14-2-bind-match-joins-and-match-scoped-reads-writes-to-the-authenticated-agent-identity.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-29 15:15 UTC: Drafted Story 14.2 for authenticated match joins and secured match-scoped access.
- 2026-03-29 16:55 UTC: Finished authenticated join-bound player resolution, secured match-scoped APIs, expanded behavior/process coverage, and passed the full quality gate.
- 2026-03-29 17:35 UTC: Removed remaining spoofable authenticated request/query fields, seeded a valid DB-backed unjoined agent for real-process smoke coverage, and aligned the story notes with the shipped contract.
