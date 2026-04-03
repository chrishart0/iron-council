# Story 45.1 Next.js dev root stability Implementation Plan

**Status:** Completed 2026-04-03

**Outcome:** Shipped the narrow config seam in `client/next.config.ts`, added focused Vitest coverage for the exported Turbopack root, added a tiny `next-env.d.ts` normalization seam for dev/build flows, and added a repo-level `next dev` smoke regression anchored to the canonical tracked file.

**Verification Summary:**
- RED: `cd client && npm test -- --run src/next-config.test.ts` failed with `turbopack.root` undefined before the config change.
- PASS: `cd client && npm test -- --run src/next-config.test.ts`
- PASS: `uv run pytest --no-cov tests/test_client_dev_smoke.py -q`
- PASS: `make client-lint`
- PASS: `make client-test`
- PASS: `make client-build`
- PASS: `uv run pytest --no-cov tests/test_local_dev_docs.py tests/test_client_dev_smoke.py -q`

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make the local `client/` Next.js dev server run without the workspace-root warning and keep one canonical tracked `client/next-env.d.ts` state across both `npm run dev` and `npm run build`.

**Architecture:** Add an explicit Next.js/Turbopack root in `client/next.config.ts` so the dev server anchors itself to the real client workspace instead of inferring the parent Hermes repo. Keep `client/next-env.d.ts` with the build-style `./.next/types/routes.d.ts` import as the canonical tracked file, add a tiny normalizer that rewrites the dev-only import back to that canonical form, call it from a thin `npm run dev` wrapper on shutdown plus `postbuild`, and prove the fix with one focused config unit test and one subprocess smoke test that boots `next dev`, interrupts it like a developer would, and confirms the repo returns to the same tracked file state.

**Tech Stack:** Next.js 16, TypeScript, Vitest, Python pytest subprocess smoke tests.

---

### Task 1: Pin the client workspace root in Next config

**Objective:** Give the client app an explicit root so local dev uses the correct workspace instead of inferring the parent Hermes checkout.

**Files:**
- Modify: `client/next.config.ts`
- Test: `client/src/next-config.test.ts`

**Step 1: Write failing test**

```ts
import { describe, expect, it } from "vitest";
import nextConfig from "../../next.config";

describe("next config", () => {
  it("pins turbopack root to the client workspace", () => {
    expect(nextConfig.turbopack?.root).toContain("iron-counsil/client");
  });
});
```

**Step 2: Run test to verify failure**

Run: `cd client && npm test -- --run src/next-config.test.ts`
Expected: FAIL because `next.config.ts` does not currently set `turbopack.root`.

**Step 3: Write minimal implementation**

```ts
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const clientRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  turbopack: {
    root: clientRoot,
  },
};

export default nextConfig;
```

**Step 4: Run test to verify pass**

Run: `cd client && npm test -- --run src/next-config.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add client/next.config.ts client/src/next-config.test.ts
git commit -m "fix: pin next client workspace root"
```

### Task 2: Add a repo-level smoke test for startup output and generated-file stability

**Objective:** Prevent regressions by proving a real `next dev` boot no longer emits the workspace-root warning or rewrites `client/next-env.d.ts`.

**Files:**
- Modify: `tests/test_local_dev_docs.py` or create `tests/test_client_dev_smoke.py`
- Possibly modify: `Makefile` only if an existing target needs a focused alias (prefer no change if `make test` already covers it)

**Step 1: Write failing test**

```python
def test_next_dev_uses_client_workspace_without_warning(tmp_path: Path) -> None:
    before = (REPO_ROOT / "client" / "next-env.d.ts").read_text()
    result = subprocess.run(
        ["npm", "run", "dev", "--", "--hostname", "127.0.0.1", "--port", "3900"],
        cwd=REPO_ROOT / "client",
        timeout=20,
        capture_output=True,
        text=True,
        env={**os.environ, "CI": "1"},
    )
    after = (REPO_ROOT / "client" / "next-env.d.ts").read_text()
    assert "inferred your workspace root" not in result.stdout + result.stderr
    assert before == after
```

**Step 2: Run test to verify failure**

Run: `uv run pytest --no-cov tests/test_client_dev_smoke.py -q`
Expected: FAIL because the current dev boot warns about the inferred workspace root and rewrites `next-env.d.ts`.

**Step 3: Write minimal implementation**

Use a subprocess helper that:
- starts `npm run dev -- --hostname 127.0.0.1 --port <ephemeral>` in `client/`
- waits until the server prints the local URL or exits
- captures stdout/stderr
- terminates the process cleanly
- asserts the warning text is absent
- compares `client/next-env.d.ts` before/after the run

Keep the helper boring and local to the test file.

**Step 4: Run test to verify pass**

Run: `uv run pytest --no-cov tests/test_client_dev_smoke.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_client_dev_smoke.py
git commit -m "test: cover next dev workspace root stability"
```

### Task 3: Run focused + repo verification and close the story

**Objective:** Prove the fix works in the real repo harness and document the BMAD closeout.

**Files:**
- Modify: `_bmad-output/implementation-artifacts/45-1-stabilize-nextjs-client-dev-root-and-generated-types.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run focused checks**

Run:
```bash
cd client && npm test -- --run src/next-config.test.ts
uv run pytest --no-cov tests/test_client_dev_smoke.py -q
```
Expected: PASS

**Step 2: Run broader repo checks**

Run:
```bash
make client-test
make client-build
uv run pytest --no-cov tests/test_local_dev_docs.py tests/test_client_dev_smoke.py -q
```
Expected: PASS

**Step 3: Review and simplify**

Check:
- `git diff --stat`
- confirm only the config, tests, and BMAD/docs changed
- confirm no overengineered helper abstractions were added

**Step 4: Update BMAD artifacts**

Record the actual commands/outcomes in the story debug log, mark Story 45.1 done, and set `next_story` only if a concrete 45.2 artifact is created in the same run.

**Step 5: Commit**

```bash
git add client/next.config.ts client/src/next-config.test.ts tests/test_client_dev_smoke.py _bmad-output/implementation-artifacts/45-1-stabilize-nextjs-client-dev-root-and-generated-types.md _bmad-output/implementation-artifacts/sprint-status.yaml docs/plans/2026-04-03-story-45-1-nextjs-dev-root-stability.md
git commit -m "fix: stabilize next client dev root"
```
