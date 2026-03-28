# iron-counsil

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
uvicorn server.main:app --reload
```

GitHub Actions runs the same `make ci` quality gate on pushes and pull requests.
Coverage is enforced through `pytest-cov`, and the harness is tuned to stay pragmatic:
it checks the public API behavior without adding implementation-detail tests.
