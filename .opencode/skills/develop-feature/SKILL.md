---
name: develop-feature
description: "Use when starting a new feature, bugfix, refactor, or docs change that is tracked in JIRA. Starts with the JIRA ticket (via Atlassian MCP) and either adopts an existing Implementation Plan document or drafts a new one, then drives the implementation step by step against that plan. Triggers on requests to 'start feature', 'implement ticket', 'work on PRO-XXX', 'draft implementation plan', 'begin work on JIRA ticket', or any workflow that begins with a JIRA ticket and ends with a feature branch ready for review. NOTE: The agent-team prepares closure; after user / PO confirmation, the agent-team executes `atlassian_transitionJiraIssue` and `gh pr merge`. Story points must be assigned before development pickup or sprint inclusion."
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

## Step 0 — Determine Current State

1. Identify the current branch and JIRA ticket:
   ```bash
   git branch --show-current
   git log --oneline -5
   ```
2. Extract the PRO-XXX ticket from the branch name or recent commits.
3. Verify the working tree is clean before proceeding:
   ```bash
   git status
   ```

2. **Optional Enhancement**: 1. Read the drafted ticket via Atlassian MCP to confirm it is ready for review (optional):
   ```
   atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["description", "status", "customfield_10028"])
   ```
   (This can be skipped if not needed)

---

## Step 1 — Read the JIRA Ticket

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

### 1e. Validate story points before development

**Critical:** If a ticket is created in the active sprint or development
is picked up, **story points must be assigned** before development
begins. Verify that `customfield_10028` is populated. If null, stop
and escalate to the PO — do not begin development.

```
atlassian_getJiraIssue(issueIdOrKey="PRO-XXX",
    fields=["summary", "customfield_10028", "status", "sprint"])

if fields["customfield_10028"] is None:
    print(f"ERROR: PRO-XXX has no story points assigned.")
    print(f"Story points must be estimated before sprint inclusion or development pickup.")
    return
```

## Step 2 — Adopt or Draft the Implementation Plan

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
JIRA description (Step 1b) and note any drift, then proceed to Step 3.

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

Walk every AC in the JIRA description (Step 1b) and confirm it appears in
the plan as a step, a verification item, or an explicit non-goal. Walk every
DoD checkbox the same way. Note discrepancies back to the user before
proceeding.

## Step 3 — Prepare the Branch

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

## Step 4 — Implement in Rollout Steps

The plan's **rollout section** (Part B step 6) is the execution order. Do
**not** implement everything in one shot. Each rollout step is a discrete,
reversible, verifiable increment that ends in a passing gate. Typical shape:

