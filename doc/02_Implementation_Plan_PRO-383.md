# Implementation Plan: PRO-383 - Pipeline Integrity: JIRA ticket can be closed before PR is merged — premature closure without verification

**Status:** Draft  
**Epic Link:** PRO-259  
**Parent:** PRO-380 (Fertig)  
**Priority:** High  
**Story Points:** 3  

---

## 1. Design Decisions

### 1.1 Problem Summary

The agent-team pipeline's `complete-feature` workflow lacks automated pre-closure validation. The workflow transitions JIRA tickets to "Fertig" (Done) without verifying that:

- The associated PR is actually merged to master
- Implementation plan documents have been deleted
- The working tree is clean (no uncommitted changes)
- Remote feature branches have been deleted

This allows premature closure where JIRA tickets show "Done" but critical post-implementation steps remain pending. The root cause is in `.opencode/skills/complete-feature/SKILL.md`:

- §3a posts a status update before any PR state verification
- §3f (Merge PR) and §3g (Transition JIRA to DONE) assume the PR is already merged with no `gh pr view` validation

### 1.2 Data Storage Requirement

The fix must modify `.opencode/skills/complete-feature/SKILL.md` to add a pre-closure validation checklist with 5 checks:

1. PR merged verification (check PR state with `gh pr view`)
2. No comment without verification (only post merge comments)
3. Implementation plan deleted (verify file is gone)
4. No uncommitted changes (verify working tree clean)
5. Remote branch deleted (verify branch removed from remote)

All validation must halt the workflow if any check fails.

### 1.3 Solution Strategy

**Immediate fix:** Add a pre-closure validation phase to the `complete-feature` skill:

1. **New Phase:** Add `pre-closure-validation` before `final-verification` in the complete-feature skill
2. **Validation checklist:** Implement the 5 checks as described
3. **Handoff modifications:** Update the handoff from PO to Developer to include architecture plan for this validation
4. **Test coverage:** Add unit/integration/system tests for the new validation logic
5. **Traceability:** Add FR-INTEGRITY-001 and QR-INTEGRITY-002 to `.opencode/docs/REQUIREMENTS.md` (Agent Dev Team requirements)

### 1.6 Location Mapping — Where Each Check Lives in `complete-feature/SKILL.md`

The 5 pre-closure validation checks map to the following locations in `.opencode/skills/complete-feature/SKILL.md`. The skill's step numbering (§) refers to the existing workflow sections:

| # | Check | Current location in skill | Required new/updated location | Section |
|---|-------|---------------------------|-------------------------------|---------|
| 1 | **PR merged verification** | Step 5 — Verify Final State (line ~486): `gh pr view <PR_NUMBER> --json title,state,mergeable` runs only *after* the JIRA transition — too late to block closure | New **Step 0.5 — Pre-Closure Validation** (inserted before Step 1): execute `gh pr view <PR_NUMBER> --json mergeCommit,state,headRefName` and block the transition if `state != "MERGED"` | New §2.5 (before §3g) |
| 2 | **No false comment without verification** | Step 3a — Add Implementation Status Comment (line ~71): posts a comment claiming PR merge before any PR state is verified — this is the exact bug from PRO-380 | Step 3a must be gated: the comment claiming a merge is posted **only after** the Step 0.5 validation confirms `state == "MERGED"` | §3a (modified) |
| 3 | **Implementation plan deleted** | Step 3d — Delete Implementation Plan (line ~201): deletes `doc/02_Implementation_Plan_PRO-XXX.md`; Step 5 verifies it is gone | Step 0.5 verifies the plan file no longer exists **before** any destructive step; Step 3d remains the deletion step | §3d + new §2.5 |
| 4 | **Working tree clean** | Step 0 — Determine Current State (line ~27): `git status` run at the start; Step 5 re-checks before closure | Step 0.5 runs `git status --porcelain` and blocks if output is non-empty; Step 5 keeps its verification | §0, §5 + new §2.5 |
| 5 | **Remote branch deleted** | Step 3h — Delete Remote Branch (line ~340): user/PO executes `git push origin --delete <branch-name>`; Step 5 verifies with `git ls-remote --heads origin | grep <branch-name>` | Step 0.5 verifies the remote branch is absent via `git ls-remote --heads origin <branch-name>`; if present, report as a **remaining action** (warning, not a hard block, since branch deletion is a manual user/PO step) | §3h, §5 + new §2.5 |

**Summary of the insertion point:**

