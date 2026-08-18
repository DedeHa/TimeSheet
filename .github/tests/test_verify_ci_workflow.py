"""Structural verification of the CI workflow ``python-ci.yml`` (PRO-368).

Consolidates the former ``test_workflow_optimization.py`` (asserts the PRO-368
optimizations are in place) and ``test_regression_ci.py`` (asserts the existing
quality gates, branch strategy and deployment behaviour are unchanged) into a
single workflow-verification suite, removing the duplicated YAML-parsing
helpers. Like the other files under ``.github/tests/`` it does not affect the
103-test application suite or the coverage gate, and can be run locally with::

    pytest -q .github/tests/test_verify_ci_workflow.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "python-ci.yml"
ACTION = ROOT / ".github" / "actions" / "setup-python-deps" / "action.yml"
COMMITLINT = ROOT / ".commitlintrc.json"
CONTRIBUTING = ROOT / "doc" / "CONTRIBUTING.md"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _action() -> dict:
    return yaml.safe_load(ACTION.read_text(encoding="utf-8"))


def _triggers() -> dict:
    # PyYAML parses the YAML key "on:" as the Python boolean True (YAML 1.1
    # quirk), so read it through that key instead.
    return _workflow()[True]


def _commitlint() -> dict:
    return json.loads(COMMITLINT.read_text(encoding="utf-8"))


def _job_steps(job_name: str) -> list[dict]:
    return _workflow()["jobs"][job_name]["steps"]


def _uses(step: dict) -> str:
    return step.get("uses", "")


# ---------------------------------------------------------------------------
# AC1 / AC2 / AC4: composite action centralises setup, caching and install.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("job", ["check", "test", "deploy"])
def test_python_job_uses_caching_composite_action(job: str):
    """Every Python job delegates setup to the reusable composite action."""
    steps = _job_steps(job)
    assert any(
        _uses(step) == "./.github/actions/setup-python-deps" for step in steps
    ), f"{job} job does not use the setup-python-deps composite action"


@pytest.mark.parametrize("job", ["check", "test", "deploy"])
def test_python_job_no_longer_has_inline_setup_python(job: str):
    """The old duplicated actions/setup-python + pip install blocks are gone."""
    steps = _job_steps(job)
    setup_steps = [s for s in steps if _uses(s).startswith("actions/setup-python")]
    assert setup_steps == [], f"{job} job still has an inline actions/setup-python step"
    install_steps = [
        s for s in steps if s.get("run", "").strip().startswith("pip install -e .[dev]")
    ]
    assert (
        install_steps == []
    ), f"{job} job still has an inline pip install -e .[dev] step"


def test_composite_action_enables_pip_cache():
    """AC1: the composite action passes cache: pip to actions/setup-python."""
    action = _action()
    setup_step = next(
        s
        for s in action["runs"]["steps"]
        if _uses(s).startswith("actions/setup-python")
    )
    assert setup_step["with"]["cache"] == "pip"
    assert setup_step["with"]["cache-dependency-path"] == "pyproject.toml"


def test_composite_action_centralises_setup_and_install():
    """AC2: the composite action covers Python setup and dependency install.

    Checkout is intentionally NOT part of the composite action: a local (``./``)
    action cannot be resolved until the repository is already on the runner, so
    each job runs ``actions/checkout`` first (see
    :func:`test_job_checks_out_before_composite_action`).
    """
    action = _action()
    assert action["runs"]["using"] == "composite"
    uses = [_uses(s) for s in action["runs"]["steps"]]
    assert not any(
        u.startswith("actions/checkout") for u in uses
    ), "checkout must live in each job, not in the composite action"
    assert any(u.startswith("actions/setup-python") for u in uses)
    assert any(
        "pip install -e .[dev]" in s.get("run", "") for s in action["runs"]["steps"]
    )


@pytest.mark.parametrize("job", ["check", "test", "deploy"])
def test_job_checks_out_before_composite_action(job: str):
    """Each job runs actions/checkout before the local composite action."""
    steps = _job_steps(job)
    checkout_idx = next(
        (i for i, s in enumerate(steps) if _uses(s).startswith("actions/checkout")),
        None,
    )
    composite_idx = next(
        (
            i
            for i, s in enumerate(steps)
            if _uses(s) == "./.github/actions/setup-python-deps"
        ),
        None,
    )
    assert checkout_idx is not None, f"{job} job is missing actions/checkout"
    assert composite_idx is not None, f"{job} job is missing the composite action"
    assert (
        checkout_idx < composite_idx
    ), f"{job} job must checkout before the local composite action"


# ---------------------------------------------------------------------------
# AC3: unnecessary Node.js installation removed; Node 24 env var retained.
# ---------------------------------------------------------------------------


def test_setup_node_removed_from_check_job():
    """AC3: the check job no longer installs Node.js unconditionally."""
    steps = _job_steps("check")
    node_steps = [s for s in steps if _uses(s).startswith("actions/setup-node")]
    assert node_steps == [], "actions/setup-node is still present in the check job"


def test_node24_migration_env_var_set():
    """The Node 24 migration env var is still set for JavaScript actions."""
    assert _workflow()["env"]["FORCE_JAVASCRIPT_ACTIONS_TO_NODE24"] is True


# ---------------------------------------------------------------------------
# AC5: independent, separately-attributable validation steps.
# ---------------------------------------------------------------------------


def test_validation_steps_are_independent():
    """AC5: the commit / PR-title / PR-body validators are separate steps."""
    steps = _job_steps("check")
    names = [s.get("name", "") for s in steps]
    assert "Validate commit messages" in names
    assert "Validate Jira reference in commits" in names
    assert "Validate PR Title" in names
    assert "Validate PR Body" in names
    # They must not be nested inside a single script step.
    assert not any("validate_pr" in s.get("run", "") for s in steps)


def test_validation_steps_fail_the_job_on_error():
    """AC5: the PRO-368 validators (Jira ref, PR title, PR body) hard-fail."""
    steps = _job_steps("check")
    validators = [
        s
        for s in steps
        if s.get("name", "")
        in {
            "Validate Jira reference in commits",
            "Validate PR Title",
            "Validate PR Body",
        }
    ]
    assert validators, "validation steps not found"
    for step in validators:
        assert (
            step.get("continue-on-error") is False
        ), f"{step['name']} must not use continue-on-error: true"


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


def test_commitlint_header_length_unchanged():
    """The commitlint config must still enforce header-max-length 100."""
    assert _commitlint()["rules"]["header-max-length"] == [2, "always", 100]


def test_pr_title_regex_unchanged():
    """The PR title validator still accepts [type][PRO-XXX] Description."""
    steps = _job_steps("check")
    title_step = next(s for s in steps if s.get("name") == "Validate PR Title")
    script = title_step["with"]["script"]
    assert r"PRO-\\d+" in script
    assert "feat|fix|docs|refactor|test|chore|hotfix" in script


def test_pr_body_sections_required():
    """The PR body validator still requires ## Summary and ## Testing."""
    steps = _job_steps("check")
    body_step = next(s for s in steps if s.get("name") == "Validate PR Body")
    script = body_step["with"]["script"]
    assert "## Summary" in script
    assert "## Testing" in script
    assert "Refs: PRO-" in script


