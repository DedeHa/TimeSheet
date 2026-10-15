---
name: discover-feature
description: "Use when discovering new features and bug tickets and creating initial JIRA Story/Bug tickets — drafting the ticket (intention/use-case, goal, steps/implementation plan, information, testing strategy, acceptance criteria, definition of done, story points) and deciding sprint placement. Triggers on requests to 'create a new ticket', 'plan a feature', 'fix a bug', 'estimate effort', 'discovery session', or any product discovery workflow. NOTE: If there is an active sprint, the user/PO must actively review and confirm sprint inclusion before the ticket is created or updated. Story points must be estimated before sprint inclusion or development pickup."
---

# Product Discovery & Bug Fix Planning

This skill covers the workflow for discovering and documenting new features as well as bug fixes in JIRA Story and Bug tickets. Based on analysis of the most recent 10 tickets in the **PRO** project: **PRO-385**, **PRO-383**, **PRO-381**, **PRO-378**, **PRO-373**, **PRO-344**, **PRO-338**, **PRO-334**, **PRO-334**, **PRO-263**.

**Triggered by:** User requests feature planning or bug fix planning after completing the PO intake conversation. The user explicitly asks the PO to plan the feature or fix the bug (e.g., "start feature PRO-XXX", "plan a feature", "fix bug PRO-XXX", "create a ticket").

**Next step:** Once the ticket is drafted, the PO runs `refine-feature` to conduct the multi-stakeholder review and finalize the ticket before development begins.

---

## Ticket Fields (Standard Across PRO Project)

### Story Ticket Fields

| Field | Value / Notes |
|-------|---------------|
| **Project** | `PRO` (key) — PROJECTS |
| **Issue Type** | `Story` (id 10003) |
| **Reporter** | Current user |
| **Priority** | `Medium` (default), or `High` if critical for release integrity |
| **Epic Link** | `customfield_10014` — link to parent Epic (e.g. `PRO-259` for TimeSheet, `PRO-356` for Home-Server, `PRO-344` for AI-Assistant) |
| **Sprint** | `customfield_10020` — set to current active sprint only after user/PO confirms sprint inclusion; otherwise leave unset for backlog |
| **Assignee** | Set to developer only after user/PO confirms who should work on it; otherwise leave unassigned |
| **Fix Versions** | Target release version (e.g. `v4.3.0`) — must exist in project |
| **Story Points** | `customfield_10028` — Fibonacci (1, 2, 3, 5, 8, 13) — **must be estimated before sprint inclusion or development pickup** |
| **Labels** | (Optional) category tags, e.g. `KI-Agent`, `Track-A`, `Phase-5` |
| **Components** | (Optional) `TimeSheet`, `Home-AssistantConfig` |

### Bug Ticket Fields

| Field | Value / Notes |
|-------|---------------|
| **Project** | `PRO` (key) — PROJECTS |
| **Issue Type** | `Bug` (id 10004) |
| **Reporter** | Current user |
| **Priority** | `High` (default for bugs — bugs are release-integrity critical) or `Medium` for minor cosmetic issues |
| **Epic Link** | `customfield_10014` — link to parent Epic (e.g. `PRO-259` for TimeSheet, `PRO-356` for Home-Server, `PRO-344` for AI-Assistant) |
| **Sprint** | `customfield_10020` — set to current active sprint only after user/PO confirms sprint inclusion; otherwise leave unset for backlog |
| **Assignee** | Set to developer only after user/PO confirms who should work on it; otherwise leave unassigned |
| **Fix Versions** | Target release version (e.g. `v4.3.0`) — must exist in project |
| **Story Points** | `customfield_10028` — Fibonacci (1, 2, 3, 5, 8, 13) — **must be estimated before sprint inclusion or development pickup** |
| **Labels** | (Optional) category tags, e.g. `bug`, `regression`, `hotfix` |
| **Components** | (Optional) `TimeSheet`, `Home-AssistantConfig` |
| **Bug Type** | `customfield_10064` — e.g. `Bug`, `Defect`, `Regression`, `Enhancement` |
| **Environment** | `customfield_10065` — e.g. `Production`, `Development`, `CI` |
| **Steps to Reproduce** | Ordered list of actions that trigger the bug |
| **Expected Behavior** | What should happen |
| **Actual Behavior** | What actually happens (observed) |

## Prerequisites

- **Intake conversation completed:** The Product Owner has held an intake
  conversation with the user to establish the goal, use-case, and information
  (see `product-owner.agent.md` §"Initial Intake — User ↔ PO Conversation").
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

## Step 1 — Sprint Inclusion Check