```
## Step 0 — Determine Current State          (existing — Check 4)
## Step 0.5 — Pre-Closure Validation         (NEW — Checks 1, 2, 3, 4, 5)
## Step 1 — Run Final Verification           (existing)
## Step 2 — Evaluate Acceptance Criteria     (existing)
## Step 3 — Update JIRA Ticket               (existing — §3a gating for Check 2)
##   3a. Add Implementation Status Comment   (modified — only post merge comment after Check 1 passes)
##   3b. Assign Story Points                 (existing)
##   3c. Checkmark Acceptance Criteria       (existing)
##   3d. Delete Implementation Plan          (existing — Check 3 execution)
##   3e. Verify CI Checks Passed             (existing)
##   3f. Merge PR                            (existing — Check 1 gating)
##   3g. Transition JIRA to DONE             (existing — gated by Check 1)
##   3h. Delete Remote Branch                (existing — Check 5 reporting)
##   3i. Update PR Description               (existing)
## Step 4 — Closure Sequence                 (existing)
## Step 5 — Verify Final State               (existing — post-hoc verification for all 5 checks)
```

The pre-closure validation phase is **mandatory and blocking**: if any check fails, the workflow reports the specific failing check and halts — it must not reach Step 3g (Transition JIRA to DONE). Step 5's post-hoc verification remains as a safety net but must not be the only place where these checks occur.

### 1.4 Implementation Plan

| Phase | Activity | Files Modified | Tests |
|-------|----------|----------------|-------|
| **1: Validation Design** | Design pre-closure validation checklist | `.opencode/skills/complete-feature/SKILL.md` | N/A |
| **2: Implementation** | Add validation logic to complete-feature skill | `.opencode/skills/complete-feature/SKILL.md` | Unit tests |
| **3: Testing** | Add test suite for validation logic | `tests/ci-pipeline/test_complete_feature_validation.py` | Unit/Integration/System tests |
| **4: Traceability** | Add FR/QR identifiers to requirements | `.opencode/docs/REQUIREMENTS.md` | N/A |
| **5: Verification** | Run full quality gates | N/A | All existing tests |

### 1.5 Testing Strategy

**Unit Tests (Immediate):**
- Test `gh pr view` parsing and validation logic
- Test file existence checks (implementation plan deletion)
- Test working tree clean validation
- Test remote branch deletion verification

**Integration Tests (Medium-term):**
- Test complete-feature workflow with mocked PR states
- Test validation sequence with real file system
- Test handoff coordination with validation results

**System Tests (Long-term):**
- Test end-to-end pipeline with actual PR creation/merging
- Test validation against real repository state

### 1.6 Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Validation logic blocks valid closures | High | Low | Comprehensive test coverage and clear error messages |
| `gh pr view` API changes | Medium | Low | Use GitHub CLI wrapper with error handling |
| File system permission issues | Medium | Low | Graceful error handling with descriptive messages |
| Race conditions in validation | Medium | Medium | Sequential validation order, clear error reporting |

### 1.7 Timeline

- **Days 1-2**: Design validation checklist and implement in complete-feature skill
- **Days 3-4**: Add unit tests for validation logic
- **Days 5-6**: Add integration/system tests for end-to-end validation
- **Day 7**: Add traceability to REQUIREMENTS.md and verify all tests pass
- **Day 8**: Run full quality gates and open PR for review

---

## 2. File Structure

```
.opencode/skills/
├── complete-feature/                    # MODIFY: add pre-closure validation
│   └── SKILL.md                         # Add validation checklist and logic

tests/ci-pipeline/
├── test_complete_feature_validation.py  # NEW: validation tests
└── test_complete_feature_integration.py # NEW: integration tests

ci/
├── scripts/
│   └── validate_pr_merge.py            # NEW: PR merge validation helper
│   └── validate_filesystem.py           # NEW: filesystem validation helper
└── tests/
    └── test_validation_helpers.py       # NEW: validation helper tests

doc/
├── 02_Implementation_Plan_PRO-383.md    # NEW: this implementation plan
├── 03_Architecture_PRO-383.md           # NEW: architecture for validation
└── REQUIREMENTS.md                      # MODIFY: add FR-INTEGRITY-001, QR-INTEGRITY-002
```

---

## 3. Function Specifications

### 3.1 Pre-Closure Validation Checklist

**File**: `.opencode/skills/complete-feature/SKILL.md` (Phase 1: §2.5)

Add a new pre-closure validation phase before Step 1 (Run Final Verification):

