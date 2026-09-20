#!/usr/bin/env python3
"""Pre-closure validation for pipeline integrity.

This module provides automated validation checks that MUST pass before
a JIRA ticket can be transitioned to Fertig (Done). It verifies:

1. PR is merged to master before JIRA closure
2. Pipeline state matches repository state
3. Implementation plan lifecycle is compliant
4. Cross-system consistency (JIRA, Git, pipeline)

Usage:
    python -m pre_closure_validation <ticket> <pr_number>
    python -m pre_closure_validation <ticket> <pr_number> --verbose
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class ValidationStatus(Enum):
    """Possible validation outcomes."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class ValidationResult:
    """Result of a single validation check."""

    check_name: str
    status: ValidationStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Aggregated report of all validation checks."""

    ticket: str
    pr_number: int
    results: List[ValidationResult] = field(default_factory=list)
    all_passed: bool = True

    @property
    def failed_checks(self) -> List[ValidationResult]:
        """Return only the checks that failed."""
        return [r for r in self.results if r.status == ValidationStatus.FAIL]

    @property
    def passed_checks(self) -> List[ValidationResult]:
        """Return only the checks that passed."""
        return [r for r in self.results if r.status == ValidationStatus.PASS]


# ---------------------------------------------------------------------------
# Pipeline state helpers
# ---------------------------------------------------------------------------

STATE_PATH = Path(__file__).resolve().parent.parent / "pipeline-state.json"


def _load_pipeline_state(ticket: str) -> Optional[Dict[str, Any]]:
    """Load pipeline state for a ticket from project-local .opencode/."""
    if not STATE_PATH.exists():
        return None
    try:
        with STATE_PATH.open("r", encoding="utf-8") as fh:
            state = json.load(fh)
        return state.get(ticket)
    except (json.JSONDecodeError, OSError):
        return None


def _get_git_status() -> str:
    """Return short git status output."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _get_current_branch() -> str:
    """Return current git branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _get_git_log(count: int = 5) -> List[str]:
    """Return recent git log entries."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{count}", "--oneline"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip().splitlines()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------


def validate_pr_merged(ticket: str, pr_number: int) -> ValidationResult:
    """Check that the PR is merged to master via GitHub API.

    Uses `gh pr view` to check PR merge status. In a real environment
    this calls the GitHub CLI; in tests it can be mocked.
    """
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "state"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return ValidationResult(
                check_name="PR Merged",
                status=ValidationStatus.FAIL,
                message=f"Failed to query PR #{pr_number}: {result.stderr.strip()}",
                details={"pr_number": pr_number, "gh_exit_code": result.returncode},
            )

        data = json.loads(result.stdout)
        state = data.get("state", "OPEN")

        if state == "MERGED":
            return ValidationResult(
                check_name="PR Merged",
                status=ValidationStatus.PASS,
                message=f"PR #{pr_number} is merged to master",
                details={"pr_number": pr_number, "state": state},
            )
        else:
            return ValidationResult(
                check_name="PR Merged",
                status=ValidationStatus.FAIL,
                message=(
                    f"PR #{pr_number} is NOT merged (state={state}). "
                    "Cannot close ticket until PR is merged."
                ),
                details={"pr_number": pr_number, "state": state},
            )
    except FileNotFoundError:
        # gh CLI not available — return SKIP with warning
        return ValidationResult(
            check_name="PR Merged",
            status=ValidationStatus.SKIP,
            message="gh CLI not available; PR merge check skipped",
            details={"pr_number": pr_number, "reason": "gh not found"},
        )
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return ValidationResult(
            check_name="PR Merged",
            status=ValidationStatus.FAIL,
            message=f"Error checking PR #{pr_number} merge status: {exc}",
            details={"pr_number": pr_number, "error": str(exc)},
        )


