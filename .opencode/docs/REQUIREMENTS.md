# Agent Dev Team Requirements

This file defines the requirements for the **Agent Dev Team** (Product Owner, Architect, Developer, Tester) that orchestrate the feature lifecycle. These requirements are separate from the SCRIPT requirements documented in `doc/REQUIREMENTS.md`.

---

## 1. Traceability Approach

Agent requirements use the identifier prefix `AGENT-REQ-XXX` so that requirements and agent behavior can be cross-referenced in the agent definition files (`.opencode/agents/*.agent.md`) and skill files (`.opencode/skills/*.md`). When an agent action or pipeline step addresses a requirement, the relevant documentation shall reference the matching requirement ID.

---

## 2. Product Owner Agent Requirements

The Product Owner is the dispatcher and orchestrator of the entire agent-team pipeline. Every feature or bug fix must flow through the Product Owner first.

| ID | Requirement | Source |
|----|-------------|--------|
| AGENT-REQ-001 | The Product Owner **must NOT** define technical solutions (database schema, API endpoints, implementation details). | `product-owner.agent.md` |
| AGENT-REQ-002 | All requirements produced by the Product Owner **must be testable and unambiguous** and **must reference acceptance criteria**. | `product-owner.agent.md` |
| AGENT-REQ-003 | All outputs from the Product Owner **must map to the project domain (TimeSheetAlgo)**: time tracking, Excel export, CSV processing. | `product-owner.agent.md` |
| AGENT-REQ-004 | The Product Owner **must NOT** dispatch the Developer without first receiving an Architect review. | `product-owner.agent.md` |
| AGENT-REQ-005 | The Product Owner **must NOT** approve a feature without final user agreement. | `product-owner.agent.md` |
| AGENT-REQ-006 | The Product Owner **must NOT** dispatch work without escalation when an agent reports a problem or when the pipeline exceeds 3 cycles. | `product-owner.agent.md` |
| AGENT-REQ-007 | The Product Owner **must interrupt and evaluate** when an agent cannot resolve an issue or when the process loops. | `product-owner.agent.md` |
| AGENT-REQ-008 | The Product Owner **must detect** the development mode (`automated` / `interactive`) from the user chat using keywords and **must persist** the mode in `~/.opencode/pipeline-state.json` per ticket. | `product-owner.agent.md` |
| AGENT-REQ-009 | If the mode is not explicitly set, the default is `interactive`. | `product-owner.agent.md` |
| AGENT-REQ-010 | The Product Owner **must not proceed** to planning until the intake conversation produces a clear goal, use-case, and information set. | `product-owner.agent.md` |
| AGENT-REQ-011 | In **automated mode**, handoffs proceed without user pauses, but escalation still triggers on blockers or cycle limit 3. | `product-owner.agent.md` |
| AGENT-REQ-012 | In **interactive mode**, the Product Owner **must pause** for user confirmation before each handoff and ask "Proceed to next stage?". | `product-owner.agent.md` |
| AGENT-REQ-013 | On blocker or cycle limit 3, escalation bypasses the mode setting and interrupts immediately. | `product-owner.agent.md` |

---

## 3. Architect Agent Requirements

The Architect translates validated user stories and requirements into detailed technical design and structured implementation plans that the Developer can execute precisely.

| ID | Requirement | Source |
|----|-------------|--------|
| AGENT-REQ-014 | The Architect **must NOT** change validated requirements. | `architect.agent.md` |
| AGENT-REQ-015 | The Architect **must NOT** implement code. | `architect.agent.md` |
| AGENT-REQ-016 | The Architect **must minimize complexity**; the simplest design that meets requirements is preferred. | `architect.agent.md` |
| AGENT-REQ-017 | The Architect **must strictly reference `doc/ARCHITECTURE.md` patterns** for all design decisions. | `architect.agent.md` |
| AGENT-REQ-018 | All designs **must align with the existing codebase**; new patterns may only be proposed if justified. | `architect.agent.md` |
| AGENT-REQ-019 | The Architect **must include all files and changes needed** to satisfy acceptance criteria (Completeness Rule). | `architect.agent.md` |
| AGENT-REQ-020 | The Architect **must ensure all components have clear, testable interfaces** (Testability Rule). | `architect.agent.md` |
| AGENT-REQ-021 | Every architectural decision **must reference project documentation** (Documentation Rule). | `architect.agent.md` |
| AGENT-REQ-022 | Before handing off to the Developer, the Architect **must report blockers with specific questions** instead of guessing. | `product-owner.agent.md` |

