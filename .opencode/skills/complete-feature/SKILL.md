---
name: complete-feature
description: "Use when completing a feature and needing to verify acceptance criteria, update JIRA ticket, checkmark ACs and DoD, update PR description, and commit/push changes. Triggers on requests to 'complete feature', 'finalise implementation', 'verify feature completeness', 'check off acceptance criteria', or 'prepare JIRA closure'. NOTE: The agent-team prepares closure. Closure steps — delete implementation plan, merge PR, transition JIRA, delete remote branch — ALWAYS require explicit final user/PO confirmation in BOTH interactive and automated workflow modes. Sprint inclusion is verified in the discover-feature skill."
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

2. **Optional Enhancement**: Read the finalized ticket via Atlassian MCP to verify readiness for closure:
   ```
   atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["summary", "description", "status", "resolution"])
   ```
   (This can be skipped if not needed)

## Step 1 — Pre-Closure Validation

Before proceeding with final verification, validate all critical closure
conditions. This phase is **mandatory and blocking**: if any check fails,
the workflow reports the specific failing check and halts — it must not
reach Step 4h (Transition JIRA to DONE).

The 5 checks are executed in order. Check 1 (PR merge) must pass before
Check 2 (comment gating) is even evaluated.

### Check 1 — PR Merge Verification

Execute `gh pr view` to confirm the PR is actually merged:

```bash
gh pr view <PR_NUMBER> --json mergeCommit,state,headRefName
```

**Pass conditions:**
- `state == "MERGED"`
- `mergeCommit` is not null (not empty)

**If failed:** Report `PR #XXX is not merged. Current state: OPEN/CLOSED. Cannot transition to Fertig.` and halt the workflow.

**If `gh pr view` fails:** Report `Cannot check PR #XXX state (gh pr view failed). Verify that gh is authenticated and the PR number is correct.` and halt the workflow.

### Check 2 — No Unverified Merge Comment

Check 1 must pass before any JIRA comment is posted claiming a PR merge.

**Gate:** Step 4a (Add Implementation Status Comment) must be gated so that
the merge comment is posted **only after** Check 1 confirms `state == "MERGED"`.

**If Check 1 fails:** Do NOT post a merge comment. Report the PR state
failure and halt.

### Check 3 — Implementation Plan Deleted

Verify that the implementation plan document has been deleted:

```bash
ls doc/02_Implementation_Plan_PRO-XXX.md
```

**Pass condition:** The file does not exist.

**If failed:** Report `Implementation plan not deleted: doc/02_Implementation_Plan_PRO-XXX.md still exists. Delete before proceeding.` and halt the workflow.

### Check 4 — Working Tree Clean

Execute `git status --porcelain` to verify there are no uncommitted changes:

```bash
git status --porcelain
```

**Pass condition:** Output is empty (no modified, staged, or untracked files).

**If failed:** Report `Uncommitted changes detected. Commit or stash before proceeding.` and halt the workflow.

### Check 5 — Remote Branch Deleted

Verify that the remote feature branch has been deleted:

```bash
git ls-remote --heads origin <branch-name>
```

**Pass condition:** Output is empty (the branch is absent from origin).

**If the branch still exists:** Report `Remote branch '<branch-name>' still exists on origin. Delete before proceeding.` and halt the workflow.

**If `git ls-remote` fails:** Treat the branch as absent (return True) and continue.

### Helper Scripts

The validation logic is implemented in reusable helper scripts that can be
used by the complete-feature workflow and by CI self-tests:

| Script | Purpose | Usage |
|--------|---------|-------|
| `ci/scripts/validate_pr_merge.py` | PR merge validation | `python ci/scripts/validate_pr_merge.py <PR_NUMBER>` |
| `ci/scripts/validate_filesystem.py` | Filesystem validation | `python ci/scripts/validate_filesystem.py <plan_path> <branch_name>` |

Both scripts return exit code 0 on success and 1 on failure, with a
descriptive message on stdout.

### Validation Order

