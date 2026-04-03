# Story 48.3: Enforce per-API-key concurrent match occupancy with honest join errors

Status: ready

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

- [ ] Add behavior-first API coverage for agent create/join flows that hit the occupancy limit and assert an honest structured domain error instead of `invalid_api_key`, `match_not_found`, or another misleading fallback. (AC: 1)
- [ ] Add focused recomputation coverage showing the same API key can create/join again after occupancy is freed by match completion or equivalent durable state changes. (AC: 2)
- [ ] Implement the smallest DB-backed occupancy helper/seam needed to count active occupancy per API key across lobby/active matches and wire it into the existing authenticated create/join path. (AC: 1, 2)
- [ ] Re-run focused API/process verification plus the repo quality gate, then update BMAD artifacts with the real outcomes. (AC: 3)

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

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-03: Created Story 48.3 implementation artifact after Story 48.2 shipped so the next BYOA hardening slice has a concrete BMAD handoff file.
