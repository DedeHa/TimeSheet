"""Tests for the PRO-368 CI workflow optimizations.

These tests validate the structural behaviour of ``python-ci.yml`` and the
reusable composite action ``setup-python-deps``. Like
``validate_docs_traceability.py`` and ``test_generate_pr_summary.py`` this file lives
under ``.github/tests/`` (not in ``tests/``), so it does not change the
103-test application suite or the coverage gate. It is executed explicitly
by the CI ``test`` job and can be run locally with::

    pytest -q .github/tests/test_workflow_optimization.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "python-ci.yml"
ACTION = ROOT / ".github" / "actions" / "setup-python-deps" / "action.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _action() -> dict:
    return yaml.safe_load(ACTION.read_text(encoding="utf-8"))


def _job_steps(job_name: str) -> list[dict]:
    return _workflow()["jobs"][job_name]["steps"]


def _uses(step: dict) -> str:
    return step.get("uses", "")


# ---------------------------------------------------------------------------
# AC1 / AC4: Dependency caching (pip + venv) enabled on every Python job.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("job", ["check", "test", "deploy"])
def test_python_job_uses_caching_composite_action(job: str):
    """Every Python job now delegates setup to the reusable composite action."""
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
        s
        for s in steps
        if s.get("run", "").strip().startswith("pip install -e .[dev]")
    ]
    assert (
        install_steps == []
    ), f"{job} job still has an inline pip install -e .[dev] step"


def test_composite_action_enables_pip_cache():
    """AC1: the composite action passes cache: pip to actions/setup-python."""
    action = _action()
    setup_step = next(
        s for s in action["runs"]["steps"] if _uses(s).startswith("actions/setup-python")
    )
    assert setup_step["with"]["cache"] == "pip"
    assert setup_step["with"]["cache-dependency-path"] == "pyproject.toml"


def test_composite_action_centralises_checkout_setup_and_install():
    """AC2: the composite action covers checkout, Python setup and install."""
    action = _action()
    assert action["runs"]["using"] == "composite"
    uses = [_uses(s) for s in action["runs"]["steps"]]
    assert "actions/checkout@v5" in uses
    assert any(u.startswith("actions/setup-python") for u in uses)
    assert any("pip install -e .[dev]" in s.get("run", "") for s in action["runs"]["steps"])


# ---------------------------------------------------------------------------
# AC3: Unnecessary Node.js installation removed from the lint job.
# ---------------------------------------------------------------------------


def test_setup_node_removed_from_check_job():
    """AC3: the check job no longer installs Node.js unconditionally."""
    steps = _job_steps("check")
    node_steps = [s for s in steps if _uses(s).startswith("actions/setup-node")]
    assert node_steps == [], "actions/setup-node is still present in the check job"


def test_node_actions_only_run_under_node24_runtime():
    """The Node 24 migration env var is still set for JavaScript actions."""
    assert _workflow()["env"]["FORCE_JAVASCRIPT_ACTIONS_TO_NODE24"] is True


# ---------------------------------------------------------------------------
# AC5: Independent, separately-attributable validation steps.
# (Steps within a job run sequentially on GitHub Actions; "independent" here
# means each validator is its own step so a failure points at the exact check,
# not that they execute in parallel.)
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
        assert step.get("continue-on-error") is False, (
            f"{step['name']} must not use continue-on-error: true"
        )


# ---------------------------------------------------------------------------
# AC6: Deployment job reuses cached dependencies.
# ---------------------------------------------------------------------------


def test_deploy_job_uses_composite_action():
    """AC6: the deploy job reuses the cached setup action instead of rebuilding."""
    steps = _job_steps("deploy")
    assert any(
        _uses(s) == "./.github/actions/setup-python-deps" for s in steps
    ), "deploy job does not reuse the composite action"


def test_deploy_job_runs_only_on_release_tags():
    """AC6: deployment is still gated on release tags (no behaviour change)."""
    assert "startsWith(github.ref, 'refs/tags/v')" in _workflow()["jobs"]["deploy"]["if"]


# ---------------------------------------------------------------------------
# Quality-gate integrity (regression).
# ---------------------------------------------------------------------------


def test_pipeline_graph_is_unchanged():
    """The job dependency graph must remain check -> test -> deploy."""
    workflow = _workflow()
    assert set(workflow["jobs"]) == {"check", "test", "deploy"}
    assert workflow["jobs"]["test"]["needs"] == ["check"]
    assert workflow["jobs"]["deploy"]["needs"] == ["check", "test"]


def test_coverage_gate_threshold_unchanged():
    """The 90% coverage gate must still be enforced in the test job."""
    steps = _job_steps("test")
    gate_steps = [s for s in steps if "fail-under=90" in s.get("run", "")]
    assert gate_steps, "the 90% coverage gate step is missing"


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
