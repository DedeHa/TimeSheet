"""Regression tests for the PRO-368 CI optimizations.

These tests assert that the changes made to ``python-ci.yml`` do not alter any
of the existing quality gates, branch strategy, or deployment behaviour. Like
``test_docs_traceability.py`` this file lives under ``.github/tests/`` (not
in ``tests/``), so it does not change the 103-test application suite or the
coverage gate. It is executed explicitly by the CI ``test`` job and can be
run locally with::

    pytest -q .github/tests/test_regression_ci.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "python-ci.yml"
COMMITLINT = ROOT / ".commitlintrc.json"
CONTRIBUTING = ROOT / "doc" / "CONTRIBUTING.md"


def _workflow() -> dict:
    # PyYAML parses the YAML key "on:" as the Python boolean True (YAML 1.1
    # quirk), so read it through that key instead.
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _triggers() -> dict:
    return _workflow()[True]


def _commitlint() -> dict:
    import json

    return json.loads(COMMITLINT.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Branch strategy enforcement (unchanged).
# ---------------------------------------------------------------------------


def test_prs_only_to_master_and_release():
    """Branch strategy: CI triggers only on PRs to master/release/* and tags."""
    triggers = _triggers()
    assert "pull_request" in triggers
    assert "master" in triggers["pull_request"]["branches"]
    assert any(b.startswith("release/") for b in triggers["pull_request"]["branches"])
    assert "push" in triggers
    assert any(t.startswith("v") for t in triggers["push"]["tags"])


def test_branch_push_does_not_trigger_ci():
    """Branch pushes must not trigger CI; only PRs, tags and manual runs do."""
    triggers = _triggers()
    assert "branches" not in triggers.get("push", {})
    assert "workflow_dispatch" in triggers


# ---------------------------------------------------------------------------
# Quality gates (unchanged).
# ---------------------------------------------------------------------------


def test_commit_types_unchanged():
    """The allowed Conventional Commit types must not be narrowed."""
    types = _commitlint()["rules"]["type-enum"][2]
    for required in ("feat", "fix", "docs", "refactor", "test", "chore", "ci", "build"):
        assert required in types, f"commit type {required} was removed"


def test_pr_title_regex_unchanged():
    """The PR title validator still accepts [type][PRO-XXX] Description."""
    steps = _workflow()["jobs"]["check"]["steps"]
    title_step = next(s for s in steps if s.get("name") == "Validate PR Title")
    script = title_step["with"]["script"]
    assert r"PRO-\\d+" in script
    assert "feat|fix|docs|refactor|test|chore|hotfix" in script


def test_pr_body_sections_required():
    """The PR body validator still requires ## Summary and ## Testing."""
    steps = _workflow()["jobs"]["check"]["steps"]
    body_step = next(s for s in steps if s.get("name") == "Validate PR Body")
    script = body_step["with"]["script"]
    assert "## Summary" in script
    assert "## Testing" in script
    assert "Refs: PRO-" in script


def test_coverage_gate_still_90_percent():
    """The 90% coverage gate must still be enforced in the test job."""
    steps = _workflow()["jobs"]["test"]["steps"]
    gate_runs = [s.get("run", "") for s in steps if "fail-under=90" in s.get("run", "")]
    assert gate_runs, "the 90% coverage gate step is missing"


# ---------------------------------------------------------------------------
# Deployment strategy (unchanged).
# ---------------------------------------------------------------------------


def test_deploy_only_on_release_tags():
    """Deployment must still be gated on release tags (vX.Y.Z)."""
    deploy = _workflow()["jobs"]["deploy"]
    assert "startsWith(github.ref, 'refs/tags/v')" in deploy["if"]
    assert deploy["environment"] == "production"


def test_deploy_needs_check_and_test():
    """The deploy job must still depend on check and test."""
    assert _workflow()["jobs"]["deploy"]["needs"] == ["check", "test"]


def test_test_job_runs_on_prs_tags_and_dispatch():
    """The test job runs the full suite on PRs, release tags and manual dispatch.

    PRO-368 originally restricted the test job to PRs targeting master. The
    release gate now also enforces the full suite on release/** PRs and on
    release tags (before deploy), so the base_ref == 'master' restriction is
    gone and the job triggers on pull_request, tag pushes and workflow_dispatch.
    """
    test = _workflow()["jobs"]["test"]
    condition = test["if"]
    assert "github.base_ref == 'master'" not in condition
    assert "pull_request" in condition
    assert "refs/tags/v" in condition
    assert "workflow_dispatch" in condition


# ---------------------------------------------------------------------------
# Workflow behaviour (unchanged).
# ---------------------------------------------------------------------------


def test_concurrency_grouping_unchanged():
    """The concurrency group must still cancel in-progress runs per PR."""
    group = _workflow()["concurrency"]["group"]
    assert "github.event.pull_request.number" in group
    assert "github.ref" in group
    assert _workflow()["concurrency"]["cancel-in-progress"] is True


def test_node24_migration_env_var_unchanged():
    """The Node 24 migration env var must still be set for JS actions."""
    assert _workflow()["env"]["FORCE_JAVASCRIPT_ACTIONS_TO_NODE24"] is True


def test_commitlint_config_unchanged():
    """The commitlint config must still enforce header-max-length 100."""
    assert _commitlint()["rules"]["header-max-length"] == [2, "always", 100]


def test_contributing_branch_strategy_unchanged():
    """CONTRIBUTING.md must still document the trunk-based branch strategy."""
    text = CONTRIBUTING.read_text(encoding="utf-8")
    for prefix in ("feature/", "bugfix/", "hotfix/", "refactor/", "docs/", "test/"):
        assert prefix in text, f"CONTRIBUTING.md no longer documents {prefix}"


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
