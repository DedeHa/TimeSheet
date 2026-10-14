# Perform Retrospective Skill

Reusable retrospective workflow for TimeSheetAlgo. Orchestrated by the Product Owner in cooperation with the agent dev team (Architect, Developer, Tester).

## Prerequisites

- Working directory: `/workspaces/TimeSheet` (repository root)
- Virtual environment activated: `source /workspaces/TimeSheet/.venv/bin/activate`
- `gh` authenticated and `git` configured
- Atlassian MCP tools available (Jira, Confluence)
- Agent team available: Architect, Developer, Tester

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

## Step 1 — Gather Agent Feedback

Dispatch parallel feedback requests to all three agent team members:

### 1a. Architect Feedback
Prompt: Review the feature lifecycle and provide feedback on architectural/design issues in the closure process, what the Architect should have caught before handoff, root causes of incomplete closure, and recommendations for preventing this in future features.

### 1b. Developer Feedback
Prompt: Review the feature lifecycle and provide feedback on development/process issues in the closure workflow, what the Developer should have verified before handoff, root causes of the incomplete closure, and recommendations for improving the development workflow.

### 1c. Tester Feedback
Prompt: Review the feature lifecycle and provide feedback on testing/validation gaps in the closure process, what the Tester should have caught during verification, root causes of the complete-feature skill bypass, and recommendations for strengthening validation gates.

## Step 2 — Synthesize Findings

Consolidate feedback from all three agents into the following structured format:

### 2a. Identified Issues
Table with columns: #, Issue, Severity, Source

### 2b. Agent Feedback Summary
Table with columns: Agent, Key Feedback

### 2c. Root Causes
Table with columns: #, Root Cause, Impact

### 2d. Resolutions
Table with columns: #, Resolution, Priority, Owner

## Step 3 — Document on Confluence

1. Read the existing retrospective page:
   ```
   atlassian_getConfluencePage(cloudId="...", pageId="393223")
   ```
2. Update the page with the synthesized retrospective content using `atlassian_updateConfluencePage`.
3. Include all sections from Step 2 plus:
   - Executive Summary
   - Action Items (with owner and timeline)
   - Recommendation for ticket consolidation

## Step 4 — Consolidate into Consolidated Tickets

### 4a. Analyze Overhead
Count the number of unique resolutions and estimate the overhead of creating separate tickets:
- Story point estimations
- Stakeholder reviews
- Implementation plans
- Closure cycles

### 4b. Apply Consolidation Strategy
Group resolutions by ownership and priority:

| Group | Criteria | Ticket Type |
|-------|----------|-------------|
| Enforcement + Validation | Same owner (PO + Developer), P0 | Single Task |
| Infrastructure + Monitoring | Same owner (PO + Architect), P0/P1 | Single Task |
| All resolutions | Cross-cutting coordination | Single Epic |

**Target:** Reduce N tickets to 2 Tasks + 1 Epic (75% overhead reduction).

### 4c. Document Recommendation
Add a "Ticket Consolidation Recommendation" section to the Confluence page with:
- Recommended ticket structure
- Scope breakdown per ticket
- Overhead reduction metrics
- Traceability guidelines

## Step 5 — Create Consolidated Tickets (User/PO Confirmed)

> Requires explicit final User / Product-Owner confirmation before execution.

### 5a. Create Epic
```bash
atlassian_createJiraIssue(
    projectKey="PRO",
    issueTypeName="Epic",
    summary="Closure Process Hardening",
    ...
)
```

### 5b. Create Tasks
```bash
atlassian_createJiraIssue(
    projectKey="PRO",
    issueTypeName="Task",
    summary="Enforce complete-feature as mandatory closure gate",
    ...
)
```

### 5c. Link Tasks to Epic
Use Epic Link (`customfield_10014`) to associate each task with the parent epic.

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

## Related Documents
- AGENTS.md — Top-level guide
- .opencode/docs/WORKFLOW.md — Agent team workflow
- doc/CONTRIBUTING.md — Development standards
- .opencode/skills/complete-feature/ — Feature completion workflow
- .opencode/skills/discover-feature/ — Feature discovery
- .opencode/skills/refine-feature/ — Stakeholder review
- .opencode/skills/develop-feature/ — Feature development
- .opencode/skills/orchestrate-feature/ — Pipeline orchestration