When a feature is planned, this does **not** directly trigger development.
The user / Product-Owner must be actively asked and the feature summary
reviewed before any ticket is created or updated and before development
begins. This ensures the feature is intentionally prioritized.

### 1. Determine sprint context

Check if there is an active sprint in the JIRA project (e.g., `TIME Sprint 33`
or `v4.3.0`). If no active sprint exists, the ticket goes to the backlog
and the user/PO decides when to pull it in.

### 2. Present the feature summary to the user / Product-Owner

Show the planned ticket content (Summary, Problem Statement, Scope,
Acceptance Criteria, Definition of Done, Story Points) for review.

### 3. Ask three questions explicitly

The user/PO must answer **all three**:

| # | Question | Options |
|---|----------|---------|
| 1 | **Keep in sprint or backlog?** | Sprint — include in current active sprint; Backlog — add to backlog for future sprint planning |
| 2 | **Start development now?** | Yes — development team begins work immediately; No — wait for sprint planning / future prioritization |
| 3 | **Assign to developer?** | Specific developer name, or "unassigned — team decides at sprint planning" |

### 4. Update ticket fields based on user/PO decisions

- **Priority** (`priority`): Set to Medium (default) or High if release-critical
- **Epic Link** (`customfield_10014`): Link to parent Epic (e.g. `PRO-259`)
- **Sprint** (`customfield_10020`): Set to active sprint if "sprint", leave unset if "backlog"
- **Assignee**: Set if developer assigned, leave unassigned otherwise
- **Fix Version** (`fixVersions`): Target release version (e.g. `v4.3.0`)
- **Status**: Keep at "Zu erledigen" — development starts only when dev begins Phase 1 of develop-feature skill

### 5. Review the intended feature ticket setup

Before finalizing the ticket, walk through the complete ticket together:

- Summary matches the feature description
- Acceptance criteria are testable and complete
- Definition of Done is realistic
- **Story points are estimated and assigned (`customfield_10028`)** — required before sprint inclusion or development pickup
- Epic link is correct
- Fix version is set
- Sprint / backlog decision is recorded
- Non-goals are documented (if scope is non-trivial)

---

## Step 2 — Draft the Ticket Summary & Description

- **Format:** Concise, action-oriented, max 1 line
- **Pattern:** `[Verb] [Target] [Context/Qualification]`
- **Examples from analysis:**
  - `Fix GitHub release signing to show "This commit was created on GitHub.com and signed with GitHub's verified signature"`
  - `Implement Continuous CI Timing Measurement and Historical Aggregation`
  - `Optimize Python CI Workflow Performance and Maintainability`
  - `US-05 · Monitoring & Logging` (with User-Story identifier)

---

## Step 3 — Draft the Ticket Description (Intention / Use-Case Based Structure)

Use the following structure (in this order). The whole plan is based on
a single **intention / use-case** that defines the goal, steps,
information, DoD, ACs, and story point estimation:

### 1. **Intention / Use-Case** *(required)*
A concise use-case statement: `As a [role], I want to [action] so that [benefit].`
This defines the common understanding of what the feature delivers.

### 2. **Goal** *(required)*
What does success look like? Quantifiable outcomes if possible.
The goal is derived directly from the use-case.

### 3. **Steps / Implementation Plan**
Ordered steps to achieve the goal:
- High-level approach or phases
- Key files to be changed
- Reference to architecture decisions

### 4. **Information** *(optional but recommended)*
- Why does this work need to happen now?
- Reference prior tickets with `PRO-XXX`
- Cite current state / observed issues
- Data sources, constraints, dependencies

### 5. **Testing Strategy**
- **Unit Tests** — what they cover
- **Integration Tests** — what they cover
- **System Tests** — what they cover (if applicable)

### 6. **Acceptance Criteria** *(required, AC-1 to AC-N)*
Format: `- [ ] AC-N: Description — implementation detail`

- Numbered (AC-1, AC-2, ...)
- Each AC is testable and binary (done / not done)
- One sentence per AC

### 7. **Definition of Done** *(required)*
Format: `- [ ] Item — description`

Common items:
- PR #NNN merged to master
- JIRA ticket closed (Fertig)
- All ACs checkmarked
- Story Points assigned
- Traceability: FR-XX, QR-XX added to docs
- CI self-tests pass

### 8. **Priority / Story Points**
- `**Priority:** [High|Medium|Low] — rationale`
- `**Story Points:** [N] (comparable to PRO-XXX = N points)` — **estimated and assigned at planning time** (required before sprint inclusion or development pickup)

