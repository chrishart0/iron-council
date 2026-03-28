# Story 9.1: Deduct fortification upkeep and degrade unpaid defenses deterministically

Status: done

## Story

As a game engine developer,
I want fortified cities to charge recurring money upkeep and lose tiers when upkeep cannot be paid,
so that defensive investment carries the ongoing economic tradeoff described in the design docs.

## Acceptance Criteria

1. Given player-owned cities with fortification tiers and sufficient money, when the resolver runs the resource and attrition phases, then the owning player's money is reduced by the documented per-tier maintenance total (tier 1 = 1 money, tier 2 = 2 money, tier 3 = 3 money per tick) and the fortification tiers remain unchanged.
2. Given multiple fortified cities whose combined upkeep exceeds the owning player's money, when upkeep resolves, then payment is applied in a deterministic city order, money clamps at zero, and each unpaid fortification decays by exactly one tier during attrition.
3. Given repeated runs from the same starting state with the same fortified-city layout, when upkeep and decay resolve, then the resulting player money, fortification tiers, and caller-owned `MatchState` remain deterministic and unmutated.

## Tasks / Subtasks

- [x] Add behavior-first resolver coverage before implementation. (AC: 1, 2, 3)
  - [x] Cover upkeep payment with enough money to preserve fortification tiers.
  - [x] Cover deterministic unpaid-tier decay when money cannot cover every fortified city.
  - [x] Cover repeated runs and input-state immutability.
- [x] Implement narrow fortification upkeep accounting. (AC: 1, 2, 3)
  - [x] Keep scope to fortification upkeep and unpaid fortification decay only; do not add siege, transfer execution, or diplomacy rules in this story.
  - [x] Use explicit tier-based maintenance costs rather than speculative scaling systems.
  - [x] Keep payment order deterministic and independent of dictionary insertion order.
- [x] Re-verify resolver and simulation behavior after merge. (AC: 1, 2, 3)
  - [x] Re-run focused resolver coverage.
  - [x] Re-run the repository quality gate.

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

- `uv sync --extra dev --frozen`
- `uv run pytest -o addopts='' tests/test_resolver.py -k 'fortification_upkeep or unpaid_fortifications or fortification_upkeep_and_decay'`
- `uv run pytest -o addopts='' tests/test_resolver.py -k 'fortification'`
- `uv run pytest tests/test_resolver.py`
- `make format`
- `make quality`
- `uv run pytest -o addopts='' tests/test_resolver.py -k 'fortification_upkeep or unpaid_fortifications or fortification_upkeep_and_decay'`

### Completion Notes List

- Added resolver-boundary tests for funded fortification upkeep, deterministic unpaid decay by city-id order, and repeated-run/input immutability.
- Recorded the initial fortification upkeep schedule in the planning source-of-truth and Story 9.1 artifact to match the shipped resolver behavior: tier 1 = 1 money, tier 2 = 2 money, tier 3 = 3 money per tick.
- Kept resolver purity by carrying unpaid fortification city IDs through an internal per-tick phase context instead of mutating the caller-owned `MatchState` or introducing persistent debt state.
- Applied decay only once per unpaid fortified city during attrition and kept payment order deterministic by sorting city IDs rather than relying on dictionary insertion order.
- `uv run pytest tests/test_resolver.py` executed successfully on behavior but failed the repository-wide coverage threshold by design for a focused run; the required full gate passed under `make quality`.

### File List

- `server/resolver.py`
- `tests/test_resolver.py`
- `_bmad-output/implementation-artifacts/9-1-deduct-fortification-upkeep-and-degrade-unpaid-defenses-deterministically.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/gdd.md`

### Change Log

- 2026-03-28 13:35 UTC: Drafted Story 9.1 for deterministic fortification upkeep and unpaid defense decay.
- 2026-03-28 13:27 UTC: Implemented resolver-boundary fortification upkeep accounting, deterministic unpaid one-tier decay, and updated BMAD tracking after passing `make quality`.
- 2026-03-28 13:50 UTC: Aligned the planning/story docs with the shipped fortification upkeep schedule (tier 1 = 1 money, tier 2 = 2 money, tier 3 = 3 money per tick) and re-ran focused resolver coverage.