The checks are executed in the following order. If any check fails, the
workflow halts immediately and reports the specific failing check — it does
not continue to the next check or reach Step 4h (Transition JIRA to DONE).

1. **PR merge verification** (Check 1) — blocks all JIRA transitions
2. **Comment gating** (Check 2) — only posts merge comments after Check 1 passes
3. **Implementation plan deletion** (Check 3)
4. **Working tree clean** (Check 4)
5. **Remote branch deletion** (Check 5) — reported as a remaining action if present

### Post-Hoc Verification

Step 5 (Verify Final State) performs a post-hoc verification of all 5 checks
as a safety net, but must not be the only place where these checks occur. The
pre-closure validation in Step 1 is the primary gate.

## Step 2 — Run Final Verification

Run the full test suite and lint checks to confirm everything passes:

```bash
# Lint checks
ruff check src_timesheetalgo tests .github
black --check src_timesheetalgo tests .github
pydocstyle src_timesheetalgo tests .github

# Application tests
python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing

# CI self-tests
python -m pytest tests/ci-pipeline/ -q

# Traceability
python .github/scripts/generate_traceability_matrix.py
```

**Gate:** All checks must pass before proceeding. If any fail, fix and re-run.

## Step 3 — Evaluate Acceptance Criteria

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

## Step 4 — Update JIRA Ticket

### 4a. Add Implementation Status Comment (Final Summary)

> **⚠️ GATED BY CHECK 1 — PR merge verification must pass first.**
>
> This comment claims that the PR is merged to master. It must be posted
> **only after** Step 1 (Check 1) confirms via `gh pr view` that
> `state == "MERGED"` and `mergeCommit` is not null. Posting this comment
> before verification is the exact failure mode of PRO-380.
>
> **Gating logic:**
>
> 1. Run Check 1: `gh pr view <PR_NUMBER> --json mergeCommit,state,headRefName`
> 2. If the PR is NOT merged (or `gh pr view` fails), do NOT post this comment.
>    Report the PR state failure and halt the workflow.
> 3. Only if Check 1 passes, proceed to post the comment below.
>
> **This is a mandatory closure artifact.** The final summary comment must be
> posted to the JIRA ticket before transitioning to Fertig. It serves as the
> permanent record of what was done, what was verified, and the final state of
> all acceptance criteria. Without this comment, the ticket closure is
> incomplete — the summary exists only in the PR body and commit history, not
> in the JIRA ticket itself.

Post a comprehensive comment using `atlassian_addCommentToJiraIssue`:

```
## PRO-XXX Final Summary — Feature Complete

All work for PRO-XXX is complete and merged to master. This comment is the
permanent closure record for the ticket.

### What Was Done
<list each optimisation/fix with a one-line description and the commit hash>

### Acceptance Criteria Status
| AC | Description | Status |
|----|-------------|--------|
| AC1 | ... | ✅ Complete |
| AC2 | ... | ✅ Complete |
| ... | ... | ... |

### Definition of Done
- [x] PR #NNN merged to master
- [x] All ACs checkmarked
- [x] Story Points: N assigned
- [x] Traceability: FR-XX, QR-XX added to doc/REQUIREMENTS.md
- [x] Architecture updated: doc/ARCHITECTURE.md lists new FR/QR
- [x] CI self-tests: N passed
- [x] Lint checks: ruff, black, pydocstyle, radon
- [x] Application tests: N passed (≥90% coverage)
- [x] Implementation plan deleted: doc/02_Implementation_Plan_PRO-XXX.md
- [x] JIRA description fully checkmarked

### Test Results
- Application tests: N passed
- CI self-tests: N passed
- Traceability: 100%
- Code coverage: XX% (gate: 90%)
- Lint: ruff ✅, black ✅, pydocstyle ✅, radon ✅

### Files Changed
<list key files added/modified/deleted>

Refs: PRO-XXX
```

### 4b. Assign Story Points

**Critical:** Story points must have been estimated **before sprint inclusion or development pickup** (`customfield_10028`). Before closing, verify they are assigned. If missing, assign them using comparable tickets as reference:

