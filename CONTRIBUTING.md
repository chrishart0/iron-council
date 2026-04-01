# Contributing to Iron Council

Thanks for contributing. Keep changes small, testable, and aligned with the repository's existing workflow.

## Development setup

Use the locked dev environment:

```bash
uv sync --extra dev --frozen
```

Use `make help` to see the standard local workflow commands.

## Working style

This repository is run through BMAD artifacts, not ad hoc task picking.

- Start from the active story under `_bmad-output/implementation-artifacts/`.
- Use `core-plan.md`, `core-architecture.md`, and `_bmad-output/planning-artifacts/` as the planning anchor.
- Update the relevant implementation artifact and sprint tracking when a story is completed.

## Testing expectations

The project standard is behavior-first testing.

- Prefer tests at the public contract boundary: API routes, schema validation, map loading, and other externally visible behavior.
- Avoid implementation-detail tests that lock in private helpers, call order, or incidental formatting.
- For bug fixes, begin with a failing regression test when the change affects runtime behavior.

Run the full local gate before asking for review:

```bash
make quality
```

That gate includes the Python checks plus the client checks under `client/`.

## Client work

If your change touches the web app, run the relevant commands from `client/` or through the top-level Make targets:

- `make client-typecheck`
- `make client-test`
- `make client-build`

## Pull requests

- Keep PRs scoped to one story or one coherent maintenance slice.
- Explain the user-visible or contract-level change.
- Note any follow-up work instead of silently broadening scope.