### 9. **Non-Goals / Out of Scope** *(optional but recommended)*
- What is explicitly NOT part of this work
- Helps prevent scope creep

### 10. **References** *(recommended)*
- `Refs: PRO-XXX` (parent / related tickets)
- Links to related PRs

---

## Sample Description (Use as Starting Point)

```markdown
**Intention / Use-Case:** As a [role], I want to [action] so that [benefit].

## Goal

[What does success look like? Quantifiable outcomes if possible.]

## Steps / Implementation Plan

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Information

[Why this work needs to happen now. Reference prior PRO-XXX tickets.
Data sources, constraints, dependencies.]

## Testing Strategy

1. **Unit Tests:**

    * [Test scope 1]
    * [Test scope 2]

2. **Integration Tests:**

    * [Test scope 1]

3. **System Tests:**

    * [Test scope 1]

## Acceptance Criteria

- [ ] AC-1: [Testable condition] — implementation detail
- [ ] AC-2: [Testable condition] — implementation detail
- [ ] AC-3: [Testable condition] — implementation detail
- [ ] AC-4: [Testable condition] — implementation detail
- [ ] AC-5: [Testable condition] — implementation detail

## Definition of Done

- [ ] PR #NNN merged to master
- [ ] JIRA ticket closed (Fertig)
- [ ] All ACs checkmarked
- [ ] Story Points: N assigned
- [ ] Traceability: FR-XX, QR-XX added to doc/REQUIREMENTS.md, doc/ARCHITECTURE.md
- [ ] CI self-tests: N tests passed

## Priority / Story Points

**Priority:** [High|Medium|Low] — [rationale]

**Story Points:** [N] (estimated at planning, required before sprint inclusion or development pickup)

## Non-Goals / Out of Scope

* [Explicitly excluded item 1]
* [Explicitly excluded item 2]

## References

* [PRO-XXX](https://mainhatten.atlassian.net/browse/PRO-XXX): [Title]
* [.github/workflows/...](link): [context]
```

---

## Step 4 — Bug Ticket Discovery

Bug tickets follow a distinct discovery workflow focused on **observed problems** rather than planned features. The discovery process mirrors the story workflow but adapts the description structure to emphasize reproduction, root cause, and verification.

### Bug Summary (Title)

- **Format:** Concise, problem-oriented, max 1 line
- **Pattern:** `[Problem Area] — [Observed Issue]`
- **Examples from analysis:**
  - `CI Timing Pipeline: Latest successful PR runs not captured in storage`
  - `Pipeline Integrity: JIRA ticket can be closed before PR is merged`
  - `Simplify and resolve Config-File Loading`
  - `Resolve remaining failed testcases`

### Bug Description (Problem-Based Structure)

Use the following structure for bug tickets (in this order):

#### 1. **Problem Statement** *(required)*
A clear description of the observed bug: what went wrong, when, and under what conditions.
Use the pattern: `When [action/condition], [unexpected result] occurs.`

#### 2. **Steps to Reproduce** *(required)*
Ordered list of actions that consistently trigger the bug:
1. [Step 1]
2. [Step 2]
3. [Step 3]

#### 3. **Expected Behavior** *(required)*
What should happen when the steps are followed correctly.

#### 4. **Actual Behavior** *(required)*
What actually happens (observed). Include error messages, logs, or screenshots if available.

#### 5. **Root Cause Analysis** *(recommended)*
- What caused the bug? (code change, configuration, dependency update, race condition)
- Reference the commit or change that introduced the issue
- Evidence from logs, debug output, or investigation

#### 6. **Information** *(optional but recommended)*
- Why does this fix need to happen now?
- Reference prior tickets with `PRO-XXX`
- Severity assessment (blocker, critical, major, minor, trivial)
- Environment affected (Production, Development, CI)
- Data sources, constraints, dependencies

#### 7. **Fix / Implementation Plan**
- Steps to resolve the bug
- Key files to be changed
- Reference to architecture decisions
- Whether the fix is a hotfix or included in next release

#### 8. **Testing Strategy**
- **Unit Tests** — regression test that reproduces the bug and verifies the fix
- **Integration Tests** — verify the fix doesn't break related functionality
- **System Tests** — end-to-end verification (if applicable)

#### 9. **Acceptance Criteria** *(required, AC-1 to AC-N)*
Format: `- [ ] AC-N: Description — implementation detail`

- Numbered (AC-1, AC-2, ...)
- Each AC is testable and binary (done / not done)
- AC-1 is always: "Bug does not reproduce after fix"
- Remaining ACs cover edge cases and regression prevention

#### 10. **Definition of Done** *(required)*
Format: `- [ ] Item — description`

