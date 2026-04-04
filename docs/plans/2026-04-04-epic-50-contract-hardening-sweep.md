# Epic 50 Contract Hardening Sweep Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add two small, behavior-first hardening stories that raise confidence in the highest-risk V1 compatibility seams without broadening product scope.

**Architecture:** Treat Epic 50 as a stabilization pass, not a feature wave. Keep the work split across two independent seams: (1) in-memory diplomacy/messaging registry behavior and (2) DB-backed rating settlement semantics. Prefer focused regressions at the public boundary first, then only the smallest production edits needed to make those regressions pass and keep the code boring.

**Tech Stack:** Python 3.12, FastAPI-compatible registry/domain models, SQLAlchemy, pytest, uv, Ruff, mypy, Make, Codex CLI.

---

## Parallelism and dependency notes

- **Safe to run in parallel:** Story 50.1 and Story 50.2. They touch different production files and primarily different test areas.
- **Must stay sequential inside each story:** write failing tests -> run focused slice -> minimal fix -> rerun focused slice -> run broader quality gate.
- **Controller responsibilities after worker completion:** inspect diffs, run focused verification again in the main repo, review for spec + quality + KISS, reconcile BMAD artifacts, then merge/cherry-pick.

### Task 1: Create Epic 50 BMAD scaffolding

**Objective:** Add the planning and story artifacts before dispatching workers so each worktree has a committed source of truth.

**Files:**
- Modify: `_bmad-output/planning-artifacts/epics.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Create: `_bmad-output/implementation-artifacts/50-1-harden-in-memory-diplomacy-and-messaging-contract-edges.md`
- Create: `_bmad-output/implementation-artifacts/50-2-harden-db-backed-rating-settlement-identity-and-tenure-edges.md`
- Create: `docs/plans/2026-04-04-epic-50-contract-hardening-sweep.md`

**Step 1: Write the files**

Add Epic 50 plus both story artifacts exactly where BMAD expects them.

**Step 2: Verify the artifacts exist**

Run: `git diff -- _bmad-output/planning-artifacts/epics.md _bmad-output/implementation-artifacts/sprint-status.yaml _bmad-output/implementation-artifacts/50-1-harden-in-memory-diplomacy-and-messaging-contract-edges.md _bmad-output/implementation-artifacts/50-2-harden-db-backed-rating-settlement-identity-and-tenure-edges.md docs/plans/2026-04-04-epic-50-contract-hardening-sweep.md`
Expected: shows only the new Epic 50 planning changes.

**Step 3: Commit**

```bash
git add _bmad-output/planning-artifacts/epics.md \
        _bmad-output/implementation-artifacts/sprint-status.yaml \
        _bmad-output/implementation-artifacts/50-1-harden-in-memory-diplomacy-and-messaging-contract-edges.md \
        _bmad-output/implementation-artifacts/50-2-harden-db-backed-rating-settlement-identity-and-tenure-edges.md \
        docs/plans/2026-04-04-epic-50-contract-hardening-sweep.md