---

## 4. Developer Agent Requirements

The Developer implements features following architectural plans precisely, ensuring code quality, adherence to project standards, and comprehensive testing.

| ID | Requirement | Source |
|----|-------------|--------|
| AGENT-REQ-023 | The Developer **must only modify files specified in the implementation plan**. | `developer.agent.md` |
| AGENT-REQ-024 | The Developer **must NOT make architectural changes** without Architect approval. | `developer.agent.md` |
| AGENT-REQ-025 | The Developer **must keep changes minimal and scoped**; no refactoring of unrelated code. | `developer.agent.md` |
| AGENT-REQ-026 | The Developer **must follow `doc/CONTRIBUTING.md` guidelines** (naming conventions, coding style). | `developer.agent.md` |
| AGENT-REQ-027 | **All code must include docstrings and type hints** on all parameters and returns. | `developer.agent.md` |
| AGENT-REQ-028 | **Each commit must reference the PRO ticket** and be small, focused, and descriptive (commit format per CONTRIBUTING.md). | `developer.agent.md` |
| AGENT-REQ-029 | The Developer **must follow the Architect's plan exactly**; if issues arise, flag for Architect review. | `developer.agent.md` |
| AGENT-REQ-030 | The Developer **must meet the CI gate** in `AGENTS.md`: **≥90% branch+line coverage**. | `developer.agent.md` |
| AGENT-REQ-031 | The Developer **must add comprehensive tests per `doc/TESTING.md` requirements** (unit, integration). | `developer.agent.md` |
| AGENT-REQ-032 | The Developer **must run the full test suite before handoff** and verify no pre-existing tests are broken. | `developer.agent.md` |

---

## 5. Tester Agent Requirements

The Tester ensures functional correctness, quality, and integration by validating implementation against requirements and executing comprehensive test strategies.

| ID | Requirement | Source |
|----|-------------|--------|
| AGENT-REQ-033 | The Tester **must evaluate against requirements, not implementation style**. | `tester.agent.md` |
| AGENT-REQ-034 | The Tester **must produce reproducible results**. | `tester.agent.md` |
| AGENT-REQ-035 | Test decisions **must be data-driven** (test results, coverage metrics, verification evidence). | `tester.agent.md` |
| AGENT-REQ-036 | The Tester **must NOT approve** without verification of **all** acceptance criteria. | `tester.agent.md` |
| AGENT-REQ-037 | Approval **requires ALL acceptance criteria verified AND test coverage ≥90% AND no critical issues**. | `tester.agent.md` |
| AGENT-REQ-038 | **Critical issues block approval**; medium issues should be fixed; low issues are optional. | `tester.agent.md` |
| AGENT-REQ-039 | **Any regression in existing tests is a critical blocker**. | `tester.agent.md` |
| AGENT-REQ-040 | Coverage **below 90% requires justification** before approval. | `tester.agent.md` |
| AGENT-REQ-041 | The Tester **must NOT approve with unresolved critical issues**, **must NOT ignore test failures**, and **must NOT approve if acceptance criteria are not met**. | `tester.agent.md` |
| AGENT-REQ-042 | The Tester **must execute the complete test suite** and check for regressions. | `tester.agent.md` |
| AGENT-REQ-043 | The Tester **must verify the traceability matrix generates without errors** (`python .github/scripts/generate_traceability_matrix.py`). | `tester.agent.md` |
| AGENT-REQ-044 | The Tester **must pass CI self-tests** (`pytest -q tests/ci-pipeline/`) before approval. | `tester.agent.md` |

---

## 6. Pipeline Coordination Requirements

These requirements govern the coordination between agents during the feature lifecycle.

| ID | Requirement | Source |
|----|-------------|--------|
| AGENT-REQ-045 | Each agent reports its cycle count; the maximum is **3 cycles per agent**. | `product-owner.agent.md` |
| AGENT-REQ-046 | If an agent reports a blocker, the Product Owner evaluates immediately (no cycle limit). | `product-owner.agent.md` |
| AGENT-REQ-047 | When cycle count equals 3, the agent **must stop and report to the Product Owner**. | `product-owner.agent.md` |
| AGENT-REQ-048 | When cycle count exceeds 3, the agent **must NOT continue** — escalate to the Product Owner. | `product-owner.agent.md` |
| AGENT-REQ-049 | When the process loops (agent repeating the same action without progress), the Product Owner **must interrupt and evaluate**. | `product-owner.agent.md` |
| AGENT-REQ-050 | When the Product Owner receives an escalation, it **must evaluate**: (1) resolvable → guidance and re-dispatch; (2) scope problem → update JIRA/requirements; (3) priority problem → re-prioritise or defer; (4) else → hand off to user. | `product-owner.agent.md` |
| AGENT-REQ-051 | Every handoff **must include**: deliverable summary, current state (cycle count, blockers, open questions), next-step request, and constraints. | `product-owner.agent.md` |
| AGENT-REQ-052 | The Product Owner **must read the persisted mode before each handoff** and apply it. | `product-owner.agent.md` |
| AGENT-REQ-053 | If the user changes the mode mid-pipeline, the Product Owner **must update the pipeline state immediately** and apply it to the next handoff. | `product-owner.agent.md` |

