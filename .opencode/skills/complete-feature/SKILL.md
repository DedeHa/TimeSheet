---
name: complete-feature
description: "Use when completing a feature and needing to verify acceptance criteria, update JIRA ticket, checkmark ACs and DoD, update PR description, and commit/push changes. Triggers on requests to 'complete feature', 'finalise implementation', 'verify feature completeness', 'check off acceptance criteria', or 'prepare JIRA closure'. NOTE: The agent-team prepares closure; after user / PO confirmation, the agent-team executes `atlassian_transitionJiraIssue` and `gh pr merge`. Sprint inclusion is verified in the plan-feature skill."
---

# Feature Complete Skill

Reusable end-to-end feature completion workflow for TimeSheetAlgo. Follows the conventions in `doc/CONTRIBUTING.md` §3 and §7.

## Prerequisites

- Working directory: `/workspaces/TimeSheet` (repository root)
- Virtual environment activated: `source /workspaces/TimeSheet/.venv/bin/activate`
- `gh` authenticated and `git` configured
- Atlassian MCP tools available (Jira)

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

## Step 1 — Run Final Verification

Run the full test suite and lint checks to confirm everything passes:

```bash
# Lint checks
ruff check src_timesheetalgo tests .github
black --check src_timesheetalgo tests .github
pydocstyle src_timesheetalgo tests .github

# Application tests
python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing

# CI self-tests
python -m pytest .github/tests/ci-pipeline/ -q

# Traceability
python .github/scripts/generate_traceability_matrix.py
```

**Gate:** All checks must pass before proceeding. If any fail, fix and re-run.

## Step 2 — Evaluate Acceptance Criteria

1. Read the implementation plan document (e.g. `doc/02_Implementation_Plan_PRO-XXX.md`).
2. Read the JIRA ticket description via Atlassian MCP:
   ```
   atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["description", "status", "fixVersions", "resolution"])
   ```
3. Cross-reference each acceptance criterion (AC-1, AC-2, ...) against:
   - The implementation plan's status table
   - The actual code/workflow state
   - Test results from Step 1
4. Update the implementation plan document to reflect final status:
   - Mark all completed steps as ✅ Done
   - Mark all ACs as ✅ Complete (or ⏳ Deferred with reason)
   - Update the timeline to reflect actual completion
   - Add a final summary noting JIRA closure

## Step 3 — Update JIRA Ticket

### 3a. Add Implementation Status Comment

Post a comprehensive comment using `atlassian_addCommentToJiraIssue`:

```
## PRO-XXX Implementation Status Update

All work for PRO-XXX is complete. Here is the final status:

### Completed Work
- List each optimisation/fix with status

### Acceptance Criteria Status
| AC | Description | Status |
|----|-------------|--------|
| AC1 | ... | ✅ Complete |
...

### Definition of Done
- [x] All items checked

### Test Results
- Application tests: N passed (100%)
- CI self-tests: N passed (100%)
- Traceability: 100%
- Code coverage: XX% (gate: 90%)

Refs: PRO-XXX
```

### 3b. Assign Story Points

**Critical:** The project uses story points in `customfield_10028`. Before closing, check if story points are assigned and assign them if missing.

1. Query recent Stories to identify the story points field and comparable estimates:
   ```
   atlassian_searchJiraIssuesUsingJql(jql='project = PRO AND issuetype = Story ORDER BY created DESC', maxResults=20)
   ```
   Look for `customfield_10028` values in the results.
2. If PRO-XXX has `customfield_10028: null`, assign a value using:
   ```
   atlassian_editJiraIssue(issueIdOrKey="PRO-XXX", fields={"customfield_10028": N})
   ```
   Use comparable tickets as reference:
   - 1-2 pts: Minor fix, documentation update
   - 3-5 pts: Moderate feature, CI/workflow change
   - 5-8 pts: Significant feature with tests
   - 8+ pts: Large refactor or complex feature

### 3c. Checkmark Acceptance Criteria and Definition of Done in Description

