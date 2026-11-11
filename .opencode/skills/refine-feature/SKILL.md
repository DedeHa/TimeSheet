---
name: refine-feature
description: "Use when refining a drafted JIRA Story/Bug ticket with stakeholder review and finalization — conducting multi-stakeholder review (developer, architect, tester) and common stakeholder review before the ticket is finalized for development. Triggers on requests to 'refine the backlog', 'stakeholder review', 'review the ticket', 'define AC', 'finalize the ticket', or 'implementation plan'. NOTE: The agent-team prepares closure; after user / PO confirmation, the agent-team executes `atlassian_transitionJiraIssue` and `gh pr merge`. Story points must be estimated before sprint inclusion or development pickup."
---

# Feature & Bug Refinement & Stakeholder Review

This skill covers the stakeholder review and finalization of a JIRA Story
or Bug ticket that was drafted by the `discover-feature` skill. It is the gate
between discovery and development: the ticket is not finalized until every
stakeholder has confirmed it.

**Triggered by:** The PO has drafted a ticket via `discover-feature` and is
ready to review and finalize it before `develop-feature` begins.

**Prerequisite:** A drafted JIRA Story or Bug ticket (status "Zu erledigen") with
Intention / Use-Case (stories) or Problem Statement (bugs), Goal, Steps / Implementation Plan, Information,
Testing Strategy, Acceptance Criteria, Definition of Done, Priority /
Story Points, Non-Goals, and References already populated by
`discover-feature`.

---

## Prerequisites

- Working directory: `/workspaces/TimeSheet` (repository root)
- Virtual environment activated: `source /workspaces/TimeSheet/.venv/bin/activate`
- `gh` authenticated and `git` configured
- Atlassian MCP tools available (Jira)
- A drafted JIRA Story or Bug ticket (status "Zu erledigen") with Intention /
  Use-Case (stories) or Problem Statement (bugs), Goal, Steps / Implementation
  Plan, Information, Testing Strategy, Acceptance Criteria, Definition of Done,
  Priority / Story Points, Non-Goals, and References already populated by
  `discover-feature`.

---

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
4. Read the drafted ticket via Atlassian MCP to confirm it is ready for review:
   ```
   atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["description", "status", "customfield_10028"])
   ```

---

## Step 1 — Multi-Stakeholder Review

After the PO defines the feature, conduct a **multi-stakeholder review** with
the developer, architect, and tester **before** the ticket is finalized.
This minimizes risk for architecture, implementation, and verification.

### Developer review

Verify implementation feasibility, effort estimate, and technical approach.
Confirm the implementation plan is realistic.

### Architect review

Verify architectural alignment, component boundaries, and integration points.
Confirm the feature fits the system architecture.

### Tester review

Verify testability of ACs, DoD completeness, and
coverage strategy. Confirm each AC can be objectively verified.

Each reviewer confirms or raises concerns. If any reviewer raises a concern,
the PO updates the feature definition before proceeding.

---

## Step 2 — Common Stakeholder Review

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

**For Bug Tickets:** The bug-specific ACs (especially "Bug does not reproduce after fix")
must be verified by the tester before finalization.

---

## Finalization Checklist

Before marking the ticket as ready for development, verify each item. The
checklist produces the inputs D1–D7 for the Definition of Ready (DoR) gate in
`develop-feature` Step 1f (PRO-407, AC-3). The orchestrator dispatches to the Developer only
after that gate passes:

| DoR input | Produced by this skill as |
|-----------|---------------------------|
| D1 Story points | "Story Points assigned" item below |
| D2 Acceptance criteria | Numbered, testable AC items |
| D3 Definition of Done | DoD `- [ ]` checklist; no placeholders in the ACs or Steps (closure items exempt until closure) |
| D4 Stakeholder review | Multi-stakeholder review (Step 1) and common review (Step 2) completed |
| D5 Scope | "Non-goals documented" item below |
| D6 Drift | No unresolved drift signals from the `develop-feature` Step 1d drift check |
| D7 Decisions | Open decisions recorded in the ticket or plan Part A |

Before finalizing, run the adversarial reviewer in `readiness-review`. It tries to
refute D1-D7 against the ticket text and records PASS or FAIL per item in pm-notes.
Fix every FAIL in the ticket (with PO confirmation) or ask for a waiver.


**Common to Stories and Bugs:**
- [ ] Intention / use-case clearly defined (stories) or Problem Statement clearly defined (bugs)
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
- [ ] **Story Points assigned** before sprint inclusion or development pickup
- [ ] Non-goals documented (if scope is non-trivial)
- [ ] References / `Refs: PRO-XXX` footer present

**Bug-Specific:**
- [ ] Root Cause Analysis is documented
- [ ] Steps to Reproduce are complete and ordered
- [ ] Expected and Actual Behavior are documented
- [ ] AC-1 is "Bug does not reproduce after fix"

---

## Sprint Context

For reference, the sprint inclusion logic from `discover-feature` applies here
as a final verification: confirm that the sprint/backlog placement, priority,
and assignee match the user/PO decisions recorded during discovery.

If any field needs to change based on stakeholder feedback, update the ticket
via `atlassian_editJiraIssue` before finalizing.

---

## Final User Agreement

The ticket is now finalized and ready for development.

**Gate:** Before starting `develop-feature`, present the finalized ticket to
the user / Product-Owner and ask explicitly:

> "The ticket is finalized (all stakeholders confirmed, ACs testable, DoD
> realistic, story points assigned, sprint placement recorded). Proceed to
> development via `develop-feature`?"

- **On "yes":** Continue to `develop-feature` (Phase 1 — read the JIRA ticket).
- **On "no":** Return to the user for revisions to the ticket before
  re-presenting.

In **interactive mode**, pause and wait for this confirmation. In
**automated mode**, proceed without a pause — but escalate immediately if
the user asks to stop or if a blocker is hit.

**After confirmation:** The agent-team executes `develop-feature` (Phase 1 — read the JIRA ticket, then Phases 2–7). Once development is complete, the tester agent runs `complete-feature` to validate and close. No further user pauses are required during the development/testing cycle unless a blocker or escalation is hit.

---

## Related Documents

- `AGENTS.md` — Top-level guide: project conventions, modes, CI gates
- `.opencode/docs/WORKFLOW.md` — Agent team workflow, diagrams, quality gates, handoff labels
- `docs/CONTRIBUTING.md` — Development standards
- `docs/REQUIREMENTS.md` — FR / QR requirement IDs
- `docs/ARCHITECTURE.md` — System architecture and design decisions
- `.opencode/skills/discover-feature/` — Initial ticket documentation
- `.opencode/skills/refine-feature/` — This skill
- `.opencode/skills/develop-feature/SKILL.md` — Workflow for developing a feature