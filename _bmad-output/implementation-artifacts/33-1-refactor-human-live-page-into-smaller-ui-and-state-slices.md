# Story: 33.1 Refactor human live page into smaller UI and state slices

Status: drafted

## Story

As a client maintainer,
I want the authenticated human live match page split into focused shell, state, and panel modules,
So that future live UI work can evolve without one 2k-line component remaining the only place that knows about session state, websocket lifecycle, summaries, messaging, diplomacy, and order drafting.

## Acceptance Criteria

1. `client/src/components/matches/human-match-live-page.tsx` remains the stable route-facing entrypoint, but the fetch/websocket/session lifecycle and the major read/write page surfaces move behind focused client modules under `client/src/components/matches/human-live/` without changing the shipped route, browser-visible headings, websocket behavior, or API helper contract.
2. The refactor preserves the existing authenticated human live experience, including the hero/loading/not-live states, map selection inspector, live summary/resources/movement panels, messaging, diplomacy, and order-draft workflows.
3. Focused browser-boundary regression tests cover the preserved human live page contract, and the repo quality gate passes.
4. The final implementation is simpler than the starting point: no framework-heavy abstraction, no context/provider sprawl, and no new generic UI system introduced just for this refactor.

## Tasks / Subtasks

- [ ] Pin the current browser contract with focused human live page regression coverage. (AC: 1, 2, 3)
- [ ] Extract the route shell and live-state hook behind boring explicit modules. (AC: 1, 2, 4)
- [ ] Extract read-only snapshot panels and selection helpers into focused components. (AC: 1, 2, 4)
- [ ] Extract interactive messaging, diplomacy, and order-draft panels while preserving current submit/feedback behavior. (AC: 1, 2, 4)
- [ ] Run focused client verification, simplification review, and the repo quality gate. (AC: 3, 4)
- [ ] Update sprint tracking and completion notes after merge. (AC: 3)

## Dev Notes

- This follows the explicit follow-up queue in `docs/issues/public-readiness-follow-ups.md`.
- Scope is refactor only. No new route, no API contract expansion, no websocket protocol changes, no new design system.
- Prefer boring component and hook seams over clever generic abstractions.
- Keep behavior tests at the user/browser boundary; do not rewrite the suite around implementation details.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Pending

### Completion Notes List

- Pending

### File List

- Pending
