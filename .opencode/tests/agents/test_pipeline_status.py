"""Status transitions owned by the CLI (PRO-407, AC-2; FR-22, FR-25).

The CLI sets the pipeline status: `continue` moves a step to in_progress, a
BLOCKED handoff blocks the pipeline and raises the escalation level, and a
COMPLETED handoff clears the block and counts a completed cycle for the step.
Interruption is derived in one place: in_progress with no completed cycle.
STATE_PATH and HISTORY_PATH are redirected to tmp_path.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PIPELINE_PATH = Path(__file__).resolve().parents[3] / ".opencode" / "scripts" / "pipeline.py"
TICKET = "PRO-407"


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    """Load pipeline.py with state and history redirected to tmp_path."""
    spec = importlib.util.spec_from_file_location("pipeline_status_under_test", PIPELINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(module, "HISTORY_PATH", tmp_path / "history.json")
    return module


def _entry(tmp_path) -> dict:
    return json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))[TICKET]


def _actions(tmp_path) -> list[str]:
    history = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    return [a["action"] for a in history[TICKET]["actions"]]


def _handoff(mgr, status: str, step: str = "plan"):
    return mgr.record_handoff(TICKET, "architect", "developer", step, status)


def test_default_entry_has_no_stored_interrupted_flag(pipeline, tmp_path):
    """The dead stored interrupted flag is gone; detection is the only definition."""
    mgr = pipeline.PipelineManager()
    mgr.set_mode(TICKET, "automated")
    entry = _entry(tmp_path)
    assert "interrupted" not in entry
    assert entry["status"] == "not_started"
    assert entry["blocked"] is False
    assert entry["escalation_level"] == 0


def test_continue_sets_status_in_progress_for_new_step(pipeline, tmp_path, capsys):
    """Advancing a step sets status in_progress on the step being entered."""
    mgr = pipeline.PipelineManager()
    mgr.set_mode(TICKET, "automated")
    _handoff(mgr, "COMPLETED", step="plan")
    mgr.continue_step(TICKET)
    entry = _entry(tmp_path)
    assert entry["current_step"] == "develop"
    assert entry["status"] == "in_progress"


def test_blocked_handoff_blocks_pipeline_and_raises_escalation(pipeline, tmp_path):
    """BLOCKED sets blocked, status blocked, and escalation_level +1."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "BLOCKED")
    entry = _entry(tmp_path)
    assert entry["blocked"] is True
    assert entry["status"] == "blocked"
    assert entry["escalation_level"] == 1
    _handoff(mgr, "BLOCKED")
    assert _entry(tmp_path)["escalation_level"] == 2


def test_completed_handoff_clears_block_and_counts_cycle(pipeline, tmp_path):
    """A later COMPLETED handoff clears the block and counts a cycle for the step."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "BLOCKED", step="plan")
    _handoff(mgr, "COMPLETED", step="plan")
    entry = _entry(tmp_path)
    assert entry["blocked"] is False
    assert entry["status"] == "in_progress"
    assert entry["cycle_counts"]["plan"] == 1
    assert entry["escalation_level"] == 1  # escalation history is kept


def test_in_progress_handoff_sets_status_without_clearing_block(pipeline, tmp_path):
    """IN_PROGRESS sets status in_progress and leaves the block flag alone."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "BLOCKED")
    _handoff(mgr, "IN_PROGRESS")
    entry = _entry(tmp_path)
    assert entry["status"] == "in_progress"
    assert entry["blocked"] is True


def test_interrupted_detected_for_in_progress_step_without_completion(pipeline, tmp_path):
    """After continue, the new step is in progress with no completion: interrupted."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "COMPLETED", step="plan")
    mgr.continue_step(TICKET)
    interruption = mgr._detect_interruption(TICKET)
    assert interruption is not None
    assert interruption["interrupted_step"] == "develop"
    _handoff(mgr, "COMPLETED", step="develop")
    assert mgr._detect_interruption(TICKET) is None


def test_what_missed_reports_actual_status_not_hardcoded_text(pipeline, tmp_path, capsys):
    """The not-interrupted message reflects the stored status."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "COMPLETED", step="plan")
    mgr.continue_step(TICKET)
    _handoff(mgr, "COMPLETED", step="develop")
    capsys.readouterr()
    mgr.what_missed(TICKET)
    assert "Pipeline status: in_progress, but not interrupted" in capsys.readouterr().out


def test_show_state_reports_blocked_pipeline(pipeline, tmp_path, capsys):
    """show state makes a blocked pipeline visible."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "BLOCKED")
    capsys.readouterr()
    mgr.show_state(TICKET)
    out = capsys.readouterr().out
    assert "PIPELINE BLOCKED" in out
    assert "Escalation Level: 1" in out
    assert "Blocked: True" in out


def test_resume_refuses_blocked_pipeline_without_force(pipeline, tmp_path, capsys):
    """A blocked pipeline is not resumed without --force and keeps its block."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "BLOCKED")
    capsys.readouterr()
    mgr.resume(TICKET, force=False)
    out = capsys.readouterr().out
    assert "needs to be reset or completed" in out
    assert _entry(tmp_path)["blocked"] is True


def test_resume_force_clears_block_and_status(pipeline, tmp_path, capsys):
    """resume --force clears the block, moves status to resumed, and records it."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "BLOCKED")
    mgr.resume(TICKET, force=True)
    entry = _entry(tmp_path)
    assert entry["blocked"] is False
    assert entry["status"] == "resumed"
    assert "interruption_cleared" in _actions(tmp_path)


def test_cli_handoff_blocked_then_completed_round_trip(pipeline, tmp_path, monkeypatch, capsys):
    """The handoff CLI drives the same transitions as the manager."""
    base = ["pipeline.py", "handoff", TICKET, "--from", "developer", "--to", "tester",
            "--step", "develop"]
    monkeypatch.setattr(sys, "argv", [*base, "--status", "BLOCKED", "--issue", "tests fail"])
    pipeline.main()
    assert _entry(tmp_path)["blocked"] is True
    monkeypatch.setattr(sys, "argv", [*base, "--status", "COMPLETED"])
    pipeline.main()
    assert _entry(tmp_path)["blocked"] is False
    capsys.readouterr()