1. Query recent Stories to identify the story points field and comparable estimates:
   ```
   atlassian_searchJiraIssuesUsingJql(jql='project = PRO AND issuetype = Story ORDER BY created DESC', maxResults=20)
   ```
   Look for `customfield_10028` values in the results.
2. Verify PRO-XXX has `customfield_10028` populated. If null, assign a value using:
   ```
   atlassian_editJiraIssue(issueIdOrKey="PRO-XXX", fields={"customfield_10028": N})
   ```
   Use comparable tickets as reference:
   - 1-2 pts: Minor fix, documentation update
   - 3-5 pts: Moderate feature, CI/workflow change
   - 5-8 pts: Significant feature with tests
   - 8+ pts: Large refactor or complex feature

### 4c. Checkmark Acceptance Criteria and Definition of Done in Description

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


### 4d. Update PR Description

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


### 4e. Delete Implementation Plan (User / PO Confirmed)

**First closure step.** The implementation plan is deleted to mark the working
document as complete. The plan has served its purpose once all work is
implemented and documented.

> **⚠️ Requires explicit final User / Product-Owner confirmation before execution — in BOTH interactive and automated workflow modes.**
> The agent-team MUST NOT run `git rm` without explicit
> user/PO confirmation. Plan deletion is permanent and cannot be
> undone without recreating the plan from scratch.
>
> **Interactive mode:** Pause and present the confirmation prompt to the user/PO. Execute only after receiving explicit confirmation.
>
> **Automated mode:** Even though no human is expected to intervene, the agent-team MUST pause, present the confirmation prompt, and wait for an explicit confirmation signal before executing. Automated mode never auto-executes destructive actions.

**What the agent-team DOES:**
1. Confirm the implementation plan document is finalised and all steps/ACs are marked Complete.
2. Prepare the deletion command and present it to the user/PO:

   ```bash
   git rm doc/02_Implementation_Plan_PRO-XXX.md
   git commit -m "docs(ci): delete stale implementation plan for PRO-XXX

   Remove implementation plan after feature completion.
   The plan is a working document that is no longer needed.

   Refs: PRO-XXX"
   ```

3. Warn the user/PO that this is irreversible and that the plan file
   will be gone from the repository after execution.

**What the user / Product-Owner confirms:**
- The implementation plan is fully documented and all steps/ACs are marked Complete
- All work from the plan has been implemented
- You are ready to delete the implementation plan

**After confirmation, the user / Product-Owner executes:**
```bash
git rm doc/02_Implementation_Plan_PRO-XXX.md
git commit -m "docs(ci): delete stale implementation plan for PRO-XXX

Remove implementation plan after feature completion.
The plan is a working document that is no longer needed.

Refs: PRO-XXX"
git push origin <branch-name>
```

**Verification:** Confirm the plan file is gone from the remote with
`git ls-remote --heads origin | grep <branch-name>` (should return nothing)
and `git ls-files doc/02_Implementation_Plan_PRO-XXX.md` returns nothing.

### 4f. Verify CI Checks Passed (User / PO Confirmed)

Before proceeding with closure steps, verify that all CI checks passed.

> **⚠️ Requires explicit final User / Product-Owner confirmation before execution — in BOTH interactive and automated workflow modes.**
> The agent-team MUST NOT proceed without explicit
> user/PO confirmation after CI verification.

**What the agent-team DOES:**
1. Check GitHub Actions for the current PR:
   ```bash
   gh run list --repo "$GITHUB_REPOSITORY" --head "<branch-name>" --limit 10
   ```
2. Verify all required jobs (check, test, publish) have status "success"
3. If any checks fail, halt and report the failures

**What the user / Product-Owner confirms:**
- All CI checks have passed
- GitHub Actions are clean for this PR
- Ready to proceed with final destructive actions

**After confirmation, the agent-team proceeds.**

### 4g. Merge PR (User / PO Confirmed)

After user/PO confirmation, the agent-team executes the PR merge.