Common items:
- PR #NNN merged to master
- JIRA ticket closed (Fertig)
- Bug does not reproduce (AC-1 checkmarked)
- Regression test added
- Story Points assigned
- Traceability: FR-XX, QR-XX added to docs
- CI self-tests pass

#### 11. **Priority / Story Points**
- `**Priority:** [High|Medium] — rationale` (Bugs default to High)
- `**Story Points:** [N] (comparable to PRO-XXX = N points)` — **estimated and assigned at planning time** (required before sprint inclusion or development pickup)

#### 12. **Non-Goals / Out of Scope** *(optional but recommended)*
- What is explicitly NOT part of this fix
- Known related issues that are not addressed

#### 13. **References** *(recommended)*
- `Refs: PRO-XXX` (parent / related tickets)
- Links to related PRs
- Reference the commit that introduced the bug

---

## Sample Bug Description (Use as Starting Point)

```markdown
**Problem Statement:** When [action/condition], [unexpected result] occurs.

## Steps to Reproduce

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Expected Behavior

[What should happen correctly.]

## Actual Behavior

[What actually happens. Include error messages or logs.]

## Root Cause Analysis

[What caused the bug. Reference commit, dependency, or configuration change.]

## Information

[Why this fix needs to happen now. Severity: blocker/critical/major/minor/trivial.
Environment affected. Reference prior PRO-XXX tickets.]

## Fix / Implementation Plan

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Testing Strategy

1. **Unit Tests:**

     * [Regression test that reproduces the bug]
     * [Edge case verification]

2. **Integration Tests:**

     * [Verify fix doesn't break related functionality]

3. **System Tests:**

     * [End-to-end verification]

## Acceptance Criteria

- [ ] AC-1: Bug does not reproduce after fix
- [ ] AC-2: [Edge case covered] — implementation detail
- [ ] AC-3: [Regression test passes] — implementation detail
- [ ] AC-4: [No side effects] — implementation detail

## Definition of Done

- [ ] PR #NNN merged to master
- [ ] JIRA ticket closed (Fertig)
- [ ] Bug does not reproduce (AC-1 checkmarked)
- [ ] Regression test added
- [ ] Story Points: N assigned
- [ ] Traceability: FR-XX, QR-XX added to doc/REQUIREMENTS.md, doc/ARCHITECTURE.md
- [ ] CI self-tests: N tests passed

## Priority / Story Points

**Priority:** High — [rationale: bug severity and impact]

**Story Points:** [N] (estimated at planning, required before sprint inclusion or development pickup)

## Non-Goals / Out of Scope

* [Explicitly excluded item 1]
* [Related issue not addressed in this fix]

## References

* [PRO-XXX](https://mainhatten.atlassian.net/browse/PRO-XXX): [Title]
* [Commit hash]: [Description of change that introduced the bug]
* [.github/workflows/...](link): [context]
```

---

## Patterns Observed Across PRO-370, PRO-369, PRO-368, PRO-367, PRO-366, PRO-365, PRO-385, PRO-383, PRO-381

| Pattern | Frequency | When to Use |
|---------|-----------|-------------|
| `**As a** / **I want** / **so that**` story block | 3/10 (large features) | When the change delivers user-visible value |
| Problem → Evaluation Data → Solution | 3/10 (bugfixes / small fixes) | When fixing an observed issue |
| **Background** section | 4/10 | Always recommended for context |
| **Scope** with In/Out of Scope | 2/10 | For features > 5 points |
| Numbered **Acceptance Criteria** | 10/10 | Always required |
| **Definition of Done** checklist | 10/10 | Always required |
| **Story Points** field | 8/10 (assigned at planning) | Assign at planning, document in description |
| **References** / `Refs:` | 10/10 | Always include |
| German / English mix | 6/10 (German for narrative, English for tech) | Match existing project style |
| **MoSCoW** priority tag | 2/10 (US-0X tickets) | For product roadmap items |
| **Non-Goals / Out of Scope** | 5/10 | Recommended for non-trivial bugs |

---

## Story Points Reference (Fibonacci Scale)

| Points | Workload | Examples in PRO Project |
|--------|----------|-------------------------|
| 1 | Trivial fix | — |
| 2 | Minor doc or small fix | PRO-342 (Update docs, integration strategy and ci/cd-pipeline) |
| 3 | Small feature, 1 file change, basic tests | PRO-370 (GPG signing fix), PRO-338 (Simplify Config-File Loading) |
| 5 | Moderate feature, multi-file, integration tests | PRO-368 (CI workflow optimization), PRO-369 (CI timing benchmark), PRO-334 (Reactivate CI/CD Chain) |
| 8 | Large feature with comprehensive tests | PRO-340 (Documentation traceability) |
| 13 | Major refactor | PRO-339 (Unit-testability refactor) |
| 21+ | Epic-scale work | PRO-341 (AI-Driven Development Workflow) |