def test_coverage_gate_is_90_percent():
    """The 90% coverage gate must still be enforced in the test job."""
    steps = _job_steps("test")
    gate_steps = [s for s in steps if "fail-under=90" in s.get("run", "")]
    assert gate_steps, "the 90% coverage gate step is missing"


# ---------------------------------------------------------------------------
# Deployment strategy (unchanged).
# ---------------------------------------------------------------------------


def test_deploy_only_on_release_tags():
    """Deployment must still be gated on release tags and target production."""
    deploy = _workflow()["jobs"]["deploy"]
    assert "startsWith(github.ref, 'refs/tags/v')" in deploy["if"]
    assert deploy["environment"] == "production"


def test_test_job_runs_on_prs_tags_and_dispatch():
    """The test job runs the full suite on PRs, release tags and manual dispatch.

    PRO-368 originally restricted the test job to PRs targeting master. The
    release gate now also enforces the full suite on release/** PRs and on
    release tags (before deploy), so the base_ref == 'master' restriction is
    gone and the job triggers on pull_request, tag pushes and workflow_dispatch.
    """
    condition = _workflow()["jobs"]["test"]["if"]
    assert "github.base_ref == 'master'" not in condition
    assert "pull_request" in condition
    assert "refs/tags/v" in condition
    assert "workflow_dispatch" in condition


# ---------------------------------------------------------------------------
# Pipeline graph & workflow behaviour (unchanged).
# ---------------------------------------------------------------------------


def test_pipeline_graph():
    """The job graph is check -> test -> {summary, deploy}."""
    workflow = _workflow()
    assert set(workflow["jobs"]) == {"check", "test", "summary", "deploy"}
    assert workflow["jobs"]["test"]["needs"] == ["check"]
    assert workflow["jobs"]["summary"]["needs"] == ["check", "test"]
    assert workflow["jobs"]["deploy"]["needs"] == ["check", "test"]


def test_summary_job_always_runs_on_prs():
    """The summary job publishes the PR comment even when check/test fail."""
    summary = _workflow()["jobs"]["summary"]
    assert "always()" in summary["if"]
    assert "pull_request" in summary["if"]


def test_concurrency_grouping_unchanged():
    """The concurrency group must still cancel in-progress runs per PR."""
    concurrency = _workflow()["concurrency"]
    assert "github.event.pull_request.number" in concurrency["group"]
    assert "github.ref" in concurrency["group"]
    assert concurrency["cancel-in-progress"] is True


def test_contributing_branch_strategy_unchanged():
    """CONTRIBUTING.md must still document the trunk-based branch strategy."""
    text = CONTRIBUTING.read_text(encoding="utf-8")
    for prefix in ("feature/", "bugfix/", "hotfix/", "refactor/", "docs/", "test/"):
        assert prefix in text, f"CONTRIBUTING.md no longer documents {prefix}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
