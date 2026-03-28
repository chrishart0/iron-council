# Story 5.1: Apply deterministic resource accounting during the resolver resource phase

Status: done

## Story

As a game engine developer,
I want the resource phase to update player stockpiles from owned-city yields and upkeep,
so that simulations reflect the real per-tick economic pressure described in the design docs.

## Acceptance Criteria

1. Given owned cities, player stockpiles, and stationed/transit armies, when the resource phase runs, then each owning player gains the summed resource yields from their cities and pays per-tick food upkeep for owned-city population plus all owned armies.
2. Given economy upgrade tiers on cities, when the resource phase computes city output, then only the primary resource yield is boosted by deterministic tier multipliers and secondary-resource yields remain at their base values.
3. Given the resolver remains a pure function, when the resource phase mutates the copied next-state, then repeated runs from the same inputs produce identical post-phase player resources without mutating the caller-owned `MatchState`.

## Tasks / Subtasks

- [x] Add focused resource-phase behavior coverage before implementation. (AC: 1, 2, 3)
  - [x] Cover owned-city yield aggregation into player stockpiles.
  - [x] Cover army and population food upkeep application.
  - [x] Cover economy-upgrade scaling on only the primary resource.
- [x] Implement deterministic resource accounting in the resolver pipeline. (AC: 1, 2, 3)
  - [x] Apply resource-phase logic to the copied `next_state`, not the caller-owned input.
  - [x] Keep the accounting derived from canonical `MatchState` data rather than external infrastructure.
  - [x] Emit the same stable `phase.resource.completed` event contract after the state update.
- [x] Verify the new state-changing behavior through resolver and simulation tests. (AC: 1, 2, 3)
  - [x] Re-run focused resolver and simulation coverage.
  - [x] Re-run the repository quality gate.

## Dev Notes

- Use `CityState.resources` as the canonical per-tick base yield profile and `CityState.upgrades.economy` as the only yield multiplier input for this story.
- Keep the multiplier table explicit and deterministic; avoid speculative balancing systems.
- Model food upkeep in a simple, documented way from the current state so later attrition work can build on a stable accounting baseline.
- Do not broaden scope into recruitment, transfers, shortages, or attrition side effects in this story.

### References

- `core-plan.md` sections 4.2, 4.3, and 5.1 for resource roles, per-tick upkeep, and economy upgrades.
- `core-architecture.md` section 4.1 for resource-phase sequencing inside the tick loop.
- `_bmad-output/planning-artifacts/epics.md` Story 5.1 acceptance criteria.

## Dev Agent Record

### Agent Model Used

OpenAI Codex CLI (`codex --yolo exec` in a dedicated git worktree) plus Hermes review subagents.

### Debug Log References

- RED/GREEN loop: `source .venv/bin/activate && pytest tests/test_resolver.py -q -o addopts=''`
- Targeted verification: `source .venv/bin/activate && pytest tests/test_resolver.py tests/test_simulation.py -q -o addopts=''`
- Full suite: `source .venv/bin/activate && pytest tests/ -q`
- Quality gate: `source .venv/bin/activate && make quality`

### Completion Notes List

- Implemented deterministic resource accounting inside `server.resolver` so owned-city yields are added to player stockpiles during the resource phase.
- Applied per-tick food upkeep for owned-city population plus all owned armies while preserving resolver purity by mutating only the copied `next_state`.
- Added an explicit economy-tier multiplier table that boosts only the inferred primary resource yield while leaving secondary-resource yields unchanged.
- Added a resolver-level regression test proving a food-deficit state no longer crashes resolution and instead clamps food to zero, intentionally deferring shortage side effects to later attrition work.
- Rebased the resolver and simulation fixture baselines onto non-deficit food pools so the public deterministic-contract tests continue to exercise the new resource phase without accidental schema failures.
- Verified Story 5.1 with focused resolver/simulation tests, a full `pytest` run, and the repository `make quality` gate.

### File List

- `_bmad-output/implementation-artifacts/5-1-apply-deterministic-resource-accounting-during-the-resolver-resource-phase.md`
- `server/resolver.py`
- `tests/test_resolver.py`
- `tests/test_simulation.py`

### Change Log

- Created Story 5.1 implementation artifact.
- Implemented deterministic resource-phase accounting, added behavior-first resolver coverage for yield/upkeep and deficit clamping, and marked Story 5.1 complete.
