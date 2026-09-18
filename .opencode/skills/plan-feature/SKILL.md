---
name: plan-feature
description: "Use when discovering, planning, or scoping new features — creating JIRA Story tickets, estimating story points, defining acceptance criteria, writing implementation plans, or refining the backlog. Triggers on requests to 'create a new ticket', 'plan a feature', 'estimate effort', 'define AC', 'discovery session', or any product planning workflow. NOTE: If there is an active sprint, the user/PO must actively review and confirm sprint inclusion before the ticket is created or updated. The agent-team prepares closure; after user / PO confirmation, the agent-team executes `atlassian_transitionJiraIssue` and `gh pr merge`. Story points must be estimated before sprint inclusion or development pickup."
---

# Product Discovery & Planning

This skill covers the end-to-end workflow for discovering, scoping, and documenting new features as JIRA Story tickets. Based on analysis of the most recent 6 Story tickets in the **PRO** project: **PRO-370**, **PRO-369**, **PRO-368**, **PRO-367**, **PRO-366**, **PRO-365**.

**Triggered by:** User requests feature planning after completing the PO intake conversation. The user explicitly asks the PO to plan the feature (e.g., "start feature PRO-XXX", "plan a feature", "create a ticket").

---

## Ticket Fields (Standard Across PRO Project)

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

## Prerequisites

- **Intake conversation completed:** The Product Owner has held an intake
  conversation with the user to establish the goal, use-case, and information
  (see `product-owner.agent.md` §"Initial Intake — User ↔ PO Conversation").
- Working directory: `/workspaces/TimeSheet` (repository root)
- Virtual environment activated: `source /workspaces/TimeSheet/.venv/bin/activate`
- `gh` authenticated and `git` configured
- Atlassian MCP tools available (Jira)

## Sprint Inclusion Check

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

### 7. Multi-stakeholder review (developer, architect, tester)

After the PO defines the feature, conduct a **multi-stakeholder review** with
the developer, architect, and tester **before** the ticket is finalized.
This minimizes risk for architecture, implementation, and verification.

**Developer review:** Verify implementation feasibility, effort estimate,
and technical approach. Confirm the implementation plan is realistic.

**Architect review:** Verify architectural alignment, component boundaries,
and integration points. Confirm the feature fits the system architecture.

**Tester review:** Verify testability of ACs, DoD completeness, and
coverage strategy. Confirm each AC can be objectively verified.

Each reviewer confirms or raises concerns. If any reviewer raises a concern,
the PO updates the feature definition before proceeding.

### 8. Common stakeholder review

After individual reviews pass, hold a **common review with all stakeholders**
(PO, developer, architect, tester) to finalize the feature definition.
Confirm:

- Intention / use-case is clearly defined
- Goal is measurable and aligned with business value
- Steps are ordered and achievable within the sprint
- Information (background, data sources, constraints) is complete
- DoD is realistic and verifiable
- ACs are testable and binary (done / not done)
- Story points are estimated and assigned

**Gate:** Do not finalize the ticket without explicit confirmation from
all stakeholders.

---

## Summary (Title)

- **Format:** Concise, action-oriented, max 1 line
- **Pattern:** `[Verb] [Target] [Context/Qualification]`
- **Examples from analysis:**
  - `Fix GitHub release signing to show "This commit was created on GitHub.com and signed with GitHub's verified signature"`
  - `Implement Continuous CI Timing Measurement and Historical Aggregation`
  - `Optimize Python CI Workflow Performance and Maintainability`
  - `US-05 · Monitoring & Logging` (with User-Story identifier)

---

## Description (Intention / Use-Case Based Structure)

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

## Patterns Observed Across PRO-370, PRO-369, PRO-368, PRO-367, PRO-366, PRO-365

| Pattern | Frequency | When to Use |
|---------|-----------|-------------|
| `**As a** / **I want** / **so that**` story block | 3/6 (large features) | When the change delivers user-visible value |
| Problem → Evaluation Data → Solution | 2/6 (bugfixes / small fixes) | When fixing an observed issue |
| **Background** section | 4/6 | Always recommended for context |
| **Scope** with In/Out of Scope | 2/6 | For features > 5 points |
| Numbered **Acceptance Criteria** | 6/6 | Always required |
| **Definition of Done** checklist | 6/6 | Always required |
| **Story Points** field | 4/6 (assigned at planning) | Assign at planning, document in description |
| **Multi-stakeholder review** | 0/6 (new) | Developer, architect, tester review before finalization |
| **Common stakeholder review** | 0/6 (new) | PO, developer, architect, tester review before finalization |
| **References** / `Refs:` | 6/6 | Always include |
| German / English mix | 5/6 (German for narrative, English for tech) | Match existing project style |
| **MoSCoW** priority tag | 2/6 (US-0X tickets) | For product roadmap items |

---

## Story Points Reference (Fibonacci Scale)

| Points | Workload | Examples in PRO Project |
|--------|----------|-------------------------|
| 1 | Trivial fix | — |
| 2 | Minor doc or small fix | PRO-342 (Update docs, integration strategy and ci/cd-pipeline) |
| 3 | Small feature, 1 file change, basic tests | PRO-370 (GPG signing fix) |
| 5 | Moderate feature, multi-file, integration tests | PRO-368 (CI workflow optimization), PRO-369 (CI timing benchmark) |
| 8 | Large feature with comprehensive tests | PRO-340 (Documentation traceability) |
| 13 | Major refactor | PRO-339 (Unit-testability refactor) |
| 21+ | Epic-scale work | PRO-341 (AI-Driven Development Workflow) |

**Note:** Story points are estimated during planning and assigned to `customfield_10028` before the ticket enters the active sprint. Do not leave story points blank when a ticket is picked up for development.

---

## Quick-Start Checklist

When creating a new Story ticket:

- [ ] Intention / use-case defined (As a / I want / so that)
- [ ] Goal is measurable and aligned with business value
- [ ] Steps are ordered and achievable within the sprint
- [ ] Information (background, data sources, constraints) is complete
- [ ] **Architecture reviewed** by architect — alignment confirmed
- [ ] **Implementation reviewed** by developer — feasibility confirmed
- [ ] **Verification reviewed** by tester — testability confirmed
- [ ] **Common stakeholder review** completed (PO, developer, architect, tester)
- [ ] Acceptance Criteria are numbered (AC-1, AC-2, ...) and testable
- [ ] Definition of Done is a `- [ ]` checklist
- [ ] **Priority** set to Medium (or High for release-critical)
- [ ] **Epic Link** set to parent epic (e.g. `PRO-259`)
- [ ] **Fix Version** set to target release (e.g. `v4.3.0`)
- [ ] **Sprint / Backlog** placement decided (user/PO confirms: sprint or backlog)
- [ ] Assignee set (or confirmed unassigned)
- [ ] Story Points assigned before sprint inclusion or development pickup
- [ ] References / `Refs: PRO-XXX` footer present

---

## Related Documents

- `AGENTS.md` — Top-level guide: project conventions, modes, CI gates
- `doc/AGENTS_WORKFLOW.md` — Agent team workflow, diagrams, quality gates, handoff labels
- `doc/CONTRIBUTING.md` — Development standards
- `doc/REQUIREMENTS.md` — FR / QR requirement IDs
- `doc/ARCHITECTURE.md` — System architecture and design decisions
- `.opencode/skills/plan-feature/` — This skill
- `.opencode/skills/complete-feature/SKILL.md` — Workflow for closing a ticket
- `.opencode/skills/develop-feature/SKILL.md` — Workflow for developing a feature
