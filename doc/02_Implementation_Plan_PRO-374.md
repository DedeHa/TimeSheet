# Implementation Plan PRO-374: Expand Agent-System Test Coverage with Dedicated Job and Comprehensive Tests

**Status:** ✅ Done  
**Epic Link:** PRO-259  
**Parent:** PRO-259 (Fertig)  
**Fix Version:** v4.3.0  
**Priority:** Medium  
**Story Points:** 5  

---

## Background

PRO-373 (Optimize Agent-System, Skill-Set and Ticket-Templates) established the 4-agent, 5-skill agent-team pipeline, but validation coverage is limited to structural checks in `test_orchestration.py` (YAML frontmatter parsing, file existence, path resolution). The agent-team pipeline lacks behavioural tests covering the handoff protocol, constraint enforcement, skill workflow ordering, output format contracts, and end-to-end pipeline simulation.

This ticket establishes a comprehensive test pyramid for the agent-system with a dedicated CI job, multi-level coverage (structural to unit to integration), and clear failure attribution.

## Goal

Establish a comprehensive test pyramid for the agent-system with:

1. Dedicated CI job for agent tests
2. Multi-level test coverage (structural to unit to integration)
3. Clear failure attribution and reporting

## Scope

### In Scope

- Create dedicated `agents` job in `python-ci.yml` with independent execution
- Add test categories: handoff protocol, constraint enforcement, skill workflow, output format validation, pipeline simulation
- Update `publish` job to depend on the `agents` job
- Document test categories in `TESTING.md`

### Out of Scope

- Modifying agent definitions or skills (PRO-373 handles this)
- Creating GitHub ISSUE_TEMPLATE files (PRO-373 handles this)
- Integration tests with live JIRA API

## Implementation Plan

### Phase 1: Handoff Protocol Tests (test_handoffs.py)

**Files:**
- `.github/tests/agents/test_handoffs.py` — NEW: handoff placeholder extraction, cycle counts, escalation triggers

**Test cases (>=5):**
1. Handoff placeholders are extracted and validated (e.g., `{{output}}`, `{{plan_output}}`, `{{developer_output}}`)
2. Cycle tracking placeholders are present in handoff prompts (`{{cycle_number}}`)
3. Escalation handoff carries required context fields (`{{current_agent}}`, `{{agent_report}}`, `{{ticket}}`, `{{blocker}}`)
4. Handoff labels are unique and non-empty across all agents
5. Handoff agent references resolve to existing agent definitions

**Gate:** All handoff tests pass.

### Phase 2: Constraint Enforcement Tests (test_constraints.py)

**Files:**
- `.github/tests/agents/test_constraints.py` — NEW: agent boundary enforcement

**Test cases (>=5):**
1. Product Owner must NOT dispatch developer without architect review
2. Product Owner must require confirmation before closure actions
3. Architect must NOT change requirements or implement code
4. Developer must only modify files specified in the plan
5. Tester must NOT approve without verification of all acceptance criteria
6. Cycle limit (max 3) is enforced in handoff prompts

**Gate:** All constraint tests pass.

### Phase 3: Output Format Validation Tests (test_agent_outputs.py)

**Files:**
- `.github/tests/agents/test_agent_outputs.py` — NEW: output format contracts

**Test cases (>=5):**
1. Product Owner output includes required sections (Feature Summary, Stakeholders, User Stories, Acceptance Criteria, Definition of Done)
2. Architect output includes required sections (Feature Summary, Architecture Analysis, Implementation Plan, Files to Modify, Test Strategy)
3. Developer output includes required sections (Changes Made, Files Modified, Tests Added/Updated, Code Quality Checks)
4. Tester output includes required sections (Validation Result, Acceptance Criteria Validation, Test Results Summary, Decision & Next Steps)
5. Escalation output format includes required fields (Escalation header, Blocked On, What's Done, What's Remaining)

**Gate:** All output format tests pass.

### Phase 4: Skill Workflow Tests (test_skill_workflows.py)

**Files:**
- `.github/tests/agents/test_skill_workflows.py` — NEW: phase execution order

