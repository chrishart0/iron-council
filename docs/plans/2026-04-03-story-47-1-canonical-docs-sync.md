# Story 47.1 Canonical docs sync and regression guard Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Bring the canonical/public entrypoint docs back into sync with the shipped Iron Council server and client surfaces, then pin that sync with a lightweight regression test.

**Architecture:** Keep this story narrow and documentation-first. Update `core-architecture.md` to describe the real mixed public/authenticated HTTP and websocket surface, refresh `README.md` and `docs/index.md` so public readers can discover the shipped browse/profile/history flows, and add one boring docs regression test that checks the most important route/env-name promises stay aligned with the code.

**Tech Stack:** Markdown docs, pytest, FastAPI/Next.js repo structure, existing docs regression tests in `tests/test_local_dev_docs.py`.

---

### Task 1: Refresh canonical architecture/public docs to match the shipped surface

**Objective:** Fix the highest-value source-of-truth drift in the architecture and public entrypoint docs.

**Files:**
- Modify: `core-architecture.md`
- Modify: `README.md`
- Modify: `docs/index.md`
- Optionally modify: `core-plan.md` only if one shipped public-profile/treaty-reputation detail needs a small clarification

**Step 1: Write the failing expectation list**

Capture the doc drift to correct:
- `core-architecture.md` must distinguish public HTTP reads from authenticated human/agent routes.
- `core-architecture.md` must document the spectator websocket as public/read-only and the player websocket as authenticated.
- The architecture doc must stop using stale names like `CORS_ORIGINS` when the repo now uses `IRON_COUNCIL_BROWSER_ORIGINS`.
- `README.md` / `docs/index.md` must mention the shipped public leaderboard, completed-match, replay/history, and public profile surfaces.

**Step 2: Run a focused docs check to establish the current gap**

Run:

```bash
source .venv/bin/activate && uv run pytest --no-cov tests/test_local_dev_docs.py -q
```

Expected: either PASS with insufficient coverage of the drift, or FAIL once the new regression assertions are added in Task 2. In either case, use the current docs/code read as the red baseline.

**Step 3: Write the minimal documentation updates**

Update the docs so they honestly reflect the shipped system:
- rename the REST section from agent-only framing to mixed public/authenticated API framing
- enumerate the shipped public profile/history routes
- update the env-var names and project-structure section at a high level instead of pretending the old layout still exists
- keep the README/docs index concise and public-reader focused

**Step 4: Review for simplicity**

Avoid a giant architecture rewrite. Prefer a narrow sync pass that fixes the stale contract descriptions and public entrypoints without re-litigating the whole system design.

**Step 5: Commit**

```bash
git add core-architecture.md README.md docs/index.md core-plan.md
git commit -m "docs: sync canonical architecture docs with shipped surface"
```

### Task 2: Add a lightweight docs regression guard

**Objective:** Prevent the key route/env-name drift from silently returning.

**Files:**
- Modify: `tests/test_local_dev_docs.py`
- Optionally create: `tests/test_architecture_docs.py` only if the existing doc test file becomes awkward

**Step 1: Write failing test**

Add behavior-level assertions against the docs text, for example:

```python
def test_core_architecture_documents_public_profiles_and_browser_origin_setting() -> None:
    architecture = (REPO_ROOT / "core-architecture.md").read_text()

    assert "/api/v1/agents/{agent_id}/profile" in architecture
    assert "/api/v1/humans/{human_id}/profile" in architecture
    assert "IRON_COUNCIL_BROWSER_ORIGINS" in architecture
    assert "/ws/match/{match_id}" in architecture
```

Also add one entrypoint-doc assertion that the README or docs index mentions the public leaderboard/completed/history/profile pages.

**Step 2: Run test to verify failure**

Run:

```bash
source .venv/bin/activate && uv run pytest --no-cov tests/test_local_dev_docs.py -q
```

Expected: FAIL before the doc updates land.

**Step 3: Write minimal implementation**

Keep the regression guard tiny and boring. The test should pin a few critical route/env-name promises, not parse the entire docs set.

**Step 4: Run test to verify pass**

Run:

```bash
source .venv/bin/activate && uv run pytest --no-cov tests/test_local_dev_docs.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_local_dev_docs.py
git commit -m "test: guard canonical docs against route drift"
```

### Task 3: Run the real docs-focused verification and close the story

**Objective:** Finish in a concise, accurate, by-the-book documentation state.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/47-1-sync-canonical-architecture-and-public-entrypoint-docs.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modify: `docs/plans/2026-04-03-story-47-1-canonical-docs-sync.md`

**Step 1: Run focused verification**

```bash
source .venv/bin/activate && uv run pytest --no-cov tests/test_local_dev_docs.py -q
```

**Step 2: Run broader repo verification if any touched docs command paths need it**

At minimum, re-run the standard quality gate after both parallel stories merge:

```bash
source .venv/bin/activate && make quality
```

**Step 3: Review and simplify**

Check:
- `git diff --stat`
- the docs now describe the real shipped surfaces without overspecifying internal implementation details
- the regression test stays tiny and readable

**Step 4: Update BMAD artifacts**

Record the actual commands/outcomes in the story file and mark Story 47.1 done only after controller-side verification passes.

**Step 5: Commit**

```bash
git add -A
git commit -m "docs: sync canonical Iron Council docs"
```
