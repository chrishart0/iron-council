# Runtime Runbook

This runbook documents the first boring operator path for Iron Council. It is intentionally small and honest:

- server runs directly from this repo with `uv run uvicorn`
- client runs separately from `client/`
- Postgres is the only required runtime dependency in the shipped baseline
- local/demo support services come from `compose.support-services.yaml`
- `./scripts/runtime-control.sh` is the checked-in operator entrypoint

Stories 51.2 and 51.3 will add explicit operator signals and a broader launch-readiness smoke path. This runbook defines the startup order and recovery baseline they should reuse.

## 1. Bootstrap the workspace

```bash
make setup
./scripts/runtime-control.sh client-install
cp env.local.example .env.local
cp env.runtime.example .env.runtime
```

Use `.env.local` for the shipped local support-services defaults. Treat `.env.runtime` (or another private file) as the explicit operator-owned env surface for any shared or hosted run, and edit it before use because `env.runtime.example` intentionally contains placeholder secrets and a placeholder hosted `DATABASE_URL`.

## 2. Run the operator doctor check

### Local/demo baseline

```bash
IRON_COUNCIL_ENV_FILE=.env.local ./scripts/runtime-control.sh doctor
```

### Shared/hosted baseline

```bash
IRON_COUNCIL_ENV_FILE=.env.runtime ./scripts/runtime-control.sh doctor
```

Expected output includes:

- repo root
- compose file path
- server env file path
- server and client URLs
- `IRON_COUNCIL_MATCH_REGISTRY_BACKEND`
- the `/health` curl target

If the env file does not exist yet, the doctor command warns instead of pretending the runtime is ready.

## 3. Start runtime dependencies

### Local/demo baseline

```bash
./scripts/runtime-control.sh support-up
IRON_COUNCIL_ENV_FILE=.env.local ./scripts/runtime-control.sh db-setup
```

This starts the shipped Postgres container and applies migrations plus deterministic seed data.

### Shared/hosted variant

If you are not using the local compose Postgres, provision your own Postgres first, set `DATABASE_URL` in the env file, and still run the same `db-setup` step against that database before the API process comes up.

## 4. Start the API process

### Local operator/dev loop

```bash
IRON_COUNCIL_ENV_FILE=.env.runtime \
IRON_COUNCIL_MATCH_REGISTRY_BACKEND=db \
IRON_COUNCIL_SERVER_RELOAD=true \
./scripts/runtime-control.sh server
```

### Shared/hosted-style API boot

```bash
IRON_COUNCIL_ENV_FILE=.env.runtime \
IRON_COUNCIL_MATCH_REGISTRY_BACKEND=db \
./scripts/runtime-control.sh server
```

The API defaults to `http://127.0.0.1:8000`.

## 5. Start the client process

### Local browser/dev loop

```bash
./scripts/runtime-control.sh client-dev
```

### Production-style client boot

```bash
./scripts/runtime-control.sh client-build
./scripts/runtime-control.sh client-start
```

The client defaults to `http://127.0.0.1:3000`.

## 6. Health verification

Once the API process is up:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/
```

Expected responses:

- `/health` returns `{"status":"ok"}`
- `/` returns service metadata including the server version

Then verify a public browse surface in the browser:

- `http://127.0.0.1:3000/matches`
- `http://127.0.0.1:3000/leaderboard`

For authenticated human flows, also verify the browser session panel can reach the API base URL you expect.

## 7. Websocket/runtime expectations

Current Story 51.1 expectations are intentionally limited:

- the API process owns the in-process match runtime
- with `IRON_COUNCIL_MATCH_REGISTRY_BACKEND=db`, startup reloads match state from the configured database before the runtime loop starts
- browser spectators and authenticated players reconnect through the existing websocket routes once the API process is healthy again
- Story 51.2 will add explicit operator-visible tick-drift, websocket-fanout, and restart-recovery signals; this story does not claim those signals exist yet

## 8. Restart basics

### API process restart

1. Stop the running API process.
2. Start it again with the same `IRON_COUNCIL_ENV_FILE` and `IRON_COUNCIL_MATCH_REGISTRY_BACKEND=db` values.
3. Re-run the `/health` and `/` checks.
4. Re-open a public browse page or live page and confirm it reconnects.

The safe assumption today is that persisted match data survives because it is DB-backed; in-process tick workers restart with the process. Treat Story 51.2 as the follow-on for explicit restart-recovery signals.

### Client restart

1. Stop `client-dev` or `client-start`.
2. Restart with the same host/port.
3. Reload the browser page and confirm the session panel still points at the intended API origin.

## 9. Basic rollback / recovery actions

### Bad runtime config

- Fix the env file.
- rerun `./scripts/runtime-control.sh doctor`
- restart the API process

### Database drift or bad local seed state

For the local support-services baseline only:

```bash
./scripts/runtime-control.sh db-reset
```

That rebuilds the schema plus deterministic seed state for the current worktree database lane.

### Broken local dependency container

```bash
./scripts/runtime-control.sh support-down
./scripts/runtime-control.sh support-up
IRON_COUNCIL_ENV_FILE=.env.runtime ./scripts/runtime-control.sh db-setup
```

### Last-known-good code rollback

This repo does not yet ship automated deployment rollback tooling. The honest rollback path in Story 51.1 is:

1. check out the last known good commit
2. keep the same env contract
3. rerun the same startup order from this runbook
4. verify `/health`, `/`, and the public browse page again

## 10. What this runbook does not promise yet

Story 51.1 intentionally does **not** promise:

- autoscaling
- zero-downtime deploys
- multi-node websocket routing
- managed secret rotation
- metrics dashboards or alerting
- large-scale load validation

Those concerns are intentionally deferred so the shipped runtime contract stays boring and honest.
