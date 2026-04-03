# Story: 43.1 Add public treaty reputation to competitor profiles

Status: ready-for-dev

## Story

As a player or spectator,
I want public competitor profiles to show treaty reputation and history,
So that betrayals, withdrawals, and honored agreements remain visible when I inspect agents and humans outside the live match UI.

## Acceptance Criteria

1. Public agent and human profile response contracts add an explicit treaty-reputation section with deterministic counts for signed, currently active, honored, withdrawn, broken-by-self, and broken-by-counterparty treaties.
2. DB-backed profile assembly maps persisted treaty rows onto persistent agent/human identities and exposes a deterministic read-only treaty-history list with match id, counterparty display name, treaty type, final status, signed tick, and break/withdraw tick when present.
3. Honest empty treaty-reputation payloads are returned when no treaty history exists; existing not-found and DB-unavailable profile contracts remain unchanged.
4. Public agent and human profile pages render a stable read-only treaty-reputation summary and treaty-history section with deterministic empty-state copy.
5. Focused API/DB/client verification passes, followed by the strongest practical repo-managed quality checks for the touched seam.

## Tasks / Subtasks

- [ ] Add additive treaty-reputation models to the shared public profile contract and keep non-DB/empty-history behavior explicit. (AC: 1, 3)
- [ ] Aggregate persisted treaty rows by public competitor identity for DB-backed agent/human profile responses without inventing provenance fields. (AC: 1, 2, 3)
- [ ] Render treaty-reputation summary/history on the public agent and human profile pages. (AC: 4)
- [ ] Add focused API/DB/client tests plus repo-managed verification and a simplification pass. (AC: 5)

## Dev Notes

- Reuse the existing public profile routes instead of creating match-specific profile endpoints in this story.
- Keep the contract additive and honest: empty arrays/counts are acceptable; fabricated treaty history is not.
- Treat `broken_by_a` / `broken_by_b` as identity-relative reputation in the profile response, exposing whether the profiled competitor broke the treaty or had it broken by the counterparty.
- Preserve the existing human-profile `503 human_profile_unavailable` behavior when no DB is configured.
- Prefer a small helper in `server/db/identity_hydration.py` or a tightly scoped sibling module over broad new abstractions.

## Dev Agent Record

### Debug Log

- 2026-04-03: Drafted as the first post-Epic-42 story so the newly honest treaty lifecycle data becomes visible on the shipped public profile surfaces.

### Completion Notes

- Pending implementation.

### File List

- `_bmad-output/implementation-artifacts/43-1-add-public-treaty-reputation-to-competitor-profiles.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`

### Change Log

- 2026-04-03: Drafted Story 43.1 and advanced BMAD tracking past the completed treaty-break story.
