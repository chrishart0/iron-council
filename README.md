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

That boots Postgres on `127.0.0.1:54321` with the same runnable credentials used by
`compose.support-services.yaml` and `env.local.example`:
`DATABASE_URL=postgresql://iron_counsil:iron_counsil@127.0.0.1:54321/iron_counsil`.
The server loads `.env.local` automatically by default, falls back to that same default
URL when no env file is present, and can use a different file via
`IRON_COUNCIL_ENV_FILE=/path/to/file`.

Run the FastAPI app normally outside containers:

```bash
uv run uvicorn server.main:app --reload
```

Focused test runs keep using the same host-shell workflow:

```bash
uv run pytest tests/api/test_health.py
```

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
make test          # behavior-first API tests
make quality       # read-only local gate
make ci            # the same gate used in GitHub Actions
```

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
