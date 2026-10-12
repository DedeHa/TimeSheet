# Architecture: PRO-383 - Pipeline Integrity: Pre-Closure Validation for complete-feature

**Status:** Draft  
**Epic Link:** PRO-259  
**Parent:** PRO-380 (Fertig)  
**Priority:** High  
**Story Points:** 3  

---

## 1. Architecture Overview

This document describes the architecture for the pre-closure validation added to the `complete-feature` skill. The validation prevents premature JIRA ticket closure by verifying critical post-implementation conditions before any JIRA transition.

### 1.1 System Context

The TimeSheetAlgo agent-team pipeline consists of 4 agents (Product Owner, Architect, Developer, Tester) and 5 skills (orchestrate-feature, discover-feature, refine-feature, develop-feature, complete-feature). The `complete-feature` skill handles ticket closure but lacked automated validation, leading to the integrity failure in PRO-380.

### 1.2 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    complete-feature Skill                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Phase 1: Pre-Closure Validation (NEW)                        │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  Check 1: PR Merge Verification                         │  │  │
│  │  │  - Execute: gh pr view <PR_NUMBER> --json               │  │  │
│  │  │  - Verify: state == "MERGED" and mergeCommit exists     │  │  │
│  │  │  - Block if not merged                                  │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  Check 2: Comment Validation                            │  │  │
│  │  │  - Verify: No merge comments posted without verification│  │  │
│  │  │  - Check: All comments reference actual PR state        │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  Check 3: Implementation Plan Deletion                  │  │  │
│  │  │  - Verify: doc/02_Implementation_Plan_PRO-XXX.md gone  │  │  │
│  │  │  - Block if file still exists                           │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  Check 4: Working Tree Clean                            │  │  │
│  │  │  - Execute: git status --porcelain                      │  │  │
│  │  │  - Verify: No uncommitted changes                       │  │  │
│  │  │  - Block if changes exist                               │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  Check 5: Remote Branch Deletion                        │  │  │
│  │  │  - Verify: Remote branch deleted from origin            │  │  │
│  │  │  - Report as remaining action if not deleted            │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Phase 2: Final Verification (existing)                       │  │
│  │  Phase 3: Evaluate Acceptance Criteria (existing)             │  │
│  │  Phase 4: Assign Story Points (existing)                      │  │
│  │  Phase 5: Prepare Closure (existing)                          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 Data Flow

```
complete-feature workflow
    │
    ├──▶ Pre-Closure Validation (NEW)
    │       │
    │       ├──▶ PR Merge Check (gh pr view)
    │       ├──▶ Comment Validation
    │       ├──▶ Implementation Plan Deletion Check
    │       ├──▶ Working Tree Clean Check
    │       └──▶ Remote Branch Deletion Check
    │       │
    │       ├── All pass ──▶ Final Verification
    │       └── Any fail ──▶ Report specific failure, halt workflow
    │
    └──▶ Final Verification
    └──▶ Evaluate Acceptance Criteria
    └──▶ Assign Story Points
    └──▶ Prepare Closure
```

---

## 2. Component Specifications

### 2.1 PR Merge Verification

**Location:** `.opencode/skills/complete-feature/SKILL.md` (§2.5), `ci/scripts/validate_pr_merge.py`

**Purpose:** Verify that the associated PR is actually merged to master before allowing JIRA transition.

**Inputs:**
- `pr_number`: The GitHub PR number (e.g., 118)

**Process:**
1. Execute `gh pr view <PR_NUMBER> --json mergeCommit,state,headRefName`
2. Parse the JSON output
3. Check `state == "MERGED"` and `mergeCommit` is not null
4. If failed, report: "PR #XXX is not merged. Current state: OPEN/CLOSED. Cannot transition to Fertig."

**Outputs:**
- `is_merged`: boolean
- `error_message`: descriptive error if not merged

**Failure Handling:**
- If `gh pr view` fails, report the error and halt
- If PR is not merged, report specific state and block transition

### 2.2 Comment Validation

**Location:** `.opencode/skills/complete-feature/SKILL.md` (§2.5)

**Purpose:** Ensure no JIRA comment claims PR merge without verification.

**Process:**
1. Check JIRA comments for claims of PR merge
2. Verify all merge-related comments reference actual PR state
3. Block if unverified merge claims are found

**Failure Handling:**
- Report the specific comment and its unverified claim
- Halt the workflow

### 2.3 Implementation Plan Deletion Check

**Location:** `.opencode/skills/complete-feature/SKILL.md` (§2.5), `ci/scripts/validate_filesystem.py`

**Purpose:** Verify that the implementation plan document has been deleted before closure.

