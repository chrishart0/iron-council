# Epic 53 Public Demo and Launch Polish Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make the first public showing of Iron Council easier to follow by tightening the top-level demo/docs path and polishing the client’s landing/session-bootstrap copy for first-time visitors.

**Architecture:** Keep Epic 53 intentionally small and launch-facing. Story 53.1 should improve the README/docs path so an external reader can find the public demo journey and operator docs without digging through BMAD history. Story 53.2 should stay entirely in the client, clarifying which routes are public, which require a bearer token, and how browser-session bootstrap connects to the shipped owned API-key flow.

**Tech Stack:** Markdown docs, Next.js 14 / React / TypeScript, Vitest + Testing Library, existing session-provider/session-config UI, `uv run pytest --no-cov`, `make client-test`, `make client-build`, `make quality`.

---

## Parallelism and dependency notes

- **Can run in parallel after this planning commit lands:** Story 53.1 mostly touches `README.md`, `docs/index.md`, and one new public demo guide. Story 53.2 mostly touches `client/src/app/page.tsx`, client tests, and session/sidebar UI.
- **Keep merge order simple:** review and merge Story 53.1 first because it defines the public demo language that Story 53.2 should stay aligned with, even though the file overlap is low.
- **Controller rule:** do not invent new backend endpoints, deployment promises, or future billing/account UX. This epic is launch polish over already shipped surfaces.

## Epic sequencing

1. **Story 53.1:** add a public demo walkthrough and entrypoint docs cleanup.
2. **Story 53.2:** polish the client home and session bootstrap for first-time visitors.

## Story breakdown

### Story 53.1: Add a public demo walkthrough and entrypoint docs cleanup

**Objective:** Give first-time readers one obvious try-it-now path and make the operator-facing runtime docs easy to discover from the public entrypoints.

**Files:**
- Modify: `README.md`
- Modify: `docs/index.md`
- Create: `docs/guides/public-demo-walkthrough.md`
- Test: `tests/test_runtime_contract_docs.py`
- Story: `_bmad-output/implementation-artifacts/53-1-add-a-public-demo-walkthrough-and-entrypoint-docs-cleanup.md`

**Bite-sized tasks:**
1. Write a failing docs regression proving the new walkthrough and top-level links are present.
2. Add a concise `docs/guides/public-demo-walkthrough.md` covering public browse, spectator/live inspection, authenticated lobby, and BYOA onboarding with honest prerequisites.
3. Update `README.md` and `docs/index.md` to surface the walkthrough plus the existing runtime env/runbook docs earlier.
4. Re-run focused docs tests, then the relevant repo gate, and record the real outcomes in the story artifact.

**Guardrails:**
- No new claims about hosted deployments, demo servers, or public internet availability.
- Keep the walkthrough centered on already shipped routes and checked-in runtime commands.
- Prefer one short explicit walkthrough over scattering duplicate prose everywhere.

### Story 53.2: Polish the client home and session bootstrap for first-time visitors

**Objective:** Make the shipped client home page and browser-session sidebar explain the public-demo path and authenticated next steps clearly.

**Files:**
- Modify: `client/src/app/page.tsx`
- Modify: `client/src/app/page.test.tsx`
- Modify: `client/src/components/session/session-config-panel.tsx`
- Modify: `client/src/components/session/session-config-panel.test.tsx`
- Story: `_bmad-output/implementation-artifacts/53-2-polish-the-client-home-and-session-bootstrap-for-first-time-visitors.md`

**Bite-sized tasks:**
1. Write failing client tests for public-vs-auth labels, clearer next-step copy, and quick links.
2. Update the home page so it presents a concise public-demo path plus authenticated follow-ons without overclaiming.
3. Update the session config panel copy/quick links so the bearer-token relationship to lobby access and owned API keys is obvious.
4. Re-run focused client tests, then the relevant repo gate, and record the real outcomes in the story artifact.

**Guardrails:**
- Keep the story client/docs-only; no backend/API changes.
- Do not add future-looking billing, payment, or deployment UX.
- Prefer stable route links and user-facing copy over internal implementation abstractions.

## Expected deliverables

- One obvious public demo walkthrough in the docs.
- Cleaner README/docs-index entrypoints for runtime/operator docs.
- A more self-explanatory client home page and session sidebar for first-time visitors.

## Out of scope

- New public APIs or backend runtime behavior
- Hosted demo environments or public deployment automation
- Billing flows, entitlement redesign, or account management beyond the shipped API-key surface
- Broad visual redesign or CSS overhaul