> **⚠️ Requires explicit final User / Product-Owner confirmation before execution — in BOTH interactive and automated workflow modes.**
> The agent-team MUST NOT call `gh pr merge` without explicit
> user/PO confirmation. PR merge is destructive and irreversible.
>
> **Interactive mode:** Pause and present the confirmation prompt to the user/PO. Execute only after receiving explicit confirmation.
>
> **Automated mode:** Even though no human is expected to intervene, the agent-team MUST pause, present the confirmation prompt, and wait for an explicit confirmation signal before executing. Automated mode never auto-executes destructive actions.

**What the agent-team DOES:**
1. Verify all CI checks passed (Step 4f).
2. Execute the PR merge:
   ```bash
   gh pr merge <PR_NUMBER> --merge
   ```

**What the user / Product-Owner confirms:**
- Ready to merge the PR to master
- All work has been verified and tested
- Confident in proceeding with merge

**After confirmation, the agent-team executes:**
```bash
gh pr merge <PR_NUMBER> --merge
```

**Verification:** The agent-team verifies the PR is merged.

### 4h. Transition JIRA to DONE (User / PO Confirmed)

This is the final ticket closure step. After user/PO confirmation, the agent-team executes the final transition to DONE.

> **⚠️ Requires explicit final User / Product-Owner confirmation before execution — in BOTH interactive and automated workflow modes.**
> The agent-team MUST NOT call `atlassian_transitionJiraIssue` without explicit
> user/PO confirmation. JIRA transition is destructive and irreversible.
>
> **Interactive mode:** Pause and present the confirmation prompt to the user/PO. Execute only after receiving explicit confirmation.
>
> **Automated mode:** Even though no human is expected to intervene, the agent-team MUST pause, present the confirmation prompt, and wait for an explicit confirmation signal before executing. Automated mode never auto-executes destructive actions.

**What the agent-team DOES:**
1. Verify the PR is merged (Step 4g verification).
2. Execute the final transition:
   ```bash
   atlassian_transitionJiraIssue(issueIdOrKey="PRO-XXX", transition={"id": "31"})
   ```

**What the user / Product-Owner confirms:**
- Ready to transition JIRA to DONE
- All work has been implemented and verified
- Confident in final JIRA closure

**After confirmation, the agent-team executes:**
```bash
atlassian_transitionJiraIssue(issueIdOrKey="PRO-XXX", transition={"id": "31"})
```

**Verification:** The agent-team verifies the JIRA ticket is in "Fertig"
status and the PR is merged.

### 4i. Delete Remote Branch (User / PO Confirmed)

After the PR is merged, the remote feature branch should be deleted to keep the
repository clean. This is a **user / Product-Owner responsibility** — the
agent-team prepares the command but does not execute it.

> **⚠️ Requires explicit final User / Product-Owner confirmation before execution — in BOTH interactive and automated workflow modes.**
> The agent-team MUST NOT run `git push origin --delete` without explicit
> user/PO confirmation. Remote branch deletion is destructive and cannot be
> undone without recreating the branch.
>
> **Interactive mode:** Pause and present the confirmation prompt to the user/PO. Execute only after receiving explicit confirmation.
>
> **Automated mode:** Even though no human is expected to intervene, the agent-team MUST pause, present the confirmation prompt, and wait for an explicit confirmation signal before executing. Automated mode never auto-executes destructive actions.

**What the agent-team DOES:**
1. Confirm the PR is merged to `master` (Step 4g verification).
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

## Step 5 — Closure Sequence (User / PO Confirmed)

The closure sequence is executed in the following order. Each step requires
explicit final User / Product-Owner confirmation in BOTH interactive and
automated workflow modes. The agent-team prepares each command and pauses for
confirmation; it never auto-executes destructive actions.

