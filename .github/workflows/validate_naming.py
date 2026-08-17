#!/usr/bin/env python3
"""
GitHub Actions naming validation script.

Validates commit messages and PR titles against project conventions:
- Conventional Commits format: type(scope): description
- PR titles: [Type][PRO-123] Description or [Type] Description
"""

import os
import re
import subprocess
import sys
from typing import List

# Allowed commit types per Conventional Commits + project spec
ALLOWED_COMMIT_TYPES = {
    "feat",
    "fix",
    "docs",
    "refactor",
    "test",
    "chore",
    "style",
    "perf",
    "ci",
    "build",
}

ALLOWED_PR_TYPES = ALLOWED_COMMIT_TYPES | {"hotfix"}

# Commit message pattern: type(scope): description
COMMIT_PATTERN = re.compile(
    r"^(?P<type>feat|fix|docs|refactor|test|chore|style|perf|ci|build)"
    r"(\((?P<scope>[^)]+)\))?:\s*(?P<description>.+)$"
)

# PR title patterns: [type][PRO-123] Description or [type] Description
PR_WITH_JIRA_PATTERN = re.compile(
    r"^\[(?P<type>feat|fix|docs|refactor|test|chore|hotfix)\]"
    r"\[(?P<jira>PRO-\d+)\]\s+(?P<description>.+)$"
)

PR_WITHOUT_JIRA_PATTERN = re.compile(
    r"^\[(?P<type>feat|fix|docs|refactor|test|chore|hotfix)\]\s+(?P<description>.+)$"
)


def validate_commit_message(message: str) -> List[str]:
    """Return a list of validation errors for a commit message."""
    errors: List[str] = []
    if not message or not message.strip():
        errors.append("Commit message must not be empty.")
        return errors

    lines = message.strip().splitlines()
    subject = lines[0].strip()
    match = COMMIT_PATTERN.match(subject)
    if not match:
        errors.append(
            "Commit message must follow the Conventional Commits format: "
            "type(scope): description"
        )
        return errors

    description = match.group("description")
    if len(description) > 50:
        errors.append("Commit descriptions must be 50 characters or fewer.")

    # Check JIRA reference in footer if present
    footer_lines = [line.strip() for line in lines[1:] if line.strip()]
    for line in footer_lines:
        if line.startswith("Refs:"):
            if not re.fullmatch(r"Refs:\s*PRO-\d+", line):
                errors.append(
                    "If a JIRA reference is included, it must use the footer format: "
                    "'Refs: PRO-123'"
                )
            break

    return errors


def validate_pr_title(title: str) -> List[str]:
    """Return a list of validation errors for a pull request title."""
    errors: List[str] = []
    if not title or not title.strip():
        errors.append("Pull request title must not be empty.")
        return errors

    title = title.strip()
    match = PR_WITH_JIRA_PATTERN.match(title)
    if match:
        description = match.group("description")
        if len(description) > 72:
            errors.append("Pull request titles must be 72 characters or fewer.")
        return errors

    match = PR_WITHOUT_JIRA_PATTERN.match(title)
    if match:
        description = match.group("description")
        if len(description) > 72:
            errors.append("Pull request titles must be 72 characters or fewer.")
        return errors

    errors.append(
        "Pull request title must follow one of the documented formats: "
        "[type][PRO-123] Description or [type] Description"
    )
    return errors


def validate_messages(messages: List[str]) -> List[str]:
    """Validate a sequence of commit messages and return all errors."""
    errors: List[str] = []
    for index, message in enumerate(messages, start=1):
        for error in validate_commit_message(message):
            errors.append(f"Commit {index}: {error}")
    return errors


def validate_titles(titles: List[str]) -> List[str]:
    """Validate a sequence of pull request titles and return all errors."""
    errors: List[str] = []
    for index, title in enumerate(titles, start=1):
        for error in validate_pr_title(title):
            errors.append(f"Pull request {index}: {error}")
    return errors


def get_commits_to_validate(before_sha: str, after_sha: str) -> List[str]:
    """
    Get list of commit messages to validate for a push event.
    """
    if before_sha == "0" * 40 or before_sha == "0" * 40:
        result = subprocess.run(
            ["git", "log", "--oneline", "--format=%B", after_sha],
            capture_output=True,
            text=True,
        )
    else:
        result = subprocess.run(
            ["git", "log", "--format=%B", f"{before_sha}..{after_sha}"],
            capture_output=True,
            text=True,
        )

    if result.returncode != 0:
        print(f"Warning: Failed to get commits: {result.stderr}")
        return []

    commits = [c.strip() for c in result.stdout.strip().split("\n\n") if c.strip()]
    return commits


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    sha = os.environ.get("GITHUB_SHA", "")
    before_sha = os.environ.get("BEFORE_SHA", "")
    pr_title = os.environ.get("PR_TITLE", "")

    print(f"Event: {event_name}")
    print(f"SHA: {sha}")
    print(f"Before SHA: {before_sha}")

    all_errors = []

    if event_name == "pull_request":
        print(f"Validating PR title: '{pr_title}'")
        errors = validate_pr_title(pr_title)
        if errors:
            all_errors.extend([f"PR Title: {e}" for e in errors])

        if before_sha and before_sha != "0" * 40:
            commits = get_commits_to_validate(before_sha, sha)
            print(f"Found {len(commits)} commits to validate in PR")
            for i, commit in enumerate(commits, 1):
                errors = validate_commit_message(commit)
                if errors:
                    all_errors.extend([f"Commit {i}: {e}" for e in errors])

    elif event_name == "push":
        commits = get_commits_to_validate(before_sha, sha)
        print(f"Found {len(commits)} commits to validate in push")
        for i, commit in enumerate(commits, 1):
            errors = validate_commit_message(commit)
            if errors:
                all_errors.extend([f"Commit {i}: {e}" for e in errors])

    if all_errors:
        print("\n❌ NAMING VALIDATION FAILED:")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print("✅ All naming validations passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
