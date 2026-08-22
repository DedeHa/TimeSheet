#!/usr/bin/env python3
"""Consolidated PR validation script (O4 / AC-5).

Replaces four sequential GitHub Actions steps (commit message validation,
Jira reference validation, PR title validation, PR body validation) with a
single Python script that produces a unified, actionable error report.

Validation rules (mirrors the previous workflow steps exactly):
  1. Commit messages: Conventional Commits format + `Refs: PRO-XXX` footer.
  2. PR title: `[type][PRO-XXX] Description`.
  3. PR body: `## Summary` + `## Testing` sections, no placeholder text,
     and a `Refs: PRO-XXX` reference.

Usage:
    python .github/scripts/validate_pr.py

Environment variables (set by the workflow):
    GITHUB_TOKEN          - GitHub token for API calls
    GITHUB_REPOSITORY     - owner/repo
    GITHUB_PR_NUMBER      - pull request number
    GITHUB_BASE_SHA       - base commit SHA
    GITHUB_HEAD_SHA       - head commit SHA

Exit codes:
    0  - all validations passed
    1  - one or more validations failed
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import List

# ---------------------------------------------------------------------------
# Validation rules (must match the previous workflow steps exactly)
# ---------------------------------------------------------------------------

# Conventional Commits types accepted for PR titles
VALID_PR_TYPES = ("feat", "fix", "docs", "refactor", "test", "chore", "hotfix")

# PR title regex: [type][PRO-XXX] Description (case-insensitive)
PR_TITLE_RE = re.compile(
    r"^\[(?:" + "|".join(VALID_PR_TYPES) + r")\]\[PRO-\d+\]\s+.+$",
    re.IGNORECASE,
)

# JIRA reference pattern (Refs: PRO-123)
JIRA_REF_RE = re.compile(r"Refs:\s*PRO-\d+", re.IGNORECASE)

# Placeholder text that is not allowed in PR bodies
PLACEHOLDER_RE = re.compile(
    r"TODO|TBD|Describe your changes\.\.\.|describe your changes\.\.\.",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_pr_metadata() -> dict:
    """Fetch PR metadata (title, body) from the GitHub API."""
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    pr_number = os.environ.get("GITHUB_PR_NUMBER", "")

    if not (token and repo and pr_number):
        print("ERROR: Missing required environment variables for PR metadata")
        sys.exit(1)

    cmd = [
        "gh",
        "pr",
        "view",
        pr_number,
        "--repo",
        repo,
        "--json",
        "title,body",
        "--jq",
        "{title: .title, body: .body}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"ERROR: Failed to fetch PR metadata: {result.stderr}")
        sys.exit(1)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse PR metadata: {e}")
        sys.exit(1)


def get_commit_messages() -> List[str]:
    """Return commit messages between base and head SHA.

    Uses a null-byte separator to reliably split individual commit messages,
    since commit bodies may contain blank lines.
    """
    base = os.environ.get("GITHUB_BASE_SHA", "")
    head = os.environ.get("GITHUB_HEAD_SHA", "")
    if not (base and head):
        print("ERROR: Missing GITHUB_BASE_SHA or GITHUB_HEAD_SHA")
        sys.exit(1)

    # %x00 = null byte separator between commits; %H = hash, %B = full body
    cmd = [
        "git",
        "log",
        "--format=%H%x00%B",
        f"{base}..{head}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"ERROR: Failed to get commit messages: {result.stderr}")
        sys.exit(1)

    # Split on null bytes, then pair hash + message
    parts = result.stdout.split("\x00")
    messages: List[str] = []
    for i in range(0, len(parts) - 1, 2):
        msg = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if msg:
            messages.append(msg)
    return messages


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------


def validate_commit_messages(messages: List[str]) -> List[str]:
    """Validate commit messages (Conventional Commits + JIRA reference).

    Returns a list of error strings (empty if all valid).
    """
    errors: List[str] = []

    # Conventional Commits format: type(scope): description
    # Types: feat, fix, docs, style, refactor, perf, test, chore, ci, build
    cc_re = re.compile(
        r"^(feat|fix|docs|style|refactor|perf|test|chore|ci|build)" r"(\([^)]+\))?: .+"
    )

    for i, msg in enumerate(messages, 1):
        lines = msg.split("\n")
        subject = lines[0] if lines else ""

        # Check Conventional Commits format
        if not cc_re.match(subject):
            errors.append(
                f"Commit {i}: subject line does not match Conventional Commits format "
                f"(expected: type(scope): description). Got: '{subject[:60]}...'"
            )

        # Check for JIRA reference (Refs: PRO-XXX) anywhere in the message
        if not JIRA_REF_RE.search(msg):
            errors.append(
                f"Commit {i}: missing JIRA reference (expected: 'Refs: PRO-XXX'). "
                f"Got: '{subject[:60]}...'"
            )

    return errors


def validate_pr_title(title: str) -> List[str]:
    """Validate PR title format.

    Returns a list of error strings (empty if valid).
    """
    errors: List[str] = []
    if not PR_TITLE_RE.match(title):
        errors.append(
            f"PR title format invalid. Expected: [type][PRO-XXX] Description "
            f"(e.g. [feat][PRO-123] Add feature). Got: '{title}'"
        )
    return errors


def validate_pr_body(body: str) -> List[str]:
    """Validate PR body sections and content.

    Returns a list of error strings (empty if valid).
    """
    errors: List[str] = []

    # Check for ## Summary section
    if not re.search(r"^##\s+Summary\s*$", body, re.MULTILINE):
        errors.append('PR body missing mandatory "## Summary" section')

    # Check for ## Testing section
    if not re.search(r"^##\s+Testing\s*$", body, re.MULTILINE):
        errors.append('PR body missing mandatory "## Testing" section')

    # Check for placeholder text
    if PLACEHOLDER_RE.search(body):
        errors.append("PR body contains placeholder text (TODO, TBD, etc.)")

    # Check for JIRA reference
    if not JIRA_REF_RE.search(body):
        errors.append("PR body must include JIRA reference (Refs: PRO-XXX)")

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Run all validations and report results.

    Returns 0 if all validations pass, 1 otherwise.
    """
    all_errors: List[str] = []

    # 1. Commit message validation
    print("Validating commit messages...")
    try:
        messages = get_commit_messages()
        commit_errors = validate_commit_messages(messages)
        if commit_errors:
            all_errors.extend(commit_errors)
            print(f"  FAIL: {len(commit_errors)} commit message error(s)")
        else:
            print(f"  OK: {len(messages)} commit message(s) valid")
    except Exception as e:
        all_errors.append(f"Commit message validation failed: {e}")
        print(f"  ERROR: {e}")

    # 2. PR title validation
    print("Validating PR title...")
    try:
        metadata = get_pr_metadata()
        title = metadata.get("title", "")
        body = metadata.get("body", "")
        title_errors = validate_pr_title(title)
        if title_errors:
            all_errors.extend(title_errors)
            print("  FAIL: PR title invalid")
        else:
            print("  OK: PR title valid")
    except Exception as e:
        all_errors.append(f"PR title validation failed: {e}")
        print(f"  ERROR: {e}")

    # 3. PR body validation
    print("Validating PR body...")
    try:
        body_errors = validate_pr_body(body)
        if body_errors:
            all_errors.extend(body_errors)
            print(f"  FAIL: {len(body_errors)} PR body error(s)")
        else:
            print("  OK: PR body valid")
    except Exception as e:
        all_errors.append(f"PR body validation failed: {e}")
        print(f"  ERROR: {e}")

    # Report
    print()
    if all_errors:
        print("=" * 60)
        print("PR VALIDATION FAILED")
        print("=" * 60)
        for error in all_errors:
            print(f"  - {error}")
        print()
        print("Please fix the above issues and push an updated commit.")
        return 1
    else:
        print("=" * 60)
        print("PR VALIDATION PASSED")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    sys.exit(main())
