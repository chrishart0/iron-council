# Story 48.3: Enforce per-API-key concurrent match occupancy with honest join errors

Status: done

## Story

As the platform operator,
I want each agent API key to respect a deterministic concurrent-match occupancy limit,
So that BYOA onboarding is safe against obvious abuse before billing is added.

## Acceptance Criteria

1. Given an agent API key already occupies its allowed number of active matches, when that key tries to create or join another active lobby or match, then the API rejects the request with a structured domain error that names occupancy rather than a misleading auth or not-found failure.
2. Given the same key later leaves or finishes a match, when occupancy is recomputed, then the key can join another allowed match without manual cleanup or hidden state drift.
3. Given this is still the pre-billing BYOA phase, when the story ships, then focused API/process verification plus the repo quality gate pass without inventing the later entitlement/billing seam early.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add behavior-first API coverage for agent create/join flows that hit the occupancy limit and assert an honest structured domain error instead of `invalid_api_key`, `match_not_found`, or another misleading fallback. (AC: 1)
- [x] Add focused recomputation coverage showing the same API key can create/join again after occupancy is freed by match completion or equivalent durable state changes. (AC: 2)
- [x] Implement the smallest DB-backed occupancy helper/seam needed to count active occupancy per API key across lobby/active matches and wire it into the existing authenticated create/join path. (AC: 1, 2)
- [x] Re-run focused API/process verification plus the repo quality gate, then update BMAD artifacts with the real outcomes. (AC: 3)

## Dev Notes

- Keep this story narrow and pre-billing. Do not introduce Stripe, paid tiers, or a generalized entitlement model yet; that belongs in Story 48.4.
- Prefer one deterministic occupancy constant for now, defined in the smallest honest seam that Story 48.4 can later replace or read through.
- Review both lobby creation and lobby join paths so the same occupancy rule/error shape applies consistently wherever an API key can start occupying a match slot.
- Be explicit about what counts toward occupancy: active lobbies and active matches for the same API key should be treated consistently, and completed/closed participation must stop counting without manual cleanup.
- Keep error naming/product copy honest: this story is about occupancy limits, not auth failure.

### References

- `core-plan.md#9.1 Bring Your Own Agent`
- `core-plan.md#9.3 Agent Access & Pricing`
- `core-architecture.md#3.1 Core Tables`
- `server/db/lobby_registry.py`
- `server/db/identity.py`
- `server/api/authenticated_lobby_routes.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `_bmad-output/planning-artifacts/epics.md#Story 48.3: Enforce per-API-key concurrent match occupancy with honest join errors`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Testing

- `source .venv/bin/activate && python -m pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k occupancy`
- `source .venv/bin/activate && python -m pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_process_api.py -k occupancy`
- `source .venv/bin/activate && make quality`

## Change Log

- 2026-04-03: Created Story 48.3 implementation artifact after Story 48.2 shipped so the next BYOA hardening slice has a concrete BMAD handoff file.
- 2026-04-03: Enforced a narrow DB-backed per-API-key occupancy limit for authenticated create/join flows, added honest `409` occupancy errors, and updated supporting tests/fixtures to use fresh unoccupied keys where the new rule now applies.

## Debug Log References

- RED/GREEN: `source .venv/bin/activate && python -m pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k occupancy`
  Outcome: passed with focused API-boundary coverage for create rejection plus join rejection/recovery after match completion.
- GREEN: `source .venv/bin/activate && python -m pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_process_api.py -k occupancy`
  Outcome: passed with running-app verification that DB-backed occupancy recomputes after a match stops counting.
- GREEN: `source .venv/bin/activate && make quality`
  Outcome: passed end-to-end with Ruff, mypy, full pytest coverage gate, client install/lint/test/build, and generated Next.js normalization checks green.
- REVIEW: spec-compliance review
  Outcome: PASS — create/join flows now return the structured occupancy conflict, occupancy is recomputed from DB state, and the story stayed pre-billing.
- REVIEW: code-quality review
  Outcome: APPROVED after tightening the error copy to say `lobby or active matches`; the small client-dev smoke guard was accepted as a fresh-worktree quality-harness ergonomics fix rather than harmful scope creep.

## Completion Notes

- Added a tiny DB-backed occupancy helper keyed on `players.api_key_id`, counting distinct `lobby`/`active` matches only, so completed matches automatically stop consuming occupancy without manual cleanup.
- Wired the same occupancy rule into both authenticated lobby creation and authenticated match join flows, preserving idempotent re-join behavior while surfacing a structured `api_key_match_occupancy_limit_reached` error as `409 CONFLICT`.
- Added behavior-first API and process regressions for create blocking, join blocking, and recovery after match completion, then updated supporting SDK/e2e/DB tests to use fresh API keys where seeded keys now correctly fail the new occupancy rule.
- Kept the implementation deliberately pre-billing with a single deterministic limit constant and no entitlement or Stripe abstractions; Story 48.4 remains the next seam-expansion slice.

## File List

- `server/api/authenticated_lobby_routes.py`
- `server/api/authenticated_write_routes.py`
- `server/db/identity.py`
- `server/db/lobby_registry.py`
- `tests/agent_sdk/test_python_client.py`
- `tests/api/test_agent_api.py`
- `tests/api/test_agent_process_api.py`
- `tests/e2e/test_agent_sdk_smoke.py`
- `tests/e2e/test_api_smoke.py`
- `tests/support.py`
- `tests/test_client_dev_smoke.py`
- `tests/test_db_registry.py`
- `docs/plans/2026-04-03-story-48-3-api-key-occupancy-limit.md`
- `_bmad-output/implementation-artifacts/48-3-enforce-per-api-key-concurrent-match-occupancy-with-honest-join-errors.md`
- `_bmad-output/implementation-artifacts/48-4-add-a-billing-ready-agent-entitlement-seam-with-manual-dev-grants.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## QA Results

- Story-focused API occupancy slice: pass
- Running-app occupancy recomputation slice: pass
- Repo quality gate after controller integration: pass (`source .venv/bin/activate && make quality`)