**Process:**
1. Check if `doc/02_Implementation_Plan_PRO-XXX.md` exists
2. If exists, report and block
3. If deleted, proceed

**Failure Handling:**
- Report the file path and block transition
- Halt the workflow

### 2.4 Working Tree Clean Check

**Location:** `.opencode/skills/complete-feature/SKILL.md` (§2.5), `ci/scripts/validate_filesystem.py`

**Purpose:** Verify there are no uncommitted changes in the working tree before closure.

**Process:**
1. Execute `git status --porcelain`
2. Check output is empty
3. If changes exist, report and block

**Failure Handling:**
- Report the uncommitted changes
- Halt the workflow

### 2.5 Remote Branch Deletion Check

**Location:** `.opencode/skills/complete-feature/SKILL.md` (§2.5), `ci/scripts/validate_filesystem.py`

**Purpose:** Verify the remote feature branch has been deleted (or report as remaining action).

**Process:**
1. Execute `git ls-remote --heads origin <branch-name>`
2. Check output is empty
3. If branch still exists, report as remaining action

**Failure Handling:**
- Report the branch name as a remaining action for the user/PO
- This check is a warning rather than a hard block (branch deletion is a manual step)

---

## 3. Integration Points

### 3.1 complete-feature Skill Phases

The new pre-closure validation phase is inserted before `final-verification`:

```python
phases:
  - pre-closure-validation      # NEW: before final-verification
  - final-verification
  - evaluate-ac
  - assign-story-points
  - prepare-closure
```

### 3.2 Handoff Modifications

The handoff from PO to Developer must include:
- The architecture plan for this validation
- The complete implementation plan
- The test strategy

### 3.3 CI Pipeline Integration

The validation tests are added to `tests/ci-pipeline/` and run as part of the CI self-tests:

```bash
pytest -q tests/ci-pipeline/test_complete_feature_validation.py
```

---

## 4. Test Strategy

### 4.1 Unit Tests

**File:** `tests/ci-pipeline/test_complete_feature_validation.py`

Test coverage:
- `test_pr_merged_returns_true`: Verify merged PR returns True
- `test_pr_not_merged_returns_false`: Verify non-merged PR returns False
- `test_pr_state_fetch_failure`: Verify error handling for fetch failure
- `test_implementation_plan_deleted`: Verify plan deletion check
- `test_working_tree_clean`: Verify working tree clean check
- `test_working_tree_not_clean`: Verify working tree not clean check
- `test_complete_validation_success`: Verify complete validation workflow

### 4.2 Integration Tests

**File:** `tests/ci-pipeline/test_complete_feature_integration.py`

Test coverage:
- `test_complete_feature_validation_sequence`: Verify validation sequence
- `test_complete_feature_validation_failure`: Verify failure handling
- `test_complete_feature_workflow_integration`: Verify end-to-end workflow

### 4.3 System Tests

**File:** `tests/ci-pipeline/test_complete_feature_system.py`

Test coverage:
- `test_end_to_end_validation`: Verify real-world validation scenario
- `test_validation_with_real_pr`: Verify validation with actual PR

---

## 5. Traceability

| Requirement | Location | Status |
|-------------|----------|--------|
| FR-INTEGRITY-001: Pre-Closure Validation | `.opencode/skills/complete-feature/SKILL.md`, `.opencode/docs/REQUIREMENTS.md` | Draft |
| QR-INTEGRITY-002: Pipeline Integrity Validation | `tests/ci-pipeline/test_complete_feature_validation.py`, `.opencode/docs/REQUIREMENTS.md` | Draft |

---

## 6. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Validation blocks valid closures | High | Low | Comprehensive test coverage and clear error messages |
| `gh pr view` API changes | Medium | Low | Use GitHub CLI wrapper with error handling |
| File system permission issues | Medium | Low | Graceful error handling with descriptive messages |
| Race conditions in validation | Medium | Medium | Sequential validation order, clear error reporting |

---

## 7. Dependencies

- GitHub CLI (`gh`) must be installed and authenticated
- Git repository with write access
- JIRA access via Atlassian MCP
- CI pipeline with access to GitHub API

---

## 8. Related Documentation

- `doc/ARCHITECTURE.md` - System design patterns
- `doc/CONTRIBUTING.md` - Development standards
- `doc/TESTING.md` - Test organization and patterns
- `.opencode/skills/complete-feature/SKILL.md` - Complete-feature workflow structure
- `doc/02_Implementation_Plan_PRO-383.md` - Implementation plan

---

**Plan Status:** Draft  
**Last Updated:** 2026-10-08  
**Next Review:** After implementation and testing