1. **Land pure code first** (scripts, modules, tests). No workflow file yet,
   so CI behaviour is unchanged. Verify with `pytest -q tests/ci-pipeline/` (or
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
     self-test gate (`pytest -q tests/ci-pipeline/`) — the verifier tests
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

## Step 5 — Final Verification

Before opening a PR, run the **full** quality gate. All of these must pass:

```bash
# CI self-tests (gate the pipeline per AGENTS.md gotcha)
pytest -q tests/ci-pipeline/

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

## Step 6 — Open the PR

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

## Step 7 — Hand off to `complete-feature`

The `complete-feature` skill takes over from here: it verifies the PR's
final state, posts the JIRA status comment, assigns story points,
checkmarks the ACs and DoD in the JIRA description, and updates the
PR description with the final status.

> **⚠️ Requires User / Product-Owner confirmation before execution.**
> The agent-team MUST obtain explicit user/PO confirmation before calling
> `atlassian_transitionJiraIssue` and `gh pr merge`.
>
> **What the agent-team DOES:**
> 1. Verify the PR's final state
> 2. Post the JIRA status comment
> 3. Assign story points
> 4. Checkmark the ACs and DoD in the JIRA description
> 5. Update the PR description with the final status
> 6. After user/PO confirmation: execute `atlassian_transitionJiraIssue` and `gh pr merge`
>
> **What the user / Product-Owner confirms:**
> - All ACs checkmarked
> - DoD complete
> - PR description accurate
> - Story points assigned
> - Test results passed
>
> **After confirmation, the agent-team executes:**
> ```
> atlassian_transitionJiraIssue(issueIdOrKey="PRO-XXX", transition={"id": "31"})
> gh pr merge <PR_NUMBER> --merge
> ```
>
> **Branch deletion:** The `complete-feature` skill includes a
> **Step 5.6 — Delete Remote Branch** that the agent-team prepares
> but the user / Product-Owner confirms and executes. See
> `.opencode/skills/complete-feature/SKILL.md` for details.
>
> **Verification:** The agent-team verifies the JIRA ticket is in "Fertig"
> status and the PR is merged.

## Reference: Command Cheatsheet

| Action | Command |
|--------|---------|
| Fetch JIRA ticket | `atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=[...])` |
| Fetch ticket comments | `atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["comment"])` |
| Add JIRA comment | `atlassian_addCommentToJiraIssue(issueIdOrKey="PRO-XXX", commentBody="…")` |
| Close JIRA ticket | `atlassian_transitionJiraIssue(issueIdOrKey="PRO-XXX", transition={"id": "31"})` — **after user/PO confirmation** |
| Adopt plan | read `doc/02_Implementation_Plan_PRO-XXX.md` |
| Draft plan | write `doc/02_Implementation_Plan_PRO-XXX.md` with Parts A/B/C |
| Reactivate venv | `source /workspaces/TimeSheet/.venv/bin/activate` |
| Create branch | `git switch -c <type>/PRO-XXX-<desc> master` |
| Run CI self-tests | `pytest -q tests/ci-pipeline/` |
| Run application tests | `python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing` |
| Lint | `ruff check src_timesheetalgo tests .github && black --check src_timesheetalgo tests .github && pydocstyle src_timesheetalgo tests .github` |
| Traceability | `python .github/scripts/generate_traceability_matrix.py` |
| Commit | `git commit -m "<type>(<scope>): <subject>\n\nRefs: PRO-XXX"` |
| Push | `git push -u origin <branch>` |
| Delete remote branch | `git push origin --delete <branch-name>` — **User/PO confirms and executes** (via complete-feature Step 5.6) |
| Delete implementation plan | `git rm doc/02_Implementation_Plan_PRO-XXX.md` — **User/PO confirms and executes** (via complete-feature Step 5.5) |
| Open PR | `gh pr create --base master --title "[<type>][PRO-XXX] …" --body "…"` |

## Reference: Worked Example — PRO-369

This skill was extracted from the PRO-369 (Continuous CI-Pipeline Timing
Benchmark) work. Useful as a reference for shape, not as a template:

- **Plan**: `doc/02_Implementation_Plan_PRO-XXX.md` (topic-numbered layout)
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

## Cycle Tracking and Escalation

This skill is invoked by an agent under the Product Owner dispatcher. Each
invocation is a **cycle**. The agent must track the current cycle and
escalate when the limit is reached.

### Cycle Limits

- **Max cycles per dispatch:** 3
- **If cycle = 1, 2:** Continue working — the agent is on schedule
- **If cycle = 3:** Stop, prepare handoff to Product Owner with summary
- **If cycle > 3:** STOP — agent must NOT continue, escalate immediately

### When to Escalate

Escalate to Product Owner when:
1. **Blocker encountered** — the agent cannot resolve an issue (questions, missing data, conflicting requirements, etc.)
2. **Cycle 3 reached** — maximum allowed cycles have been used
3. **Process loops** — repeating the same step without progress (e.g., same test failing after 3 attempts, same lint error recurring)

### Escalation Handoff

When escalating, provide:

```markdown
## Escalation: [Skill Name] — [Brief Description]

### Cycle Information
- Current cycle: [N] of max 3
- Started: [approximate time]
- Last action: [what was just done]

### Blocked On
- [Specific question, missing info, or issue]

### What's Done
- [Summary of completed steps]

### What's Remaining
- [Steps that could not be completed]
```

### Common Escalation Triggers

| Trigger | Example | Escalate? |
|---------|---------|-----------|
| Test fails 3+ times | Same test failure after 3 fix attempts | Yes |
| Lint error recurs | Same ruff/black error after 3 fix attempts | Yes |
| JIRA field missing | Cannot determine acceptance criteria | Yes — ask PO |
| Plan ambiguous | Two valid interpretations of requirement | Yes — ask PO |

## Related Documents

- `AGENTS.md` — Top-level guide: project conventions, modes, CI gates
- `.opencode/docs/WORKFLOW.md` — Agent team workflow, diagrams, quality gates, handoff labels
- `doc/CONTRIBUTING.md` — Development standards
- `doc/TESTING.md` — Test structure, test markers, test organization
- `doc/ARCHITECTURE.md` — System architecture and design decisions
- `.opencode/skills/develop-feature/` — This skill
- `.opencode/skills/discover-feature/SKILL.md` — Feature discovery and ticket creation
- `.opencode/skills/refine-feature/SKILL.md` — Stakeholder review and finalization
- `.opencode/skills/complete-feature/SKILL.md` — Workflow for closing a ticket
| Out of scope | Implementation requires changes not in plan | Yes — ask PO |
| External dependency | Waiting on third-party or upstream PR | Yes — pause and notify |
