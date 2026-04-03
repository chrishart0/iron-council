# Story 48.4: Add a billing-ready agent entitlement seam with manual/dev grants

Status: done

## Story

As a maintainer of the BYOA platform,
I want API-key issuance and occupancy rules to read from a narrow entitlement seam,
So that later billing integration can plug in without rewriting the agent-auth contract.

## Acceptance Criteria

1. Given the repo is not yet integrating Stripe checkout, when the first entitlement seam lands, then API-key lifecycle and occupancy rules read from a small entitlement model that supports manual/dev grants and keeps the billing dependency out of the request path.
2. Given future billing work will extend this seam, when the story finishes, then the initial implementation stays small, typed, and well-covered without promising a full payment system yet.

## Ready Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Tasks / Subtasks

- [x] Define the smallest typed entitlement read seam that API-key lifecycle and occupancy checks can share without introducing payment-provider code.
- [x] Add manual/dev grant fixtures plus behavior-first tests proving non-entitled API keys are gated honestly and entitled keys retain the expected BYOA lifecycle/occupancy behavior.
- [x] Wire the current API-key lifecycle and occupancy rules through the entitlement seam while keeping Story 48.3's honest occupancy errors intact.
- [x] Re-run focused verification plus the repo quality gate, then update BMAD artifacts with the real outcomes.

## Dev Notes

- Build directly on Story 48.3's shipped occupancy seam; do not re-open broader BYOA UX scope here.
- Keep the seam local and typed so future billing integration can plug in later without adding Stripe/webhook dependencies to request-time code now.
- Manual/dev grants should be explicit and inspectable in local development and tests.
- Do not turn this into a full subscription system, checkout flow, or admin console story.

### References

- `core-plan.md#9.1 Bring Your Own Agent`
- `core-plan.md#9.3 Agent Access & Pricing`
- `server/db/api_key_lifecycle.py`
- `server/db/identity.py`
- `server/db/lobby_registry.py`
- `_bmad-output/planning-artifacts/epics.md#Story 48.4: Add a billing-ready agent entitlement seam with manual/dev grants`

## Complete Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-03: Drafted Story 48.4 as the next BYOA follow-on once Story 48.3 shipped the pre-billing occupancy limit.
- 2026-04-03: Follow-up patch seeded missing manual entitlement grants for fresh DB-backed API-key create/join tests so the new entitlement seam gates only the intended agent flows and preserves honest occupancy/error coverage.
- 2026-04-03: Second follow-up patched the remaining shared DB/SDK/e2e test helpers so fresh API-key lobby create/join success paths seed explicit manual entitlement grants without loosening production gating.

## Debug Log References

- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'occupancy or api_key or entitlement or create_match_lobby_route or start_match_lobby_route or persists_db_backed_lobby_membership'`
  Outcome: failed with 5 DB-backed API-key tests returning `403 agent_entitlement_required` or missing `match_id` because fresh create/join keys lacked seeded entitlement grants.
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'occupancy or api_key or entitlement or create_match_lobby_route or start_match_lobby_route or persists_db_backed_lobby_membership'`
  Outcome: passed with 19 tests green after seeding positive manual grants for the DB-backed API keys expected to create or join lobbies.
- RED: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py tests/agent_sdk/test_python_client.py tests/e2e/test_api_smoke.py tests/e2e/test_agent_sdk_smoke.py`
  Outcome: failed with 19 broader DB/SDK/e2e tests because fresh API-key lobby create/join paths still inserted keys without matching manual entitlement grants.
- GREEN: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py tests/agent_sdk/test_python_client.py tests/e2e/test_api_smoke.py tests/e2e/test_agent_sdk_smoke.py`
  Outcome: passed with 110 tests green after routing the positive create/join fixtures through a shared API-key-plus-manual-entitlement helper and updating the DB registry helper seam.
- GREEN: `source .venv/bin/activate && make quality`
  Outcome: passed after the helper coverage patch and BMAD artifact updates.

## Completion Notes

- Added only the missing manual entitlement-grant setup in DB-backed API tests whose fresh API keys are expected to create or join matches under the new entitlement seam.
- Left negative entitlement coverage intact so zero-capacity and unentitled agent flows still fail with `agent_entitlement_required`.
- Kept human bearer-auth create/join/start coverage unchanged so ungated human flows remain validated separately from agent entitlement gating.
- Added a shared test helper for inserting a fresh API key together with an explicit manual entitlement grant, then reused that seam in DB registry, SDK, and real-process smoke coverage to minimize duplication.
- Preserved production gating by changing only test fixtures/helpers and by keeping negative entitlement scenarios on the non-entitled path.

## File List

- `tests/support.py`
- `tests/test_db_registry.py`
- `tests/agent_sdk/test_python_client.py`
- `tests/e2e/test_api_smoke.py`
- `tests/e2e/test_agent_sdk_smoke.py`
- `_bmad-output/implementation-artifacts/48-4-add-a-billing-ready-agent-entitlement-seam-with-manual-dev-grants.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
