---
name: feature-development
description: Use when starting a new feature, bugfix, refactor, or docs change that is tracked in JIRA. Starts with the JIRA ticket (via Atlassian MCP) and either adopts an existing Implementation Plan document or drafts a new one, then drives the implementation step by step against that plan. Triggers on requests to "start feature", "implement ticket", "work on PRO-XXX", "draft implementation plan", "begin work on JIRA ticket", or any workflow that begins with a JIRA ticket and ends with a feature branch ready for review.
---

# Feature Development Skill

End-to-end feature development workflow for TimeSheetAlgo. Begins with the
JIRA ticket, cross-references or drafts the Implementation Plan document, then
executes the plan in verifiable increments. Follows the conventions in
`doc/CONTRIBUTING.md` §1–§3 and the project lifecycle documented in
`AGENTS.md` §"Development Workflow".

## Prerequisites

- Working directory: `/workspaces/TimeSheet` (repository root)
- Virtual environment activated: `source /workspaces/TimeSheet/.venv/bin/activate`
- `gh` authenticated and `git` configured
- Atlassian MCP tools available (Jira)
- A clean working tree on the correct base branch

## Phase 1 — Read the JIRA Ticket

### 1a. Resolve the ticket

If the user has not named a ticket, identify the next one to work on by
looking at the branch name (`feature/PRO-XXX-…`, `bugfix/PRO-XXX-…`, etc.) or
asking the user. The PRO-XXX number is the single source of truth for
naming, commits, PRs, and the implementation plan file.

### 1b. Fetch the ticket

```
atlassian_getJiraIssue(issueIdOrKey="PRO-XXX",
    fields=["summary", "description", "status", "issuetype", "priority",
            "assignee", "reporter", "parent", "comment", "fixVersions"])
```

Extract and record:
- Summary, issue type (Story / Bug / Task), priority
- Acceptance Criteria (AC1, AC2, …) from the description
- Definition of Done checklist
- Parent epic (e.g. PRO-259) and any blockers / related tickets
- Open comments — they often contain late additions or scope changes
- Current status ("Zu erledigen" = To Do, "In Arbeit" = In Progress,
  "Fertig" = Done)

### 1c. Resolve the parent epic (if any)

```
atlassian_getJiraIssue(issueIdOrKey="PRO-XXX",
    fields=["parent", "summary", "status"])
```

Record whether the ticket is a child of a larger epic, since the implementation
plan and PR title both reference the parent.

### 1d. Record ticket-drift signals

Before drafting the plan, surface anything in the ticket that disagrees with
the repo state. Common drift to look for and call out explicitly:
- A "parent" referenced in the description that no longer exists or has moved
- Acceptance criteria that contradict existing code or other open tickets
- A status that says "New" but the linked branch is already in use
- "Out of Scope" / "Non-Goals" lists that this work would silently violate

If any drift is found, stop and confirm with the user before proceeding.

## Phase 2 — Adopt or Draft the Implementation Plan

### 2a. Look for an existing plan

Check `doc/` for an existing implementation plan:

```bash
ls doc/*Implementation_Plan*.md doc/*PLAN*.md 2>/dev/null
```

Two layouts are in use:
- `doc/02_Implementation_Plan_PRO-XXX.md` (current convention — one file per ticket)
- `doc/NN_Implementation_Plan_<Topic>.md` (older convention — topic-numbered)

The newer convention wins. If a plan for PRO-XXX already exists, **adopt it
as the source of truth** — do not rewrite it. Cross-check the plan against the
JIRA description (Phase 1b) and note any drift, then proceed to Phase 3.

### 2b. Draft a new plan (only if none exists)

If no plan exists, draft one in `doc/02_Implementation_Plan_PRO-XXX.md` with
three parts. Use the file as the **single source of truth** for the rest of
the workflow; every step below refers back to it.

**Part A — Preanalysis.** Resolve the open questions the implementation
will face: data source, scope, exclusion rules, persistence, persistence
isolation (i.e. the mechanism must not pollute the PR branch or re-trigger
CI), trigger, statistics + granularity, security/permissions, accuracy
caveats, and a feasibility verdict. Each section ends with a decision that
B will reuse.

