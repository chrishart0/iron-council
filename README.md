# iron-counsil

## Local support services

Prerequisite: install Docker with the Compose plugin available via `docker compose`
before using the support-services targets in this repository.

The app continues to run directly on your machine in dev mode. The only default support
service stack is a local Postgres instance defined in
`compose.support-services.yaml`.

Set up the local database wiring once:

```bash
cp env.local.example .env.local
```

Start the backing service:

```bash
make support-services-up
make support-services-ps
```

Provision the current worktree database with migrated schema plus deterministic seed data:

```bash
make db-setup
```

Reset the current worktree database back to the same seeded baseline with:

```bash
make db-reset
```

That boots Postgres on `127.0.0.1:54321` with the same runnable credentials used by
`compose.support-services.yaml` and `env.local.example`:
`DATABASE_URL=postgresql+psycopg://iron_counsil:iron_counsil@127.0.0.1:54321/iron_counsil`.
The support service owns the cluster-level credentials; the app and DB tooling then derive
a worktree-local database name from the current worktree path so sibling worktrees do not
collide. Set `IRON_COUNCIL_DB_LANE` to add a deterministic suffix for parallel Codex
workers or multiple lanes inside one worktree.

The server loads `.env.local` automatically by default, derives the worktree-local
database URL from that base Postgres URL, and can use a different env file via
`IRON_COUNCIL_ENV_FILE=/path/to/file`. If an older local env file still uses the bare
`postgresql://` scheme, the settings layer normalizes it to the installed `psycopg`
driver automatically.

Run the FastAPI app normally outside containers:

```bash
uv run uvicorn server.main:app --reload
```

To boot the agent API against the seeded database-backed registry instead of the default
in-memory registry, set:

```bash
IRON_COUNCIL_MATCH_REGISTRY_BACKEND=db uv run uvicorn server.main:app --reload
```

Focused test runs keep using the same host-shell workflow:

```bash
uv run pytest --no-cov tests/api/test_health.py
```

The repo-level pytest config enables the coverage gate by default, so a plain
`uv run pytest tests/api/test_health.py` can fail on coverage even when the
selected test itself passes.

DB-backed tests and future integration flows should prepare their database through the
shared helpers in `server.db.testing`. `prepare_test_database` upgrades a target
database to Alembic `head`, and `provision_seeded_database` recreates the deterministic
integration baseline. The reusable pytest fixture is `migrated_test_database_url`.

When finished:

```bash
make support-services-logs
make support-services-down
```

## Server quality harness

The FastAPI scaffold keeps quality checks close to the API surface: formatting, linting,
strict typing, and behavior-first HTTP tests.

Set up the local environment once:

```bash
make setup
```

That installs the locked dev dependencies and both git hooks:

- `pre-commit` for hygiene, formatting, linting, and typing on staged changes
- `pre-push` for the behavior-first API test suite

The daily workflow is:

```bash
make format        # apply formatter changes
make lint          # ruff + mypy
make test-real-api # running-process, real-DB API integration checks
make test-smoke    # small real-process smoke journey
make test          # full repository test suite, including the targets above
make quality       # read-only local gate
make ci            # the same gate used in GitHub Actions
```

`make test-real-api` and `make test-smoke` do not require Docker. They provision a
temporary migrated and deterministically seeded SQLite database, boot `uvicorn` as a
real process, and hit the service over HTTP. Keep the support-services Postgres stack
for worktree-local manual runs and DB tooling flows.

If you prefer to run hooks manually:

```bash
uv run pre-commit run --all-files --show-diff-on-failure
```

Run the API locally with:

```bash
uv run uvicorn server.main:app --reload
```

GitHub Actions runs the same `make ci` quality gate on pushes and pull requests.
Coverage is enforced through `pytest-cov`, and the harness is tuned to stay pragmatic:
it checks the public API behavior without adding implementation-detail tests.

## Public match browser client

Story 24.1 adds a minimal supported Next.js client under `client/`. It only ships a
public read-only `/matches` page backed by the existing `GET /api/v1/matches`
contract.

Install the locked client dependencies once:

```bash
make client-install
```

Run the FastAPI server in one shell:

```bash
uv run uvicorn server.main:app --reload
```

Then run the client in another shell:

```bash
cd client
cp .env.example .env.local
npm run dev
```

Visit `http://127.0.0.1:3000/matches` to browse the live public match list. The
client reads `IRON_COUNCIL_API_BASE_URL` from `client/.env.local`; the default local
server target is `http://127.0.0.1:8000`.

The repo quality gate now includes the client checks:

```bash
make client-lint
make client-test
make client-build
make quality
make ci
```
