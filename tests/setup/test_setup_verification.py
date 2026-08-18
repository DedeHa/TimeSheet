"""Test setup verification for PRO-336 CI pipeline standardization.

This module validates that the project's testing environment is correctly
configured after the CI workflow and naming-convention changes:

- Unit tests live under ``tests/unit/``
- Integration tests live under ``tests/integration/``
- System tests live under ``tests/system/``
- CI helper scripts live under ``.github/workflows/`` with underscore names
  (``validate_*``/``generate_*``); workflow tests live under ``.github/tests/``

Run with::

    python -m pytest tests/setup/test_setup_verification.py
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_DIRS = [
    REPO_ROOT / "tests" / "unit",
    REPO_ROOT / "tests" / "integration",
    REPO_ROOT / "tests" / "system",
]
EXPECTED_WORKFLOW_FILES = [
    REPO_ROOT / ".github" / "workflows" / "python-ci.yml",
    REPO_ROOT / ".github" / "actions" / "setup-python-deps" / "action.yml",
    REPO_ROOT / ".github" / "workflows" / "generate_pr_summary.py",
    REPO_ROOT / ".github" / "tests" / "test_docs_traceability.py",
    REPO_ROOT / ".github" / "tests" / "test_generate_pr_summary.py",
    REPO_ROOT / ".github" / "tests" / "test_regression_ci.py",
    REPO_ROOT / ".github" / "tests" / "test_workflow_optimization.py",
]


def test_unit_dir_exists():
    assert EXPECTED_DIRS[0].is_dir(), "tests/unit directory is missing"


def test_integration_dir_exists():
    assert EXPECTED_DIRS[1].is_dir(), "tests/integration directory is missing"


def test_system_dir_exists():
    assert EXPECTED_DIRS[2].is_dir(), "tests/system directory is missing"


def test_workflow_files_exist():
    missing = [str(p) for p in EXPECTED_WORKFLOW_FILES if not p.is_file()]
    assert not missing, f"Missing workflow files: {missing}"


def test_no_underscore_workflow_files():
    workflow_dir = REPO_ROOT / ".github" / "workflows"
    bad = [
        f.name
        for f in workflow_dir.glob("*.py")
        if "_" in f.name
        and f.name
        not in {
            # generate_pr_summary.py is a production generator script (not a
            # test) and legitimately lives in the workflows dir. The
            # traceability test moved to .github/tests/test_docs_traceability.py.
            "generate_pr_summary.py",
        }
    ]
    assert not bad, f"Workflow files still use underscores: {bad}"
