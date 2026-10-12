#!/usr/bin/env python3
"""PR merge validation helper for the complete-feature pre-closure validation.

This module provides helper functions to validate that a GitHub pull request is
actually merged before a JIRA ticket is transitioned to "Fertig" (Done). It is
used by the complete-feature workflow (see
`.opencode/skills/complete-feature/SKILL.md`, Step 0.5) and by the
FR-INTEGRITY-001 / QR-INTEGRITY-002 validation gates.

Usage:
    python ci/scripts/validate_pr_merge.py <PR_NUMBER>

Exit codes:
    0  - PR is merged (validation passed)
    1  - PR is not merged or state could not be determined (validation failed)

Environment:
    GITHUB_TOKEN - optional GitHub token for authenticated API access
    GITHUB_REPOSITORY - optional owner/repo for gh pr view

Requirements:
    - GitHub CLI (`gh`) must be installed and authenticated
    - The PR number must be valid and accessible
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Dict, Optional, Tuple

# PR state values returned by `gh pr view --json state`
PR_STATE_MERGED = "MERGED"
PR_STATE_OPEN = "OPEN"
PR_STATE_CLOSED = "CLOSED"

# Fields requested from the GitHub CLI
PR_VIEW_FIELDS = "mergeCommit,state,headRefName"


def get_pr_state(pr_number: int) -> Optional[Dict]:
    """Get PR state using the GitHub CLI.

    Executes ``gh pr view <pr_number> --json mergeCommit,state,headRefName``
    and parses the JSON output.

    Args:
        pr_number: The pull request number to inspect.

    Returns:
        A dictionary with ``mergeCommit``, ``state`` and ``headRefName`` keys
        if the PR could be fetched, or ``None`` if the fetch failed.
    """
    cmd = [
        "gh",
        "pr",
        "view",
        str(pr_number),
        "--json",
        PR_VIEW_FIELDS,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print(
            f"ERROR: Failed to get PR state for PR #{pr_number}: {result.stderr.strip()}"
        )
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Failed to parse PR state JSON for PR #{pr_number}: {exc}")
        return None


def is_pr_merged(pr_state: Dict) -> bool:
    """Check if a PR is actually merged.

    A PR is considered merged only if its state is ``MERGED`` AND a
    ``mergeCommit`` SHA exists. A PR with state ``OPEN`` or ``CLOSED`` is not
    merged.

    Args:
        pr_state: The PR state dictionary returned by :func:`get_pr_state`.

    Returns:
        ``True`` if the PR is merged, ``False`` otherwise.
    """
    return (
        pr_state.get("state") == PR_STATE_MERGED
        and pr_state.get("mergeCommit") is not None
    )


def validate_pr_merge(pr_number: int) -> Tuple[bool, str]:
    """Validate that a PR is merged.

    Fetches the PR state via ``gh pr view`` and checks that the PR is merged.

    Args:
        pr_number: The pull request number to validate.

    Returns:
        A tuple ``(is_valid, message)``. ``is_valid`` is ``True`` when the PR
        is merged; ``message`` contains a human-readable description of the
        result.
    """
    pr_state = get_pr_state(pr_number)

    if pr_state is None:
        return (
            False,
            f"Cannot check PR #{pr_number} state (gh pr view failed). "
            "Verify that gh is authenticated and the PR number is correct.",
        )

    if is_pr_merged(pr_state):
        head_ref = pr_state.get("headRefName", "unknown")
        merge_commit = pr_state.get("mergeCommit", "")
        return (
            True,
            f"PR #{pr_number} is merged (state={PR_STATE_MERGED}, "
            f"head={head_ref}, mergeCommit={merge_commit})",
        )

    current_state = pr_state.get("state", "UNKNOWN")
    return (
        False,
        f"PR #{pr_number} is not merged. Current state: {current_state}. "
        "Cannot transition to Fertig.",
    )


def main(argv: Optional[list] = None) -> int:
    """Run the PR merge validation from the command line.

    Args:
        argv: Command line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code: 0 if the PR is merged, 1 otherwise.
    """
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        print("ERROR: PR number required", file=sys.stderr)
        print(f"Usage: python {sys.argv[0]} <PR_NUMBER>", file=sys.stderr)
        return 1

    try:
        pr_number = int(args[0])
    except ValueError:
        print(
            f"ERROR: Invalid PR number: {args[0]!r} (must be an integer)",
            file=sys.stderr,
        )
        return 1

    is_valid, message = validate_pr_merge(pr_number)
    print(message)
    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
