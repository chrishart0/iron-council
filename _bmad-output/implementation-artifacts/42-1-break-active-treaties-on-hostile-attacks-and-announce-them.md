# Story: 42.1 Break active treaties on hostile attacks and announce them

Status: drafted

## Story

As a player or spectator,
I want active treaties to break automatically when one side attacks the other,
So that diplomacy history, world chat, and match reputation reflect actual betrayals instead of only manual withdrawals.

## Acceptance Criteria

1. An active treaty automatically transitions to `broken_by_a` or `broken_by_b` when one side launches a hostile accepted attack against the treaty partner during tick advancement.
2. The automatic break records the break tick and stops surfacing the treaty as active.
3. World chat receives one deterministic treaty-break announcement for each automatic break.
4. Authenticated/read/realtime treaty payloads serialize the broken statuses honestly.
5. Focused registry/API/process verification passes.

## Tasks / Subtasks

- [ ] Extend the treaty status contract to include `broken_by_a` and `broken_by_b`. (AC: 1, 2, 4)
- [ ] Detect hostile treaty violations during match tick advancement using the pre-resolution state plus accepted hostile movement orders. (AC: 1, 2)
- [ ] Record a deterministic world-chat treaty-break announcement exactly once per break. (AC: 3)
- [ ] Verify the new statuses flow through registry/API/process payloads without regressing existing diplomacy actions. (AC: 4, 5)
- [ ] Run focused verification and a simplification pass. (AC: 5)

## Dev Notes

- Keep the resolver pure over `MatchState`; implement treaty-break reconciliation in the match-registry tick path where `MatchRecord` already owns treaties and messages.
- Prefer the smallest explicit helper surface over a new diplomacy framework.
- Use the treaty pair ordering already established in `agent_registry_diplomacy.py` so broken statuses are deterministic and reviewable.
- Honor the DB/source-doc direction that treaty history distinguishes formal withdrawals from actual breaks.

## Dev Agent Record

### Debug Log

- Pending.

### Completion Notes

- Pending.

### File List

- `_bmad-output/implementation-artifacts/42-1-break-active-treaties-on-hostile-attacks-and-announce-them.md`

### Change Log

- 2026-04-02: Drafted Story 42.1 to close the treaty-break gap left after Epic 41.