def validate_pipeline_state(ticket: str) -> ValidationResult:
    """Verify pipeline state is consistent with repository state.

    Checks that pipeline state file exists and contains valid data.
    Verifies that the pipeline is not in an inconsistent state
    (e.g., marked completed while git shows uncommitted changes).
    """
    state = _load_pipeline_state(ticket)
    if state is None:
        return ValidationResult(
            check_name="Pipeline State",
            status=ValidationStatus.FAIL,
            message=f"No pipeline state found for {ticket}",
            details={"ticket": ticket, "state_path": str(STATE_PATH)},
        )

    current_step = state.get("current_step", "unknown")
    status = state.get("status", "unknown")
    development_mode = state.get("development_mode", "unknown")

    # Check for inconsistent states
    git_status = _get_git_status()
    git_branch = _get_current_branch()

    issues: List[str] = []

    if status == "completed" and current_step not in ("complete",):
        issues.append(
            f"Pipeline status=completed but current_step={current_step} "
            f"(expected 'complete')"
        )

    # Check for in-progress with uncommitted changes and plan step active
    if status == "in_progress" and current_step == "plan" and git_status:
        issues.append(
            "Pipeline in progress with uncommitted changes and plan step active"
        )

    # Check for completed with uncommitted changes
    if status == "completed" and git_status:
        issues.append("Pipeline marked complete but uncommitted changes exist")

    # Check for in-progress with zero cycles
    cycle_counts = state.get("cycle_counts", {})
    current_cycles = cycle_counts.get(current_step, 0)
    if status == "in_progress" and current_cycles == 0:
        issues.append(
            f"Pipeline in progress with {current_step} step has {current_cycles} cycles"
        )

    if not git_branch:
        issues.append("Cannot determine current git branch")

    if issues:
        return ValidationResult(
            check_name="Pipeline State",
            status=ValidationStatus.FAIL,
            message="Pipeline state is inconsistent with repository state",
            details={
                "ticket": ticket,
                "pipeline_step": current_step,
                "pipeline_status": status,
                "development_mode": development_mode,
                "git_branch": git_branch,
                "git_status": git_status,
                "issues": issues,
            },
        )

    return ValidationResult(
        check_name="Pipeline State",
        status=ValidationStatus.PASS,
        message=(
            f"Pipeline state consistent: step={current_step}, "
            f"status={status}, branch={git_branch}"
        ),
        details={
            "ticket": ticket,
            "pipeline_step": current_step,
            "pipeline_status": status,
            "git_branch": git_branch,
            "git_status": git_status,
        },
    )


def validate_plan_lifecycle(ticket: str) -> ValidationResult:
    """Verify implementation plan lifecycle is compliant.

    During implementation: plan document should exist
    After merge: plan document should be deleted (stale)

    For closure validation, we check that if a plan exists, it's
    properly maintained, and if it doesn't exist, that's expected
    for a completed feature.
    """
    plan_path = Path(f"doc/02_Implementation_Plan_{ticket}.md")
    plan_exists = plan_path.exists()

    git_log = _get_git_log(10)
    plan_referenced = any(
        "Implementation_Plan" in entry or ticket in entry for entry in git_log
    )

    if plan_exists and not plan_referenced:
        return ValidationResult(
            check_name="Plan Lifecycle",
            status=ValidationStatus.FAIL,
            message=(
                f"Plan document exists at {plan_path} but is not referenced "
                f"in recent git history"
            ),
            details={
                "plan_exists": True,
                "plan_path": str(plan_path),
                "plan_referenced": False,
            },
        )

    if plan_exists:
        return ValidationResult(
            check_name="Plan Lifecycle",
            status=ValidationStatus.PASS,
            message=f"Plan document exists and is properly maintained: {plan_path}",
            details={
                "plan_exists": True,
                "plan_path": str(plan_path),
                "plan_referenced": True,
            },
        )

    return ValidationResult(
        check_name="Plan Lifecycle",
        status=ValidationStatus.PASS,
        message="No plan document exists (expected for completed feature)",
        details={"plan_exists": False, "plan_path": str(plan_path)},
    )


