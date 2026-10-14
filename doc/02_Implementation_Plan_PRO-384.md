# Implementation Plan — PRO-384

**Ticket:** PRO-384 — Implement simplified agent model for streamlined workflow orchestration  
**Epic:** PRO-259 (Setup Timesheet)  
**Status:** Not yet implemented  

## Part A — Preanalysis

### 1. Problem Analysis
The TimeSheetAlgo project has a complex agent workflow structure that requires users to understand:
- Agent YAML files
- Skill files
- Multiple script names (detect_mode.py, pipeline.py, migration/validation helpers)
- Migration helpers
- Verification helpers

This complexity creates a high barrier for new contributors and reduces project adoption.

### 2. Solution Approach
Simplify the user-facing model while preserving the underlying technical separation of concerns. Hide the complexity behind a single, clean entry point (Product Owner) while maintaining the core architecture.

### 3. Technical Context
- Current entry point: Product Owner (complex documentation)
- Target entry point: Product Owner (simplified documentation)
- Scripts to be documented: detect_mode.py, pipeline.py, migration/validation helpers
- Architecture: Three-layer separation (interaction, policy, runtime)

### 4. Feasibility Verdict
**HIGH** — This is a documentation and process improvement, not a technical refactor. All existing functionality will be preserved. The changes are limited to documentation and user-facing guidance.

## Part B — Implementation Plan

| Step | Files Changed | Schema Impact | Workflow / Module Logic | Report / API Shape | Configuration Knobs | Rollout Plan | Non-Goals |
|------|---------------|---------------|-------------------------|-------------------|---------------------|--------------|-----------|
| 1 | AGENTS.md, doc/AGENTS_WORKFLOW.md | None | Update documentation structure | Updated user journey documentation | None | Documentation-only rollout | Remove any scripts or tools |
| 2 | .opencode/agents/product-owner.agent.md | None | Clarify Product Owner role as sole entry point | Clear entry point documentation | None | Documentation-only rollout | Break technical separation of concerns |
| 3 | .opencode/skills/orchestrate-feature/SKILL.md | None | Emphasize workflow coordination role | Updated skill documentation | None | Documentation-only rollout | Change core agent, skill, or script functionality |
| 4 | doc/AGENTS_WORKFLOW.md | None | Document simplified agent model specification | Three-script documentation | None | Documentation-only rollout | Affect existing workflow execution engine |
| 5 | .opencode/agents/product-owner.agent.md | None | Update Product Owner documentation | Enhanced entry point guidance | None | Documentation-only rollout | Alter fundamental architecture |
| 6 | .opencode/skills/orchestrate-feature/SKILL.md | None | Update workflow coordination documentation | Refined skill guidance | None | Documentation-only rollout | Change agent, skill, or script functionality |
| 7 | AGENTS.md | None | Update AGENTS.md with simplified model overview | Simplified structure documentation | None | Documentation-only rollout | Update external dependencies |
| 8 | doc/AGENTS_WORKFLOW.md | None | Update with simplified user journey | Updated journey documentation | None | Documentation-only rollout | Modify configuration files |

**Rollout Steps:**
1. **Phase 1 (Documentation Only):** Update all documentation files to reflect simplified model
2. **Phase 2 (Documentation Verification):** Review all documentation changes for accuracy and completeness
3. **Phase 3 (Finalization):** Finalize documentation and ensure all references are consistent

## Part C — Verification Definition

### V1 — Documentation Quality
- All documentation files updated with simplified model
- User journey clearly documented (3-4 main commands: run in mode, start feature, continue feature, validate feature)
- Product Owner is the only documented entry point
- Agent, skill, and script files are simplified to hide complexity from user documentation

### V2 — Content Accuracy
- Simplified model specification documents the back-end architecture with clear separation of concerns
- All references to existing tickets (PRO-370, PRO-369, PRO-368, PRO-367, PRO-366, PRO-365) are updated with simplified model references
- Updated AGENTS.md and doc/AGENTS_WORKFLOW.md reflect the simplified model

### V3 — User Experience
- User can start a feature with only "Run in automated mode" or "Run in interactive mode"
- Migration helpers are hidden behind Product Owner or pipeline commands
- All existing functionality is preserved with improved user experience
- Product Owner agent's entry point documentation clearly explains its gatekeeper role
- Orchestrate-feature skill documentation focuses on workflow coordination, not independent workflows

### V4 — Documentation Completeness
- All acceptance criteria are documented and verifiable
- Definition of Done checklist is realistic and complete
- Story points are assigned and documented
- Traceability matrix is updated with FR-AGENT-001, QR-AGENT-002
- All CI self-tests pass

