---
name: feature-complete
description: Use when completing a feature and needing to verify acceptance criteria, update JIRA ticket, close the ticket, update PR description, and commit/push changes. Triggers on requests to "complete feature", "close JIRA ticket", "finalise implementation", "verify feature completeness", "check off acceptance criteria", or any JIRA ticket closure workflow.
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
python -m pytest .github/tests/ -q

# Traceability
python .github/scripts/generate_traceability_matrix.py
```

**Gate:** All checks must pass before proceeding. If any fail, fix and re-run.

## Step 2 — Evaluate Acceptance Criteria

1. Read the implementation plan document (e.g. `doc/02_Implementation_Plan_PRO-XXX.md`).
2. Read the JIRA ticket description via Atlassian MCP:
   ```
   atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["description", "status", "fixVersions"])
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

### 3b. Checkmark Acceptance Criteria in Description

Update the JIRA ticket description using `atlassian_editJiraIssue` to add ✅ markers next to each completed AC and check off the DoD checklist items.

### 3c. Transition to Done

Get available transitions and close the ticket:
```
atlassian_getTransitionsForJiraIssue(issueIdOrKey="PRO-XXX")
atlassian_transitionJiraIssue(issueIdOrKey="PRO-XXX", transition={"id": "31"})
```
- Transition ID `31` = "Fertig" (Done) for this JIRA instance
- Verify the ticket is closed:
  ```
  atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["status", "resolution"])
  ```

## Step 4 — Update PR Description

Update the PR description with final status:
```bash
gh pr edit <PR_NUMBER> --body '## Summary

...final status with all ACs marked complete...

## Testing
- All checks passed
...

Refs: PRO-XXX'
```

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

## Step 6 — Verify Final State

```bash
# Working tree clean
git status

# Latest commit includes all changes
git log --oneline -3

# PR is up to date
gh pr view <PR_NUMBER> --json title,state,mergeable

# JIRA ticket is closed
atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["status", "resolution"])
```

## Reference: Quick Command Cheatsheet

| Action | Command |
|--------|---------|
| Run tests | `python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing` |
| Run CI self-tests | `python -m pytest .github/tests/ -q` |
| Run lint | `ruff check src_timesheetalgo tests .github` |
| Check traceability | `python .github/scripts/generate_traceability_matrix.py` |
| Add JIRA comment | `atlassian_addCommentToJiraIssue(issueIdOrKey="PRO-XXX", commentBody="...")` |
| Update JIRA description | `atlassian_editJiraIssue(issueIdOrKey="PRO-XXX", fields={"description": "..."})` |
| Close JIRA ticket | `atlassian_transitionJiraIssue(issueIdOrKey="PRO-XXX", transition={"id": "31"})` |
| Update PR description | `gh pr edit <N> --body '...'` |
| Stage all | `git add -A` |
| Commit | `git commit -m "docs(ci): finalise PRO-XXX...\n\nRefs: PRO-XXX"` |
| Push | `git push origin <branch>` |