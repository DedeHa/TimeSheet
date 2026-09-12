# Implementation Plan PRO-376: Expand Agent-System Test Coverage with Full Pipeline Simulation

**Status:** In Progress  
**Epic Link:** PRO-259  
**Parent:** PRO-259 (In Arbeit)  
**Fix Version:** v4.3.0  
**Priority:** Medium  
**Story Points:** 8  

---

## Background

PRO-374 established the foundational agent-system test coverage with dedicated CI jobs and structural tests. PRO-376 extends this with comprehensive integration and system tests that validate the entire agent-team pipeline for both **manual (interactive)** and **automated** feature implementation modes, using a deterministic dummy feature implementation as the test scenario.

The agent-team pipeline (Product Owner → Architect → Developer → Tester → Product Owner) currently has strong structural and unit-level test coverage (150 tests, 100% passing), but lacks a true end-to-end integration/system test that exercises the complete workflow with a real feature implementation scenario.

## Goal

Create a system test that simulates the full agent-team pipeline using the dummy feature: **"Develop division of two complex numbers"**.

The test must validate:

1. **PO Intake** — goal, use-case, information, scope, and AC direction are collected
2. **Mode Detection** — user chat messages are parsed and persisted correctly
3. **Architect Phase** — architecture plan and implementation plan are produced
4. **Developer Phase** — code is implemented per the plan
5. **Tester Phase** — ACs are validated against the implementation
6. **PO Review** — final review produces a complete summary
7. **Mode Behavior** — interactive mode pauses for confirmation; automated mode proceeds directly
8. **Pipeline State** — state persists correctly across all handoffs
9. **Context Propagation** — all context flows correctly between agents

## Scope

### In Scope

- Create a system test file for the full agent-team pipeline
- Use a deterministic dummy feature: **"Develop division of two complex numbers"**
- Implement the dummy feature as a real, testable code change
- Verify the pipeline works in **interactive mode** (manual confirmation gates)
- Verify the pipeline works in **automated mode** (direct dispatch)
- Verify mode detection from conversational user messages
- Verify pipeline state persistence across handoffs
- Verify context propagation between agents
- Verify final output quality and completeness
- Document the test scenario and results in JIRA

### Out of Scope

- Live JIRA API integration tests
- Real GitHub PR creation/merge
- Real agent-model execution (use deterministic mock agents)
- Production deployment verification
- Performance or load testing of the pipeline

## Implementation Plan

### Phase 1: Mode Detection Script

**Files:**
- `.opencode/scripts/detect_mode.py` — NEW: conversational mode detection and persistence

**Test cases (>=5):**
1. Automated mode detection from conversational phrases
2. Interactive mode detection from conversational phrases
3. Low-confidence hints detection
4. No-mode detection returns None
5. Mode persistence round-trip through pipeline state

**Gate:** All mode detection tests pass.

### Phase 2: Mode Detection Tests

**Files:**
- `.github/tests/agents/test_mode_detection.py` — NEW: mode detection coverage

**Test cases (>=5):**
1. Conversational pattern detection
2. Confidence level validation
3. Matched phrase reporting
4. Mode persistence round-trip
5. Default interactive mode fallback

**Gate:** All mode detection tests pass.

### Phase 3: Full Pipeline System Test

**Files:**
- `.github/tests/agents/test_agent_team_system.py` — NEW: end-to-end pipeline simulation

**Test classes (>=4):**
1. Interactive mode pipeline tests
2. Automated mode pipeline tests
3. Mode detection edge case tests
4. Pipeline state management tests
5. Dummy feature implementation tests

**Test cases (>=20):**
1. PO intake collects all required fields
2. Mode detection from interactive chat
3. Architect produces implementation plan
4. Developer implements feature
5. Tester validates against ACs
6. PO final review produces complete summary
7. Context propagation through pipeline
8. Pipeline state persists
9. Mode detection from automated chat
10. Mode persistence across handoffs
11. Automated mode proceeds without pauses
12. Full pipeline automated mode
13. Both modes detected with automated precedence
14. No mode returns None
15. Empty message returns None
16. Mode defaults to interactive
17. Mode can change mid-pipeline
18. State file created
19. State includes last_updated
20. State includes development_mode
21. State survives reload
22. Complex division mathematical correctness
23. Division by zero raises error
24. Complex division edge cases
25. Dummy feature acceptance criteria