**Part B — Implementation Plan.** A table of new/changed files, the data
schema (if any), the workflow / module logic in numbered steps, the report
or API shape, the configuration knobs, an explicit rollout plan, and an
explicit non-goals list (what this work deliberately does *not* cover).

**Part C — Verification Definition.** Unit-level (V1–V4), integration-level
(V5–V7), and a checklist of acceptance criteria plus a Definition of Done.
Each item must be objectively checkable from the repo or from a test
command.

Header convention: include the JIRA key, parent epic, current status, and
"not yet implemented" so the file documents its own state.

### 2c. Cross-check the plan against the ticket

Walk every AC in the JIRA description (Phase 1b) and confirm it appears in
the plan as a step, a verification item, or an explicit non-goal. Walk every
DoD checkbox the same way. Note discrepancies back to the user before
proceeding.

## Phase 3 — Prepare the Branch

```bash
# From a clean working tree
git status
git fetch origin
git switch master && git pull --ff-only
git switch -c feature/PRO-XXX-<short-description> master
# (or bugfix/ / refactor/ / docs/ / test/ — match the work type)
```

If a feature branch for this ticket already exists, switch to it instead of
creating a new one. Never create a second branch for the same ticket.

Reactivate the virtual environment after every branch switch
(`source /workspaces/TimeSheet/.venv/bin/activate` — see `AGENTS.md` gotcha
#1).

## Phase 4 — Implement in Rollout Steps

The plan's **rollout section** (Part B step 6) is the execution order. Do
**not** implement everything in one shot. Each rollout step is a discrete,
reversible, verifiable increment that ends in a passing gate. Typical shape:

1. **Land pure code first** (scripts, modules, tests). No workflow file yet,
   so CI behaviour is unchanged. Verify with `pytest -q .github/tests/` (or
   the appropriate marker) and the linters.
2. **Land the workflow / API surface**. Initially in a manual-trigger-only
   mode (`workflow_dispatch`) so the live system is not yet affected.
   Verify the workflow YAML is valid and the unit tests still pass.
3. **Seed the persistent data** (orphan branch, initial dataset, etc.).
   Run the manual trigger once and inspect the result.
4. **Enable the continuous trigger** (`workflow_run`, schedule, etc.) only
   after step 3 looks right.
5. **Document** in `AGENTS.md` and `doc/CONTRIBUTING.md` — where the artefact
   lives, that it is non-gating, what the no-loop invariants are.

For each rollout step:

1. **Re-read the plan section** for this step. The plan is the spec; do
   not silently extend scope.
2. **Implement the change** following the existing code conventions
   (composite actions, stdlib-only CI scripts, Conventional Commits, no
   comments unless asked).
3. **Verify immediately** — run the gate that this step is supposed to
   unblock, not the whole suite every time:
   - For step 1 (pure code): unit tests + `ruff` + `black` + `pydocstyle`
     on the changed files.
   - For step 2 (workflow YAML): YAML validity, plus the existing CI
     self-test gate (`pytest -q .github/tests/`) — the verifier tests
     catch workflow regressions.
   - For step 3 (data seed): smoke-test the new scripts with synthetic
     input rather than live API calls.
   - For step 4 (trigger): not verifiable locally; rely on the unit
     tests + the existing CI self-test gate that enforces the no-loop
     invariant (`test_ci_timing_does_not_retrigger_python_ci` is a
     worked example).
4. **Update the plan's status table** as each step completes. The plan
   documents progress; do not let it drift from reality.
5. **Commit each step** with a Conventional Commits message and a
   `Refs: PRO-XXX` trailer. Keep commits logically grouped (one rollout
   step = one commit, or one logical change = one commit).

## Phase 5 — Final Verification

Before opening a PR, run the **full** quality gate. All of these must pass:

```bash
# CI self-tests (gate the pipeline per AGENTS.md gotcha)
pytest -q .github/tests/

# Application tests
python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing

# Lint
ruff check src_timesheetalgo tests .github
black --check src_timesheetalgo tests .github
pydocstyle src_timesheetalgo tests .github

# Traceability
python .github/scripts/generate_traceability_matrix.py
```

If the gate is the **PR quality gate**, also confirm:
- Plan's status table is fully checked off
- Every AC in the JIRA description is implemented, deferred (with reason),
  or moved to a non-goal
- Definition of Done items in the plan match reality

## Phase 6 — Open the PR

Branch name and PR title follow `doc/CONTRIBUTING.md` §5:
- Title: `[<type>][PRO-XXX] <Description>` (e.g. `[feat][PRO-369] …`)
- Body: `## Summary` + `## Testing` sections, `Refs: PRO-XXX`, no TODO/TBD
  placeholders (the naming validator blocks merge on these)

```bash
git push -u origin feature/PRO-XXX-<short-description>

gh pr create \
  --base master \
  --title "[<type>][PRO-XXX] <Description>" \
  --body "$(cat <<'EOF'
## Summary
…
## Testing
- …
Refs: PRO-XXX
EOF
)"
```

After opening, surface the PR URL and let the user drive review.

## Phase 7 — Hand off to `feature-complete`

The `feature-complete` skill takes over from here: it verifies the PR's
final state, posts the JIRA status comment, transitions the ticket to
**Fertig (Done)**, and updates the PR description with the closure status.
Do not attempt to close the ticket from this skill — the closure workflow
lives in `feature-complete` so the two phases are independently testable.

## Reference: Command Cheatsheet

| Action | Command |
|--------|---------|
| Fetch JIRA ticket | `atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=[...])` |
| Fetch ticket comments | `atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["comment"])` |
| Add JIRA comment | `atlassian_addCommentToJiraIssue(issueIdOrKey="PRO-XXX", commentBody="…")` |
| Close JIRA ticket | `atlassian_transitionJiraIssue(issueIdOrKey="PRO-XXX", transition={"id": "31"})` |
| Adopt plan | read `doc/02_Implementation_Plan_PRO-XXX.md` |
| Draft plan | write `doc/02_Implementation_Plan_PRO-XXX.md` with Parts A/B/C |
| Reactivate venv | `source /workspaces/TimeSheet/.venv/bin/activate` |
| Create branch | `git switch -c <type>/PRO-XXX-<desc> master` |
| Run CI self-tests | `pytest -q .github/tests/` |
| Run application tests | `python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing` |
| Lint | `ruff check src_timesheetalgo tests .github && black --check src_timesheetalgo tests .github && pydocstyle src_timesheetalgo tests .github` |
| Traceability | `python .github/scripts/generate_traceability_matrix.py` |
| Commit | `git commit -m "<type>(<scope>): <subject>\n\nRefs: PRO-XXX"` |
| Push | `git push -u origin <branch>` |
| Open PR | `gh pr create --base master --title "[<type>][PRO-XXX] …" --body "…"` |

## Reference: Worked Example — PRO-369

This skill was extracted from the PRO-369 (Continuous CI-Pipeline Timing
Benchmark) work. Useful as a reference for shape, not as a template:

- **Plan**: `doc/01_Implementation_Plan_CI_Timing_Benchmark.md` (older
  topic-numbered layout — the repo is migrating to
  `02_Implementation_Plan_PRO-XXX.md`)
- **JIRA**: PRO-368 parent (Fertig), PRO-369 child (In Arbeit),
  parent epic PRO-259
- **Rollout steps** in the plan: 1) scripts + tests, 2) workflow +
  orphan branch, 3) verify seeded report + enable continuous trigger,
  4) docs. This skill was developed *after* the plan was drafted, so the
  rollout was followed step-by-step.
- **Drift caught during cross-check**: the plan said PRO-369 was
  "New" but JIRA showed "In Arbeit"; the plan's `00_…` cross-reference
  pointed to a non-existent file. Both were noted in the chat before
  implementation started.
- **Test-driven bug catch**: the backfill driver's first draft was
  neither idempotent nor attempt-aware. Unit tests caught both bugs
  before the workflow was wired up.