Update the JIRA ticket description using `atlassian_editJiraIssue` so that
every AC and every DoD item renders as an actual interactive checkbox in the
JIRA UI. A comment is **not** a substitute for editing the description.

**Required skeleton (do not skip any section; copy verbatim and fill in):**

```markdown
## Summary

<one-paragraph scope summary>

## Acceptance Criteria

- [x] AC-1: <description> — <implementation detail>
- [x] AC-2: <description> — <implementation detail>
- [ ] AC-N: <description> — **Deferred:** <reason> *(only if deferred)*

## DoD

**Story Points:** N

- [x] PR #NNN merged to master
- [x] All ACs checkmarked
- [x] Story Points: N assigned
- [x] Traceability: FR-XX, QR-XX added to doc/REQUIREMENTS.md
- [x] Architecture updated: doc/ARCHITECTURE.md lists new FR/QR
- [x] CI self-tests: N passed
- [x] Lint checks: ruff, black, pydocstyle, radon
- [x] Application tests: N passed (≥90% coverage)
- [x] Implementation plan updated: doc/02_Implementation_Plan_PRO-XXX.md
- [x] JIRA description fully checkmarked

## Dependencies

<list of related tickets, modules, or external systems>

## Notes

<architectural context, design decisions, follow-ups>
```

**How to send the update:**

1. Read the existing description with
   `atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["description"])`.
2. Build the **full** new description as a single string, preserving all
   existing context (Context, Current State Analysis, Key Observations, …).
   Replace only the `## AC` and `## DoD` blocks.
3. Send it with `atlassian_editJiraIssue(issueIdOrKey="PRO-XXX", fields={"description": "..."})`.
4. **Verify** by re-reading the issue and confirming every AC and DoD bullet
   starts with `- [x]` (or `- [` for any deferred AC). Re-run the edit if
   anything is missing.

**Required DoD lines (every ticket must include all 9):**

| # | DoD line |
|---|----------|
| 1 | `PR #NNN merged to master` |
| 2 | `All ACs checkmarked` |
| 3 | `Story Points: N assigned` |
| 4 | `Traceability: FR-XX, QR-XX added to doc/REQUIREMENTS.md` |
| 5 | `Architecture updated: doc/ARCHITECTURE.md lists new FR/QR` |
| 6 | `CI self-tests: N passed` |
| 7 | `Lint checks: ruff, black, pydocstyle, radon` |
| 8 | `Application tests: N passed (≥90% coverage)` |
| 9 | `Implementation plan updated: doc/02_Implementation_Plan_PRO-XXX.md` |
| 10 | `JIRA description fully checkmarked` |

**Common failure modes (avoid these):**

| Failure | Why it's wrong | Fix |
|---------|----------------|-----|
| Leaving the original `* [ ] AC-N` bullet unedited | Stays an open checkbox in the UI | Replace every AC line with `- [x] AC-N: <desc> — <detail>` |
| Writing only a status comment, never editing the description | Comment is not the description; the ACs stay unchecked | Always call `atlassian_editJiraIssue` with `fields.description` |
| Using `## DoD` heading with no bullets | The DoD section is empty | Include all 10 DoD lines above |
| Story points line placed in `## Summary` | Hides it from the description head | Place `**Story Points:** N` directly under `## DoD` |
| PR number missing or `TBD` | DoD item stays open | Update after PR is opened: `- [x] PR #NNN merged to master` |
| Original `## Dependencies` / `## Notes` sections dropped | Loses stakeholder context | Preserve all non-AC/DoD sections verbatim |

### 3d. Transition to Done

After user/PO confirmation of the prepared closure, the agent-team executes the final transition:

> **⚠️ Requires User / Product-Owner confirmation before execution.**
> The agent-team MUST obtain explicit user/PO confirmation before calling
> `atlassian_transitionJiraIssue` and `gh pr merge`.
>
> **What the agent-team DOES:**
> 1. Step 3a: Post the implementation status comment
> 2. Step 3b: Assign story points
> 3. Step 3c: Update JIRA description with `- [x]` AC and DoD checkmarks
> 4. Step 4: Update PR description with final status
> 5. After user/PO confirmation: execute `atlassian_transitionJiraIssue` and `gh pr merge`
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
> **Verification:** The agent-team verifies the JIRA ticket is in "Fertig"
> status and the PR is merged.

