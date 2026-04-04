# Story 50.1: Harden in-memory diplomacy and messaging contract edges

Status: in_progress

## Story

As a maintainer,
I want focused behavior-first regressions around the in-memory diplomacy and messaging seams,
So that treaty/alliance transitions and chat visibility rules stay deterministic while the registry remains a simple compatibility surface.

## Acceptance Criteria

1. Given alliance creation, join, leave, and treaty transitions already power the authenticated API and smoke fixtures, when focused regressions exercise edge transitions such as missing inputs, leader handoff, unsupported treaty accept/withdraw flows, and `since_tick` visibility filters, then the tests pin the current public behavior without reaching into implementation details or relying on internal ordering not exposed by the registry contract.
2. Given world/direct/group messaging all feed briefings and live views, when focused regressions cover recipient validation, membership enforcement, and visible message grouping, then the implementation keeps the same deterministic browser/agent-facing behavior and any necessary production changes remain small and convention-aligned.
3. Given the story ships, when the focused test slice and the repo quality gate run, then the new regressions pass and the BMAD artifact records the real verification commands and outcomes.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add focused regressions for alliance/treaty transition edge cases and `since_tick` filtering at the `AgentRegistry` boundary. (AC: 1)
- [x] Add focused regressions for messaging recipient validation, group membership enforcement, and briefing visibility/grouping behavior. (AC: 2)
- [x] Make the smallest implementation cleanup needed for any exposed drift, keeping the registry surface boring and convention-aligned. (AC: 1, 2)
- [ ] Re-run the focused test slice plus `make quality`, then close out this BMAD artifact with real outcomes. (AC: 3)

## Dev Notes

- Keep the scope narrow to `server/agent_registry_diplomacy.py`, `server/agent_registry_messaging.py`, and their existing `AgentRegistry` behavior surfaces.
- Prefer tests at the `tests/test_agent_registry.py` boundary over direct helper internals unless a tiny direct helper test is the only honest way to pin a public compatibility seam.
- If a production change is required, favor the smallest fix over new abstractions.
- Do not broaden into DB-backed diplomacy/message flows; this story is only about the in-memory compatibility path.

### References

- `_bmad-output/planning-artifacts/epics.md#Story 50.1: Harden in-memory diplomacy and messaging contract edges`
- `server/agent_registry.py`
- `server/agent_registry_diplomacy.py`
- `server/agent_registry_messaging.py`
- `tests/test_agent_registry.py`
- `tests/api/test_agent_api.py`

## Complete Signoff

- [ ] Engineering / Architecture
- [ ] Product Owner

## Change Log

- 2026-04-04: Drafted Story 50.1 to harden high-risk in-memory diplomacy and messaging behaviors after the guided-agent milestone.
- 2026-04-04: Added a focused AgentRegistry regression for unsupported treaty withdrawal without an existing treaty and verified the full `tests/test_agent_registry.py` contract slice on `story/50-1-contract-hardening`.

## Debug Log References

- 2026-04-04: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py -k 'treaty or alliance or message or group_chat or briefing'` (pass)
- 2026-04-04: `uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_agent_registry.py` (pass)
- 2026-04-04: `make quality` (fails in baseline mypy environment with widespread third-party import resolution errors such as missing `pydantic`, `fastapi`, and `sqlalchemy` stubs; not caused by this story-local regression)

## Completion Notes

- Existing production behavior already rejected unsupported withdraws at the AgentRegistry boundary with `treaty_not_found`; the follow-up only needed a missing regression test, not a production change.
- The unsupported treaty withdraw regression stays story-local in `tests/test_agent_registry.py` and leaves unrelated legacy test coverage untouched.
- Story closeout remains blocked on the repo-wide `make quality` failure, so the artifact stays in progress despite the targeted registry regressions passing.

## File List

- `_bmad-output/implementation-artifacts/50-1-harden-in-memory-diplomacy-and-messaging-contract-edges.md`
- `tests/test_agent_registry.py`
