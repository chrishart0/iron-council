# Story 11.3 Batch Simulation Regression Harness Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a deterministic large-batch simulation regression harness that exercises many curated scenarios, checks documented state invariants, reports reproducible failures, and plugs into the local/CI quality workflow.

**Architecture:** Keep the first harness deliberately small and deterministic. Reuse the existing pure-function simulation stack and smoke-scenario patterns, add a dedicated regression module/test file with scenario factories plus invariant checks, and expose a single make target for targeted reruns. Avoid introducing fuzzing, external services, or a new framework.

**Tech Stack:** Python 3.12, pytest, existing `server.simulation` / `server.resolver` contracts, uv + Makefile quality workflow.

---

## Parallelism / sequencing decision

- **Sequential:** Story 11.3 implementation, workflow wiring, and BMAD artifact updates all touch the same test harness and `Makefile`; they should stay in one thread.
- **Parallelizable reviews only:** After implementation, spec-compliance review and code-quality review can run as fresh isolated reviewer passes.

---

### Task 1: Define deterministic batch scenario and invariant strategy

**Objective:** Lock the invariant list, scenario mix, and reproduction shape before adding harness code.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/11-3-add-a-large-batch-simulation-regression-harness-with-invariant-checks.md`
- Create: `tests/test_simulation_regression.py`

**Step 1: Write failing test skeleton**

```python
def test_regression_harness_executes_declared_batch() -> None:
    scenarios = build_regression_scenarios()
    result = run_simulation_regression_batch(scenarios)

    assert result.total_runs >= 12
    assert result.failures == []
```

**Step 2: Run test to verify failure**

Run: `uv run pytest --no-cov tests/test_simulation_regression.py::test_regression_harness_executes_declared_batch`
Expected: FAIL — helpers do not exist yet.

**Step 3: Add minimal scenario strategy**

Implement curated scenarios by combining:
- a stable baseline fixture
- existing smoke-style scripted scenarios
- small deterministic matrix variations over tick counts / order timing / resource pressure

Record reproducible IDs like `frontier_campaign/ticks=6/variant=late-upgrade`.

**Step 4: Run test to verify pass**

Run: `uv run pytest --no-cov tests/test_simulation_regression.py::test_regression_harness_executes_declared_batch`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_simulation_regression.py _bmad-output/implementation-artifacts/11-3-add-a-large-batch-simulation-regression-harness-with-invariant-checks.md
git commit -m "test: define deterministic regression scenario batch"
```

### Task 2: Implement invariant checks and reproduction-friendly failure reporting

**Objective:** Ensure every batch run validates meaningful post-tick invariants and clearly identifies failures.

**Files:**
- Modify: `tests/test_simulation_regression.py`
- Optional create/modify: `server/simulation_regression.py`

**Step 1: Write failing invariant test**

```python
def test_regression_harness_reports_reproducible_invariant_failures() -> None:
    failing_result = run_simulation_regression_batch([
        broken_reference_regression_case()
    ])

    assert failing_result.failures == [
        RegressionFailure(
            scenario_id="broken-reference",
            invariant="army-owner-exists",
            tick=3,
            detail="army 'army_1' references unknown owner 'ghost'",
        )
    ]
```

**Step 2: Run test to verify failure**

Run: `uv run pytest --no-cov tests/test_simulation_regression.py::test_regression_harness_reports_reproducible_invariant_failures`
Expected: FAIL

**Step 3: Write minimal implementation**

Add invariant checks for:
- every city owner exists in `players`
- every `players[*].cities_owned` city exists and matches actual city ownership
- every army owner exists and army `location` / `destination` / `path` references valid cities
- no impossible negatives or zero-troop armies appear in dumped snapshots
- victory counts are consistent with owned-city totals / threshold bounds

Return failures with `scenario_id`, `tick`, `invariant`, and a clear detail string.

**Step 4: Run focused tests**

Run:
- `uv run pytest --no-cov tests/test_simulation_regression.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_simulation_regression.py server/simulation_regression.py
git commit -m "feat: add deterministic simulation invariant regression harness"
```

### Task 3: Wire the harness into the developer workflow

**Objective:** Add a stable command path and prove the batch remains deterministic and CI-friendly.

**Files:**
- Modify: `Makefile`
- Modify: `.github/workflows/quality.yml` only if needed (prefer pytest discovery if not needed)
- Modify: `_bmad-output/implementation-artifacts/11-3-add-a-large-batch-simulation-regression-harness-with-invariant-checks.md`

**Step 1: Write failing workflow test or expectation**

Prefer a behavior test asserting repeated batch execution produces the same digest:

```python
def test_regression_harness_is_deterministic_across_repeated_runs() -> None:
    first = run_simulation_regression_batch(build_regression_scenarios())
    second = run_simulation_regression_batch(build_regression_scenarios())

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
```

**Step 2: Run focused test**

Run: `uv run pytest --no-cov tests/test_simulation_regression.py::test_regression_harness_is_deterministic_across_repeated_runs`
Expected: PASS after implementation.

**Step 3: Add stable command path**

Add a make target like:

```make
regression-test: ## Run the deterministic simulation regression batch harness.
	$(UV) run pytest --no-cov tests/test_simulation_regression.py
```

**Step 4: Run repo checks**

Run:
- `uv run pytest --no-cov tests/test_simulation_regression.py`
- `make regression-test`
- `make quality`

Expected: all PASS within practical local runtime.

**Step 5: Commit**

```bash
git add Makefile tests/test_simulation_regression.py _bmad-output/implementation-artifacts/11-3-add-a-large-batch-simulation-regression-harness-with-invariant-checks.md
git commit -m "chore: wire simulation regression harness into workflow"
```

---

## Implementation notes for the worker

- Prefer test-local helper code unless a reusable `server/simulation_regression.py` module meaningfully reduces duplication.
- Reuse existing smoke-scenario construction patterns instead of inventing a second scenario DSL.
- Check behavior from the public simulation boundary (`simulate_ticks`) rather than resolver internals.
- Keep the initial run count modest but non-trivial (enough to be meaningful, small enough for CI).
- Failure output must let a developer rerun a single scenario directly.

## Verification commands

```bash
uv run pytest --no-cov tests/test_simulation_regression.py
make regression-test
make quality
```