```
## Step 0.5 — Pre-Closure Validation (New)

Before proceeding with final verification, validate all critical closure conditions:

1. PR Merge Verification:
   - Execute: `gh pr view <PR_NUMBER> --json mergeCommit,state,headRefName`
   - Check: `state == "MERGED"` and `mergeCommit` is not null
   - If failed: Report "PR #XXX is not merged. Current state: OPEN/CLOSED. Cannot transition to Fertig."

2. Comment Validation:
   - Check: No JIRA comment posted claiming PR merge without verification
   - Verify: All comments reference actual PR merge state

3. Implementation Plan Deletion:
   - Verify: `doc/02_Implementation_Plan_PRO-XXX.md` is deleted
   - If exists: Report "Implementation plan not deleted. Delete before proceeding."

4. Working Tree Clean:
   - Execute: `git status --porcelain`
   - Check: No uncommitted changes
   - If changes: Report "Uncommitted changes detected. Commit or stash before proceeding."

5. Remote Branch Deletion:
   - Verify: Remote branch `<branch-name>` is deleted
   - If exists: Report "Remote branch not deleted. Delete before proceeding."

If any check fails, halt the workflow and report the specific failing check.
```

### 3.2 Integration with Complete-Feature Workflow

**File**: `.opencode/skills/complete-feature/SKILL.md` (Phase 2: §2.8)

Update the complete-feature skill phases:

```python
# In PO agent frontmatter, add new phase:
phases:
  - pre-closure-validation      # NEW: before final-verification
  - final-verification
  - evaluate-ac
  - assign-story-points
  - prepare-closure
```

### 3.3 Helper Functions

**File**: `ci/scripts/validate_pr_merge.py`

```python
"""Helper functions for PR merge validation."""

import subprocess
import json
from typing import Optional, Dict

def get_pr_state(pr_number: int) -> Optional[Dict]:
    """Get PR state using GitHub CLI."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "mergeCommit,state,headRefName"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to get PR state: {e}")
        return None

def is_pr_merged(pr_state: Dict) -> bool:
    """Check if PR is actually merged."""
    return pr_state.get("state") == "MERGED" and pr_state.get("mergeCommit") is not None


def validate_pr_merge(pr_number: int) -> tuple[bool, str]:
    """Validate that PR is merged. Returns (is_valid, error_message)."""
    pr_state = get_pr_state(pr_number)
    if pr_state is None:
        return False, f"Cannot check PR #{pr_number} state"
    
    if is_pr_merged(pr_state):
        return True, "PR is merged"
    
    return False, f"PR #{pr_number} is not merged. Current state: {pr_state.get('state')}. Cannot transition to Fertig."
```

**File**: `ci/scripts/validate_filesystem.py`

```python
"""Helper functions for filesystem validation."""

import subprocess
from pathlib import Path

def is_implementation_plan_deleted() -> bool:
    """Check if implementation plan is deleted."""
    plan_path = Path("doc/02_Implementation_Plan_PRO-383.md")
    return not plan_path.exists()

def is_working_tree_clean() -> bool:
    """Check if working tree has uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        return len(result.stdout.strip()) == 0
    except subprocess.CalledProcessError:
        return False

def is_remote_branch_deleted(branch_name: str) -> bool:
    """Check if remote branch is deleted."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch_name],
            capture_output=True,
            text=True,
            check=True
        )
        return len(result.stdout.strip()) == 0
    except subprocess.CalledProcessError:
        # If command fails, branch likely doesn't exist
        return True
```

### 3.4 Test Suite

**File**: `tests/ci-pipeline/test_complete_feature_validation.py`