git commit -m "docs: draft epic 50 contract hardening sweep"
```

### Task 2: Implement Story 50.1 in its own worktree

**Objective:** Harden the in-memory diplomacy/messaging compatibility seam with focused behavior tests and only minimal production edits.

**Files:**
- Modify: `tests/test_agent_registry.py`
- Possible small fix: `server/agent_registry_diplomacy.py`
- Possible small fix: `server/agent_registry_messaging.py`
- Modify: `_bmad-output/implementation-artifacts/50-1-harden-in-memory-diplomacy-and-messaging-contract-edges.md`

**Step 1: Write failing tests**

Add focused regressions for:
- alliance create/join input validation
- leader handoff or alliance removal edge handling
- treaty accept/withdraw invalid transition handling and `since_tick` filtering
- messaging recipient validation for group/world/direct modes
- briefing visibility/grouped ordering for visible messages

**Step 2: Run the focused slice to verify failure**

Run: `uv run pytest -o addopts='' tests/test_agent_registry.py -k 'alliance or treaty or briefing or group_chat or message'`
Expected: FAIL until the new regression contract is implemented.

**Step 3: Write the minimal implementation fix**

Keep production changes tiny and compatibility-oriented.

**Step 4: Re-run the focused slice**

Run: `uv run pytest -o addopts='' tests/test_agent_registry.py -k 'alliance or treaty or briefing or group_chat or message'`
Expected: PASS.

**Step 5: Run repo quality**

Run: `source .venv/bin/activate && make quality`
Expected: PASS.

**Step 6: Commit in the worker**

```bash
git add tests/test_agent_registry.py server/agent_registry_diplomacy.py server/agent_registry_messaging.py _bmad-output/implementation-artifacts/50-1-harden-in-memory-diplomacy-and-messaging-contract-edges.md
git commit -m "test: harden in-memory diplomacy and messaging contracts"
```

### Task 3: Implement Story 50.2 in its own worktree

**Objective:** Harden completed-match rating settlement semantics with DB-backed regressions and only minimal production edits.

**Files:**
- Modify: `tests/test_db_registry.py` or create a small focused DB test module if clearer
- Possible small fix: `server/db/rating_settlement.py`
- Modify: `_bmad-output/implementation-artifacts/50-2-harden-db-backed-rating-settlement-identity-and-tenure-edges.md`

**Step 1: Write failing DB-backed tests**

Add focused regressions for:
- winner identity resolution (solo winner, alliance winner, draw)
- zero-territory fallback / tenure weighting math staying deterministic
- latest human settled ELO preferring the newest settlement deterministically
- aggregate identity grouping remaining stable for human vs agent identities

**Step 2: Run the focused DB slice to verify failure**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'settle_completed_match_if_needed or latest_human_settled_elo or settlement'`
Expected: FAIL until the new contract is pinned.

**Step 3: Write the minimal implementation fix**

Keep the production fix limited to the settlement seam.

**Step 4: Re-run the focused DB slice**

Run: `uv run pytest -o addopts='' tests/test_db_registry.py -k 'settle_completed_match_if_needed or latest_human_settled_elo or settlement'`
Expected: PASS.

**Step 5: Run repo quality**

Run: `source .venv/bin/activate && make quality`
Expected: PASS.

**Step 6: Commit in the worker**

```bash
git add tests/test_db_registry.py server/db/rating_settlement.py _bmad-output/implementation-artifacts/50-2-harden-db-backed-rating-settlement-identity-and-tenure-edges.md
git commit -m "test: harden rating settlement edge contracts"
```

### Task 4: Review, integrate, and simplify

**Objective:** Merge only reviewed, verified worker results and leave the main repo in the simplest coherent state.

**Files:**
- Modify: main repo copies of all worker-changed files
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: story artifacts with final signoff, debug logs, completion notes, and file lists

**Step 1: Spec review each story**

Check each worker diff against its story acceptance criteria.

**Step 2: Code-quality review each story**

Check for unnecessary abstraction, brittle tests, or helper churn.

**Step 3: Import worker commits**

Cherry-pick only the intended commits into `master`.

**Step 4: Re-run controller verification**

Run:
- `source .venv/bin/activate && make quality`
- `git diff --stat HEAD~2..HEAD` (or equivalent review window)

Expected: PASS and a small coherent diff.

**Step 5: Reconcile BMAD closeout**

Update each story artifact with:
- `Status: done`
- checked complete signoff boxes
- real debug commands
- completion notes
- file list

Update `sprint-status.yaml` so completed story statuses are `done` and `next_story` reflects the next unfinished item or `null` if the sweep is complete.

**Step 6: Commit and push**

```bash
git add -A
git commit -m "test: complete epic 50 contract hardening sweep"
git push origin master
```
