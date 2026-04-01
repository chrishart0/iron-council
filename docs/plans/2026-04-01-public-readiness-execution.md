# Public Repository Readiness Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Turn the public Iron Council repository into a credible external landing surface with clear product framing, quickstart docs, governance files, curated docs entrypoints, and an explicit consultant-style follow-up backlog.

**Architecture:** Keep the product/runtime code unchanged unless verification exposes a real doc/command mismatch. Treat this as a documentation-and-governance delivery slice anchored to the existing public-readiness epic. Use one worker for public-facing README/docs curation and a second worker in parallel for OSS governance/trust files because those touch mostly separate files. Finish with a consultant-style repo assessment artifact plus a small tracked issue/debt list.

**Tech Stack:** Markdown docs, Make/uv workflow verification, GitHub metadata files, BMAD artifacts.

---

### Task 1: Establish the execution slice and artifact targets

**Objective:** Lock the exact files and acceptance targets for this run before Codex workers start editing.

**Files:**
- Create: `docs/plans/2026-04-01-public-readiness-execution.md`
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Confirm the current repo state**

Run: `git status --short && git branch --show-current && git log --oneline -5`
Expected: clean worktree on `master` with the recent public-readiness planning commit visible.

**Step 2: Confirm the public-readiness source plan**

Read: `docs/plans/2026-04-01-public-repo-readiness.md`
Expected: Stories 1-4 and acceptance criteria AC1-AC6 are present.

**Step 3: Decide safe parallelism**

Parallelize:
- Worker A: `README.md`, `docs/index.md`, curated public-doc wording updates.
- Worker B: `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`.

Serialize later:
- README link wiring, final naming cleanup, consultant assessment, BMAD status updates.

**Step 4: Update tracking only after story completion**

Rule: do not mark any story complete in `sprint-status.yaml` until README/docs or governance files are verified and merged.

**Step 5: Commit plan artifact if needed**

```bash
git add docs/plans/2026-04-01-public-readiness-execution.md
git commit -m "docs: add public readiness execution plan"
```

### Task 2: Deliver README landing page plus curated docs entrypoint

**Objective:** Make the repo legible to a cold visitor in under 3 minutes.

**Files:**
- Modify: `README.md`
- Create: `docs/index.md`
- Possibly modify: `agent-sdk/README.md`, `core-plan.md`, `_bmad-output/planning-artifacts/gdd.md`
- Test: verify documented commands against `Makefile`

**Step 1: Write the acceptance-oriented diff target**

Required README sections:
- one-paragraph product summary
- core pillars (diplomacy, bring-your-own-agent, spectator-first drama)
- current status (implemented today vs planned next)
- 5-minute quickstart for server, client, SDK/example agent
- quality harness summary
- architecture-at-a-glance
- links to docs/governance/security

**Step 2: Add the docs entrypoint**

Create `docs/index.md` with:
- Start here orientation
- docs map (README, architecture, GDD, SDK, plans)
- explanation of `_bmad`, `_bmad-output`, and `AGENTS.md`
- note that BMAD artifacts remain visible because the repo is built in the open

**Step 3: Remove or contextualize confusing public wording**

If `core-plan.md` / mirrored GDD still say `Confidential`, either:
- replace that wording with a public-friendly status line, or
- add explicit context saying the document originated as an internal draft but is now public.

Prefer the smallest honest change that aligns source-of-truth docs with the public repo.

**Step 4: Verify command-path accuracy**

Run exact public commands from the README shape, at minimum:
- `make help`
- `make quality` or the narrower documented prerequisites if full gate is too expensive before merge review
- if README claims a 5-minute flow, make sure every referenced command really exists in `Makefile`

**Step 5: Commit**

```bash
git add README.md docs/index.md agent-sdk/README.md core-plan.md _bmad-output/planning-artifacts/gdd.md
git commit -m "docs: overhaul public repo landing docs"
```

### Task 3: Add OSS trust and governance files

**Objective:** Add standard public-repo trust scaffolding with project-specific guidance.

**Files:**
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `CODE_OF_CONDUCT.md`
- Create: `SECURITY.md`
- Modify later in Task 2/4: `README.md`

**Step 1: Choose the simplest credible templates**

Use:
- MIT License unless repository policy requires otherwise
- concise contribution workflow tied to `make setup`, `make quality`, BMAD artifacts, and behavior-first tests
- Contributor Covenant style code of conduct
- simple security policy with private reporting path placeholder that routes through GitHub Security Advisories/issues guidance without promising unsupported infrastructure

**Step 2: Ensure repo-specific guidance is accurate**

`CONTRIBUTING.md` must mention:
- `uv sync --extra dev --frozen`
- `make quality`
- client checks live under `client/`
- BMAD artifacts drive story work
- behavior-first testing / no implementation-detail tests

**Step 3: Verify cross-links exist**

The files should be linkable from the README after merge.

**Step 4: Commit**

```bash
git add LICENSE CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md
git commit -m "docs: add public governance files"
```

### Task 4: Add consultant-style assessment and explicit follow-up debt

**Objective:** Publish a concise maturity assessment and explicit next cleanup backlog.

**Files:**
- Create: `docs/consulting/public-repo-assessment-2026-04-01.md`
- Create or modify: `docs/issues/public-readiness-follow-ups.md`
- Modify: `README.md` or `docs/index.md` only to link these artifacts if helpful
- Modify: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Capture strengths, risks, hotspots**

Assessment sections:
- strengths already visible in the repo
- current public-first risks
- maintainability hotspots / oversized modules / naming debt
- prioritized follow-up actions

**Step 2: Make follow-up debt explicit**

Create a small issue/debt list with 3-6 actionable items, such as:
- canonical package/repo naming cleanup (`iron-counsil` vs `iron-council`)
- oversized public hotspots deserving refactor follow-up
- trimming public/internal BMAD noise over time
- deployment/demo environment story for public visitors

**Step 3: Run final review commands**

Minimum final checks:
- `git diff --stat`
- `make quality`
- any focused docs/command verification needed after merges

**Step 4: Update BMAD tracking**

After verified completion, update `sprint-status.yaml` to reflect the public-readiness stories completed in this run or add an explicit note if this epic is tracked outside the numbered story stream.

**Step 5: Commit**

```bash
git add docs/consulting/public-repo-assessment-2026-04-01.md docs/issues/public-readiness-follow-ups.md README.md docs/index.md _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "docs: capture public repo readiness assessment"
```
