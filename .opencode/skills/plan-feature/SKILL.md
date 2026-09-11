---
name: plan-feature
description: "Use when discovering, planning, or scoping new features — creating JIRA Story tickets, estimating story points, defining acceptance criteria, writing implementation plans, or refining the backlog. Triggers on requests to 'create a new ticket', 'plan a feature', 'estimate effort', 'define AC', 'discovery session', or any product planning workflow. NOTE: If there is an active sprint, the user/PO must actively review and confirm sprint inclusion before the ticket is created or updated. The agent-team prepares closure; after user / PO confirmation, the agent-team executes `atlassian_transitionJiraIssue` and `gh pr merge`."
---

# Product Discovery & Planning

This skill covers the end-to-end workflow for discovering, scoping, and documenting new features as JIRA Story tickets. Based on analysis of the most recent 6 Story tickets in the **PRO** project: **PRO-370**, **PRO-369**, **PRO-368**, **PRO-367**, **PRO-366**, **PRO-365**.

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
| **Story Points** | `customfield_10028` — Fibonacci (1, 2, 3, 5, 8, 13) |
| **Labels** | (Optional) category tags, e.g. `KI-Agent`, `Track-A`, `Phase-5` |
| **Components** | (Optional) `TimeSheet`, `Home-AssistantConfig` |

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

- **Sprint** (`customfield_10020`): Set to active sprint if "sprint", leave unset if "backlog"
- **Assignee**: Set if developer assigned, leave unassigned otherwise
- **Status**: Keep at "Zu erledigen" — development starts only when dev begins Phase 1 of develop-feature skill

### 5. Review the intended feature ticket setup

Before finalizing the ticket, walk through the complete ticket together:

- Summary matches the feature description
- Acceptance criteria are testable and complete
- Definition of Done is realistic
- Story points are estimated
- Epic link is correct
- Fix version is set
- Sprint / backlog decision is recorded
- Non-goals are documented (if scope is non-trivial)

### 6. Proceed only after explicit user/PO confirmation

The user/PO must confirm:
- All three questions above are answered
- The ticket setup is reviewed and approved
- Development should begin (if "start development now" = Yes)

**Gate:** Do not create or update the ticket, and do not begin development,
without explicit user/PO confirmation of sprint inclusion and development
readiness.

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

## Description (Standard Sections)

Use the following structure (in this order):

### 1. **Story Block / Problem Statement**
Start with a user story or problem description.

- **For features:** `**As a** [role], **I want** [goal], **so that** [benefit].`
- **For bug fixes:** `Create a [thing] to [goal] — context about the problem.`

### 2. **Background / Evaluation Data** *(optional but recommended)*
- Why does this work need to happen now?
- Reference prior tickets with `PRO-XXX`
- Cite current state / observed issues

### 3. **Goal / Business Value** *(for larger features)*
- What does success look like?
- Quantifiable outcomes if possible

### 4. **Scope** *(for larger features)*
- What is included
- What is explicitly NOT included (out of scope / non-goals)

### 5. **Implementation Plan** *(optional)*
- High-level approach or phases
- Key files to be changed
- Reference to architecture decisions

### 6. **Next Steps / Technical Approach**
- Numbered, actionable list
- References to specific files or config

### 7. **Testing Strategy**
- **Unit Tests** — what they cover
- **Integration Tests** — what they cover
- **System Tests** — what they cover (if applicable)

### 8. **Priority / Story Points**
- `**Priority:** [High|Medium|Low] — rationale`
- `**Story Points:** [N] (comparable to PRO-XXX = N points)` — fill in when closing

### 9. **Acceptance Criteria** *(required, AC-1 to AC-N)*
Format: `- [ ] AC-N: Description — implementation detail`

- Numbered (AC-1, AC-2, ...)
- Each AC is testable and binary (done / not done)
- One sentence per AC

### 10. **Definition of Done** *(required)*
Format: `- [ ] Item — description`