**Bug-Specific Guidance:**
- **1 point:** Trivial typo, cosmetic, or obvious fix
- **2 points:** Minor bug, single-file change, simple regression test
- **3 points:** Small bug with clear root cause, 1-2 file changes, basic regression test
- **5 points:** Moderate bug with multi-file fix, integration tests needed
- **8 points:** Complex bug requiring architectural change, comprehensive testing
- **13+ points:** Major defect affecting multiple subsystems

**Note:** Story points are estimated during planning and assigned to `customfield_10028` before the ticket enters the active sprint. Do not leave story points blank when a ticket is picked up for development.

---

## Quick-Start Checklist

### Story Ticket Checklist

- [ ] Intention / use-case defined (As a / I want / so that)
- [ ] Goal is measurable and aligned with business value
- [ ] Steps are ordered and achievable within the sprint
- [ ] Information (background, data sources, constraints) is complete
- [ ] Acceptance Criteria are numbered (AC-1, AC-2, ...) and testable
- [ ] Definition of Done is a `- [ ]` checklist
- [ ] **Priority** set to Medium (or High for release-critical)
- [ ] **Epic Link** set to parent epic (e.g. `PRO-259`)
- [ ] **Fix Version** set to target release (e.g. `v4.3.0`)
- [ ] **Sprint / Backlog** placement decided (user/PO confirms: sprint or backlog)
- [ ] Assignee set (or confirmed unassigned)
- [ ] Story Points assigned before sprint inclusion or development pickup
- [ ] References / `Refs: PRO-XXX` footer present

### Bug Ticket Checklist

- [ ] Problem Statement defined (When [action], [unexpected result] occurs)
- [ ] Steps to Reproduce are ordered and complete
- [ ] Expected Behavior is documented
- [ ] Actual Behavior is documented (with logs/errors if available)
- [ ] Root Cause Analysis is documented (if known)
- [ ] Information (severity, environment, constraints) is complete
- [ ] Fix / Implementation Plan is ordered and achievable within the sprint
- [ ] Acceptance Criteria are numbered (AC-1 to AC-N) and testable
- [ ] AC-1 is "Bug does not reproduce after fix"
- [ ] Definition of Done is a `- [ ]` checklist
- [ ] Regression test is included in Definition of Done
- [ ] **Priority** set to High (default for bugs) or Medium for minor issues
- [ ] **Epic Link** set to parent epic (e.g. `PRO-259`)
- [ ] **Fix Version** set to target release (e.g. `v4.3.0`)
- [ ] **Sprint / Backlog** placement decided (user/PO confirms: sprint or backlog)
- [ ] Assignee set (or confirmed unassigned)
- [ ] Story Points assigned before sprint inclusion or development pickup
- [ ] References / `Refs: PRO-XXX` footer present
- [ ] Commit that introduced the bug is referenced (if known)

---

## Handoff to refine-feature

The ticket is now drafted and ready for stakeholder review.

**Gate:** Before starting `refine-feature`, present the drafted ticket to the
user / Product-Owner and ask explicitly:

> "The ticket draft is complete (Summary, ACs, DoD, story points, sprint
> placement). Proceed to stakeholder review via `refine-feature`?"

- **On "yes":** Continue to `refine-feature` (multi-stakeholder review + finalization).
- **On "no":** Return to the user for revisions to the ticket draft before
  re-presenting.

**For Bug Tickets:** The same gate applies. Ask:

> "The bug draft is complete (Problem Statement, Steps to Reproduce, ACs, DoD,
> story points, sprint placement). Proceed to stakeholder review via
> `refine-feature`?"

In **both interactive and automated modes**, pause and wait for this
confirmation before starting refinement.

---

## Related Documents

- `AGENTS.md` — Top-level guide: project conventions, modes, CI gates
- `.opencode/docs/WORKFLOW.md` — Agent team workflow, diagrams, quality gates, handoff labels
- `doc/CONTRIBUTING.md` — Development standards
- `doc/REQUIREMENTS.md` — FR / QR requirement IDs
- `doc/ARCHITECTURE.md` — System architecture and design decisions
- `.opencode/skills/discover-feature/` — This skill
- `.opencode/skills/refine-feature/` — Stakeholder review and ticket finalization
- `.opencode/skills/develop-feature/SKILL.md` — Workflow for developing a feature