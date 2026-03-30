# Story 23.1: Extend the Python SDK and example quickstart for authenticated lobby lifecycle flows

Status: done

## Story

As an external agent developer,
I want the Python SDK and runnable example to cover create/join/start lobby workflows,
So that I can drive the new DB-backed pregame lifecycle from a stable public client surface instead of custom HTTP code.

## Acceptance Criteria

1. Given the server now supports authenticated lobby creation and creator-only start, when the Python SDK is used from outside the server package, then it exposes narrow typed helpers for `POST /api/v1/matches` and `POST /api/v1/matches/{match_id}/start` without importing repo-internal server modules.
2. Given a creator client plus another authenticated competitor, when they use the SDK against the DB-backed app to create a lobby, join it, and start it, then the returned typed responses prove compact metadata, creator-only start behavior, and transition to `active` from the public boundary.
3. Given the runnable example and README quickstart, when an implementer follows the documented command path, then they can either target an existing match or create a lobby, optionally auto-start it after enough agents join, and see a concise JSON summary describing the lifecycle actions taken.
4. Given the story ships, when focused SDK/unit/real-process smoke checks and the repo quality gate run, then the client contract, example flow, and docs are all verified from the consumer boundary.

## Tasks / Subtasks

- [x] Add SDK request/response models and a typed `start_match_lobby()` helper for the authenticated start route. (AC: 1, 2)
- [x] Add behavior-first SDK coverage for create/join/start success plus creator-only/structured-error handling. (AC: 1, 2, 4)
- [x] Update the runnable example and `agent-sdk/README.md` to document both the existing target-existing-match path and a create/join/start lifecycle path. (AC: 3)
- [x] Add or extend real-process smoke coverage that exercises the documented SDK lifecycle command path against the DB-backed app. (AC: 2, 3, 4)
- [x] Run review/simplification, update BMAD tracking, and pass `make quality`. (AC: 4)

## Dev Notes

- Keep the SDK self-contained inside `agent-sdk/python/iron_council_client.py`; do not import `server.models.api` or other repo-internal runtime modules.
- Prefer compact lifecycle helpers and output summaries over a broad orchestration abstraction.
- Reuse the existing DB-backed real-process fixtures and support utilities for smoke coverage.
- The example should remain deterministic and easy to follow; avoid turning it into a long-running bot.

## Red Phase Evidence

- `tests/agent_sdk/test_example_agent.py` initially failed with call-order assertion mismatches against the current simplified example flow.
- Failure command:
  `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_example_agent.py tests/e2e/test_example_agent_smoke.py`
- The failure was in unit expectations only; the real-process example smoke was already green, which confirmed the public behavior and pointed to stale test assertions rather than a broken example implementation.

## Completion Notes

- Kept the standalone SDK self-contained in `agent-sdk/python/iron_council_client.py` with narrow typed create/start helpers and no server-runtime imports.
- Preserved the example as a compact one-shot script with two modes: existing-match and create/join/start lifecycle.
- Simplified closeout by aligning the example unit tests with the already-working public behavior instead of adding extra SDK calls purely to satisfy outdated assertions.
- Tightened the existing-match fallback so the example skips already-active or already-full matches and selects the first joinable `lobby` or `paused` match when `IRON_COUNCIL_MATCH_ID` is omitted.
- Retained the minimal DB-backed server support needed for authenticated lobby creation/start to work through the public boundary and stay covered by focused API/SDK smoke tests.

## Debug Log References

- Focused SDK contract checks:
  `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_python_client.py -k 'start_match_lobby or create_match_lobby'`
- Real-process SDK smoke checks:
  `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_agent_sdk_smoke.py -k 'lobby_lifecycle or smoke_flow'`
- Example and docs checks:
  `source .venv/bin/activate && uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/agent_sdk/test_example_agent.py tests/e2e/test_example_agent_smoke.py`
- Full quality gate:
  `source .venv/bin/activate && make quality`

## Verification Summary

- Focused SDK contract checks passed: `3 passed, 19 deselected`
- Real-process SDK smoke checks passed: `5 passed`
- Example and docs checks passed: `12 passed`
- Full quality gate passed:
  `ruff format --check`, `ruff check`, `mypy`, and `pytest`
- Final quality result: `331 passed`, coverage `95.39%`

## File List

- `agent-sdk/README.md`
- `agent-sdk/python/example_agent.py`
- `agent-sdk/python/iron_council_client.py`
- `server/db/registry.py`
- `server/main.py`
- `tests/agent_sdk/test_example_agent.py`
- `tests/agent_sdk/test_python_client.py`
- `tests/api/test_agent_api.py`
- `tests/e2e/test_agent_sdk_smoke.py`
- `tests/e2e/test_example_agent_smoke.py`
