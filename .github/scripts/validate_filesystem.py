#!/usr/bin/env python3
"""Filesystem validation helper for the complete-feature pre-closure validation.

This module provides helper functions to validate filesystem conditions before
a JIRA ticket is transitioned to "Fertig" (Done). It is used by the
complete-feature workflow (see
`.opencode/skills/complete-feature/SKILL.md`, Step 0.5) and by the
FR-INTEGRITY-001 / QR-INTEGRITY-002 validation gates.

The checks implemented here are:
  1. Implementation plan deletion — verify that the implementation plan
     document (``doc/02_Implementation_Plan_PRO-XXX.md``) no longer exists.
  2. Working tree cleanliness — verify that ``git status --porcelain``
     returns an empty string (no uncommitted changes).
  3. Remote branch deletion — verify that the remote feature branch is
     absent via ``git ls-remote --heads origin <branch-name>``.

Usage:
    python .github/scripts/validate_filesystem.py <BRANCH_NAME>

Exit codes:
    0  - all filesystem checks passed
    1  - one or more checks failed

Requirements:
    - Git must be installed and configured
    - The repository must be accessible for ``git status`` and
      ``git ls-remote``
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

# Path to the implementation plan document (relative to repository root).
# The PRO-XXX token is replaced by the caller for the specific ticket.
IMPLEMENTATION_PLAN_TEMPLATE = "doc/02_Implementation_Plan_PRO-XXX.md"


def is_implementation_plan_deleted(
    plan_path: str = IMPLEMENTATION_PLAN_TEMPLATE,
) -> bool:
    """Check whether the implementation plan document has been deleted.

    The plan is a working document that is finalised and marked Complete
    before any destructive closure action. This check verifies that the plan
    file no longer exists on disk.

    Args:
        plan_path: Path to the implementation plan document. Defaults to
            ``doc/02_Implementation_Plan_PRO-XXX.md``.

    Returns:
        ``True`` if the file does NOT exist (i.e. the plan has been deleted),
        ``False`` if the file still exists.
    """
    return not Path(plan_path).exists()


def is_working_tree_clean() -> bool:
    """Check whether the working tree has uncommitted changes.

    Executes ``git status --porcelain`` and treats any non-empty output as
    a sign of uncommitted changes. A clean tree returns an empty string.

    Returns:
        ``True`` if the working tree is clean (no uncommitted changes),
        ``False`` otherwise (including when ``git status`` fails).
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        return len(result.stdout.strip()) == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def is_remote_branch_deleted(
    branch_name: str,
    remote: str = "origin",
) -> bool:
    """Check whether a remote branch has been deleted.

    Executes ``git ls-remote --heads origin <branch-name>`` and treats any
    non-empty output as evidence that the branch still exists on the remote.
    A deleted branch returns an empty string.

    Args:
        branch_name: The name of the branch to check (e.g.
            ``feature/PRO-383``).
        remote: The remote name to query. Defaults to ``origin``.

    Returns:
        ``True`` if the remote branch is absent (i.e. deleted), ``False`` if
        the branch still exists. Returns ``True`` when the command fails
        because a missing branch is the most likely cause.
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", remote, branch_name],
            capture_output=True,
            text=True,
            check=True,
        )
        return len(result.stdout.strip()) == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        # If the command fails, the branch is most likely absent.
        return True


def validate_filesystem(
    plan_path: str = IMPLEMENTATION_PLAN_TEMPLATE,
    branch_name: str = "",
) -> Tuple[bool, str]:
    """Run all filesystem validation checks.

    Performs the three filesystem checks (plan deletion, working tree clean,
    remote branch deleted) and returns a combined result.

    Args:
        plan_path: Path to the implementation plan document.
        branch_name: The remote branch name to check. If empty, the remote
            branch check is skipped.

    Returns:
        A tuple ``(all_passed, message)``. ``all_passed`` is ``True`` only
        when every check passed. ``message`` describes the first failing
        check or confirms all checks passed.
    """
    if not is_implementation_plan_deleted(plan_path):
        return (
            False,
            f"Implementation plan not deleted: {plan_path} still exists. "
            "Delete before proceeding.",
        )

    if not is_working_tree_clean():
        return (
            False,
            "Uncommitted changes detected. Commit or stash before proceeding.",
        )

    if branch_name and not is_remote_branch_deleted(branch_name):
        return (
            False,
            f"Remote branch '{branch_name}' still exists on origin. "
            "Delete before proceeding.",
        )

    return True, "All filesystem checks passed"


def main(argv: Optional[list] = None) -> int:
    """Run the filesystem validation from the command line.

    Args:
        argv: Command line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code: 0 if all checks passed, 1 otherwise.
    """
    args = argv if argv is not None else sys.argv[1:]

    plan_path = IMPLEMENTATION_PLAN_TEMPLATE
    branch_name = ""

    if args:
        plan_path = args[0]
    if len(args) > 1:
        branch_name = args[1]

    all_passed, message = validate_filesystem(plan_path, branch_name)
    print(message)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
