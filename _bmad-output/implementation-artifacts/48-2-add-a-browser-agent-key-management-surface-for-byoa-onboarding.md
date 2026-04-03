# Story 48.2: Add a browser agent-key management surface for BYOA onboarding

Status: backlog

## Story

As an authenticated human player,
I want a small settings surface in the web client for creating and revoking my agent API keys,
So that I can complete BYOA onboarding from the shipped product without reaching for curl or direct DB tooling.

## Acceptance Criteria

1. Given the lifecycle endpoints from Story 48.1 already exist, when an authenticated human opens the browser settings surface, then the UI lists owned keys, their active state, rating metadata, and creation time using the existing bearer-token session without inventing a parallel auth flow.
2. Given the user creates a new key in the browser, when the request succeeds, then the UI reveals the raw secret exactly once, explains that it will not be shown again, and keeps the durable list view free of raw secrets afterward.
3. Given the user revokes an owned key, when the action completes, then the UI updates deterministically, preserves the rest of the settings surface, and reflects the new inactive state without pretending the key still works.
4. Given the new settings surface ships, when focused browser-boundary tests and the repo quality gate run, then the BYOA onboarding path is covered from the real authenticated browser boundary and remains simple to use locally.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [ ] Add focused client tests for viewing owned keys, one-time secret reveal, and revoke flows from the authenticated browser boundary. (AC: 1, 2, 3)
- [ ] Add a typed client API seam for the new lifecycle endpoints while preserving the existing session/bearer-token model. (AC: 1, 2, 3)
- [ ] Add a small settings panel/page for key management without mixing in future billing or entitlement UX. (AC: 1, 2, 3)
- [ ] Re-run focused browser verification plus the repo quality gate, then update BMAD/docs artifacts with real outcomes. (AC: 4)

## Dev Notes

- Keep this story dependent on Story 48.1; do not start implementation until the lifecycle routes and response shapes are stable.
- Prefer extending the existing browser session/settings area rather than creating a parallel onboarding microsite.
- The success UX must be explicit that the raw API key is visible once only. After dismissal or refresh, the list view should show summary metadata only.
- Do not fold occupancy limits, billing, or guided-agent gameplay controls into this story.

### References

- `client/src/components/session/session-config-panel.tsx`
- `client/src/components/session/session-provider.tsx`
- `client/src/lib/api.ts`
- `core-plan.md#9.1 Bring Your Own Agent`
- `core-plan.md#9.3 Agent Access & Pricing`
- `_bmad-output/planning-artifacts/epics.md#Story 48.2: Add a browser agent-key management surface for BYOA onboarding`

## Complete Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-03: Drafted Story 48.2 as the immediate browser follow-on once Story 48.1 stabilizes the lifecycle contract.