---

## 7. Handoff Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| AGENT-REQ-054 | PO → Architect handoff **must include** the complete User Story output, assumptions, clarifications, domain context, documentation references, and prioritization. | `product-owner.agent.md` |
| AGENT-REQ-055 | Architect → Developer handoff **must include** the complete architecture output, Phase-by-Phase breakdown, exact file paths, files to create/modify, test strategy, CONTRIBUTING.md references, and blockers. | `architect.agent.md` |
| AGENT-REQ-056 | Developer → Tester handoff **must include** the complete "Changes Made" output, before/after test coverage metrics, file list with changes, git commit history, and deviations from the plan. | `developer.agent.md` |
| AGENT-REQ-057 | Tester → PO handoff **must include** the complete validation output, test execution evidence, confirmation all acceptance criteria are met, and final recommendations. | `tester.agent.md` |
| AGENT-REQ-058 | The PO → User handoff **must include** the complete summary, AC status, DoD status, PR description checkmarks, and request `atlassian_transitionJiraIssue` + `gh pr merge`. | `product-owner.agent.md` |

---

## 7. Agent Team Functional & Quality Requirements

These are the functional (`FR-INTEGRITY-XXX`) and quality (`QR-INTEGRITY-XXX`) requirements that apply to the **Agent Dev Team pipeline** (the agent-team orchestration workflow, `complete-feature` skill, JIRA/PR closure gating). They are distinct from the SCRIPT requirements in `doc/REQUIREMENTS.md` (TimeSheetAlgo system functionality).

| ID | Requirement | Source |
|----|-------------|--------|
| FR-INTEGRITY-001 | **Pre-Closure Validation** — The complete-feature workflow shall validate all critical post-implementation conditions before transitioning a JIRA ticket to "Fertig" (Done). The validation shall include: PR merge status verification using `gh pr view`; Implementation plan document deletion; Working tree cleanliness (no uncommitted changes); Remote branch deletion; No unverified PR merge claims in JIRA comments. | `doc/02_Implementation_Plan_PRO-383.md`, `.opencode/skills/complete-feature/SKILL.md` |
| QR-INTEGRITY-002 | **Pipeline Integrity Validation** — The agent-team pipeline shall provide automated validation of pipeline integrity to prevent premature JIRA closure, with all validation logic covered by a test suite (unit, integration and system tests) that runs as CI self-tests. | `doc/REQUIREMENTS.md` (moved from), `tests/ci-pipeline/test_complete_feature_validation.py` |

**Related:** PRO-380 (bug where premature closure was discovered), PRO-383 (fix ticket)

---

## 8. Mode Keywords

| Mode | Keywords |
|------|----------|
| Automated | "run automated", "run automated mode", "go ahead", "proceed", "without confirmation", "no pauses" |
| Interactive | "run interactive", "run interactive mode", "pause", "confirm", "ask me", "stop between steps" |

---

## 9. References

This requirements document is maintained alongside:

- `AGENTS.md` — Top-level guide: project conventions, modes, CI gates
- `.opencode/docs/WORKFLOW.md` — Agent team workflow, diagrams, quality gates, handoff labels
- `.opencode/agents/product-owner.agent.md` — Product Owner agent definition
- `.opencode/agents/architect.agent.md` — Architect agent definition
- `.opencode/agents/developer.agent.md` — Developer agent definition
- `.opencode/agents/tester.agent.md` — Tester agent definition
- `.opencode/skills/` — Feature pipeline skills
- `~/.opencode/pipeline-state.json` — Persisted pipeline state per ticket
- `doc/REQUIREMENTS.md` — SCRIPT requirements (separate; not duplicated here)

---

## 10. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-10-08 | Initial creation — separated Agent Dev Team requirements from SCRIPT requirements |
