# Story 53.1: Add a public demo walkthrough and entrypoint docs cleanup

Status: approved

## Story

As a first-time external reader,
I want one obvious demo walkthrough plus better linked operator docs,
So that I can reach a credible try-it-now path without reading through internal planning artifacts first.

## Acceptance Criteria

1. Given the repo already has a working README, docs index, runtime contract, and public routes, when a newcomer follows the top-level documentation, then they can see one explicit demo walkthrough covering public browse, live spectator viewing, authenticated human lobby access, and BYOA agent-key onboarding with honest prerequisites.
2. Given runtime runbook and env-contract docs already exist, when the docs cleanup ships, then the README and docs index link to those operator-facing entrypoints in a way that is easy to find from the public landing page rather than buried in delivery history.
3. Given the story ships, when focused docs regression coverage plus the relevant repo quality checks run, then they pass and this artifact records the real commands and outcomes.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [ ] Add a concise public demo walkthrough that covers public browse, live spectator viewing, authenticated lobby entry, and BYOA onboarding without overclaiming hosted/demo availability. (AC: 1)
- [ ] Update the README and docs index so the new walkthrough plus runtime env/runbook links are easy to find from the public landing path. (AC: 1, 2)
- [ ] Re-run focused docs verification and the relevant repo gate, then record the real outcomes here. (AC: 3)

## Dev Notes

- Keep this story docs-only.
- Reuse the existing runtime-control, runtime env contract, and route surfaces; do not invent new setup flows.
- Aim for one clean try-it-now path rather than adding another sprawling docs map.

### References

- `docs/issues/public-readiness-follow-ups.md`
- `docs/consulting/public-repo-assessment-2026-04-01.md`
- `_bmad-output/planning-artifacts/epics.md#Epic 53: Public Demo and Launch Polish`
- `docs/plans/2026-04-04-epic-53-public-demo-launch-polish.md`
- `README.md`
- `docs/index.md`
- `docs/operations/runtime-env-contract.md`
- `docs/operations/runtime-runbook.md`

## Complete Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-04: Drafted Story 53.1 for the post-runtime public demo/docs polish slice.

## Debug Log References

- Pending implementation.

## Completion Notes

- Pending implementation.

## File List

- `_bmad-output/implementation-artifacts/53-1-add-a-public-demo-walkthrough-and-entrypoint-docs-cleanup.md`
