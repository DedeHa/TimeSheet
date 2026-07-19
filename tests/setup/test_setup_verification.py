"""Test setup verification for PRO-336 CI pipeline standardization.

This module validates that the project's testing environment is correctly
configured after the CI workflow and naming-convention changes:

- Unit tests live under ``tests/@tests/unit/``
- Integration tests live under ``tests/integration/``
- System tests live under ``tests/system/``
- CI support scripts live under ``.github/workflows/`` with hyphenated names

Run with::

    python -m pytest tests/setup/test_setup_verification.py
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_DIRS = [
    REPO_ROOT / "tests" / "@tests" / "unit",
    REPO_ROOT / "tests" / "integration",
    REPO_ROOT / "tests" / "system",
]
EXPECTED_WORKFLOW_FILES = [
    REPO_ROOT / ".github" / "workflows" / "python-ci.yml",
    REPO_ROOT / ".github" / "workflows" / "pr-test-summary.py",
    REPO_ROOT / ".github" / "workflows" / "test-docs-traceability.py",
    REPO_ROOT / ".github" / "workflows" / "test-pr-test-summary.py",
    REPO_ROOT / ".github" / "workflows" / "naming-validation.py",
]


def test_unit_dir_exists():
    assert EXPECTED_DIRS[0].is_dir(), "tests/@tests/unit directory is missing"


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
        if "_" in f.name and f.name not in {"naming_validation.py"}
    ]
    assert not bad, f"Workflow files still use underscores: {bad}"
