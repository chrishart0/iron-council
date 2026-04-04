# Public Readiness Follow-Ups

Date: 2026-04-04
Source: [public repo assessment](../consulting/public-repo-assessment-2026-04-01.md)

## Priority Queue

1. Define deployable runtime packaging, environment contract, and an operator runbook.
Owner suggestion: platform/server/docs maintainers
Scope: make the shipped server, client, and support-service runtime honestly deployable outside the current dev-only context with one boring packaging path and one explicit env contract.
Why now: Epic 51 should start by removing ambiguity around how Iron Council is started, checked, and recovered in a real launch scenario.

2. Add runtime observability for tick drift, websocket fanout, and restart recovery.
Owner suggestion: server/platform maintainers
Scope: expose boring operator-facing signals for the async tick loop, websocket connection/fanout behavior, and whether active matches resume cleanly after process restart.
Why now: the architecture already calls out these failure modes as launch risks, but the repo still lacks a small, explicit observability seam for them.

3. Add multi-match/load validation plus a launch-readiness smoke path.
Owner suggestion: server/QA maintainers
Scope: prove the packaged runtime survives a small realistic concurrent-match slice with websocket subscribers and restart/resume checks, without pretending to ship large-scale benchmarking.
Why now: current quality gates prove correctness well, but launch confidence still leans too hard on single-match or developer-local assumptions.

4. Do one small public demo and launch-polish pass after runtime hardening lands.
Owner suggestion: docs/client maintainers
Scope: tighten the public-facing demo path, operator-facing docs links, and any obviously rough launch copy or presentation seams that still block a credible first public showing.
Why now: once the runtime path is honest, the remaining launch debt should be framed as polish and demo readiness rather than more internal refactor work.
