# Public Repo Assessment

Date: 2026-04-01
Scope: public-readiness Story 4 consultant pass

## Overall Readiness

Iron Council now presents as a credible public engineering project rather than an internal-only worktree. The README, docs entrypoint, and governance files give an external visitor enough context to understand the product, the quality bar, and how to engage with the repo.

The remaining public-readiness debt is narrower and more structural than existential. The biggest visible issue is unresolved naming inconsistency between `Iron Council` and `iron-counsil` across package, service, and local-dev surfaces. That mismatch is still noticeable enough to keep the broader public-readiness epic in progress.

## Strengths

- Public entrypoints are now clear: [README.md](/tmp/iron-public-assessment/README.md) and [docs/index.md](/tmp/iron-public-assessment/docs/index.md) explain the game, shipped surface, local quickstart, and quality story without hiding how the repo is built.
- Trust scaffolding is present: [LICENSE](/tmp/iron-public-assessment/LICENSE), [CONTRIBUTING.md](/tmp/iron-public-assessment/CONTRIBUTING.md), [CODE_OF_CONDUCT.md](/tmp/iron-public-assessment/CODE_OF_CONDUCT.md), and [SECURITY.md](/tmp/iron-public-assessment/SECURITY.md) make the public repo feel maintained.
- The engineering quality bar is visible and credible. The root [Makefile](/tmp/iron-public-assessment/Makefile) exposes a coherent `make quality` gate spanning formatting, linting, strict typing, Python tests, client checks, and production build verification.
- The repo has real product depth rather than placeholder scaffolding: server, client, SDK, seeded local workflows, and public browse/live surfaces are all visible in the current tree.

## Public-Facing Risks

- Naming inconsistency remains unresolved. Public branding now says `Iron Council`, but runtime and package-facing surfaces still expose `iron-counsil`, including [pyproject.toml](/tmp/iron-public-assessment/pyproject.toml), [server/main.py](/tmp/iron-public-assessment/server/main.py#L738), [server/settings.py](/tmp/iron-public-assessment/server/settings.py), [compose.support-services.yaml](/tmp/iron-public-assessment/compose.support-services.yaml), and [env.local.example](/tmp/iron-public-assessment/env.local.example). This creates avoidable friction for external readers and future package consumers.
- Public docs still require some explanation of BMAD-heavy repository structure. The new docs do that honestly, but the repo still reads as "built in public with process artifacts attached" rather than a fully curated external product repo.

## Maintainability Hotspots

- [server/main.py](/tmp/iron-public-assessment/server/main.py) is currently 2,140 lines and concentrates a large amount of API and app wiring. That is workable today, but it is an obvious future split candidate.
- [client/src/components/matches/human-match-live-page.tsx](/tmp/iron-public-assessment/client/src/components/matches/human-match-live-page.tsx) is currently 2,167 lines. That makes the most complex human live surface expensive to reason about and raises regression risk for future UI changes.
- [server/agent_registry.py](/tmp/iron-public-assessment/server/agent_registry.py) at 1,599 lines and [server/db/registry.py](/tmp/iron-public-assessment/server/db/registry.py) at 1,559 lines suggest registry and persistence responsibilities are accumulating in large single modules.
- [client/src/lib/api.ts](/tmp/iron-public-assessment/client/src/lib/api.ts) at 1,393 lines is another visible concentration point on the public client boundary.

These are not immediate blockers, and this assessment does not claim they are broken. They are worth tracking because they are large enough to slow safe public-facing iteration.

## Priority Follow-Ups

1. Resolve the `iron-counsil` versus `iron-council` naming debt across package metadata, service metadata, local dev defaults, and user-visible strings, with a compatibility plan where direct renames would be disruptive.
2. Split the largest public-facing modules along stable boundaries, starting with [server/main.py](/tmp/iron-public-assessment/server/main.py) and [client/src/components/matches/human-match-live-page.tsx](/tmp/iron-public-assessment/client/src/components/matches/human-match-live-page.tsx).
3. Define a lighter-weight public-facing explanation strategy for BMAD artifacts over time so external readers can find product and developer docs before process history.
4. Add a small public demo/deployment guidance slice when the project is ready, since local quality is now well documented but public try-it-now guidance is still intentionally absent.