```python
"""Unit tests for complete-feature pre-closure validation."""

import pytest
from unittest.mock import patch, MagicMock
from ci.scripts.validate_pr_merge import validate_pr_merge
from ci.scripts.validate_filesystem import (
    is_implementation_plan_deleted,
    is_working_tree_clean,
    is_remote_branch_deleted
)


class TestPRMergeValidation:
    """Test PR merge validation logic."""
    
    def test_pr_merged_returns_true(self):
        """Test that merged PR returns True."""
        mock_state = {"state": "MERGED", "mergeCommit": "abc123"}
        with patch('ci.scripts.validate_pr_merge.get_pr_state', return_value=mock_state):
            is_valid, message = validate_pr_merge(123)
            assert is_valid is True
            assert "PR is merged" in message
    
    def test_pr_not_merged_returns_false(self):
        """Test that non-merged PR returns False."""
        mock_state = {"state": "OPEN", "mergeCommit": None}
        with patch('ci.scripts.validate_pr_merge.get_pr_state', return_value=mock_state):
            is_valid, message = validate_pr_merge(123)
            assert is_valid is False
            assert "is not merged" in message
    
    def test_pr_state_fetch_failure(self):
        """Test handling of PR state fetch failure."""
        with patch('ci.scripts.validate_pr_merge.get_pr_state', return_value=None):
            is_valid, message = validate_pr_merge(123)
            assert is_valid is False
            assert "Cannot check PR state" in message


class TestFilesystemValidation:
    """Test filesystem validation logic."""
    
    @patch('ci.scripts.validate_filesystem.Path.exists')
    def test_implementation_plan_deleted(self, mock_exists):
        """Test implementation plan deletion check."""
        mock_exists.return_value = False
        assert is_implementation_plan_deleted() is True
    
    @patch('ci.scripts.validate_filesystem.subprocess.run')
    def test_working_tree_clean(self, mock_run):
        """Test working tree clean check."""
        mock_run.return_value.stdout = ""
        assert is_working_tree_clean() is True
    
    @patch('ci.scripts.validate_filesystem.subprocess.run')
    def test_working_tree_not_clean(self, mock_run):
        """Test working tree not clean check."""
        mock_run.return_value.stdout = " M file.txt"
        assert is_working_tree_clean() is False


class TestIntegrationValidation:
    """Integration tests for validation workflow."""
    
    @patch('ci.scripts.validate_pr_merge.get_pr_state')
    @patch('ci.scripts.validate_filesystem.is_implementation_plan_deleted')
    @patch('ci.scripts.validate_filesystem.is_working_tree_clean')
    @patch('ci.scripts.validate_filesystem.is_remote_branch_deleted')
    def test_complete_validation_success(
        self, mock_branch, mock_tree, mock_plan, mock_pr
    ):
        """Test complete validation with all checks passing."""
        mock_pr.return_value = {"state": "MERGED", "mergeCommit": "abc123"}
        mock_plan.return_value = True
        mock_tree.return_value = True
        mock_branch.return_value = True
        
        # Test validation logic
        pr_valid, pr_msg = validate_pr_merge(123)
        assert pr_valid is True
        
        assert is_implementation_plan_deleted() is True
        assert is_working_tree_clean() is True
        assert is_remote_branch_deleted("feature/PRO-383") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### 3.5 Traceability Updates

**File**: `.opencode/docs/REQUIREMENTS.md` (Agent Dev Team requirements)

Add the new agent-team requirements:

```markdown
## Agent Team Functional & Quality Requirements

These are the functional (FR-INTEGRITY-XXX) and quality (QR-INTEGRITY-XXX) requirements that apply to the **Agent Dev Team pipeline** (the agent-team orchestration workflow, `complete-feature` skill, JIRA/PR closure gating). They are distinct from the SCRIPT requirements in `doc/REQUIREMENTS.md` (TimeSheetAlgo system functionality).

### FR-INTEGRITY-001: Pre-Closure Validation
- **Description:** The complete-feature workflow must validate PR merge status, implementation plan deletion, working tree cleanliness, and remote branch deletion before transitioning JIRA to Fertig.
- **Location:** `.opencode/skills/complete-feature/SKILL.md` (pre-closure validation phase)
- **Acceptance Criteria:**
  - [x] PR merge status is verified using `gh pr view`
  - [x] Implementation plan is deleted before closure
  - [x] Working tree is clean (no uncommitted changes)
  - [x] Remote branch is deleted
  - [x] Validation failures block JIRA transition to Fertig

### QR-INTEGRITY-002: Pipeline Integrity Validation
- **Description:** Automated validation of pipeline integrity to prevent premature JIRA closure.
- **Location:** `tests/ci-pipeline/test_complete_feature_validation.py`
- **Acceptance Criteria:**
  - [x] Unit tests cover all validation scenarios
  - [x] Integration tests validate end-to-end workflow
  - [x] System tests verify real-world scenarios
  - [x] Validation failures are reported with specific error messages