def validate_cross_system_consistency(ticket: str) -> ValidationResult:
    """Verify cross-system consistency between JIRA, Git, and pipeline.

    Checks:
    - Pipeline state reflects actual git state
    - No orphaned pipeline entries
    - Ticket key appears in relevant branches/commits
    """
    state = _load_pipeline_state(ticket)
    git_branch = _get_current_branch()
    git_log = _get_git_log(10)
    git_status = _get_git_status()

    issues: List[str] = []

    # Check if ticket key appears in git history
    ticket_in_git = any(ticket in entry for entry in git_log)
    if not ticket_in_git and state is not None:
        issues.append(f"Ticket {ticket} not found in recent git history")

    # Check if pipeline state matches current branch context
    if state is not None:
        pipeline_step = state.get("current_step", "")
        pipeline_status = state.get("status", "")
        if pipeline_status == "completed" and git_status:
            issues.append("Pipeline marked complete but uncommitted changes exist")
        if pipeline_status == "completed" and pipeline_step != "complete":
            issues.append(f"Pipeline status=completed but step={pipeline_step}")

    # Check for orphaned pipeline entries (state exists but no git activity)
    if state is not None and not ticket_in_git:
        issues.append(f"Pipeline state exists for {ticket} but no git activity found")

    if issues:
        return ValidationResult(
            check_name="Cross-System Consistency",
            status=ValidationStatus.FAIL,
            message="Cross-system consistency check failed",
            details={
                "ticket": ticket,
                "git_branch": git_branch,
                "ticket_in_git": ticket_in_git,
                "pipeline_state": state,
                "issues": issues,
            },
        )

    return ValidationResult(
        check_name="Cross-System Consistency",
        status=ValidationStatus.PASS,
        message=(
            f"Cross-system consistency verified: ticket={ticket}, "
            f"branch={git_branch}, ticket_in_git={ticket_in_git}"
        ),
        details={
            "ticket": ticket,
            "git_branch": git_branch,
            "ticket_in_git": ticket_in_git,
        },
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_pre_closure_validation(ticket: str, pr_number: int) -> ValidationReport:
    """Run all pre-closure validation checks and return a report.

    Args:
        ticket: JIRA ticket key (e.g., "PRO-381")
        pr_number: GitHub PR number associated with the ticket

    Returns:
        ValidationReport with results from all checks
    """
    results: List[ValidationResult] = [
        validate_pr_merged(ticket, pr_number),
        validate_pipeline_state(ticket),
        validate_plan_lifecycle(ticket),
        validate_cross_system_consistency(ticket),
    ]

    all_passed = all(r.status == ValidationStatus.PASS for r in results)

    return ValidationReport(
        ticket=ticket,
        pr_number=pr_number,
        results=results,
        all_passed=all_passed,
    )


def format_report(report: ValidationReport) -> str:
    """Format validation report as human-readable string."""
    lines = [
        f"=== Pre-Closure Validation Report: {report.ticket} ===",
        f"PR #{report.pr_number}",
        f"All Passed: {report.all_passed}",
        "",
    ]

    for result in report.results:
        icon = (
            "✅"
            if result.status == ValidationStatus.PASS
            else "❌" if result.status == ValidationStatus.FAIL else "⏭️"
        )
        lines.append(f"{icon} {result.check_name}: {result.status.value}")
        if result.message:
            lines.append(f"   {result.message}")
        if result.details:
            lines.append(f"   Details: {json.dumps(result.details, indent=2)}")
        lines.append("")

    if report.failed_checks:
        lines.append("BLOCKED: Cannot close ticket. Resolve failed checks above.")
    else:
        lines.append("CLEARED: All checks passed. Ticket may be closed.")

    return "\n".join(lines)


def main() -> int:
    """CLI entry point."""
    if len(sys.argv) < 3:
        print(
            "Usage: python pre_closure_validation.py <ticket> <pr_number> [--verbose]"
        )
        return 1

    ticket = sys.argv[1]
    try:
        pr_number = int(sys.argv[2])
    except ValueError:
        print(f"Error: PR number must be an integer, got: {sys.argv[2]}")
        return 1

    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    report = run_pre_closure_validation(ticket, pr_number)
    output = format_report(report)
    print(output)

    if verbose and report.failed_checks:
        print("\n--- Failed Check Details ---")
        for result in report.failed_checks:
            print(f"\n{result.check_name}:")
            print(f"  Message: {result.message}")
            if result.details:
                for key, value in result.details.items():
                    print(f"  {key}: {value}")

    return 0 if report.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
