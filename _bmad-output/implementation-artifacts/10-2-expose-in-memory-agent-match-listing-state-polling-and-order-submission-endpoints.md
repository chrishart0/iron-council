# Story 10.2: Expose in-memory agent match listing, state polling, and order submission endpoints

Status: drafted

## Story

As an AI agent developer,
I want minimal REST endpoints for listing matches, polling my visible state, and submitting orders,
so that automated clients can drive headless matches before database-backed persistence lands.

## Acceptance Criteria

1. Given seeded in-memory matches, when the agent API lists matches, then it returns stable JSON summaries with match identity, status, and tick metadata suitable for polling clients.
2. Given a valid player in a seeded match, when the agent API fetches `/api/v1/matches/{id}/state`, then it returns the fog-filtered projection from Story 10.1 for that player and rejects unknown match or player IDs with structured HTTP errors.
3. Given valid and invalid order envelopes for a seeded match, when the agent API posts `/api/v1/matches/{id}/orders`, then it stores accepted submissions in deterministic in-memory order, echoes a stable acceptance payload, and rejects mismatched match IDs or unknown players without mutating stored submissions.

## Tasks / Subtasks

- [ ] Add behavior-first API tests before implementation. (AC: 1, 2, 3)
  - [ ] Cover stable match-list summaries from seeded in-memory data.
  - [ ] Cover state polling success plus unknown match/player error contracts.
  - [ ] Cover accepted order submission and rejection of mismatched/unknown envelopes without side effects.
- [ ] Implement a small in-memory match registry and agent API router. (AC: 1, 2, 3)
  - [ ] Keep scope to list/state/orders endpoints only; do not add Supabase auth, lobby joins, or websocket handling.
  - [ ] Reuse Story 10.1 fog projection for state responses rather than duplicating visibility logic.
  - [ ] Keep stored order submission order deterministic and easy to inspect in tests.
- [ ] Re-verify API behavior after merge. (AC: 1, 2, 3)
  - [ ] Re-run focused API coverage.
  - [ ] Re-run the repository quality gate.

## Dev Notes

- Prefer API-boundary tests with `httpx.AsyncClient` over internal handler-only tests.
- Preserve the existing lightweight app scaffold and avoid speculative persistence abstractions.
- Keep the registry injectable/resettable so tests can seed matches without cross-test leakage.

### References

- `core-architecture.md` section 5.2 for the first agent REST endpoint set.
- `core-architecture.md` section 3.3 for the fog-filtered state payload intent.
- `_bmad-output/planning-artifacts/epics.md` Story 10.2 acceptance criteria.

## Dev Agent Record

### Agent Model Used

_TBD_

### Debug Log References

- _TBD_

### Completion Notes List

- _TBD_

### File List

- _TBD_

### Change Log

- 2026-03-28 14:25 UTC: Drafted Story 10.2 for in-memory agent list/state/orders endpoints.
