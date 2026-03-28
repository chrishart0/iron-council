# Epic 4 Headless Tick Skeleton Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Deliver Epic 4 by adding a pure-function tick resolver skeleton and a deterministic headless simulation harness for smoke-testing ticks.

**Architecture:** Keep the engine surface narrow and deterministic. Story 4.1 adds a public resolver boundary that deep-copies `MatchState`, runs a fixed ordered list of placeholder phase handlers, and emits stable metadata. Story 4.2 builds a headless runner on top of that boundary so simulation tests exercise the public contracts rather than internal helpers.

**Tech Stack:** Python 3.12, Pydantic v2 models, pytest, ruff, mypy, uv, FastAPI repo scaffold.

---

### Task 1: Create the Story 4.2 BMAD artifact

**Objective:** Add the missing story file so execution stays anchored to BMAD artifacts before coding Story 4.2.

**Files:**
- Create: `_bmad-output/implementation-artifacts/4-2-provide-a-headless-simulation-harness-for-smoke-testing-ticks.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Write the story artifact**

Create a story file with acceptance criteria covering deterministic N-tick simulation, stable event logs, and no API/database dependency.

**Step 2: Mark the story as ready for implementation**

Update sprint status so Epic 4 remains active and Story 4.2 is visible as the next dependency after Story 4.1.

**Step 3: Commit**

```bash
git add _bmad-output/implementation-artifacts/4-2-provide-a-headless-simulation-harness-for-smoke-testing-ticks.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "docs: add story 4.2 implementation artifact"
```

### Task 2: Implement Story 4.1 resolver boundary with TDD

**Objective:** Add a public pure-function resolver that advances a match through the documented phase order without mutating inputs.

**Files:**
- Create: `server/resolver.py`
- Modify: `server/__init__.py`
- Test: `tests/test_resolver.py`
- Modify: `_bmad-output/implementation-artifacts/4-1-add-a-pure-function-tick-resolver-skeleton-with-phase-ordering.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `AGENTS.md` if it is still untracked and intended as a repository file

**Step 1: Write failing behavior tests**

Add tests that verify:
- `resolve_tick(...)` returns a new state object and leaves the input unchanged
- emitted phases are exactly `resource`, `build`, `movement`, `combat`, `siege`, `attrition`, `diplomacy`, `victory`
- repeated runs with the same validated orders produce identical outputs

Use focused red-phase command:

```bash
uv run pytest --no-cov tests/test_resolver.py -q
```

Expected: FAIL because resolver contracts do not exist yet.

**Step 2: Write the minimal implementation**

Create Pydantic result/metadata models and a `resolve_tick` function that:
- deep-copies the incoming `MatchState`
- iterates the canonical phase list in order
- appends stable phase/event metadata
- returns the copied state unchanged except for tick advancement if required by the chosen public contract

Keep placeholder handlers simple and deterministic.

**Step 3: Verify the focused tests pass**

```bash
uv run pytest --no-cov tests/test_resolver.py -q
```

Expected: PASS.

**Step 4: Run the repository quality gate**

```bash
make quality
```

Expected: PASS.

**Step 5: Update BMAD artifacts and commit**

```bash
git add AGENTS.md server/resolver.py server/__init__.py tests/test_resolver.py _bmad-output/implementation-artifacts/4-1-add-a-pure-function-tick-resolver-skeleton-with-phase-ordering.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "feat: add tick resolver skeleton"
```

### Task 3: Implement Story 4.2 headless simulation harness with TDD

**Objective:** Add a small public harness that advances a match for N ticks using the resolver and emits deterministic snapshots plus event logs.

**Files:**
- Create: `server/simulation.py`
- Test: `tests/test_simulation.py`
- Modify: `server/__init__.py`
- Modify: `_bmad-output/implementation-artifacts/4-2-provide-a-headless-simulation-harness-for-smoke-testing-ticks.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Write failing behavior tests**

Add tests that verify:
- advancing N ticks returns N ordered results/snapshots
- repeated runs from the same initial state and orders are deterministic
- the harness works with no web, DB, or external side effects

Run:

```bash
uv run pytest --no-cov tests/test_simulation.py -q
```

Expected: FAIL because the harness does not exist yet.

**Step 2: Write the minimal implementation**

Add a simulation function that:
- accepts an initial `MatchState`
- accepts either a static validated order batch or a per-tick order provider
- calls `resolve_tick` for each tick
- accumulates snapshots and phase/event logs in a stable return object

**Step 3: Verify the focused tests pass**

```bash
uv run pytest --no-cov tests/test_simulation.py -q
```

Expected: PASS.

**Step 4: Run the repository quality gate**

```bash
make quality
```

Expected: PASS.

**Step 5: Update BMAD artifacts and commit**

```bash
git add server/simulation.py server/__init__.py tests/test_simulation.py _bmad-output/implementation-artifacts/4-2-provide-a-headless-simulation-harness-for-smoke-testing-ticks.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "feat: add headless tick simulation harness"
```

### Task 4: Run final integration review and simplification pass

**Objective:** Confirm both stories integrate cleanly and remain the simplest coherent shippable version.

**Files:**
- Review: `server/resolver.py`
- Review: `server/simulation.py`
- Review: `tests/test_resolver.py`
- Review: `tests/test_simulation.py`

**Step 1: Run integration checks**

```bash
make quality
git diff --stat HEAD~2..HEAD
```

Expected: PASS with only story-scoped files changed.

**Step 2: Review for overcomplexity**

Confirm there is no unnecessary abstraction, no helper-only testing, and no repo-convention drift.

**Step 3: Final commit if needed**

```bash
git add -A
git commit -m "refactor: simplify epic 4 tick skeleton integration"
```

Only commit if the refinement pass changed code.
