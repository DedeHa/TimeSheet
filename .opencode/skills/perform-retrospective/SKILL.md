---
name: perform-retrospective
description: "Use when conducting a feature retrospective or post-mortem with the agent dev team. Orchestrated by the Product Owner in cooperation with Architect, Developer, and Tester. Triggers on requests to 'retrospective', 'post-mortem', 'review the feature', 'what went wrong', 'lessons learned', or any workflow that begins with a completed feature and ends with consolidated JIRA tickets for process improvements. NOTE: The agent-team prepares the retrospective; ticket creation requires explicit final user/PO confirmation in BOTH interactive and automated workflow modes."
---

# Perform Retrospective Skill

Reusable retrospective workflow for TimeSheetAlgo. Orchestrated by the Product
Owner in cooperation with the agent dev team (Architect, Developer, Tester).

## Prerequisites

- Working directory: `/workspaces/TimeSheet` (repository root)
- Virtual environment activated: `source /workspaces/TimeSheet/.venv/bin/activate`
- `gh` authenticated and `git` configured
- Atlassian MCP tools available (Jira, Confluence)
- Agent team available: Architect, Developer, Tester

---

## Step 1 — Determine Current State

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

---

## Step 2 — Gather Agent Feedback

Dispatch parallel feedback requests to all three agent team members.

### Architect

Review the feature lifecycle and provide feedback on:
- Architectural/design issues in the closure process
- What the Architect should have caught before handoff
- Root causes of incomplete closure
- Recommendations for preventing this in future features

### Developer

Review the feature lifecycle and provide feedback on:
- Development/process issues in the closure workflow
- What the Developer should have verified before handoff
- Root causes of the incomplete closure
- Recommendations for improving the development workflow

### Tester

Review the feature lifecycle and provide feedback on:
- Testing/validation gaps in the closure process
- What the Tester should have caught during verification
- Root causes of the complete-feature skill bypass
- Recommendations for strengthening validation gates

---

## Step 3 — Synthesize Findings

Consolidate feedback from all three agents into the following structured
format:

### Identified Issues

Table with columns: #, Issue, Severity, Source

### Agent Feedback Summary

Table with columns: Agent, Key Feedback

### Root Causes

Table with columns: #, Root Cause, Impact

### Resolutions

Table with columns: #, Resolution, Priority, Owner

---

## Step 4 — Document on Confluence

1. Read the existing retrospective page:
   ```
   atlassian_getConfluencePage(cloudId="<cloudId>", pageId="<pageId>")
   ```
2. Update the page with the synthesized retrospective content using
   `atlassian_updateConfluencePage`.
3. Include all sections from Step 3 plus:
   - Executive Summary
   - Action Items (with owner and timeline)
   - Recommendation for ticket consolidation

---

## Step 5 — Consolidate into Consolidated Tickets

### Analyze Overhead

Count the number of unique resolutions and estimate the overhead of creating
separate tickets:
- Story point estimations
- Stakeholder reviews
- Implementation plans
- Closure cycles

### Apply Consolidation Strategy

Group resolutions by ownership and priority:

| Group | Criteria | Ticket Type |
|-------|----------|-------------|
| Enforcement + Validation | Same owner (PO + Developer), P0 | Single Task |
| Infrastructure + Monitoring | Same owner (PO + Architect), P0/P1 | Single Task |
| All resolutions | Cross-cutting coordination | Single Epic |

**Target:** Reduce N tickets to 2 Tasks + 1 Epic (75% overhead reduction).

### Document Recommendation

Add a "Ticket Consolidation Recommendation" section to the Confluence page
with:
- Recommended ticket structure
- Scope breakdown per ticket
- Overhead reduction metrics
- Traceability guidelines

---

## Step 6 — Create Consolidated Tickets (User/PO Confirmed)

> Requires explicit final User / Product-Owner confirmation before execution.

### Create Epic

```bash
atlassian_createJiraIssue(
    projectKey="PRO",
    issueTypeName="Epic",
    summary="Closure Process Hardening",
    ...
)
```

### Create Tasks

```bash
atlassian_createJiraIssue(
    projectKey="PRO",
    issueTypeName="Task",
    summary="Enforce complete-feature as mandatory closure gate",
    ...
)
```

### Link Tasks to Epic

Use Epic Link (`customfield_10014`) to associate each task with the parent
epic.

---

## Cycle Tracking and Escalation

This skill is invoked by the Product Owner. Each invocation is a cycle.

### Cycle Limits

- Max cycles per dispatch: 3
- If cycle = 1, 2: Continue verification
- If cycle = 3: Stop, prepare handoff to Product Owner with summary
- If cycle > 3: STOP — escalate immediately

### When to Escalate

Escalate to Product Owner when:
1. Agent feedback is inconsistent or conflicting
2. Confluence page update fails
3. Ticket creation fails
4. Process loops — repeated failures without progress

---

## Related Documents

- AGENTS.md — Top-level guide
- .opencode/docs/WORKFLOW.md — Agent team workflow
- doc/CONTRIBUTING.md — Development standards
- .opencode/skills/complete-feature/ — Feature completion workflow
- .opencode/skills/discover-feature/ — Feature discovery
- .opencode/skills/refine-feature/ — Stakeholder review
- .opencode/skills/develop-feature/ — Feature development
- .opencode/skills/orchestrate-feature/ — Pipeline orchestration
