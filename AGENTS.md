# AGENTS.md

Guidance for any agent working in this repository.

## Mission

Build the game incrementally using the BMAD method and its generated artifacts while maintaining a strong quality loop.
Do not optimize for speed at the expense of test quality or public-contract correctness.

BMAD is not optional in this repo. Agents should treat BMAD as the operating system for planning and delivery, not as decorative documentation.

## Required delivery workflow

1. Start from the active BMAD story artifact in `_bmad-output/implementation-artifacts/`.
2. Confirm the work is anchored to BMAD planning artifacts before coding:
   - `core-plan.md`
   - `core-architecture.md`
   - `_bmad-output/planning-artifacts/`
   - `_bmad-output/implementation-artifacts/`
3. Use BMAD sequencing rather than ad hoc implementation:
   - story selection from the implementation artifacts
   - acceptance-criteria-driven implementation
   - artifact updates as part of completion
   - sprint status updates as part of completion
4. Work in TDD order:
   - write or extend a failing test first
   - verify the failure is for the expected reason
   - implement the smallest change that makes the test pass
   - refactor only with tests green
5. Run the local quality gate before declaring work done:
   - `make quality`
6. Update the relevant BMAD implementation artifact with:
   - status
   - completed tasks
   - debug log references
   - completion notes
   - file list
7. Update sprint tracking when story status changes.
8. Do not skip BMAD just because the work seems small. If the work belongs to a story, execute it through the story.
9. Do not modify BMAD framework files under `_bmad/` unless the task is explicitly about the framework.

## Testing doctrine

The repository standard is behavior-first testing.

### Non-negotiable rules

- Prefer tests at the highest meaningful level of abstraction.
- Test functionality and externally observable behavior, not implementation details.
- Test through public interfaces, API boundaries, and stable contracts whenever possible.
- Never write tests whose only value is proving a helper function does what its own code says.
- Never lock in refactor-hostile details such as private method calls, internal helper sequencing, temporary variable names, or exact internal data structure choices unless those are part of the contract.
- If a helper has no independent public contract, cover it indirectly through the public behavior that uses it.
- Every bug fix should begin with a failing regression test.
- Avoid snapshot-style assertions unless the full serialized output is the real contract.

### TDD expectations

For each story or bugfix:

1. RED
   - add a failing test for the requested behavior
   - confirm it fails before implementation
2. GREEN
   - implement the smallest viable change
   - get the new and relevant existing tests passing
3. REFACTOR
   - improve code structure only while tests remain green
   - keep the public contract unchanged unless the story explicitly changes it

Document the red-phase evidence in the story file when practical.

## Test pyramid expectations

Favor a healthy pyramid:

- Few end-to-end tests for critical user journeys
- More API/integration/contract tests around boundaries and domain flows
- Focused unit tests for pure domain behavior and validation rules

For this repo today, prefer:

- API tests for FastAPI route behavior and response contracts
- Contract/model tests for domain schemas, map validation, and serialization boundaries
- Unit tests only for stable domain behavior with meaningful business value

Do not build an inverted pyramid full of brittle UI or implementation-detail tests.

## What good tests look like here

Good tests usually:

- name the behavior being verified
- arrange only the data needed for that behavior
- assert the externally visible outcome
- include representative happy-path and failure-path coverage
- exercise acceptance criteria from as close to the API or public contract boundary as feasible

Examples of preferred test targets:

- HTTP route contract and status code behavior
- model validation errors for malformed inputs
- map loading and validation through the public loader/validator
- serialized domain envelopes accepted by public schema models

Examples to avoid unless explicitly justified:

- tests that call private helpers directly
- tests that mock every collaborator and only verify call counts
- tests that assert incidental formatting or internal ordering not required by the contract
- tests that duplicate the implementation algorithm line-by-line

## Quality harness

Before finishing work, agents should normally run:

- `make format` when editing code
- `make lint`
- `make test`
- `make quality`

The enforced harness includes:

- Ruff formatting and linting
- mypy strict type checking
- pytest with coverage enforcement
- pre-commit hooks
- GitHub Actions running `make ci`

Do not claim completion if the harness is red.

## Change-sizing guidance

- Keep stories small and composable.
- Prefer additive, contract-first changes.
- Preserve existing public contracts unless the story explicitly authorizes a breaking change.
- If a change suggests missing quality infrastructure, improve the harness early rather than deferring it.

## Review checklist for agents

Before marking a story done, confirm:

- failing test existed first or red-phase evidence is captured
- tests validate behavior rather than internals
- no helper-only tests were added without a real contract justification
- acceptance criteria are covered by tests
- `make quality` passes
- BMAD artifact status and notes are updated
