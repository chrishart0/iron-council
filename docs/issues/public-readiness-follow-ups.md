# Public Readiness Follow-Ups

Date: 2026-04-01
Source: [public repo assessment](../consulting/public-repo-assessment-2026-04-01.md)

## Priority Queue

1. Canonicalize project/package naming.
Owner suggestion: maintainers
Scope: replace or intentionally alias remaining `iron-counsil` identifiers in package metadata, service metadata, local dev defaults, and public-facing strings.
Grounding: [pyproject.toml](../../pyproject.toml), [server/main.py](../../server/main.py#L738), [compose.support-services.yaml](../../compose.support-services.yaml), [env.local.example](../../env.local.example), [server/settings.py](../../server/settings.py).

2. Refactor the human live page into smaller UI and state slices.
Owner suggestion: client maintainers
Scope: carve [human-match-live-page.tsx](../../client/src/components/matches/human-match-live-page.tsx) into smaller components/hooks without changing the public route contract.
Why now: the file is already 2,167 lines and sits on a high-change, user-visible path.

3. Split server API/app wiring out of the monolithic main module.
Owner suggestion: server maintainers
Scope: move route groups, app setup, or dependency wiring out of [server/main.py](../../server/main.py) behind stable module boundaries.
Why now: the file is already 2,140 lines and is a likely regression magnet as public API surface grows.

4. Reduce registry concentration in server persistence and agent workflows.
Owner suggestion: server maintainers
Scope: review [server/agent_registry.py](../../server/agent_registry.py) and [server/db/registry.py](../../server/db/registry.py) for extraction opportunities around read/write responsibilities and lifecycle operations.

5. Continue public-doc curation around BMAD-visible repo structure.
Owner suggestion: docs maintainers
Scope: keep [README.md](../../README.md) and [docs/index.md](../../docs/index.md) as the first stop for external readers and avoid letting planning artifacts become the accidental public landing surface.