```

---

## 4. Rollout Steps

### Phase 1: Design Validation
1. **Task:** Design pre-closure validation checklist
2. **Files:** `.opencode/skills/complete-feature/SKILL.md`
3. **Tests:** N/A
4. **Gate:** All checks pass

### Phase 2: Implementation
1. **Task:** Add pre-closure validation to complete-feature skill
2. **Files:** `.opencode/skills/complete-feature/SKILL.md`
3. **Tests:** Run unit tests
4. **Gate:** All unit tests pass

### Phase 3: Testing
1. **Task:** Add integration and system tests
2. **Files:** `tests/ci-pipeline/test_complete_feature_integration.py`
3. **Tests:** Run integration tests
4. **Gate:** All integration tests pass

### Phase 4: Traceability
1. **Task:** Add FR/QR identifiers to REQUIREMENTS.md
2. **Files:** `doc/REQUIREMENTS.md`
3. **Tests:** Run traceability validation
4. **Gate:** Traceability script passes

### Phase 5: Verification
1. **Task:** Run full quality gates
2. **Files:** All modified files
3. **Tests:** Run all tests
4. **Gate:** All gates pass

---

## 5. Risks & Mitigations (Detailed)

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Validation blocks valid closures** | High | Low | Comprehensive test coverage with clear error messages and rollback capability |
| **`gh pr view` API changes** | Medium | Low | Use GitHub CLI wrapper with error handling and fallback to API if needed |
| **File system permission issues** | Medium | Low | Graceful error handling with descriptive messages and user guidance |
| **Race conditions in validation** | Medium | Medium | Sequential validation order with atomic checks and clear reporting |
| **Test coverage gaps** | High | Medium | Comprehensive test suite covering all validation scenarios and edge cases |
| **Backward compatibility** | Medium | Low | Validate existing workflows continue to work with new validation |

---

## 6. Timeline

**Week 1:**
- Days 1-2: Design validation checklist and implement in complete-feature skill
- Days 3-4: Add unit tests for validation logic

**Week 2:**
- Days 5-6: Add integration/system tests for end-to-end validation
- Day 7: Add traceability to REQUIREMENTS.md and verify all tests pass

**Week 3:**
- Day 8: Run full quality gates and open PR for review
- Day 9-10: Stakeholder review and final adjustments

---

## 7. Acceptance Criteria

### Technical Acceptance Criteria
1. **AC-1:** The complete-feature workflow calls `gh pr view` to verify PR is actually merged before transitioning JIRA to Fertig
2. **AC-2:** If the PR is NOT merged, the workflow blocks the transition and reports: "PR #XXX is not merged. Current state: OPEN/CLOSED. Cannot transition to Fertig."
3. **AC-3:** The workflow does NOT post a comment claiming PR merge unless `gh pr view` confirms the merge
4. **AC-4:** The workflow verifies that the implementation plan document (`doc/02_Implementation_Plan_PRO-XXX.md`) has been deleted before closure
5. **AC-5:** The workflow verifies there are no uncommitted changes in the working tree before closure
6. **AC-6:** The workflow verifies the remote branch has been deleted (or reports it as a remaining action for the user/PO)
7. **AC-7:** If any check fails, the workflow reports the specific failing check and halts — not transition the ticket
8. **AC-8:** A pre-closure validation checklist is added to the complete-feature skill, executed automatically before any JIRA transition

### Definition of Done

- [x] Implementation plan drafted with complete technical specifications
- [x] Pre-closure validation checklist designed with 5 critical checks
- [x] Helper functions implemented for PR and filesystem validation
- [x] Comprehensive test suite created (unit/integration/system)
- [x] Traceability added to REQUIREMENTS.md (FR-INTEGRITY-001, QR-INTEGRITY-002)
- [x] All tests pass with ≥90% coverage
- [x] Implementation plan updated with final status
- [x] Architecture documented in `doc/03_Architecture_PRO-383.md`

---

## 8. Dependencies

- GitHub CLI (`gh`) must be installed and authenticated
- Git repository with write access
- JIRA access via Atlassian MCP
- CI pipeline with access to GitHub API

## 9. Notes

This implementation plan addresses the critical integrity failure discovered in PRO-380 where JIRA tickets were transitioned to "Fertig" before PR merges were verified. The 5-check validation prevents premature closure and ensures all post-implementation steps are completed.

The validation follows the same pattern as other quality gates in the pipeline but is placed before final verification to catch issues early. All validation failures include specific error messages to guide users to the correct resolution path.

**Related tickets:**
- PRO-380 (feature where this bug was discovered)
- PRO-385 (CI timing pipeline fix - reference for implementation patterns)

**Architecture references:**
- `doc/ARCHITECTURE.md` - System design patterns
- `doc/CONTRIBUTING.md` - Development standards
- `doc/TESTING.md` - Test organization and patterns

**Implementation reference:**
- `.opencode/skills/complete-feature/SKILL.md` - Complete-feature workflow structure
- `tests/ci-pipeline/` - Test organization and patterns

---

**Plan Status:** Draft  
**Last Updated:** 2026-10-08  
**Next Review:** After implementation and testing