## Verification Gates

### Unit-Level Verification (V1–V4)
- Documentation files are syntactically correct (no broken links, proper markdown)
- All references are valid and point to existing files
- User journey documentation is clear and actionable
- Technical separation of concerns is preserved in documentation

### Integration-Level Verification (V5–V7)
- Documentation cross-references are consistent
- User journey flows logically through the simplified model
- All stakeholder roles are clearly defined
- Migration paths are documented and clear

### System-Level Verification (V8+)
- Documentation is complete and comprehensive
- All acceptance criteria are documented and testable
- Definition of Done is realistic and achievable
- Implementation plan is complete and accurate

## Acceptance Criteria (from JIRA ticket)

- [ ] AC-1: User can start a feature with only "Run in automated mode" or "Run in interactive mode"
- [ ] AC-2: Product Owner is the only documented entry point for workflow initiation
- [ ] AC-3: Agent, skill, and script files are simplified to hide complexity from user documentation
- [ ] AC-4: Simplified model specification documents the back-end architecture with clear separation of concerns
- [ ] AC-5: User journey documentation shows only 3-4 main commands: run in mode, start feature, continue feature, validate feature
- [ ] AC-6: Migration helpers are hidden behind Product Owner or pipeline commands
- [ ] AC-7: All existing functionality is preserved with improved user experience
- [ ] AC-8: Updated AGENTS.md and doc/AGENTS_WORKFLOW.md reflect the simplified model
- [ ] AC-9: Product Owner agent's entry point documentation clearly explains its gatekeeper role
- [ ] AC-10: Orchestrate-feature skill documentation focuses on workflow coordination, not independent workflows

## Definition of Done

- [ ] PR #NNN merged to master
- [ ] JIRA ticket closed (Fertig)
- [ ] All ACs checkmarked
- [ ] Story Points: 13 assigned
- [ ] Traceability: FR-AGENT-001, QR-AGENT-002 added to doc/REQUIREMENTS.md, doc/ARCHITECTURE.md
- [ ] CI self-tests: All agent model tests passed
- [ ] Documentation: Updated AGENTS.md, doc/AGENTS_WORKFLOW.md with simplified model
- [ ] Developer Guide: Updated with new simplified workflow entry points
- [ ] Migration plan documented for the simplified model transition
- [ ] All referenced tickets (PRO-370, PRO-369, PRO-368, PRO-367, PRO-366, PRO-365) updated with simplified model references

## Priority / Story Points

**Priority:** High — Simplifying the user experience reduces friction for new contributors and improves project adoption

**Story Points:** 13 (Major refactor - comprehensive documentation and implementation changes)

## Non-Goals / Out of Scope

* Removing any scripts or tools that currently exist
* Breaking the underlying technical separation of concerns
* Changing the core agent, skill, or script functionality
* Affecting the existing workflow execution engine
* Altering the fundamental architecture of the system

## References

* [PRO-370](https://mainhatten.atlassian.net/browse/PRO-370): Current agent complexity analysis
* [PRO-369](https://mainhatten.atlassian.net/browse/PRO-369): Similar simplification initiatives
* [PRO-368](https://mainhatten.atlassian.net/browse/PRO-368): CI workflow optimization
* [PRO-367](https://mainhatten.atlassian.net/browse/PRO-367): Agent coordination refactoring
* [PRO-366](https://mainhatten.atlassian.net/browse/PRO-366): Documentation simplification
* [PRO-365](https://mainhatten.atlassian.net/browse/PRO-365): User experience improvement
* [.opencode/agents/product-owner.agent.md](.opencode/agents/product-owner.agent.md): Current entry point documentation
* [.opencode/skills/orchestrate-feature/SKILL.md](.opencode/skills/orchestrate-feature/SKILL.md): Current workflow coordination documentation
* [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md): Development contribution guidelines

## Implementation Summary

This is a documentation-only refactor that simplifies the TimeSheetAlgo agent workflow structure while preserving all existing functionality. The goal is to make the system easier to understand and use by hiding the complexity behind a single, clean entry point.

**Key Changes:**
- Updated AGENTS.md with simplified model overview
- Updated doc/AGENTS_WORKFLOW.md with simplified user journey
- Clarified Product Owner role as sole entry point
- Updated orchestrate-feature skill documentation
- Documented the three remaining scripts (detect_mode.py, pipeline.py, migration/validation helpers)
- Updated all related documentation references

**No functional changes** — all existing agent, skill, and script functionality remains intact.

**Verification:** All 10 acceptance criteria are testable and verifiable through documentation review and user testing.