Common items:
- PR #NNN merged to master
- JIRA ticket closed (Fertig)
- All ACs checkmarked
- Story Points assigned
- Traceability: FR-XX, QR-XX added to docs
- CI self-tests pass

### 11. **Non-Goals / Out of Scope** *(optional but recommended)*
- What is explicitly NOT part of this work
- Helps prevent scope creep

### 12. **References** *(recommended)*
- `Refs: PRO-XXX` (parent / related tickets)
- Links to related PRs

---

## Sample Description (Use as Starting Point)

```markdown
**As a** [role, e.g. development team],

**I want** [goal],

**so that** [measurable benefit].

---

## Background

[Why this work matters now. Reference related PRO-XXX tickets. Describe current state.]

---

## Goal

[What does success look like? Quantifiable outcomes if possible.]

---

## Scope

### In Scope

* [Included work item 1]
* [Included work item 2]

### Out of Scope

* [Explicitly excluded item 1]
* [Explicitly excluded item 2]

---

## Implementation Plan

1. [Step 1]
2. [Step 2]
3. [Step 3]

---

## Next Steps

1. [Concrete file/action 1]
2. [Concrete file/action 2]

---

## Testing Strategy

1. **Unit Tests:**

    * [Test scope 1]
    * [Test scope 2]

2. **Integration Tests:**

    * [Test scope 1]

3. **System Tests:**

    * [Test scope 1]

---

**Priority:** [High|Medium|Low] — [rationale]

**Story Points:** [N] (filled when closing, comparable to PRO-XXX = N points)

---

## Acceptance Criteria

- [ ] AC-1: [Testable condition] — implementation detail
- [ ] AC-2: [Testable condition] — implementation detail
- [ ] AC-3: [Testable condition] — implementation detail
- [ ] AC-4: [Testable condition] — implementation detail
- [ ] AC-5: [Testable condition] — implementation detail

---

## Definition of Done

- [ ] PR #NNN merged to master
- [ ] JIRA ticket closed (Fertig)
- [ ] All ACs checkmarked
- [ ] Story Points: N assigned
- [ ] Traceability: FR-XX, QR-XX added to doc/REQUIREMENTS.md, doc/ARCHITECTURE.md
- [ ] CI self-tests: N tests passed

---

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
| **Story Points** field | 4/6 (when closed) | Assign at close, document in description |
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

---

## Quick-Start Checklist

When creating a new Story ticket:

- [ ] Project: `PRO`, Issue Type: `Story`
- [ ] Summary follows `[Verb] [Target] [Context]` pattern
- [ ] Description has: Story block OR Problem statement
- [ ] **Background** section references prior PRO-XXX if applicable
- [ ] **Implementation Plan** lists concrete files/steps
- [ ] **Acceptance Criteria** are numbered (AC-1, AC-2, ...) and testable
- [ ] **Definition of Done** is a `- [ ]` checklist
- [ ] **References** / `Refs: PRO-XXX` footer present
- [ ] **Priority** set to Medium (or High for release-critical)
- [ ] **Epic Link** set to parent epic (e.g. `PRO-259`)
- [ ] **Fix Version** set to target release (e.g. `v4.3.0`)
- [ ] **Sprint / Backlog** placement decided (user/PO confirms: sprint or backlog)
- [ ] Development start confirmed (user/PO confirms: yes, team begins now; or no, deferred)
- [ ] Assignee set (or confirmed unassigned)
- [ ] Ticket setup reviewed and approved by user/PO
- [ ] Story Points to be assigned when closing the ticket

---

## Related Documents

- `doc/CONTRIBUTING.md` — Development standards
- `doc/REQUIREMENTS.md` — FR / QR requirement IDs
- `doc/ARCHITECTURE.md` — System architecture and design decisions
- `.opencode/skills/plan-feature/` — This skill
- `.opencode/skills/complete-feature/SKILL.md` — Workflow for closing a ticket
- `.opencode/skills/develop-feature/SKILL.md` — Workflow for developing a feature
