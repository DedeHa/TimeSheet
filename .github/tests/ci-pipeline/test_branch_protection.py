"""Unit tests for the branch protection script (PRO-386).

Like the other CI support-script tests, this file lives under
``.github/tests/ci-pipeline/`` (not in ``tests/``), so it does not change the
103-test application suite or the coverage gate.

Run with::

    pytest -q .github/tests/ci-pipeline/test_branch_protection.py
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

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


# ---------------------------------------------------------------------------
# CLI dispatch tests (main / argparse)
# ---------------------------------------------------------------------------


def test_main_help_exits_zero(monkeypatch):
    """main() with --help prints help and exits 0."""
    monkeypatch.setattr(sys, "argv", ["branch_protection.py", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        mod.main()
    assert exc_info.value.code == 0


def test_main_no_subcommand_exits_error(monkeypatch):
    """main() with no subcommand exits with error."""
    monkeypatch.setattr(sys, "argv", ["branch_protection.py"])
    with pytest.raises(SystemExit) as exc_info:
        mod.main()
    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# CLI dispatch tests with mocked GitHub API
# ---------------------------------------------------------------------------


class FakeGhOutput:
    """Mock for the stdout returned by subprocess.run for gh api calls."""

    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.returncode = 0


def _mock_gh_repo_view(cmd: list[str], **kwargs) -> FakeGhOutput:
    """Mock for the gh repo view call (resolves owner/repo)."""
    return FakeGhOutput('{"owner": {"login": "test"}, "name": "repo"}')


def _mock_gh_protection(cmd: list[str], **kwargs) -> FakeGhOutput:
    """Mock for the GET /branches/{branch}/protection call (verify)."""
    return FakeGhOutput(
        json.dumps(
            {
                "required_status_checks": {
                    "strict": False,
                    "checks": [
                        {"context": "Python CI / Naming Conventions & Linting Check"},
                    ],
                }
            }
        )
    )


def test_main_verify_success(monkeypatch) -> None:
    """main() verify subcommand succeeds when the required check is present."""

    def mock_run(cmd: list[str], **kwargs) -> FakeGhOutput:
        if cmd[1] == "repo" and cmd[2] == "view":
            return _mock_gh_repo_view(cmd, **kwargs)
        return _mock_gh_protection(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(
        sys, "argv", ["branch_protection.py", "verify", "--branch", "master"]
    )
    exit_code = mod.main()
    assert exit_code == 0, "verify should succeed when the required check is configured"


def test_main_verify_missing_check(monkeypatch) -> None:
    """main() verify subcommand fails when the required check is missing."""
    protection = {"required_status_checks": {"checks": [{"context": "Other check"}]}}

    def mock_run(cmd: list[str], **kwargs) -> FakeGhOutput:
        if cmd[1] == "repo" and cmd[2] == "view":
            return _mock_gh_repo_view(cmd, **kwargs)
        return FakeGhOutput(json.dumps(protection))

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(
        sys, "argv", ["branch_protection.py", "verify", "--branch", "master"]
    )
    exit_code = mod.main()
    assert exit_code == 1, "verify should fail when the required check is missing"


def test_main_apply(monkeypatch) -> None:
    """main() apply subcommand sets branch protection."""

    def mock_run(cmd: list[str], **kwargs) -> FakeGhOutput:
        if cmd[1] == "repo" and cmd[2] == "view":
            return _mock_gh_repo_view(cmd, **kwargs)
        return FakeGhOutput("")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(
        sys, "argv", ["branch_protection.py", "apply", "--branch", "master"]
    )
    exit_code = mod.main()
    assert exit_code == 0, "apply should succeed"


def test_main_apply_failure(monkeypatch) -> None:
    """main() apply subcommand fails when gh api returns an error."""

    def mock_run(cmd: list[str], **kwargs) -> FakeGhOutput:
        if cmd[1] == "repo" and cmd[2] == "view":
            return _mock_gh_repo_view(cmd, **kwargs)
        raise subprocess.CalledProcessError(1, cmd, stderr="API error")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(
        sys, "argv", ["branch_protection.py", "apply", "--branch", "master"]
    )
    exit_code = mod.main()
    assert exit_code == 1, "apply should fail when gh api errors"


def test_main_verify_api_failure(monkeypatch) -> None:
    """main() verify subcommand fails when the API call errors."""

    def mock_run(cmd: list[str], **kwargs) -> FakeGhOutput:
        if cmd[1] == "repo" and cmd[2] == "view":
            return _mock_gh_repo_view(cmd, **kwargs)
        raise subprocess.CalledProcessError(1, cmd, stderr="API error")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(
        sys, "argv", ["branch_protection.py", "verify", "--branch", "master"]
    )
    exit_code = mod.main()
    assert exit_code == 1, "verify should fail when the API call errors"
