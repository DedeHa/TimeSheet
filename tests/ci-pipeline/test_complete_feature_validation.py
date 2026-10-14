"""Unit tests for the complete-feature pre-closure validation helpers.

These tests validate the PR merge and filesystem validation logic in
isolation. They live under ``tests/ci-pipeline/`` (not in ``tests/``)
so they do not change the 103-test application suite or the coverage gate.

Run with::

    pytest -q tests/ci-pipeline/test_complete_feature_validation.py
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "scripts" / "validate_pr_merge.py"
)
_SPEC = importlib.util.spec_from_file_location("validate_pr_merge", _MODULE_PATH)
assert _SPEC and _SPEC.loader
sys.modules["validate_pr_merge"] = mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)

_FILESYSTEM_PATH = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "scripts"
    / "validate_filesystem.py"
)
_FS_SPEC = importlib.util.spec_from_file_location(
    "validate_filesystem", _FILESYSTEM_PATH
)
assert _FS_SPEC and _FS_SPEC.loader
sys.modules["validate_filesystem"] = fs_mod = importlib.util.module_from_spec(_FS_SPEC)
_FS_SPEC.loader.exec_module(fs_mod)


# ---------------------------------------------------------------------------
# PR merge validation
# ---------------------------------------------------------------------------


class TestGetPrState:
    """Test PR state fetching via gh pr view."""

    def test_get_pr_state_parses_merged_pr(self):
        """get_pr_state returns parsed JSON for a merged PR."""
        mock_output = '{"mergeCommit": "abc123def456", "state": "MERGED", "headRefName": "feature/PRO-405"}'
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = mock_output
            mock_run.return_value.stderr = ""
            state = mod.get_pr_state(123)
            assert state is not None
            assert state["state"] == "MERGED"
            assert state["mergeCommit"] == "abc123def456"
            assert state["headRefName"] == "feature/PRO-405"

    def test_get_pr_state_returns_none_on_failure(self):
        """get_pr_state returns None when gh pr view fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "gh: command not found"
            assert mod.get_pr_state(999) is None

    def test_get_pr_state_returns_none_on_bad_json(self):
        """get_pr_state returns None when JSON parsing fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "not valid json {"
            assert mod.get_pr_state(999) is None


class TestIsPrMerged:
    """Test PR merge state detection."""

    def test_merged_state_with_commit_is_merged(self):
        """MERGED state with a mergeCommit is considered merged."""
        assert mod.is_pr_merged({"state": "MERGED", "mergeCommit": "abc123"}) is True

    def test_open_state_is_not_merged(self):
        """OPEN state is not merged."""
        assert mod.is_pr_merged({"state": "OPEN", "mergeCommit": None}) is False

    def test_closed_state_is_not_merged(self):
        """CLOSED state is not merged."""
        assert mod.is_pr_merged({"state": "CLOSED", "mergeCommit": None}) is False

    def test_merged_without_commit_is_not_merged(self):
        """MERGED state without a mergeCommit is not considered merged."""
        assert mod.is_pr_merged({"state": "MERGED", "mergeCommit": None}) is False

    def test_unknown_state_is_not_merged(self):
        """Unknown state is not merged."""
        assert mod.is_pr_merged({"state": "UNKNOWN", "mergeCommit": "abc123"}) is False


class TestValidatePrMerge:
    """Test the validate_pr_merge entry point."""

    def test_pr_merged_returns_true(self):
        """validate_pr_merge returns True for a merged PR."""
        mock_state = {
            "state": "MERGED",
            "mergeCommit": "abc123def",
            "headRefName": "feature/PRO-405",
        }
        with patch.object(mod, "get_pr_state", return_value=mock_state):
            is_valid, message = mod.validate_pr_merge(123)
            assert is_valid is True
            assert "is merged" in message

    def test_pr_not_merged_returns_false(self):
        """validate_pr_merge returns False for an OPEN PR."""
        mock_state = {
            "state": "OPEN",
            "mergeCommit": None,
            "headRefName": "feature/PRO-405",
        }
        with patch.object(mod, "get_pr_state", return_value=mock_state):
            is_valid, message = mod.validate_pr_merge(123)
            assert is_valid is False
            assert "is not merged" in message
            assert "Cannot transition to Fertig" in message

    def test_pr_closed_returns_false(self):
        """validate_pr_merge returns False for a CLOSED PR."""
        mock_state = {
            "state": "CLOSED",
            "mergeCommit": None,
            "headRefName": "feature/PRO-405",
        }
        with patch.object(mod, "get_pr_state", return_value=mock_state):
            is_valid, message = mod.validate_pr_merge(123)
            assert is_valid is False
            assert "is not merged" in message

    def test_pr_state_fetch_failure_returns_false(self):
        """validate_pr_merge returns False when PR state cannot be fetched."""
        with patch.object(mod, "get_pr_state", return_value=None):
            is_valid, message = mod.validate_pr_merge(123)
            assert is_valid is False
            assert "Cannot check PR" in message

    def test_validate_pr_merge_main_success(self):
        """main() returns exit code 0 for a merged PR."""
        mock_state = {
            "state": "MERGED",
            "mergeCommit": "abc123",
            "headRefName": "feature/PRO-405",
        }
        with patch.object(mod, "get_pr_state", return_value=mock_state):
            assert mod.main(["123"]) == 0

    def test_validate_pr_merge_main_failure(self):
        """main() returns exit code 1 for a non-merged PR."""
        mock_state = {
            "state": "OPEN",
            "mergeCommit": None,
            "headRefName": "feature/PRO-405",
        }
        with patch.object(mod, "get_pr_state", return_value=mock_state):
            assert mod.main(["123"]) == 1

    def test_validate_pr_merge_main_missing_arg(self):
        """main() returns exit code 1 when PR number is missing."""
        assert mod.main([]) == 1

    def test_validate_pr_merge_main_invalid_arg(self):
        """main() returns exit code 1 for a non-integer PR number."""
        assert mod.main(["abc"]) == 1


# ---------------------------------------------------------------------------
# Filesystem validation
# ---------------------------------------------------------------------------


class TestIsImplementationPlanDeleted:
    """Test implementation plan deletion check."""

    def test_plan_deleted_returns_true(self):
        """Returns True when the plan file does not exist."""
        with patch.object(fs_mod.Path, "exists", return_value=False):
            assert fs_mod.is_implementation_plan_deleted() is True

    def test_plan_exists_returns_false(self):
        """Returns False when the plan file still exists."""
        with patch.object(fs_mod.Path, "exists", return_value=True):
            assert fs_mod.is_implementation_plan_deleted() is False


class TestIsWorkingTreeClean:
    """Test working tree cleanliness check."""

    def test_working_tree_clean_empty_output(self):
        """Returns True when git status --porcelain returns empty."""
        with patch.object(fs_mod.subprocess, "run") as mock_run:
            mock_run.return_value.stdout = ""
            assert fs_mod.is_working_tree_clean() is True

    def test_working_tree_clean_whitespace_only(self):
        """Returns True when output contains only whitespace."""
        with patch.object(fs_mod.subprocess, "run") as mock_run:
            mock_run.return_value.stdout = "\n   \n"
            assert fs_mod.is_working_tree_clean() is True

    def test_working_tree_not_clean_modified_file(self):
        """Returns False when a file is modified."""
        with patch.object(fs_mod.subprocess, "run") as mock_run:
            mock_run.return_value.stdout = " M file.txt\n"
            assert fs_mod.is_working_tree_clean() is False

    def test_working_tree_not_clean_untracked_file(self):
        """Returns False when a file is untracked."""
        with patch.object(fs_mod.subprocess, "run") as mock_run:
            mock_run.return_value.stdout = "?? newfile.txt\n"
            assert fs_mod.is_working_tree_clean() is False

    def test_working_tree_not_clean_multiple_changes(self):
        """Returns False when multiple changes are present."""
        with patch.object(fs_mod.subprocess, "run") as mock_run:
            mock_run.return_value.stdout = " M a.txt\n M b.txt\n?? c.txt\n"
            assert fs_mod.is_working_tree_clean() is False

    def test_working_tree_clean_git_failure_returns_false(self):
        """Returns False when git status command fails."""
        with patch.object(fs_mod.subprocess, "run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")
            assert fs_mod.is_working_tree_clean() is False

    def test_working_tree_clean_git_not_found_returns_false(self):
        """Returns False when git is not installed."""
        with patch.object(fs_mod.subprocess, "run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git")
            assert fs_mod.is_working_tree_clean() is False


class TestIsRemoteBranchDeleted:
    """Test remote branch deletion check."""

    def test_remote_branch_deleted_empty_output(self):
        """Returns True when the branch is absent from origin."""
        with patch.object(fs_mod.subprocess, "run") as mock_run:
            mock_run.return_value.stdout = ""
            assert fs_mod.is_remote_branch_deleted("feature/PRO-405") is True

    def test_remote_branch_present_returns_false(self):
        """Returns False when the branch still exists on origin."""
        with patch.object(fs_mod.subprocess, "run") as mock_run:
            mock_run.return_value.stdout = "abc123\trefs/heads/feature/PRO-405\n"
            assert fs_mod.is_remote_branch_deleted("feature/PRO-405") is False

    def test_remote_branch_deleted_git_failure_returns_true(self):
        """Returns True when ls-remote fails (branch likely absent)."""
        with patch.object(fs_mod.subprocess, "run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")
            assert fs_mod.is_remote_branch_deleted("feature/PRO-405") is True

    def test_remote_branch_deleted_git_not_found_returns_true(self):
        """Returns True when git is not installed (branch likely absent)."""
        with patch.object(fs_mod.subprocess, "run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git")
            assert fs_mod.is_remote_branch_deleted("feature/PRO-405") is True


class TestValidateFilesystem:
    """Test the validate_filesystem entry point."""

    def test_all_checks_pass(self):
        """Returns True when all filesystem checks pass."""
        with (
            patch.object(fs_mod, "is_implementation_plan_deleted", return_value=True),
            patch.object(fs_mod, "is_working_tree_clean", return_value=True),
            patch.object(fs_mod, "is_remote_branch_deleted", return_value=True),
        ):
            all_passed, message = fs_mod.validate_filesystem(
                "doc/02_Implementation_Plan_PRO-405.md", "feature/PRO-405"
            )
            assert all_passed is True
            assert "All filesystem checks passed" in message

    def test_plan_not_deleted(self):
        """Returns False when the implementation plan still exists."""
        with (
            patch.object(fs_mod, "is_implementation_plan_deleted", return_value=False),
            patch.object(fs_mod, "is_working_tree_clean", return_value=True),
            patch.object(fs_mod, "is_remote_branch_deleted", return_value=True),
        ):
            all_passed, message = fs_mod.validate_filesystem(
                "doc/02_Implementation_Plan_PRO-405.md", "feature/PRO-405"
            )
            assert all_passed is False
            assert "Implementation plan not deleted" in message

    def test_working_tree_dirty(self):
        """Returns False when the working tree has uncommitted changes."""
        with (
            patch.object(fs_mod, "is_implementation_plan_deleted", return_value=True),
            patch.object(fs_mod, "is_working_tree_clean", return_value=False),
            patch.object(fs_mod, "is_remote_branch_deleted", return_value=True),
        ):
            all_passed, message = fs_mod.validate_filesystem(
                "doc/02_Implementation_Plan_PRO-405.md", "feature/PRO-405"
            )
            assert all_passed is False
            assert "Uncommitted changes detected" in message

    def test_remote_branch_present(self):
        """Returns False when the remote branch still exists."""
        with (
            patch.object(fs_mod, "is_implementation_plan_deleted", return_value=True),
            patch.object(fs_mod, "is_working_tree_clean", return_value=True),
            patch.object(fs_mod, "is_remote_branch_deleted", return_value=False),
        ):
            all_passed, message = fs_mod.validate_filesystem(
                "doc/02_Implementation_Plan_PRO-405.md", "feature/PRO-405"
            )
            assert all_passed is False
            assert "Remote branch" in message and "still exists" in message

    def test_remote_branch_check_skipped_when_empty(self):
        """Remote branch check is skipped when branch_name is empty."""
        with (
            patch.object(fs_mod, "is_implementation_plan_deleted", return_value=True),
            patch.object(fs_mod, "is_working_tree_clean", return_value=True),
            patch.object(fs_mod, "is_remote_branch_deleted") as mock_branch,
        ):
            all_passed, message = fs_mod.validate_filesystem(
                "doc/02_Implementation_Plan_PRO-405.md", ""
            )
            assert all_passed is True
            mock_branch.assert_not_called()

    def test_validate_filesystem_main_success(self):
        """main() returns exit code 0 when all checks pass."""
        with (
            patch.object(fs_mod, "is_implementation_plan_deleted", return_value=True),
            patch.object(fs_mod, "is_working_tree_clean", return_value=True),
            patch.object(fs_mod, "is_remote_branch_deleted", return_value=True),
        ):
            assert (
                fs_mod.main(
                    ["doc/02_Implementation_Plan_PRO-405.md", "feature/PRO-405"]
                )
                == 0
            )

    def test_validate_filesystem_main_failure(self):
        """main() returns exit code 1 when a check fails."""
        with patch.object(fs_mod, "is_implementation_plan_deleted", return_value=False):
            assert fs_mod.main(["doc/02_Implementation_Plan_PRO-405.md"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
