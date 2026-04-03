# Story 48.4: Add a billing-ready agent entitlement seam with manual/dev grants

Status: backlog

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

- [ ] Define the smallest typed entitlement read seam that API-key lifecycle and occupancy checks can share without introducing payment-provider code.
- [ ] Add manual/dev grant fixtures plus behavior-first tests proving non-entitled API keys are gated honestly and entitled keys retain the expected BYOA lifecycle/occupancy behavior.
- [ ] Wire the current API-key lifecycle and occupancy rules through the entitlement seam while keeping Story 48.3's honest occupancy errors intact.
- [ ] Re-run focused verification plus the repo quality gate, then update BMAD artifacts with the real outcomes.

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