## Step 4 — Update PR Description

Update the PR description with final status. The PR body must contain **four
mandatory sections**; `gh pr edit` only updates the description, it does not
merge the PR.

**Mandatory sections (in order, do not skip any):**

```markdown
## Summary

<one-paragraph scope summary>

## Acceptance Criteria

| AC | Description | Status |
|----|-------------|--------|
| AC1 | ... | ✅ Complete |
| AC2 | ... | ⏳ Deferred — <reason> |

## Definition of Done

- [x] PR #NNN merged to master
- [x] All ACs checkmarked
- [x] Story Points: N assigned
- [x] Traceability: FR-XX, QR-XX added to doc/REQUIREMENTS.md
- [x] Architecture updated: doc/ARCHITECTURE.md lists new FR/QR
- [x] CI self-tests: N passed
- [x] Lint checks: ruff, black, pydocstyle, radon
- [x] Application tests: N passed (≥90% coverage)
- [x] Implementation plan updated: doc/02_Implementation_Plan_PRO-XXX.md
- [x] JIRA description fully checkmarked

## Testing

- All checks passed: ruff, black, pydocstyle, radon
- Application tests: N passed
- CI self-tests: N passed
- Traceability: 100%
- Code coverage: ~99% (gate: 90%)

Refs: PRO-XXX
```

**How to send the update:**

1. Write the PR body to a temp file (avoid shell-escaping issues with `Refs: PRO-XXX`):
   ```bash
   cat > /tmp/opencode/pr_body.md <<'EOF'
   ## Summary
   ...
   Refs: PRO-XXX
   EOF
   ```
2. Run `gh pr edit <PR_NUMBER> --body-file /tmp/opencode/pr_body.md`.
3. Verify with `gh pr view <PR_NUMBER> --json body` and confirm all four
   mandatory sections are present.

**Common failure modes (avoid these):**

| Failure | Why it's wrong | Fix |
|---------|----------------|-----|
| Missing `## Acceptance Criteria` section | PR body is incomplete | Always include the AC table |
| Missing `## Definition of Done` section | DoD not visible in the PR | Include the 10 DoD lines |
| `## Testing` section present but empty | Stakeholders cannot verify | Populate with actual numbers |
| `Refs: PRO-XXX` missing | Conventional Commits gate fails | Always include the footer |
| Inline multi-line body passed to `gh pr edit --body` | Shell-escaping truncates the body | Use `--body-file` instead |

## Step 5 — Stage, Commit, and Push

1. Stage all changes:
   ```bash
   git add -A
   ```
2. Review the staged diff:
   ```bash
   git diff --cached
   ```
3. Commit with Conventional Commits format:
   ```bash
   git commit -m "docs(ci): finalise PRO-XXX implementation plan and JIRA closure

   Update implementation plan to reflect completed status:
   - Mark all steps as Done including JIRA closure
   - Add all ACs with completion status
   - Note JIRA transitioned to Fertig (Done)

   Refs: PRO-XXX"
   ```
4. Push to remote:
   ```bash
   git push origin <branch-name>
   ```

**Note:** `git push` pushes the branch only; it does not merge the PR.

## Step 5.5 — Delete Remote Branch (User / PO Confirmed)

After the PR is merged, the remote feature branch should be deleted to keep the
repository clean. This is a **user / Product-Owner responsibility** — the
agent-team prepares the command but does not execute it.

> **⚠️ Requires User / Product-Owner confirmation before execution.**
> The agent-team MUST NOT run `git push origin --delete` without explicit
> user/PO confirmation. Remote branch deletion is destructive and cannot be
> undone without recreating the branch.

**What the agent-team DOES:**
1. Confirm the PR is merged to `master` (Step 6 verification).
2. Identify the branch name from `git branch --show-current` or the PR metadata.
3. Prepare the deletion command and present it to the user/PO:

   ```bash
   git push origin --delete <branch-name>
   ```

