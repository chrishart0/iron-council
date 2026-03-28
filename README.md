# iron-counsil

## Server quality harness

Install the local development dependencies and run the full quality gate:

```bash
uv sync --extra dev
make quality
```

Run the API locally with:

```bash
uvicorn server.main:app --reload
```

Optional local git hooks:

```bash
pre-commit install
pre-commit run --all-files
```