**Gate:** All system tests pass.

### Phase 4: Agent and Skill Integration

**Files:**
- `.opencode/agents/product-owner.agent.md` — UPDATE: mode detection constraints and handoff protocol
- `.opencode/skills/orchestrate-feature/SKILL.md` — UPDATE: mode detection and state management
- `AGENTS.md` — UPDATE: agent development modes and mode detection documentation

**Verification:**
1. PO agent detects and persists development mode
2. PO agent checks mode before each handoff
3. Interactive mode pauses for confirmation
4. Automated mode proceeds without pauses
5. Escalation still triggers on blockers or cycle limit (3)

**Gate:** All agent integration tests pass.

### Phase 5: Existing Agent Test Updates

**Files:**
- `.github/tests/agents/test_handoffs.py` — UPDATE: mode detection and handoff protocol tests
- `.github/tests/agents/test_orchestration.py` — UPDATE: orchestration and mode detection tests

**Verification:**
1. Handoff protocol tests include mode detection
2. Orchestration tests validate mode-aware dispatch
3. All existing agent tests continue to pass

**Gate:** All agent tests pass.

### Phase 6: Documentation and JIRA

**Files:**
- `doc/02_Implementation_Plan_PRO-376.md` — NEW: this plan
- JIRA PRO-376 — UPDATE: implementation details and test results

**Verification:**
1. Implementation plan created and maintained
2. JIRA ticket documented with test results
3. DoD checklist checkmarked

**Gate:** Documentation complete.

## Data Schema

No new data schema. Tests validate YAML frontmatter, markdown sections, placeholder strings, and pipeline state in `~/.opencode/pipeline-state.json`.

## Configuration Knobs

No new configuration knobs. Mode detection uses conversational patterns and persists to the existing pipeline state file.

## Rollout Steps

1. ✅ Draft implementation plan
2. ✅ Implement mode detection script
3. ✅ Implement mode detection tests
4. ✅ Implement full pipeline system test
5. ✅ Update agent and skill integration
6. ✅ Update existing agent tests
7. ✅ Run final verification: `pytest -q .github/tests/agents/`, `pytest -q .github/tests/`, lint checks, traceability
8. ⬜ Commit with Conventional Commits + `Refs: PRO-376`
9. ⬜ Push feature branch and open Pull Request
10. ⬜ Update JIRA with checkmarked ACs/DoD
11. ⬜ Transition JIRA to Fertig after user/PO confirmation

## Non-Goals

- Does not modify the application codebase
- Does not create live JIRA API integration tests
- Does not change the application test suite or coverage gate
- Does not open or merge real GitHub PRs
- Does not perform production deployment verification

## Acceptance Criteria

- [ ] AC-1: System test file created for full agent-team pipeline
- [ ] AC-2: Dummy feature "develop division of two complex numbers" implemented as test subject
- [ ] AC-3: Interactive mode pipeline verified with confirmation gates
- [ ] AC-4: Automated mode pipeline verified with direct dispatch
- [ ] AC-5: Mode detection verified from conversational user messages
- [ ] AC-6: Pipeline state persistence verified across handoffs
- [ ] AC-7: Context propagation verified between all agents
- [ ] AC-8: Final PO review output verified for completeness
- [ ] AC-9: System test documented in JIRA with results
- [ ] AC-10: Test runs in CI and passes

## Definition of Done

- [ ] PR merged to master
- [ ] JIRA ticket closed (Fertig)
- [ ] All ACs checkmarked
- [ ] Story Points: 8 assigned
- [ ] All new tests passing
- [ ] CI self-tests pass: pytest -q .github/tests/
- [ ] Lint checks pass: ruff, black, pydocstyle, radon
- [ ] Traceability matrix updated

Refs: PRO-259
