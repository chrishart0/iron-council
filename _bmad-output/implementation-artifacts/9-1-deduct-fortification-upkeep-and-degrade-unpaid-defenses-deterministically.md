# Story 9.1: Deduct fortification upkeep and degrade unpaid defenses deterministically

Status: ready

## Story

As a game engine developer,
I want fortified cities to charge recurring money upkeep and lose tiers when upkeep cannot be paid,
so that defensive investment carries the ongoing economic tradeoff described in the design docs.

## Acceptance Criteria

1. Given player-owned cities with fortification tiers and sufficient money, when the resolver runs the resource and attrition phases, then the owning player's money is reduced by the documented per-tier maintenance total and the fortification tiers remain unchanged.
2. Given multiple fortified cities whose combined upkeep exceeds the owning player's money, when upkeep resolves, then payment is applied in a deterministic city order, money clamps at zero, and each unpaid fortification decays by exactly one tier during attrition.
3. Given repeated runs from the same starting state with the same fortified-city layout, when upkeep and decay resolve, then the resulting player money, fortification tiers, and caller-owned `MatchState` remain deterministic and unmutated.

## Tasks / Subtasks

- [ ] Add behavior-first resolver coverage before implementation. (AC: 1, 2, 3)
  - [ ] Cover upkeep payment with enough money to preserve fortification tiers.
  - [ ] Cover deterministic unpaid-tier decay when money cannot cover every fortified city.
  - [ ] Cover repeated runs and input-state immutability.
- [ ] Implement narrow fortification upkeep accounting. (AC: 1, 2, 3)
  - [ ] Keep scope to fortification upkeep and unpaid fortification decay only; do not add siege, transfer execution, or diplomacy rules in this story.
  - [ ] Use explicit tier-based maintenance costs rather than speculative scaling systems.
  - [ ] Keep payment order deterministic and independent of dictionary insertion order.
- [ ] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [ ] Re-run focused resolver coverage.
  - [ ] Re-run the repository quality gate.

## Dev Notes

- Prefer resolver-boundary tests over helper-only tests.
- Follow the architecture's phase contract: money upkeep is charged before attrition consequences are applied.
- Keep the first maintenance model simple and deterministic; do not invent delayed debt counters unless tests require them.

### References

- `core-plan.md` sections 4.2, 5.1, and 6.3 for money maintenance, fortification tiers, and defensive wear.
- `core-architecture.md` sections 4.2 and 4.3 for resource/attrition phase responsibilities.
- `_bmad-output/planning-artifacts/epics.md` Story 9.1 acceptance criteria.

## Dev Agent Record

### Agent Model Used

_GPT-5 Codex_

### Debug Log References

- _To be filled during implementation._

### Completion Notes List

- _To be filled during implementation._

### File List

- `_bmad-output/implementation-artifacts/9-1-deduct-fortification-upkeep-and-degrade-unpaid-defenses-deterministically.md`

### Change Log

- 2026-03-28 13:35 UTC: Drafted Story 9.1 for deterministic fortification upkeep and unpaid defense decay.
