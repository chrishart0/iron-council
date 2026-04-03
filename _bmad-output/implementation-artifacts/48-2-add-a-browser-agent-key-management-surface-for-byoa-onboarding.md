# Story 48.2: Add a browser agent-key management surface for BYOA onboarding

Status: done

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

- [x] Add focused client tests for viewing owned keys, one-time secret reveal, and revoke flows from the authenticated browser boundary. (AC: 1, 2, 3)
- [x] Add a typed client API seam for the new lifecycle endpoints while preserving the existing session/bearer-token model. (AC: 1, 2, 3)
- [x] Add a small settings panel/page for key management without mixing in future billing or entitlement UX. (AC: 1, 2, 3)
- [x] Re-run focused browser verification plus the repo quality gate, then update BMAD/docs artifacts with real outcomes. (AC: 4)

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

- [x] Engineering / Architecture
- [x] Product Owner

## Testing

- `cd client && npm test -- --run src/lib/api.test.ts src/components/session/session-config-panel.test.tsx`
- `source .venv/bin/activate && make quality`

## Change Log

- 2026-04-03: Drafted Story 48.2 as the immediate browser follow-on once Story 48.1 stabilizes the lifecycle contract.
- 2026-04-03: Added Bearer-authenticated browser API-key management helpers and session-panel UI with one-time secret reveal, deterministic revoke updates, session-switch race guards, and focused browser-boundary coverage.

## Debug Log References

- RED/GREEN: `cd client && npm test -- --run src/lib/api.test.ts src/components/session/session-config-panel.test.tsx`
  Outcome: passed with focused API-helper and session-panel coverage for list/create/revoke flows plus unhappy-path/session-switch guards.
- GREEN: `source .venv/bin/activate && make quality`
  Outcome: passed end-to-end with server checks, full pytest suite, client typecheck/tests, and production client build green.

## Completion Notes

- Added typed client lifecycle helpers for owned API keys using the existing bearer-token session and compact list/create/revoke contracts from Story 48.1.
- Extended the existing browser session panel with owned-key listing, one-time raw secret reveal, deterministic revoke updates, and explicit no-token guidance without introducing a parallel auth flow.
- Hardened the panel against session-switch stale-state races so keys/secrets from one bearer-token session do not leak into another session after reload failures or late responses.

## File List

- `client/src/lib/types.ts`
- `client/src/lib/api.ts`
- `client/src/lib/api.test.ts`
- `client/src/components/session/session-config-panel.tsx`
- `client/src/components/session/session-config-panel.test.tsx`
- `docs/plans/2026-04-03-story-48-2-browser-agent-key-management.md`
- `_bmad-output/implementation-artifacts/48-2-add-a-browser-agent-key-management-surface-for-byoa-onboarding.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## QA Results

- Focused browser/session API-key slice: pass
- Repo quality gate: pass