4. Warn the user/PO that this is irreversible and that the branch will be gone
   from the remote after execution.

**What the user / Product-Owner confirms:**
- PR is merged and the branch is no longer needed
- All work from the branch has been preserved (merged to master)
- You are ready to delete the remote branch

**After confirmation, the user / Product-Owner executes:**
```bash
git push origin --delete <branch-name>
```

**Verification:** Confirm the branch is gone from the remote with
`git ls-remote --heads origin | grep <branch-name>` (should return nothing).

## Step 6 — Verify Final State

```bash
# Working tree clean
git status

# Latest commit includes all changes
git log --oneline -3

# PR is up to date
gh pr view <PR_NUMBER> --json title,state,mergeable

# JIRA ticket is closed
atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["status", "resolution", "customfield_10028"])

# Remote branch deleted (after user/PO confirmation)
git ls-remote --heads origin | grep <branch-name>  # should return nothing
```

## Reference: Quick Command Cheatsheet

| Action | Command |
|--------|---------|
| Run tests | `python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing` |
| Run CI self-tests | `python -m pytest .github/tests/ci-pipeline/ -q` |
| Run lint | `ruff check src_timesheetalgo tests .github` |
| Check traceability | `python .github/scripts/generate_traceability_matrix.py` |
| Add JIRA comment | `atlassian_addCommentToJiraIssue(issueIdOrKey="PRO-XXX", commentBody="...")` |
| Get JIRA issue | `atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["*all"])` |
| Search JIRA stories | `atlassian_searchJiraIssuesUsingJql(jql="project = PRO AND issuetype = Story ORDER BY created DESC", maxResults=20)` |
| Assign story points | `atlassian_editJiraIssue(issueIdOrKey="PRO-XXX", fields={"customfield_10028": N})` |
| Update JIRA description | `atlassian_editJiraIssue(issueIdOrKey="PRO-XXX", fields={"description": "..."})` |
| Close JIRA ticket | `atlassian_transitionJiraIssue(issueIdOrKey="PRO-XXX", transition={"id": "31"})` |
| Update PR description | `gh pr edit <N> --body '...'` |
| Stage all | `git add -A` |
| Commit | `git commit -m "docs(ci): finalise PRO-XXX...\n\nRefs: PRO-XXX"` |
| Push | `git push origin <branch>` |
| Delete remote branch | `git push origin --delete <branch-name>` — **User/PO confirms and executes** |

## Cycle Tracking and Escalation

This skill is invoked by the tester agent under the Product Owner dispatcher.
Each invocation is a **cycle**. The agent must track the current cycle and
escalate when the limit is reached.

### Cycle Limits

- **Max cycles per dispatch:** 3
- **If cycle = 1, 2:** Continue verification — the agent is on schedule
- **If cycle = 3:** Stop, prepare handoff to Product Owner with summary
- **If cycle > 3:** STOP — agent must NOT continue, escalate immediately

### When to Escalate

Escalate to Product Owner when:
1. **Blocker encountered** — verification cannot proceed (broken CI, missing artifacts, conflicting results, etc.)
2. **Cycle 3 reached** — maximum allowed cycles have been used
3. **Process loops** — repeated failures without progress (e.g., tests fail after 3 fix attempts, coverage regresses)

### Escalation Handoff

When escalating, provide:

```markdown
## Escalation: Feature Completion — [Brief Description]

### Cycle Information
- Current cycle: [N] of max 3
- Started: [approximate time]
- Last action: [what was just done]

### Blocked On
- [Specific question, missing info, or issue]

### What's Done
- [Summary of completed checks]

### What's Remaining
- [Checks that could not be completed]
```

### Common Escalation Triggers

| Trigger | Example | Escalate? |
|---------|---------|-----------|
| Coverage < 90% | Tests added but threshold not met after 3 attempts | Yes |
| Lint error | Cannot resolve ruff/black issue | Yes |
| JIRA update fails | Description update returns error | Yes — ask PO |
| Test fails | Same test fails after 3 fix attempts | Yes |
| Out of scope | Required changes not in original ACs | Yes — ask PO |
