"""Tests for pre-closure validation script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure the .opencode/scripts directory is on the path
SCRIPT_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / ".opencode" / "scripts"
)
sys.path.insert(0, str(SCRIPT_DIR))

import pre_closure_validation as pcl  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_pipeline_state(tmp_path: Path) -> dict:
    """Return a sample pipeline state entry."""
    return {
        "development_mode": "automated",
        "current_step": "develop",
        "cycle_counts": {"plan": 1, "develop": 2, "complete": 0},
        "last_updated": "2026-09-19T12:00:00+00:00",
        "status": "in_progress",
        "blocked": False,
        "escalation_level": 0,
        "interrupted": False,
        "interrupted_step": None,
        "interrupted_at": None,
    }


@pytest.fixture
def completed_pipeline_state(tmp_path: Path) -> dict:
    """Return a sample completed pipeline state entry."""
    return {
        "development_mode": "automated",
        "current_step": "complete",
        "cycle_counts": {"plan": 1, "develop": 1, "complete": 1},
        "last_updated": "2026-09-19T12:00:00+00:00",
        "status": "completed",
        "blocked": False,
        "escalation_level": 0,
        "interrupted": False,
        "interrupted_step": None,
        "interrupted_at": None,
    }


# ---------------------------------------------------------------------------
# Tests for validate_pr_merged
# ---------------------------------------------------------------------------


class TestValidatePRMerged:
    """Tests for the PR merge status validation."""

    def test_pr_merged_returns_pass(self):
        """When PR state is MERGED, validation passes."""
        mock_response = json.dumps({"state": "MERGED", "mergeState": "MERGED"})
        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=mock_response, stderr=""
            )
            result = pcl.validate_pr_merged("PRO-381", 123)

        assert result.status == pcl.ValidationStatus.PASS
        assert "PR #123 is merged" in result.message

    def test_pr_open_returns_fail(self):
        """When PR state is OPEN, validation fails."""
        mock_response = json.dumps({"state": "OPEN", "mergeState": "OPEN"})
        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=mock_response, stderr=""
            )
            result = pcl.validate_pr_merged("PRO-381", 456)

        assert result.status == pcl.ValidationStatus.FAIL
        assert "NOT merged" in result.message

    def test_pr_closed_without_merge_returns_fail(self):
        """When PR state is CLOSED without merging, validation fails."""
        mock_response = json.dumps({"state": "CLOSED", "mergeState": "CLOSED"})
        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=mock_response, stderr=""
            )
            result = pcl.validate_pr_merged("PRO-381", 789)

        assert result.status == pcl.ValidationStatus.FAIL
        assert "NOT merged" in result.message

    def test_gh_not_found_returns_skip(self):
        """When gh CLI is not available, validation is skipped."""
        with patch.object(subprocess, "run", side_effect=FileNotFoundError()):
            result = pcl.validate_pr_merged("PRO-381", 111)

        assert result.status == pcl.ValidationStatus.SKIP
        assert "gh CLI not available" in result.message

    def test_timeout_returns_fail(self):
        """When gh CLI times out, validation fails."""
        with patch.object(
            subprocess, "run", side_effect=subprocess.TimeoutExpired("gh", 15)
        ):
            result = pcl.validate_pr_merged("PRO-381", 222)

        assert result.status == pcl.ValidationStatus.FAIL
        assert "Error checking PR" in result.message

    def test_invalid_json_returns_fail(self):
        """When gh CLI returns invalid JSON, validation fails."""
        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="not json", stderr=""
            )
            result = pcl.validate_pr_merged("PRO-381", 333)

        assert result.status == pcl.ValidationStatus.FAIL

    def test_gh_nonzero_exit_returns_fail(self):
        """When gh CLI returns non-zero exit code, validation fails."""
        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="gh: error"
            )
            result = pcl.validate_pr_merged("PRO-381", 444)

        assert result.status == pcl.ValidationStatus.FAIL
        assert "Failed to query PR" in result.message


# ---------------------------------------------------------------------------
# Tests for validate_pipeline_state
# ---------------------------------------------------------------------------


class TestValidatePipelineState:
    """Tests for the pipeline state validation."""

    def test_no_state_file_returns_fail(self, tmp_path: Path):
        """When pipeline state file does not exist, validation fails."""
        # Create a temporary directory structure
        test_dir = tmp_path / "tmp" / "opencode"
        test_dir.mkdir(parents=True, exist_ok=True)
        state_file = test_dir / "pipeline-state.json"

        with patch.object(pcl, "STATE_PATH", state_file):
            result = pcl.validate_pipeline_state("PRO-381")

        assert result.status == pcl.ValidationStatus.FAIL
        assert "No pipeline state found" in result.message

    def test_valid_in_progress_state_returns_pass(self, sample_pipeline_state: dict):
        """When pipeline state is valid and consistent, validation passes."""
        # Create a temporary directory structure for the pipeline state
        import tempfile

        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up the pipeline state path
            state_path = Path(temp_dir) / "pipeline-state.json"
            state_path.write_text(json.dumps({"PRO-381": sample_pipeline_state}))

            with patch.object(pcl, "STATE_PATH", state_path):
                with patch.object(pcl, "_get_git_status", return_value=""):
                    with patch.object(
                        pcl, "_get_current_branch", return_value="feature/PRO-381-test"
                    ):
                        result = pcl.validate_pipeline_state("PRO-381")

        assert result.status == pcl.ValidationStatus.PASS

    def test_completed_with_uncommitted_changes_returns_fail(
        self, tmp_path: Path, completed_pipeline_state: dict
    ):
        """When pipeline completed with uncommitted changes, validation fails."""
        state_path = tmp_path / "pipeline-state.json"
        state_path.write_text(json.dumps({"PRO-381": completed_pipeline_state}))

        with patch.object(pcl, "STATE_PATH", state_path):
            with patch.object(pcl, "_get_git_status", return_value=" M src/file.py"):
                with patch.object(pcl, "_get_current_branch", return_value="master"):
                    result = pcl.validate_pipeline_state("PRO-381")

        assert result.status == pcl.ValidationStatus.FAIL
        assert "inconsistent" in result.message

    def test_in_progress_with_zero_cycles_returns_fail(self, tmp_path: Path):
        """When pipeline is in_progress but step has zero cycles, validation fails."""
        state = {
            "development_mode": "automated",
            "current_step": "plan",
            "cycle_counts": {"plan": 0, "develop": 0, "complete": 0},
            "last_updated": "2026-09-19T12:00:00+00:00",
            "status": "in_progress",
            "blocked": False,
            "escalation_level": 0,
            "interrupted": False,
            "interrupted_step": None,
            "interrupted_at": None,
        }
        state_path = tmp_path / "pipeline-state.json"
        state_path.write_text(json.dumps({"PRO-381": state}))

        with patch.object(pcl, "STATE_PATH", state_path):
            with patch.object(pcl, "_get_git_status", return_value=""):
                with patch.object(
                    pcl, "_get_current_branch", return_value="feature/PRO-381-test"
                ):
                    result = pcl.validate_pipeline_state("PRO-381")

        assert result.status == pcl.ValidationStatus.FAIL
        assert "inconsistent" in result.message


# ---------------------------------------------------------------------------
# Tests for validate_plan_lifecycle
# ---------------------------------------------------------------------------


class TestValidatePlanLifecycle:
    """Tests for the implementation plan lifecycle validation."""

    def test_plan_exists_and_referenced_returns_pass(self, tmp_path: Path):
        """When plan exists and is referenced in git history, validation passes."""
        plan_path = tmp_path / "doc" / "02_Implementation_Plan_PRO-381.md"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text("# Implementation Plan\n\nContent here.")

        with patch.object(pcl.Path, "exists", return_value=True):
            with patch.object(
                pcl,
                "_get_git_log",
                return_value=["doc/02_Implementation_Plan_PRO-381.md"],
            ):
                result = pcl.validate_plan_lifecycle("PRO-381")

        assert result.status == pcl.ValidationStatus.PASS
        assert "exists and is properly maintained" in result.message

    def test_plan_not_referenced_returns_fail(self, tmp_path: Path):
        """When plan exists but is not referenced in git history, validation fails."""
        plan_path = tmp_path / "doc" / "02_Implementation_Plan_PRO-381.md"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text("# Implementation Plan\n\nContent here.")

        with patch.object(pcl.Path, "exists", return_value=True):
            with patch.object(pcl, "_get_git_log", return_value=["some other commit"]):
                result = pcl.validate_plan_lifecycle("PRO-381")

        assert result.status == pcl.ValidationStatus.FAIL
        assert "not referenced" in result.message

    def test_no_plan_returns_pass(self, tmp_path: Path):
        """When no plan exists (completed feature), validation passes."""
        with patch.object(pcl.Path, "exists", return_value=False):
            result = pcl.validate_plan_lifecycle("PRO-381")

        assert result.status == pcl.ValidationStatus.PASS
        assert "No plan document exists" in result.message


# ---------------------------------------------------------------------------
# Tests for validate_cross_system_consistency
# ---------------------------------------------------------------------------


class TestValidateCrossSystemConsistency:
    """Tests for the cross-system consistency validation."""

    def test_consistent_state_returns_pass(self, sample_pipeline_state: dict):
        """When all systems are consistent, validation passes."""
        state_path = Path("/tmp/test_pipeline_state.json")
        state_path.write_text(json.dumps({"PRO-381": sample_pipeline_state}))

        with patch.object(pcl, "STATE_PATH", state_path):
            with patch.object(
                pcl, "_get_current_branch", return_value="feature/PRO-381-test"
            ):
                with patch.object(
                    pcl, "_get_git_log", return_value=["PRO-381 some commit"]
                ):
                    with patch.object(pcl, "_get_git_status", return_value=""):
                        result = pcl.validate_cross_system_consistency("PRO-381")

        assert result.status == pcl.ValidationStatus.PASS
        assert "Cross-system consistency verified" in result.message

    def test_ticket_not_in_git_returns_fail(self, sample_pipeline_state: dict):
        """When ticket is not found in git history, validation fails."""
        state_path = Path("/tmp/test_pipeline_state.json")
        state_path.write_text(json.dumps({"PRO-381": sample_pipeline_state}))

        with patch.object(pcl, "STATE_PATH", state_path):
            with patch.object(
                pcl, "_get_current_branch", return_value="feature/PRO-381-test"
            ):
                with patch.object(
                    pcl, "_get_git_log", return_value=["some other commit"]
                ):
                    with patch.object(pcl, "_get_git_status", return_value=""):
                        result = pcl.validate_cross_system_consistency("PRO-381")

        assert result.status == pcl.ValidationStatus.FAIL
        assert result.details.get("ticket_in_git") is False
        assert any(
            "not found in recent git history" in issue
            for issue in result.details.get("issues", [])
        )

    def test_completed_with_uncommitted_changes_returns_fail(self):
        """When completed pipeline has uncommitted changes, validation fails."""
        state = {
            "development_mode": "automated",
            "current_step": "complete",
            "cycle_counts": {"plan": 1, "develop": 1, "complete": 1},
            "last_updated": "2026-09-19T12:00:00+00:00",
            "status": "completed",
            "blocked": False,
            "escalation_level": 0,
            "interrupted": False,
            "interrupted_step": None,
            "interrupted_at": None,
        }
        state_path = Path("/tmp/test_pipeline_state.json")
        state_path.write_text(json.dumps({"PRO-381": state}))

        with patch.object(pcl, "STATE_PATH", state_path):
            with patch.object(pcl, "_get_current_branch", return_value="master"):
                with patch.object(pcl, "_get_git_log", return_value=["PRO-381 commit"]):
                    with patch.object(
                        pcl, "_get_git_status", return_value=" M src/file.py"
                    ):
                        result = pcl.validate_cross_system_consistency("PRO-381")

        assert result.status == pcl.ValidationStatus.FAIL
        assert any(
            "uncommitted changes" in issue for issue in result.details.get("issues", [])
        )

    def test_orphaned_pipeline_entry_returns_fail(self):
        """When pipeline state exists without git activity, validation fails."""
        state = {
            "development_mode": "automated",
            "current_step": "develop",
            "cycle_counts": {"plan": 1, "develop": 1, "complete": 0},
            "last_updated": "2026-09-19T12:00:00+00:00",
            "status": "in_progress",
            "blocked": False,
            "escalation_level": 0,
            "interrupted": False,
            "interrupted_step": None,
            "interrupted_at": None,
        }
        state_path = Path("/tmp/test_pipeline_state.json")
        state_path.write_text(json.dumps({"PRO-381": state}))

        with patch.object(pcl, "STATE_PATH", state_path):
            with patch.object(
                pcl, "_get_current_branch", return_value="feature/PRO-381-test"
            ):
                with patch.object(
                    pcl, "_get_git_log", return_value=["some other commit"]
                ):
                    with patch.object(pcl, "_get_git_status", return_value=""):
                        result = pcl.validate_cross_system_consistency("PRO-381")

        assert result.status == pcl.ValidationStatus.FAIL
        assert result.details.get("ticket_in_git") is False
        assert any(
            "no git activity" in issue for issue in result.details.get("issues", [])
        )


# ---------------------------------------------------------------------------
# Tests for run_pre_closure_validation
# ---------------------------------------------------------------------------


class TestRunPreClosureValidation:
    """Tests for the main validation orchestrator."""

    def test_all_checks_pass(self):
        """When all checks pass, report shows all_passed=True."""
        with patch.object(pcl, "validate_pr_merged") as mock_pr:
            with patch.object(pcl, "validate_pipeline_state") as mock_pipe:
                with patch.object(pcl, "validate_plan_lifecycle") as mock_plan:
                    with patch.object(
                        pcl, "validate_cross_system_consistency"
                    ) as mock_cross:
                        mock_pr.return_value = pcl.ValidationResult(
                            "PR Merged", pcl.ValidationStatus.PASS, "PR #1 merged"
                        )
                        mock_pipe.return_value = pcl.ValidationResult(
                            "Pipeline State",
                            pcl.ValidationStatus.PASS,
                            "State consistent",
                        )
                        mock_plan.return_value = pcl.ValidationResult(
                            "Plan Lifecycle", pcl.ValidationStatus.PASS, "Plan OK"
                        )
                        mock_cross.return_value = pcl.ValidationResult(
                            "Cross-System Consistency",
                            pcl.ValidationStatus.PASS,
                            "Consistent",
                        )

                        report = pcl.run_pre_closure_validation("PRO-381", 1)

        assert report.all_passed is True
        assert len(report.results) == 4
        assert len(report.passed_checks) == 4
        assert len(report.failed_checks) == 0

    def test_one_check_fails(self):
        """When one check fails, report shows all_passed=False."""
        with patch.object(pcl, "validate_pr_merged") as mock_pr:
            with patch.object(pcl, "validate_pipeline_state") as mock_pipe:
                with patch.object(pcl, "validate_plan_lifecycle") as mock_plan:
                    with patch.object(
                        pcl, "validate_cross_system_consistency"
                    ) as mock_cross:
                        mock_pr.return_value = pcl.ValidationResult(
                            "PR Merged", pcl.ValidationStatus.PASS, "PR #1 merged"
                        )
                        mock_pipe.return_value = pcl.ValidationResult(
                            "Pipeline State",
                            pcl.ValidationStatus.FAIL,
                            "State inconsistent",
                        )
                        mock_plan.return_value = pcl.ValidationResult(
                            "Plan Lifecycle", pcl.ValidationStatus.PASS, "Plan OK"
                        )
                        mock_cross.return_value = pcl.ValidationResult(
                            "Cross-System Consistency",
                            pcl.ValidationStatus.PASS,
                            "Consistent",
                        )

                        report = pcl.run_pre_closure_validation("PRO-381", 1)

        assert report.all_passed is False
        assert len(report.passed_checks) == 3
        assert len(report.failed_checks) == 1
        assert report.failed_checks[0].check_name == "Pipeline State"

    def test_report_format(self):
        """The report format includes all required sections."""
        report = pcl.ValidationReport(
            ticket="PRO-381",
            pr_number=1,
            results=[
                pcl.ValidationResult(
                    "PR Merged", pcl.ValidationStatus.PASS, "PR merged"
                ),
                pcl.ValidationResult(
                    "Pipeline State", pcl.ValidationStatus.FAIL, "Inconsistent"
                ),
            ],
            all_passed=False,
        )
        formatted = pcl.format_report(report)

        assert "PRO-381" in formatted
        assert "PR #1" in formatted
        assert "PASS" in formatted
        assert "FAIL" in formatted
        assert "BLOCKED" in formatted

    def test_empty_report(self):
        """An empty report has all_passed=True (vacuously true)."""
        report = pcl.ValidationReport(
            ticket="PRO-381",
            pr_number=1,
            results=[],
            all_passed=True,
        )
        assert report.all_passed is True
        assert len(report.passed_checks) == 0
        assert len(report.failed_checks) == 0


# ---------------------------------------------------------------------------
# Tests for ValidationReport properties
# ---------------------------------------------------------------------------


class TestValidationReportProperties:
    """Tests for ValidationReport computed properties."""

    def test_passed_checks_filter(self):
        """passed_checks returns only PASS results."""
        report = pcl.ValidationReport(
            ticket="PRO-381",
            pr_number=1,
            results=[
                pcl.ValidationResult("A", pcl.ValidationStatus.PASS),
                pcl.ValidationResult("B", pcl.ValidationStatus.FAIL),
                pcl.ValidationResult("C", pcl.ValidationStatus.PASS),
            ],
            all_passed=False,
        )
        assert len(report.passed_checks) == 2
        assert all(r.status == pcl.ValidationStatus.PASS for r in report.passed_checks)

    def test_failed_checks_filter(self):
        """failed_checks returns only FAIL results."""
        report = pcl.ValidationReport(
            ticket="PRO-381",
            pr_number=1,
            results=[
                pcl.ValidationResult("A", pcl.ValidationStatus.PASS),
                pcl.ValidationResult("B", pcl.ValidationStatus.FAIL),
                pcl.ValidationResult("C", pcl.ValidationStatus.FAIL),
            ],
            all_passed=False,
        )
        assert len(report.failed_checks) == 2
        assert all(r.status == pcl.ValidationStatus.FAIL for r in report.failed_checks)


# ---------------------------------------------------------------------------
# Tests for main entry point
# ---------------------------------------------------------------------------


class TestMainEntryPoint:
    """Tests for the CLI main() function."""

    def test_main_with_valid_args(self):
        """main() with valid args returns 0 when all checks pass."""
        with patch.object(pcl, "run_pre_closure_validation") as mock_run:
            mock_run.return_value = pcl.ValidationReport(
                ticket="PRO-381",
                pr_number=1,
                results=[
                    pcl.ValidationResult("PR Merged", pcl.ValidationStatus.PASS),
                    pcl.ValidationResult("Pipeline State", pcl.ValidationStatus.PASS),
                    pcl.ValidationResult("Plan Lifecycle", pcl.ValidationStatus.PASS),
                    pcl.ValidationResult(
                        "Cross-System Consistency", pcl.ValidationStatus.PASS
                    ),
                ],
                all_passed=True,
            )
            with patch.object(
                sys, "argv", ["pre_closure_validation.py", "PRO-381", "1"]
            ):
                result = pcl.main()

        assert result == 0

    def test_main_with_failed_checks(self):
        """main() with failed checks returns 1."""
        with patch.object(pcl, "run_pre_closure_validation") as mock_run:
            mock_run.return_value = pcl.ValidationReport(
                ticket="PRO-381",
                pr_number=1,
                results=[
                    pcl.ValidationResult("PR Merged", pcl.ValidationStatus.PASS),
                    pcl.ValidationResult("Pipeline State", pcl.ValidationStatus.FAIL),
                    pcl.ValidationResult("Plan Lifecycle", pcl.ValidationStatus.PASS),
                    pcl.ValidationResult(
                        "Cross-System Consistency", pcl.ValidationStatus.PASS
                    ),
                ],
                all_passed=False,
            )
            with patch.object(
                sys, "argv", ["pre_closure_validation.py", "PRO-381", "1"]
            ):
                result = pcl.main()

        assert result == 1

    def test_main_with_missing_args(self):
        """main() with missing args returns 1."""
        with patch.object(sys, "argv", ["pre_closure_validation.py"]):
            result = pcl.main()

        assert result == 1

    def test_main_with_invalid_pr_number(self):
        """main() with non-integer PR number returns 1."""
        with patch.object(
            sys, "argv", ["pre_closure_validation.py", "PRO-381", "not-a-number"]
        ):
            result = pcl.main()

        assert result == 1
