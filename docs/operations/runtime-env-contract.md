# Runtime Environment Contract

This is the boring runtime contract for Iron Council after Story 51.1. It intentionally documents one small deployable shape:

- **Server:** host-run FastAPI/uvicorn process from this repo.
- **Client:** separately run Next.js process from `client/`.
- **Runtime dependency:** Postgres.
- **Local support-services artifact:** `compose.support-services.yaml` for the shipped Postgres baseline.
- **Operator entrypoint:** `./scripts/runtime-control.sh`.

This story does **not** claim autoscaling, managed secrets, HA orchestration, blue/green deploys, or vendor observability. Stories 51.2 and 51.3 build on this contract for operator signals and launch-readiness smoke coverage.

## Required server variables

| Variable | Required when | Notes |
| --- | --- | --- |
| `DATABASE_URL` | Any DB-backed runtime | SQLAlchemy URL for the durable match/history database. Local docs default to the support-services Postgres; hosted runs should point at a managed or self-run Postgres instance. |
| `IRON_COUNCIL_MATCH_REGISTRY_BACKEND` | Always | Use `db` for any durable shared runtime. `memory` remains useful only for isolated tests or throwaway local sessions. |
| `HUMAN_JWT_SECRET` | Human-authenticated HTTP or websocket flows are enabled | Shared secret used to validate shipped human Bearer tokens. |
| `HUMAN_JWT_ISSUER` | Human-authenticated HTTP or websocket flows are enabled | Expected JWT issuer. |
| `HUMAN_JWT_AUDIENCE` | Human-authenticated HTTP or websocket flows are enabled | Expected JWT audience. |
| `HUMAN_JWT_REQUIRED_ROLE` | Optional in practice, but part of the auth contract | Defaults to `authenticated`; set explicitly in shared runtimes so the contract is visible. |
| `IRON_COUNCIL_AUTHENTICATED_WRITE_MAX_BODY_BYTES` | Optional in practice, but part of the launch abuse-control contract | Defaults to `65536`; authenticated write routes reject larger request bodies with a structured `413 payload_too_large` API error. |
| `IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_LIMIT` | Optional in practice, but part of the launch abuse-control contract | Defaults to `30`; authenticated write routes allow this many requests per caller per guarded route inside the current local window before returning `429 rate_limit_exceeded`. |
| `IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS` | Optional in practice, but part of the launch abuse-control contract | Defaults to `10`; defines the server-local burst window paired with `IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_LIMIT`. |

## Optional server variables

| Variable | Purpose | Default / expectation |
| --- | --- | --- |
| `IRON_COUNCIL_ENV_FILE` | Env file path that the server launcher should load | Defaults to `.env.local`; point it at `.env.runtime` or another private file for shared/hosted operation. |
| `IRON_COUNCIL_BROWSER_ORIGINS` | CORS/browser allowlist for the API process | Defaults to `http://127.0.0.1:3000,http://localhost:3000`. Set it explicitly when the client runs on a different origin. |
| `IRON_COUNCIL_DB_LANE` | Deterministic DB suffix for parallel local lanes | Local-only. Leave unset in shared or hosted runs. |

## Launch abuse-control contract

Stories 52.1 and 52.2 leave behind one intentionally boring abuse-control seam for launch:

- `IRON_COUNCIL_AUTHENTICATED_WRITE_MAX_BODY_BYTES` enforces request-size limits on authenticated HTTP write routes before oversized bodies are processed.
- `IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_LIMIT` plus `IRON_COUNCIL_AUTHENTICATED_WRITE_RATE_WINDOW_SECONDS` define one shared server-local burst window implementation.
- The current shipped runtime reuses that same limiter for authenticated write routes, selected public HTTP hotspots (`/api/v1/matches` and `/health/runtime`), and `/ws/match/{match_id}` websocket handshake bursts.
- Structured failures stay on the existing public contracts: `413 payload_too_large` and `429 rate_limit_exceeded` for HTTP, plus the existing websocket close/error path when handshake bursts are throttled.
- This contract is local in-process only and uses direct caller identity boundaries already available to the server. It does not claim distributed coordination, CDN filtering, or WAF protection.

## Launcher-only operator knobs

These are consumed by `./scripts/runtime-control.sh`, not by application code:

| Variable | Purpose | Default |
| --- | --- | --- |
| `IRON_COUNCIL_SERVER_HOST` | Uvicorn bind host | `127.0.0.1` |
| `IRON_COUNCIL_SERVER_PORT` | Uvicorn bind port | `8000` |
| `IRON_COUNCIL_SERVER_RELOAD` | Adds `--reload` for local operator/dev loops | `false` |
| `IRON_COUNCIL_CLIENT_HOST` | Next.js bind host | `127.0.0.1` |
| `IRON_COUNCIL_CLIENT_PORT` | Next.js bind port | `3000` |

## Client contract

The shipped Next.js client does **not** require checked-in environment variables today.

- Public pages are readable without auth.
- Browser sessions store the API base URL and optional human bearer token in local storage.
- Operators still need the API origin to be reachable from the browser and allowed by `IRON_COUNCIL_BROWSER_ORIGINS`.
- For production-style serving, build the client with `./scripts/runtime-control.sh client-build` and start it with `./scripts/runtime-control.sh client-start`.

## Runtime dependency contract

### Postgres

- The local/developer baseline is defined in `compose.support-services.yaml`.
- The same schema lifecycle is applied through `python -m server.db.tooling setup` / `reset`.
- Shared/hosted operation may replace the local compose Postgres with another Postgres instance, but the runtime contract still expects a reachable `DATABASE_URL` and a migrated schema before the API process starts.

## Checked-in artifacts

Story 51.1 intentionally leaves behind a small concrete runtime surface:

- `./scripts/runtime-control.sh`
- `env.runtime.example`
- `compose.support-services.yaml`
- this contract doc
- `docs/operations/runtime-runbook.md`

Use those as the single source of truth for Stories 51.2 and 51.3.
