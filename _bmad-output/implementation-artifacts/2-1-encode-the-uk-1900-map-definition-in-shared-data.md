# Story 2.1: Encode the UK 1900 map definition in shared data

Status: done

## Story

As a game engine developer,
I want a canonical map artifact for cities, edges, and resource profiles,
so that initialization and movement logic can consume one source of truth.

## Acceptance Criteria

1. Given the V1 UK map specification, when the shared map file is loaded, then it contains the full 25-city roster, resource profiles, neutrality flags, and movement edges.
2. Given Ireland has special constraints, when the map is validated, then Belfast, Dublin, Cork, and Galway are marked neutral and no-spawn by default.

## Tasks / Subtasks

- [x] Add the canonical UK 1900 shared map artifact. (AC: 1)
  - [x] Create `server/data/map_uk_1900.json`.
  - [x] Encode 25 cities with regions, primary resources, notes, and fixed coordinates.
  - [x] Encode movement edges, including the Liverpool-Belfast sea crossing metadata.
- [x] Add a stable public loader contract. (AC: 1, 2)
  - [x] Add `server/data/maps.py` with validated map models and a cached loader.
  - [x] Keep the public surface small enough for later validation and engine work.
- [x] Add behavior-focused tests for the canonical map contract. (AC: 1, 2)
  - [x] Verify the loader exposes the expected map identity and full city roster.
  - [x] Verify representative city facts and Ireland neutrality/no-spawn behavior.
  - [x] Verify the Liverpool-Belfast crossing is the special sea route with extra travel cost metadata.

## Dev Notes

- Chose JSON for the canonical artifact to align with the architecture notes and keep the data consumable by future server/client tooling.
- Added a thin validated loader instead of exposing raw JSON so later systems can depend on a typed contract without coupling to the storage format.
- Kept scope to shared data only; no graph-integrity validation or match bootstrap logic was introduced here.

### Project Structure Notes

- Added shared map data under `server/data/`, matching the architecture direction for canonical map artifacts.
- Left existing model-layer work untouched and isolated Story 2.1 in new files plus a dedicated contract test module.

### References

- `core-plan.md` sections 3-4 for the V1 map roster, resource profiles, and Ireland special rules.
- `core-architecture.md#7. Project Structure` for the canonical map file location.

## Dev Agent Record

### Agent Model Used

OpenAI Codex CLI (`codex --yolo exec` recommended if workspace sandboxing blocks local shell access)

### Debug Log References

- `uv run pytest tests/test_map_data.py` failed first with `ModuleNotFoundError: No module named 'server.data'`, confirming the red TDD step before implementation.
- Added `server/data/` with the canonical JSON artifact plus a validated cached loader, then reran `uv run pytest tests/test_map_data.py`.
- Ran `make quality` after the implementation to verify Ruff, mypy, pytest, and the repository coverage gate.

### Completion Notes List

- Added a canonical `uk_1900` map artifact with 25 cities, practical coordinates, resource profiles, movement edges, and neutral Ireland defaults.
- Encoded the Liverpool-Belfast route as the special sea crossing with extra tick cost and a landing combat penalty flag for later resolver work.
- Added a small typed loader contract so later validation and engine modules can consume stable shared map data without reading raw JSON directly.
- Added public-contract tests covering loader behavior, representative city facts, Irish neutrality/no-spawn behavior, and the special crossing metadata.

### File List

- `_bmad-output/implementation-artifacts/2-1-encode-the-uk-1900-map-definition-in-shared-data.md`
- `server/data/__init__.py`
- `server/data/map_uk_1900.json`
- `server/data/maps.py`
- `tests/test_map_data.py`