**Test cases (>=3):**
1. `orchestrate-feature` phases execute in order: state-detection -> dispatch -> cycle-tracking -> escalation -> handoff-coordination
2. `develop-feature` phases execute in order: prepare-branch -> implement-rollout -> final-verification -> open-pr
3. `complete-feature` phases execute in order: final-verification -> evaluate-ac -> assign-story-points -> prepare-closure

**Gate:** All skill workflow tests pass.

### Phase 5: Pipeline Simulation Tests (test_pipeline_flow.py)

**Files:**
- `.github/tests/agents/test_pipeline_flow.py` — NEW: end-to-end pipeline simulation

**Test cases (>=3):**
1. Full pipeline flow simulation (PO -> Architect -> Developer -> Tester)
2. Cycle escalation handling (cycle 3 -> escalate to Product Owner)
3. Error propagation through handoffs (blocker reported by agent -> escalation handoff)

**Gate:** All pipeline simulation tests pass.

### Phase 6: CI Job and Publish Dependency

**Files:**
- `.github/workflows/python-ci.yml` — add dedicated `agents` job
- `.github/workflows/python-ci.yml` — update `publish` job `needs` to include `agents`

**Job specification:**
```yaml
agents:
  name: Agent System Tests
  runs-on: ubuntu-latest
  if: >-
    github.event_name == 'pull_request' ||
    github.event_name == 'workflow_dispatch'
  steps:
    - uses: actions/checkout@v5
    - uses: ./.github/actions/setup-python-deps
    - name: Run agent tests
      run: pytest -q .github/tests/agents/ --junitxml=tests/reports/agent-results.xml
```

**Gate:** Workflow YAML valid, agents job runs independently.

### Phase 7: Documentation

**Files:**
- `doc/TESTING.md` — document agent-system test categories and how to run them

**Gate:** Documentation updated.

## Data Schema

No new data schema. Tests validate YAML frontmatter, markdown sections, and placeholder strings in agent/skill definition files.

## Configuration Knobs

No new configuration knobs.

## Rollout Steps

1. ✅ Draft implementation plan
2. ✅ Implement handoff protocol tests
3. ✅ Implement constraint enforcement tests
4. ✅ Implement output format validation tests
5. ✅ Implement skill workflow tests
6. ✅ Implement pipeline simulation tests
7. ✅ Add dedicated agents job to python-ci.yml
8. ✅ Update publish job dependency
9. ✅ Update TESTING.md
10. ✅ Final verification: `pytest -q .github/tests/agents/` (103 passed), `pytest -q .github/tests/` (196 passed), lint checks, traceability
11. ⬜ Commit with Conventional Commits + `Refs: PRO-374`
12. ⬜ Push feature branch and open Pull Request

## Non-Goals

- Does not modify agent definitions or skills
- Does not create GitHub ISSUE_TEMPLATE files
- Does not add live JIRA API integration tests
- Does not change the application test suite or coverage gate

## Acceptance Criteria

- [ ] AC-1: Dedicated agents job added to python-ci.yml with independent execution
- [ ] AC-2: test_handoffs.py created with >=5 test cases for handoff protocol validation
- [ ] AC-3: test_constraints.py created with >=5 test cases for constraint enforcement
- [ ] AC-4: test_agent_outputs.py created with >=5 test cases for output format validation
- [ ] AC-5: test_skill_workflows.py created with >=3 test cases for workflow execution
- [ ] AC-6: test_pipeline_flow.py created with >=3 test cases for end-to-end simulation
- [ ] AC-7: publish job updated to depend on agents job
- [ ] AC-8: All new tests pass with pytest -q .github/tests/agents/
- [ ] AC-9: TESTING.md updated with agent-system test documentation

## Definition of Done

- [ ] PR merged to master
- [ ] JIRA ticket closed (Fertig)
- [ ] All ACs checkmarked
- [ ] Story Points: 5 assigned
- [ ] All new tests passing
- [ ] CI self-tests pass: pytest -q .github/tests/

Refs: PRO-259
