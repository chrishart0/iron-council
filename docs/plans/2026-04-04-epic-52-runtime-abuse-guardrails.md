# Epic 52 Runtime Abuse Guardrails Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add the smallest honest abuse-protection slice needed for the first public launch: request-size limits and identity-aware rate limiting on the highest-risk write surfaces, then extend the same guardrails to websocket/public entrypoints and launch docs.

**Architecture:** Keep Epic 52 boring and server-local. Reuse the existing FastAPI app, settings/env contract, and `ApiError` surface rather than introducing Redis, vendor middleware, or distributed quotas. The first story should add one reusable abuse-guard seam plus production-facing enforcement on authenticated write routes so later stories can extend the same policy model to websocket handshakes, public reads, and operator docs without splitting behavior across multiple mechanisms.

**Tech Stack:** Python 3.12, FastAPI, Starlette middleware/dependencies, existing `server.settings` env loading, `ApiError` structured responses, pytest API/e2e coverage, `make quality`, runtime contract docs.

---

## Parallelism and dependency notes

- **Must go first:** Story 52.1. Later guardrail work should not invent second policy mechanisms or duplicate env knobs.
- **Sequential after 52.1:** Story 52.2 depends on the shared limiter/size-limit seam but can focus on websocket/public-entrypoint enforcement.
- **Can overlap after 52.1 if needed:** Story 52.3 can draft docs/smoke validation against the 52.1 contract while 52.2 finishes, but controller review should keep final merge order simple.
- **Controller rule:** prefer small in-process guardrails and public-boundary tests. Do not widen scope into CDN/WAF/payment abuse, bot scoring, CAPTCHA, or distributed infrastructure.

## Epic sequencing

1. **Story 52.1:** add authenticated write abuse guardrails.
2. **Story 52.2:** extend abuse guardrails to websocket and public-entrypoint hotspots.
3. **Story 52.3:** document and validate the launch abuse-control contract.

## Story breakdown

### Story 52.1: Add authenticated write abuse guardrails

**Objective:** Add one reusable server-local abuse-protection seam and enforce it on the highest-risk authenticated write routes with structured `413` / `429` responses.

**Files:**
- Modify: `server/main.py`
- Modify: `server/settings.py`
- Modify: `server/api/authenticated_write_routes.py`
- Modify: `server/api/errors.py`
- Create: `server/api/abuse.py`
- Test: `tests/api/test_authenticated_write_abuse.py`
- Test: `tests/test_runtime_contract_docs.py`
- Docs: `docs/operations/runtime-env-contract.md`, `README.md`, `env.runtime.example`

**Bite-sized tasks:**
1. Write failing API-boundary tests for oversized write requests and bursty repeated writes returning structured `413` / `429` errors.
2. Add settings/env knobs for max authenticated-write request bytes and per-window write burst limits.
3. Implement a tiny in-process abuse helper (`server/api/abuse.py`) that can:
   - reject oversized request bodies from `Content-Length` and bounded body reads
   - track simple per-identity/per-route rate windows without external services
4. Wire the helper into authenticated write routes only, keeping identity keys aligned with the already-resolved API key / human auth boundary.
5. Update runtime-contract docs and env example with the new knobs.
6. Re-run focused tests, then `make quality`, and record the real commands/outcomes in the story artifact.

**Guardrails:**
- No Redis, Celery, or vendor rate-limit package unless an existing repo convention requires it.
- No per-endpoint magic numbers hidden in route code; policies should come from one settings-backed seam.
- Do not weaken existing auth semantics to make throttling easier.

### Story 52.2: Extend abuse guardrails to websocket and public-entrypoint hotspots

**Objective:** Reuse the same settings/policy seam for public browse hotspots and websocket handshake bursts so launch abuse controls are not write-only.

**Bite-sized tasks:**
1. Add failing public-boundary tests for repeated websocket or browse entrypoint abuse.
2. Extend the 52.1 guard seam to the selected public/websocket hotspots.
3. Keep the responses honest and narrow: `429` for burst abuse, auth/close semantics unchanged otherwise.
4. Re-run focused tests plus any real-process smoke that exercises those entrypoints.

### Story 52.3: Document and validate the launch abuse-control contract

**Objective:** Fold the shipped abuse controls into the runtime env/runbook story so operators know which knobs exist and the launch smoke path proves the contract stays wired.

**Bite-sized tasks:**
1. Update README/runtime env contract/runbook with the abuse-control knobs and intended launch posture.
2. Add docs regression coverage and, if needed, one narrow smoke assertion that the configured controls appear in the expected runtime path.
3. Re-run `make quality` and any launch-focused smoke target touched by the docs or settings flow.

## Expected deliverables

- One shared abuse-guard helper and settings contract.
- Structured `413 payload_too_large` / `429 rate_limit_exceeded` style responses on authenticated write routes.
- Docs and runtime env examples that describe the launch abuse-control knobs honestly.

## Out of scope

- Distributed/global rate limiting
- Payment fraud, Stripe enforcement, or entitlement redesign
- CAPTCHA / bot-detection systems
- CDN/WAF configuration
- Per-message moderation or content scanning
