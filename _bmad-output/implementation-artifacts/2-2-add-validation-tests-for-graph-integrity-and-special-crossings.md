# Story 2.2: Add validation tests for graph integrity and special crossings

Status: done

## Story

As a game engine developer,
I want automated map validation,
so that malformed adjacency or missing cities are caught before runtime.

## Acceptance Criteria

1. Given the shared map definition, when graph validation tests run, then every edge references valid cities.
2. Given the shared map definition, when graph validation tests run, then all edge distances are positive.
3. Given the shared map definition, when graph validation tests run, then the Liverpool-Belfast route is the only Irish Sea crossing.
4. Given the shared map definition, when graph validation runs against malformed input, then representative invalid cases fail with clear validation errors.

## Tasks / Subtasks

- [x] Add graph validation support for the canonical map contract. (AC: 1, 2, 3, 4)
  - [x] Decide whether validation belongs inside the loader, model validators, or a dedicated validation function.
  - [x] Ensure edge endpoints must reference known city IDs.
  - [x] Ensure edge distances must be positive.
  - [x] Ensure only Liverpool-Belfast is encoded as a sea crossing involving Ireland.
- [x] Add behavior-focused tests for valid canonical graph behavior. (AC: 1, 2, 3)
  - [x] Verify the committed UK 1900 map passes validation.
  - [x] Verify the special crossing rule for Liverpool-Belfast.
- [x] Add negative tests for malformed map input. (AC: 4)
  - [x] Cover at least one missing-city edge reference.
  - [x] Cover at least one non-positive distance case.
  - [x] Cover at least one invalid extra Irish Sea crossing case.

## Dev Notes

- Keep the scope tight: validate graph integrity and special-crossing rules only.
- Do not implement match initialization, gameplay movement logic, or pathfinding in this story.
- Prefer testing the public validation contract of the shared map loader/module rather than internals.
- Preserve the canonical map artifact introduced in Story 2.1 and extend its loader/validator surface only as needed.

### References

- `core-plan.md` sections 3-4 for map structure, Ireland constraints, and Liverpool-Belfast sea-crossing behavior.
- `core-architecture.md#7. Project Structure` for shared data placement.
- `_bmad-output/planning-artifacts/epics.md` Story 2.2 acceptance criteria.

## Dev Agent Record

### Agent Model Used

OpenAI Codex CLI (`codex --yolo exec` recommended in this environment)

### Debug Log References

- `uv run pytest tests/test_map_data.py` failed first during collection with `ImportError: cannot import name 'validate_map_definition'`, confirming the red TDD step.
- `uv run pytest --no-cov tests/test_map_data.py` passed after adding the public validator surface and graph rules.
- `make quality` initially failed on Ruff import ordering in `tests/test_map_data.py`; reran after fixing imports and it passed fully.

### Completion Notes List

- Added reusable graph validation to the public map contract via `validate_map_definition(...)` backed by `MapDefinition` model validation.
- Enforced that every edge references known city IDs and that only the Liverpool-Belfast route may be a sea crossing involving Ireland.
- Added public-contract tests for canonical validation success plus representative malformed payload failures with clear validation messages.
- Preserved the canonical Story 2.1 JSON artifact unchanged.

### File List

- `_bmad-output/implementation-artifacts/2-2-add-validation-tests-for-graph-integrity-and-special-crossings.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `server/data/maps.py`
- `tests/test_map_data.py`

### Change Log

- Added reusable graph validation to the public UK 1900 map loader/contract surface.
- Added positive and negative map validation tests covering graph integrity and Irish Sea crossing constraints.
