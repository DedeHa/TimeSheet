"""Tests for CI-timing data flow (PRO-406).

Validates that:
1. No data/ files are committed to the master branch from ci-timing.yml
   (all JSON data lives on the ci-metrics orphan branch only).
2. A configurable MAX_RUNS env var exists for future rolling-window use.
3. The update_data input is retained as a no-op placeholder for backward
   compatibility but no longer triggers a master write.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

_SCRIPTS = Path(__file__).resolve().parents[2] / ".github" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

_ROOT = Path(__file__).resolve().parents[2]
CI_TIMING = _ROOT / ".github" / "workflows" / "ci-timing.yml"


def _workflow() -> dict:
    return yaml.safe_load(CI_TIMING.read_text(encoding="utf-8"))


def _env() -> dict:
    return _workflow()["env"]


def _triggers() -> dict:
    """Get triggers dict, handling PyYAML's on->True boolean alias."""
    raw = _workflow()
    return raw.get(True) or raw.get("on") or {}


def _collect_steps() -> list[dict]:
    return _workflow()["jobs"]["collect"]["steps"]


# ---------------------------------------------------------------------------
# PRO-406: No more master writes
# ---------------------------------------------------------------------------


def test_no_data_commit_step_to_master():
    """PRO-406: ci-timing.yml must NOT contain a step that commits data/ to master."""
    steps = _collect_steps()
    for step in steps:
        run_script = step.get("run", "")
        assert (
            "push --quiet origin master" not in run_script
        ), f"Step '{step.get('name')}' still pushes to master: {run_script}"


def test_no_update_data_env_var():
    """PRO-406: The UPDATE_DATA env var must be removed (no longer needed)."""
    env = _env()
    assert (
        "UPDATE_DATA" not in env
    ), "UPDATE_DATA env var must be removed — data no longer goes to master"


def test_max_runs_env_var_exists():
    """PRO-406: MAX_RUNS env var must exist for future rolling-window use."""
    env = _env()
    assert (
        "MAX_RUNS" in env
    ), "MAX_RUNS env var is missing — needed for configurable rolling window"


def test_max_runs_defaults_to_unlimited():
    """PRO-406: MAX_RUNS must default to 0 (unlimited)."""
    env = _env()
    expr = env["MAX_RUNS"]
    assert "0" in expr, f"MAX_RUNS must default to 0 (unlimited), got: {expr}"


def test_metrics_branch_env_var_exists():
    """The orphan branch name must be configurable via METRICS_BRANCH."""
    env = _env()
    assert "METRICS_BRANCH" in env, "METRICS_BRANCH env var is missing"


def test_metrics_branch_defaults_to_ci_metrics():
    """METRICS_BRANCH must default to 'ci-metrics'."""
    env = _env()
    expr = env["METRICS_BRANCH"]
    assert (
        "ci-metrics" in expr
    ), f"METRICS_BRANCH must default to 'ci-metrics', got: {expr}"


# ---------------------------------------------------------------------------
# Regression: workflow_run trigger still present
# ---------------------------------------------------------------------------


def test_workflow_run_trigger_exists():
    """Regression: workflow_run trigger must be present in the workflow."""
    triggers = _triggers()
    assert (
        "workflow_run" in triggers
    ), "workflow_run trigger is missing from ci-timing.yml"


def test_workflow_run_triggers_on_python_ci():
    """workflow_run must trigger on 'Python CI' workflow."""
    triggers = _triggers()
    wr = triggers["workflow_run"]
    assert wr["workflows"] == [
        "Python CI"
    ], f"workflow_run triggers on wrong workflow: {wr['workflows']}"


def test_workflow_run_triggers_on_completed():
    """workflow_run must trigger on 'completed' type."""
    triggers = _triggers()
    wr = triggers["workflow_run"]
    assert (
        "completed" in wr["types"]
    ), f"workflow_run must trigger on 'completed', got: {wr['types']}"


def test_workflow_dispatch_max_runs_input():
    """workflow_dispatch must have a max_runs input."""
    triggers = _triggers()
    wd = triggers["workflow_dispatch"]
    inputs = wd.get("inputs", {})
    assert "max_runs" in inputs, "workflow_dispatch must have max_runs input"
    assert (
        inputs["max_runs"]["default"] == "0"
    ), "max_runs input must default to '0' (unlimited)"


def test_update_data_input_retained_as_noop():
    """PRO-406: update_data input is retained as a no-op placeholder."""
    triggers = _triggers()
    wd = triggers["workflow_dispatch"]
    inputs = wd.get("inputs", {})
    assert (
        "update_data" in inputs
    ), "update_data input must still exist for backward compat"


# ---------------------------------------------------------------------------
# Orphan branch write still present
# ---------------------------------------------------------------------------


def test_commit_and_push_step_targets_orphan_branch():
    """The ci-metrics commit step must push to the orphan branch, not master."""
    steps = _collect_steps()
    push_steps = [
        s
        for s in steps
        if "push" in s.get("run", "") and "METRICS_BRANCH" in s.get("run", "")
    ]
    assert push_steps, "No step found that pushes to METRICS_BRANCH"
    for step in push_steps:
        run_script = step.get("run", "")
        assert (
            "origin master" not in run_script
        ), f"Step '{step.get('name')}' pushes to master instead of orphan branch"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
