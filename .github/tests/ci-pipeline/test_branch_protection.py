"""Unit tests for the branch protection script (PRO-386).

Like the other CI support-script tests, this file lives under
``.github/tests/ci-pipeline/`` (not in ``tests/``), so it does not change the
103-test application suite or the coverage gate.

Run with::

    pytest -q .github/tests/ci-pipeline/test_branch_protection.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[3] / ".github" / "scripts" / "branch_protection.py"
)
_spec = importlib.util.spec_from_file_location("branch_protection", _MODULE_PATH)
mod = importlib.util.module_from_spec(_spec)
sys.modules["branch_protection"] = mod
_spec.loader.exec_module(mod)


# ---------------------------------------------------------------------------
# Guard tests: ensure the declarative required-status-checks list is correct
# ---------------------------------------------------------------------------


def test_required_status_checks_not_empty():
    """Guard test: required status checks list must be non-empty."""
    assert (
        mod.REQUIRED_STATUS_CHECKS
    ), "REQUIRED_STATUS_CHECKS must be non-empty (regression guard for AC-3)"


def test_naming_lint_context_in_required_list():
    """Guard test: the "Naming Conventions & Linting Check" context is required."""
    expected = "Python CI / Naming Conventions & Linting Check"
    assert (
        expected in mod.REQUIRED_STATUS_CHECKS
    ), f"Expected context '{expected}' must be in REQUIRED_STATUS_CHECKS (AC-2)"


def test_master_in_protected_branches():
    """Guard test: master must be in PROTECTED_BRANCHES."""
    assert "master" in mod.PROTECTED_BRANCHES, "master must be protected"


# ---------------------------------------------------------------------------
# Helper / fixture tests for extract_context_names and verify logic
# ---------------------------------------------------------------------------


def test_extract_context_names_from_checks():
    """extract_context_names correctly parses the 'checks' form."""
    protection = {
        "required_status_checks": {
            "checks": [
                {"context": "Python CI / Naming Conventions & Linting Check"},
                {"context": "Other check"},
            ],
            "strict": True,
        },
        "enforcement_level": "non_admins",
    }
    contexts = mod.extract_context_names(protection)
    expected = {"Python CI / Naming Conventions & Linting Check", "Other check"}
    assert set(contexts) == expected


def test_extract_context_names_from_contexts():
    """extract_context_names correctly parses the legacy 'contexts' form."""
    protection = {
        "required_status_checks": {
            "contexts": ["Python CI / Naming Conventions & Linting Check"],
        },
    }
    contexts = mod.extract_context_names(protection)
    assert contexts == ["Python CI / Naming Conventions & Linting Check"]


def test_extract_context_names_empty():
    """extract_context_names returns empty list when no required checks configured."""
    protection = {"required_status_checks": {}}
    contexts = mod.extract_context_names(protection)
    assert contexts == []


def test_verify_empty_checks_returns_error():
    """verify() returns error when required_status_checks.checks is empty."""
    protection = {"required_status_checks": {"checks": []}}
    required = ["Python CI / Naming Conventions & Linting Check"]
    errors = mod.verify(required, protection, "test-branch")
    assert len(errors) == 1
    assert "EMPTY" in errors[0] or "empty" in errors[0].lower()


def test_verify_missing_context_returns_error():
    """verify() returns error when a required context is missing."""
    protection = {"required_status_checks": {"checks": [{"context": "Other check"}]}}
    required = ["Python CI / Naming Conventions & Linting Check"]
    errors = mod.verify(required, protection, "test-branch")
    assert len(errors) == 1
    assert "missing" in errors[0].lower()


def test_verify_all_contexts_present():
    """verify() returns no errors when all required contexts are present."""
    protection = {
        "required_status_checks": {
            "checks": [{"context": "Python CI / Naming Conventions & Linting Check"}],
        },
    }
    required = ["Python CI / Naming Conventions & Linting Check"]
    errors = mod.verify(required, protection, "test-branch")
    assert errors == []


def test_verify_multiple_contexts_present():
    """verify() works when multiple required contexts are all present."""
    required = [
        "Python CI / Naming Conventions & Linting Check",
        "Other check",
    ]
    protection = {
        "required_status_checks": {
            "checks": [
                {"context": "Python CI / Naming Conventions & Linting Check"},
                {"context": "Other check"},
            ],
        },
    }
    errors = mod.verify(required, protection, "test-branch")
    assert errors == []
