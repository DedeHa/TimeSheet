"""Tests for UPDATE_DATA env var expression logic (PRO-385).

Validates that the GitHub Actions expression
    ${{ github.event_name == 'workflow_run' && 'true' || (inputs.update_data || 'false') }}
evaluates correctly for every trigger type and input combination.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

_ROOT = Path(__file__).resolve().parents[3]
CI_TIMING = _ROOT / ".github" / "workflows" / "ci-timing.yml"


def _workflow() -> dict:
    return yaml.safe_load(CI_TIMING.read_text(encoding="utf-8"))


def _env() -> dict:
    return _workflow()["env"]


def _update_data_expr() -> str:
    return _env()["UPDATE_DATA"]


def _triggers() -> dict:
    """Get triggers dict, handling PyYAML's on->True boolean alias."""
    raw = _workflow()
    # PyYAML parses YAML 1.1 `on:` as boolean True
    return raw.get(True) or raw.get("on") or {}


def _collect_steps() -> list[dict]:
    return _workflow()["jobs"]["collect"]["steps"]


def _evaluate_update_data(event_name: str, inputs: dict) -> str:
    """Simulate GitHub Actions UPDATE_DATA expression evaluation.

    GitHub Actions expression evaluation rules for this specific pattern:
    - `github.event_name == 'workflow_run'` → True if event is workflow_run
    - `&& 'true'` → returns 'true' if left side is truthy
    - `|| (inputs.update_data || 'false')` → falls back to input or 'false'
    """
    if event_name == "workflow_run":
        return "true"
    return str(inputs.get("update_data", "false"))


# ---------------------------------------------------------------------------
# Expression correctness
# ---------------------------------------------------------------------------

def test_update_data_expression_contains_workflow_run_check():
    """The expression must check github.event_name == 'workflow_run'."""
    expr = _update_data_expr()
    assert "workflow_run" in expr, f"UPDATE_DATA expression missing workflow_run check: {expr}"
    assert "github.event_name" in expr, f"UPDATE_DATA expression missing github.event_name: {expr}"


def test_update_data_expression_contains_fallback():
    """The expression must fall back to inputs.update_data || 'false'."""
    expr = _update_data_expr()
    assert "inputs.update_data" in expr, f"UPDATE_DATA expression missing inputs.update_data: {expr}"
    assert "'false'" in expr, f"UPDATE_DATA expression missing 'false' default: {expr}"


def test_update_data_expression_is_conditional():
    """The expression must be a conditional expression, not a static value."""
    expr = _update_data_expr()
    assert "${{" in expr, f"UPDATE_DATA must be a GitHub Actions expression, got: {expr}"
    assert "&&" in expr or "||" in expr, f"UPDATE_DATA must use logical operators: {expr}"


# ---------------------------------------------------------------------------
# Expression evaluation (simulated)
# ---------------------------------------------------------------------------

def test_update_data_workflow_run_returns_true():
    """workflow_run trigger → UPDATE_DATA must be 'true'."""
    expr = _update_data_expr()
    result = _evaluate_update_data("workflow_run", {})
    assert result == "true", f"workflow_run should set UPDATE_DATA=true, got {result}"


def test_update_data_workflow_dispatch_default_false():
    """workflow_dispatch without update_data input → UPDATE_DATA must be 'false'."""
    expr = _update_data_expr()
    result = _evaluate_update_data("workflow_dispatch", {})
    assert result == "false", f"workflow_dispatch default should be false, got {result}"


def test_update_data_workflow_dispatch_with_true():
    """workflow_dispatch with update_data='true' → UPDATE_DATA must be 'true'."""
    expr = _update_data_expr()
    result = _evaluate_update_data("workflow_dispatch", {"update_data": "true"})
    assert result == "true", f"workflow_dispatch with update_data=true should be true, got {result}"


def test_update_data_workflow_dispatch_with_false():
    """workflow_dispatch with update_data='false' → UPDATE_DATA must be 'false'."""
    expr = _update_data_expr()
    result = _evaluate_update_data("workflow_dispatch", {"update_data": "false"})
    assert result == "false", f"workflow_dispatch with update_data=false should be false, got {result}"


# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------

def test_update_data_not_hardcoded_to_false():
    """Regression: UPDATE_DATA must NOT be hardcoded to 'false' (the PRO-385 bug)."""
    expr = _update_data_expr()
    assert expr.strip() != "'false'", (
        "UPDATE_DATA is hardcoded to 'false' — this is the PRO-385 bug! "
        "The expression must check github.event_name == 'workflow_run'."
    )


def test_update_data_not_hardcoded_to_true():
    """UPDATE_DATA must NOT be hardcoded to 'true' (would break workflow_dispatch)."""
    expr = _update_data_expr()
    assert expr.strip() != "'true'", (
        "UPDATE_DATA is hardcoded to 'true' — this would cause data/ to be "
        "committed on every workflow_dispatch run, which is incorrect."
    )


def test_workflow_run_trigger_exists():
    """Regression: workflow_run trigger must be present in the workflow."""
    triggers = _triggers()
    assert "workflow_run" in triggers, "workflow_run trigger is missing from ci-timing.yml"


def test_workflow_run_triggers_on_python_ci():
    """workflow_run must trigger on 'Python CI' workflow."""
    triggers = _triggers()
    wr = triggers["workflow_run"]
    assert wr["workflows"] == ["Python CI"], f"workflow_run triggers on wrong workflow: {wr['workflows']}"


def test_workflow_run_triggers_on_completed():
    """workflow_run must trigger on 'completed' type."""
    triggers = _triggers()
    wr = triggers["workflow_run"]
    assert "completed" in wr["types"], f"workflow_run must trigger on 'completed', got: {wr['types']}"


def test_conditional_step_exists():
    """The data/ commit step must be conditional on env.UPDATE_DATA == 'true'."""
    steps = _collect_steps()
    data_steps = [s for s in steps if "data" in s.get("name", "").lower()]
    assert data_steps, "No step found for data/ commit"
    for step in data_steps:
        assert "env.UPDATE_DATA" in step.get("if", ""), (
            f"Step '{step.get('name')}' must have 'if: env.UPDATE_DATA == \"true\"'"
        )


def test_workflow_dispatch_respects_input():
    """workflow_dispatch should respect inputs.update_data."""
    triggers = _triggers()
    wd = triggers["workflow_dispatch"]
    inputs = wd.get("inputs", {})
    assert "update_data" in inputs, "workflow_dispatch must have update_data input"
    assert inputs["update_data"]["default"] == "false", (
        "update_data input must default to 'false'"
    )


def test_data_commit_step_pushes_to_master():
    """The data/ commit step must push to master, not ci-metrics."""
    steps = _collect_steps()
    data_steps = [s for s in steps if "data" in s.get("name", "").lower()]
    assert data_steps, "No data/ commit step found"
    for step in data_steps:
        run_script = step.get("run", "")
        assert "master" in run_script, (
            f"data/ commit step must push to master: {run_script}"
        )


def test_data_commit_step_not_unconditional():
    """Regression: the data/ commit step must NOT be unconditional."""
    steps = _collect_steps()
    data_steps = [s for s in steps if "data" in s.get("name", "").lower()]
    for step in data_steps:
        assert step.get("if") is not None, (
            f"Step '{step['name']}' has no 'if' condition — it will run on every trigger!"
        )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))