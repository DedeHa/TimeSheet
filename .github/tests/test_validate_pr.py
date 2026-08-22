"""Unit tests for the consolidated PR validator (O4 / AC-5).

These tests validate the parsing and rendering logic of ``validate_pr.py`` in
isolation. Like the other CI support-script tests, this file lives under
``.github/tests/`` (not in ``tests/``), so it does not change the 103-test
application suite or the coverage gate.

Run with::

    pytest -q .github/tests/test_validate_pr.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "scripts" / "validate_pr.py"
)
_spec = importlib.util.spec_from_file_location("validate_pr", _MODULE_PATH)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["validate_pr"] = mod
_spec.loader.exec_module(mod)


# ---------------------------------------------------------------------------
# Commit message validation
# ---------------------------------------------------------------------------


def test_valid_commit_messages():
    """Commits with Conventional Commits format and JIRA ref pass."""
    messages = [
        "feat(auth): add login endpoint\n\nRefs: PRO-123",
        "fix(ui): correct button alignment\n\nRefs: PRO-124",
    ]
    errors = mod.validate_commit_messages(messages)
    assert errors == []


def test_invalid_conventional_commits_format():
    """Commits without Conventional Commits format are flagged."""
    messages = ["add new feature\n\nRefs: PRO-123"]
    errors = mod.validate_commit_messages(messages)
    assert len(errors) == 1
    assert "Conventional Commits" in errors[0]


def test_missing_jira_reference():
    """Commits without JIRA reference are flagged."""
    messages = ["feat(auth): add login endpoint"]
    errors = mod.validate_commit_messages(messages)
    assert len(errors) == 1
    assert "JIRA reference" in errors[0]


def test_multiple_commits_mixed_validity():
    """Mixed valid/invalid commits produce multiple errors."""
    messages = [
        "feat(auth): add login endpoint\n\nRefs: PRO-123",
        "bad commit message",
    ]
    errors = mod.validate_commit_messages(messages)
    assert len(errors) == 2  # one for CC format, one for missing JIRA ref


def test_empty_commit_messages():
    """Empty commit list produces no errors."""
    errors = mod.validate_commit_messages([])
    assert errors == []


def test_commit_with_multiline_body_and_jira_ref():
    """A commit with a multi-line body containing the JIRA ref is valid.

    Regression test: the old blank-line splitting incorrectly treated body
    paragraphs as separate commits, causing false failures.
    """
    messages = [
        "feat(ci): implement O2 venv caching and O4 consolidated PR validators\n"
        "\n"
        "- O2 (AC-4): Cache virtual environment in setup-python-deps composite action\n"
        "  using actions/cache@v4 keyed on pyproject.toml\n"
        "- O4 (AC-5): Replace four sequential validation steps with single script\n"
        "\n"
        "Refs: PRO-368"
    ]
    errors = mod.validate_commit_messages(messages)
    assert errors == [], f"Expected no errors, got: {errors}"


# ---------------------------------------------------------------------------
# PR title validation
# ---------------------------------------------------------------------------


def test_valid_pr_titles():
    """Valid PR titles pass."""
    valid_titles = [
        "[feat][PRO-123] Add new feature",
        "[fix][PRO-456] Resolve bug",
        "[docs][PRO-789] Update documentation",
        "[refactor][PRO-100] Refactor module",
        "[test][PRO-200] Add unit tests",
        "[chore][PRO-300] Bump dependency",
        "[hotfix][PRO-400] Critical fix",
    ]
    for title in valid_titles:
        errors = mod.validate_pr_title(title)
        assert errors == [], f"Title '{title}' should be valid"


def test_invalid_pr_title_format():
    """Invalid PR titles are flagged."""
    invalid_titles = [
        "Add new feature",  # missing [type][PRO-XXX]
        "[feat] Add feature",  # missing PRO-XXX
        "[feat][PRO-123]",  # missing description
        "[unknown][PRO-123] Add feature",  # invalid type
    ]
    for title in invalid_titles:
        errors = mod.validate_pr_title(title)
        assert len(errors) == 1, f"Title '{title}' should be invalid"


def test_pr_title_case_insensitive():
    """PR title type is case-insensitive."""
    errors = mod.validate_pr_title("[FEAT][PRO-123] Add feature")
    assert errors == []


# ---------------------------------------------------------------------------
# PR body validation
# ---------------------------------------------------------------------------


def test_valid_pr_body():
    """PR body with all required sections passes."""
    body = """## Summary

This is a summary of the changes.

## Testing

These changes were tested with unit tests.

Refs: PRO-123
"""
    errors = mod.validate_pr_body(body)
    assert errors == []


def test_missing_summary_section():
    """PR body without ## Summary is flagged."""
    body = """## Testing

Some testing info.

Refs: PRO-123
"""
    errors = mod.validate_pr_body(body)
    assert len(errors) == 1
    assert "Summary" in errors[0]


def test_missing_testing_section():
    """PR body without ## Testing is flagged."""
    body = """## Summary

Some summary.

Refs: PRO-123
"""
    errors = mod.validate_pr_body(body)
    assert len(errors) == 1
    assert "Testing" in errors[0]


def test_placeholder_text_in_body():
    """PR body with TODO/TBD is flagged."""
    body = """## Summary

This is a summary.

## Testing

TODO: add tests.

Refs: PRO-123
"""
    errors = mod.validate_pr_body(body)
    assert len(errors) == 1
    assert "placeholder" in errors[0].lower()


def test_missing_jira_reference_in_body():
    """PR body without JIRA reference is flagged."""
    body = """## Summary

This is a summary.

## Testing

Some testing info.
"""
    errors = mod.validate_pr_body(body)
    assert len(errors) == 1
    assert "JIRA" in errors[0]


def test_multiple_body_errors():
    """PR body with multiple issues produces multiple errors."""
    body = """## Summary

TODO: write summary.

## Testing

Some testing info.
"""
    errors = mod.validate_pr_body(body)
    assert len(errors) >= 2  # placeholder + missing JIRA ref


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_body():
    """Empty PR body produces errors for all checks except placeholder."""
    errors = mod.validate_pr_body("")
    assert len(errors) == 3  # summary, testing, jira ref


def test_body_with_only_summary():
    """Body with only ## Summary still fails other checks."""
    body = """## Summary

Some summary.
"""
    errors = mod.validate_pr_body(body)
    assert len(errors) == 2  # testing, jira ref
