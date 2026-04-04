# Story 49.4: Add guided-agent controls to the live web client

Status: done

## Story

As an authenticated human player,
I want browser controls for whispering guidance and overriding my agent's queued next-tick actions,
So that guided mode is usable from the shipped web client rather than only via raw API calls.

## Acceptance Criteria

1. Given the guided-session, guidance, and override contracts already exist, when the owner opens the live browser flow for their guided agent, then the UI shows the current queued actions, guidance history, and override controls without leaking hidden data or bypassing the existing authenticated session model.
2. Given a guidance or override action succeeds or fails, when the browser updates, then the result is rendered clearly with deterministic success/error states and no pretend optimistic state that outruns the authoritative server contract.
3. Given the story ships, when focused browser-boundary tests plus the repo quality gate run, then the guided live flow remains covered from the real authenticated browser/API boundary and the BMAD artifacts capture the actual verification commands and outcomes.

## Ready Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Tasks / Subtasks

- [x] Add typed client request/response helpers for guided-session reads plus guidance and override writes using the existing bearer-token session and shipped backend routes only. (AC: 1, 2)
- [x] Extend the live browser page with a narrow guided panel that shows current queued actions, prior private guidance, a guidance composer, and an override flow that submits only deterministic next-tick order payloads. (AC: 1, 2)
- [x] Add focused browser-boundary tests covering guided-session loading, success flows, structured error handling, and authoritative websocket/source-of-truth behavior. (AC: 1, 2)
- [x] Re-run focused client verification plus the repo quality gate, then close out the BMAD artifacts with real commands and outcomes. (AC: 3)

## Dev Notes

- Build on Stories 49.1, 49.2, and 49.3; do not add new backend routes or mutate the public server contract in this story.
- Keep the UI deterministic and boring. The guided panel may show accepted guidance/override metadata, but visible authoritative state should still come from the shipped guided-session read model and websocket snapshot rather than optimistic local mutation.
- Reuse the existing browser session model and authenticated live page. Do not add a parallel auth/session configuration path.
- Keep the surface narrow: text-first controls and explicit accepted/error feedback are in scope; speculative state syncing, background polling loops, and workflow redesign are not.

### References

- `core-plan.md#9.1 Bring Your Own Agent`
- `core-plan.md#9.2 Human vs. Agent vs. Guided Play`
- `_bmad-output/planning-artifacts/epics.md#Story 49.4: Add guided-agent controls to the live web client`
- `_bmad-output/implementation-artifacts/49-1-add-an-owned-agent-guided-session-read-model.md`
- `_bmad-output/implementation-artifacts/49-2-deliver-private-human-to-agent-guidance-through-the-briefing-path.md`
- `_bmad-output/implementation-artifacts/49-3-add-pre-tick-human-override-semantics-for-guided-agents.md`
- `client/src/components/matches/human-match-live-page.tsx`
- `client/src/components/matches/human-live/human-match-live-snapshot.tsx`
- `client/src/lib/api.ts`
- `client/src/lib/types.ts`

## Complete Signoff

- [x] Engineering / Architecture
- [x] Product Owner

## Change Log

- 2026-04-04: Drafted Story 49.4 as the browser follow-on to the guided-session read model, private guidance delivery, and guided override server contracts.
- 2026-04-04: Implemented guided live client controls, including additive guided-session guidance history exposure, browser-boundary error coverage, and websocket-tick guided-session refresh.

## Debug Log References

- `uv run pytest --no-cov tests/api/test_agent_api.py -q`
- `cd client && npm test -- --run src/lib/api.test.ts src/components/matches/human-match-live-page.test.tsx`
- `make quality`

## Completion Notes

- Added typed guided-session / guidance / override client helpers and a narrow guided live panel on the authenticated human live page.
- Exposed persisted private guidance history on the existing owned guided-session read model without adding a new route family.
- Added browser-boundary coverage for guided success, guided failure, and websocket-tick guided-session refresh so the panel stays authoritative with the live snapshot.
- Verified controller-side focused API/client checks plus the full repo `make quality` gate successfully passed after merge.

## File List

- `_bmad-output/implementation-artifacts/49-4-add-guided-agent-controls-to-the-live-web-client.md`
- `docs/plans/2026-04-04-story-49-4-guided-agent-live-client-controls.md`
- `client/src/components/matches/human-live/human-live-guided-panel.tsx`
- `client/src/components/matches/human-live/human-match-live-shell.tsx`
- `client/src/components/matches/human-live/human-match-live-snapshot.tsx`
- `client/src/components/matches/human-live/human-match-live-types.ts`
- `client/src/components/matches/human-match-live-page.tsx`
- `client/src/components/matches/human-match-live-page.test.tsx`
- `client/src/lib/api.ts`
- `client/src/lib/api.test.ts`
- `client/src/lib/types.ts`
- `server/api/authenticated_read_routes.py`
- `server/models/api.py`
- `tests/api/test_agent_api.py`
