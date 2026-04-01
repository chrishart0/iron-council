# Public Repository Readiness Plan

> For Hermes: treat this as an epic-level repo-polish and public-launch-readiness plan. Commit and push after each coherent slice.

Goal: make Iron Council legible, trustworthy, and attractive to an external visitor who lands on the public GitHub repo with no prior context.

Why now:
- The repo is now public.
- The engineering quality is already strong enough to support outside attention.
- The current public framing lags the implementation quality.

Public-readiness assessment summary:
- Strengths: strong quality gate, meaningful test coverage, real backend/client/SDK surface, credible architecture docs.
- Biggest gaps: sparse README, naming inconsistency (`iron-counsil` vs `iron-council`), missing LICENSE / CONTRIBUTING / CODE_OF_CONDUCT / SECURITY, and too much internal-process noise in the public first impression.
- Product risk: outsiders may conclude the project is an exposed internal workspace rather than a curated public project.

## Epic: Public repository readiness and curation

This epic packages the work needed before broader public promotion.

### Desired outcome
A new visitor should be able to answer all of these within 2-3 minutes:
- What is Iron Council?
- Who is it for?
- What works today?
- How do I run it locally?
- How do I use the SDK?
- What is the current project status?
- What are the rules for using, contributing to, and reporting issues on the repo?

## Scope

### In scope
1. Public README overhaul
2. Repo naming cleanup in public-facing surfaces
3. Open-source trust/governance files
4. Curated docs entrypoint for external readers
5. Public-facing quality and architecture summary
6. Clean code consultant review write-up with visible follow-up actions

### Out of scope
- Large feature implementation unrelated to repo presentation
- Full architectural refactors of existing large files
- Production deployment hardening beyond basic public documentation

## Acceptance criteria

### AC1: README works as a landing page
- README opens with a clear one-paragraph product summary.
- README explains the core pillars: diplomacy, bring-your-own-agent, spectator-first drama.
- README includes current status: what is implemented today vs still planned.
- README includes a 5-minute local quickstart for server, client, and example agent/SDK flow.
- README links to deeper docs for architecture, SDK, contribution, and security.

### AC2: Public naming is consistent
- Top-level public-facing docs and metadata use a single canonical project spelling.
- Unintended `iron-counsil` references are removed or minimized from public surfaces.
- Any legacy/internal exceptions are documented if they remain temporarily.

### AC3: Trust scaffolding exists
- Add `LICENSE`.
- Add `CONTRIBUTING.md`.
- Add `CODE_OF_CONDUCT.md`.
- Add `SECURITY.md`.
- Link all of them from the README.

### AC4: Public docs are curated
- Add a simple docs index or “Start here” section.
- Explain unusual public directories that remain visible (`_bmad`, `_bmad-output`, `AGENTS.md`) or reduce their prominence.
- Remove or reframe clearly confusing public wording such as confidential/pre-production language where inappropriate for a public repo.

### AC5: Public quality story is obvious
- README summarizes the quality harness (`make quality`, CI, coverage gate, smoke tests).
- README includes a short architecture-at-a-glance section.
- Consultant assessment is captured as a public/internal artifact with prioritized follow-up actions.

### AC6: Public launch debt is explicit
- Create follow-up issues for maintainability hotspots discovered during the consultant pass.
- At minimum, identify oversized public hotspots and document them as known technical debt.

## Proposed stories

### Story 1: README and first-impression overhaul
As a public visitor,
I want the README to feel like a polished game/product page rather than internal setup notes,
so that I immediately understand why Iron Council is exciting and how AI agents fit into the experience.

Done when:
- landing-page README exists
- opening copy is user-facing and energetic
- README clearly pitches the core fantasy: diplomacy, spectatorship, and bring-your-own-agent play
- README includes a dedicated section on how your own AI agent can play through the shipped API/SDK
- README includes at least 2-3 strong gameplay/product screenshots (public match browser, match detail, live spectator or human live view)
- quickstart is tested
- SDK/client/server links are prominent
- README distinguishes player value, agent-builder value, and spectator value

### Story 2: OSS trust and governance files
As a potential user or contributor,
I want clear usage, contribution, and conduct rules,
so that I know how to engage with the project safely.

Done when:
- LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY all exist and are linked

### Story 3: Public docs curation and naming cleanup
As an external reader,
I want the repo structure and naming to feel intentional,
so that the project feels credible rather than accidental.

Done when:
- public naming is aligned
- confusing/confidential wording is removed or contextualized
- docs entrypoint exists

### Story 4: Clean-code consultant pass and follow-up issue set
As a maintainer,
I want a concise consultant-style assessment of public-facing code and repo maturity,
so that the next cleanup work is prioritized and visible.

Done when:
- strengths / risks / hotspots are documented
- at least one follow-up issue list exists for major maintainability concerns

## Suggested implementation order
1. Story 1: README and first impression
2. Story 2: OSS trust files
3. Story 3: docs curation and naming cleanup
4. Story 4: consultant pass and follow-up issues

## Notes from current assessment
- Current README begins with local support services instead of product framing.
- No LICENSE found.
- No CONTRIBUTING found.
- No CODE_OF_CONDUCT found.
- No SECURITY policy found.
- `core-plan.md` still contains `Confidential`, which is a poor fit for a public repo unless intentionally preserved and contextualized.
- Engineering quality is already a selling point and should be surfaced more clearly.
- Screenshot capture from the live Next.js client is currently blocked in local browser runs by missing CORS headers on the FastAPI public API, so screenshot-ready polish may require either enabling local browser access or capturing against a packaged/demo environment.

## Verification checklist
- A cold external reader can explain the project after reading README only.
- A developer can run the documented quickstart without guesswork.
- Repo root includes the standard governance files expected of a public project.
- Public docs no longer feel like internal-only notes.
- Follow-up debt/issues exist for anything intentionally deferred.