| Order | Step | Section | Command |
|-------|------|---------|---------|
| 1 | Delete implementation plan | §4e | `git rm doc/02_Implementation_Plan_PRO-XXX.md` + commit + push |
| 2 | Post JIRA final summary comment | §4a | `atlassian_addCommentToJiraIssue(issueIdOrKey="PRO-XXX", commentBody="...")` |
| 3 | Merge PR | §4g | `gh pr merge <PR_NUMBER> --merge` |
| 4 | Transition JIRA to DONE | §4h | `atlassian_transitionJiraIssue(issueIdOrKey="PRO-XXX", transition={"id": "31"})` |
| 5 | Delete remote branch | §4i | `git push origin --delete <branch-name>` |

**Rationale for this order:**
1. The implementation plan is a working document that is finalised and marked
   Complete before any destructive action. Deleting it first removes the
   dependency on the plan and lets the merge commit stand on its own.
2. The JIRA final summary comment is posted before the merge so the ticket
   has a permanent closure record that includes the PR number, test results,
   and AC status. This comment is the authoritative summary for stakeholders
   and must exist before the ticket transitions to Fertig.
3. The PR is merged to `master` so the work is preserved in the mainline before
   the feature branch is removed.
4. The JIRA ticket is transitioned to Fertig once the PR is merged, the
   summary comment is posted, and all checks are verified.
5. The remote feature branch is deleted last, after everything else is done, so
   the branch remains available until the final step is confirmed.

**Note:** `gh pr edit` updates only the PR description; it does not merge the PR.
The PR body must contain the four mandatory sections (Summary, Acceptance
Criteria, Definition of Done, Testing) and the `Refs: PRO-XXX` footer.

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
| Run CI self-tests | `python -m pytest tests/ci-pipeline/ -q` |
| Run lint | `ruff check src_timesheetalgo tests .github` |
| Check traceability | `python .github/scripts/generate_traceability_matrix.py` |
| Add JIRA comment | `atlassian_addCommentToJiraIssue(issueIdOrKey="PRO-XXX", commentBody="...")` |
| Get JIRA issue | `atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["*all"])` |
| Search JIRA stories | `atlassian_searchJiraIssuesUsingJql(jql="project = PRO AND issuetype = Story ORDER BY created DESC", maxResults=20)` |
| Assign story points | `atlassian_editJiraIssue(issueIdOrKey="PRO-XXX", fields={"customfield_10028": N})` |
| Update JIRA description | `atlassian_editJiraIssue(issueIdOrKey="PRO-XXX", fields={"description": "..."})` |
| Close JIRA ticket | `atlassian_transitionJiraIssue(issueIdOrKey="PRO-XXX", transition={"id": "31"})` |
| Update PR description | `gh pr edit <N> --body-file /tmp/opencode/pr_body.md` |
| Stage all | `git add -A` |
| Commit | `git commit -m "docs(ci): finalise PRO-XXX...\n\nRefs: PRO-XXX"` |
| Push | `git push origin <branch>` |
| Delete implementation plan | `git rm doc/02_Implementation_Plan_PRO-XXX.md` — **User/PO confirms and executes** (via Step 4, order 1) |
| Merge PR | `gh pr merge <PR_NUMBER> --merge` — **User/PO confirms and executes** (via Step 4, order 2) |
| Transition JIRA | `atlassian_transitionJiraIssue(issueIdOrKey="PRO-XXX", transition={"id": "31"})` — **User/PO confirms and executes** (via Step 4, order 3) |
| Delete remote branch | `git push origin --delete <branch-name>` — **User/PO confirms and executes** (via Step 4, order 4) |

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

## Related Documents

- `AGENTS.md` — Top-level guide: project conventions, modes, CI gates
- `.opencode/docs/WORKFLOW.md` — Agent team workflow, diagrams, quality gates, handoff labels
- `doc/CONTRIBUTING.md` — Development standards
- `doc/TESTING.md` — Test structure, test markers, test organization
- `doc/ARCHITECTURE.md` — System architecture and design decisions
- `.opencode/skills/complete-feature/` — This skill
- `.opencode/skills/discover-feature/SKILL.md` — Feature discovery and ticket creation
- `.opencode/skills/refine-feature/SKILL.md` — Stakeholder review and finalization
- `.opencode/skills/develop-feature/SKILL.md` — Workflow for developing a feature
