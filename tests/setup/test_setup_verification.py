"""Test setup verification for PRO-336 CI pipeline standardization.

This module validates that the project's testing environment is correctly
configured after the CI workflow and naming-convention changes:

- Unit tests live under ``tests/unit/``
- Integration tests live under ``tests/integration/``
- System tests live under ``tests/system/``
- ``.github/workflows/`` holds workflow definitions only (no ``.py`` scripts)
- ``.github/scripts/`` holds CI support scripts (``verb_subject``, e.g.
  ``generate_pr_summary``); ``.github/tests/ci-pipeline/`` holds their unit
  tests (``test_verb_subject``), and ``tests/`` holds agent-team
  and opencode script tests.

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
GITHUB_DIR = REPO_ROOT / ".github"
WORKFLOWS_DIR = GITHUB_DIR / "workflows"
SCRIPTS_DIR = GITHUB_DIR / "scripts"
TESTS_DIR = GITHUB_DIR / "tests" / "ci-pipeline"
OPENCODE_TESTS_DIR = REPO_ROOT / "tests"
OPENCODE_AGENT_TESTS_DIR = OPENCODE_TESTS_DIR / "agents"
OPENCODE_SCRIPT_TESTS_DIR = OPENCODE_TESTS_DIR / "opencode"

EXPECTED_CI_FILES = [
    WORKFLOWS_DIR / "python-ci.yml",
    GITHUB_DIR / "actions" / "setup-python-deps" / "action.yml",
    SCRIPTS_DIR / "generate_pr_summary.py",
    SCRIPTS_DIR / "generate_traceability_matrix.py",
    SCRIPTS_DIR / "validate_pr.py",
    TESTS_DIR / "test_generate_pr_summary.py",
    TESTS_DIR / "test_generate_traceability_matrix.py",
    TESTS_DIR / "test_validate_pr.py",
    TESTS_DIR / "test_verify_ci_workflow.py",
]


def test_unit_dir_exists():
    assert EXPECTED_DIRS[0].is_dir(), "tests/unit directory is missing"


def test_integration_dir_exists():
    assert EXPECTED_DIRS[1].is_dir(), "tests/integration directory is missing"


def test_system_dir_exists():
    assert EXPECTED_DIRS[2].is_dir(), "tests/system directory is missing"


def test_ci_files_exist():
    missing = [str(p) for p in EXPECTED_CI_FILES if not p.is_file()]
    assert not missing, f"Missing CI files: {missing}"


def test_workflows_dir_has_only_definitions():
    """.github/workflows/ holds workflow definitions only - no Python scripts."""
    stray = [f.name for f in WORKFLOWS_DIR.glob("*.py")]
    assert (
        not stray
    ), f"Python scripts must live in .github/scripts/, not workflows/: {stray}"


def test_ci_scripts_are_not_named_as_tests():
    """.github/scripts/ holds production scripts (verb_subject), never test_*."""
    bad = [f.name for f in SCRIPTS_DIR.glob("*.py") if f.name.startswith("test_")]
    assert not bad, f"Test files must live in .github/tests/, not scripts/: {bad}"


def test_ci_tests_use_test_prefix():
    """CI support tests and opencode tests use the test_* module prefix."""
    bad = [f.name for f in TESTS_DIR.glob("*.py") if not f.name.startswith("test_")]
    for directory in (OPENCODE_AGENT_TESTS_DIR, OPENCODE_SCRIPT_TESTS_DIR):
        bad += [
            f.name for f in directory.glob("*.py") if not f.name.startswith("test_")
        ]
    assert not bad, f"Test directories must contain only test_* files: {bad}"


def test_opencode_test_directories_exist():
    """Agent and script tests are owned by the opencode subsystem."""
    assert OPENCODE_AGENT_TESTS_DIR.is_dir()
    assert OPENCODE_SCRIPT_TESTS_DIR.is_dir()
