"""Status transitions owned by the CLI (PRO-407, AC-2; FR-22, FR-25).

The CLI sets the pipeline status: `continue` moves a step to in_progress, a
BLOCKED handoff blocks the pipeline and raises the escalation level, and a
COMPLETED handoff clears the block and counts a completed cycle for the step. An
IN_PROGRESS handoff does not clear a block (PRO-407, architect finding 4).
Interruption is derived in one place (interruption_reason): BLOCKED, a marker, or a
stale in_progress step.
STATE_PATH and HISTORY_PATH are redirected to tmp_path.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

PIPELINE_PATH = (
    Path(__file__).resolve().parents[3] / ".opencode" / "scripts" / "pipeline.py"
)
TICKET = "PRO-407"


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    """Load pipeline.py with state and history redirected to tmp_path."""
    spec = importlib.util.spec_from_file_location(
        "pipeline_status_under_test", PIPELINE_PATH
    )
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


def _pass_dor(mgr) -> None:
    """Record a fully passing DoR checklist so the develop gate does not interfere."""
    mgr.record_dor(
        TICKET,
        {dor_id: "pass" for dor_id in ("D1", "D2", "D3", "D4", "D5", "D6", "D7")},
    )


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
    _pass_dor(mgr)
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


def test_in_progress_handoff_does_not_clear_block(pipeline, tmp_path):
    """IN_PROGRESS after BLOCKED keeps the block (PRO-407, finding architect #4).

    The earlier rule set status in_progress and left blocked True, so show state could
    report a pipeline that was in progress while its flag still said blocked. The new
    rule: a later IN_PROGRESS does not silently clear BLOCKED. The block stays until a
    COMPLETED handoff, a forced continue, or a forced resume.
    """
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "BLOCKED")
    _handoff(mgr, "IN_PROGRESS")
    entry = _entry(tmp_path)
    assert entry["status"] == "blocked"
    assert entry["blocked"] is True


def test_forced_continue_after_blocked_clears_block_and_records_reason(
    pipeline, tmp_path, capsys
):
    """continue --force after BLOCKED clears blocked and records why (finding architect #4).

    The forced_advance action names the bypassed BLOCKED handoff and cleared_block True,
    and show state no longer reports the pipeline as BLOCKED.
    """
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "BLOCKED", step="plan")
    _pass_dor(mgr)
    capsys.readouterr()
    assert mgr.continue_step(TICKET, force=True) == 0
    entry = _entry(tmp_path)
    assert entry["current_step"] == "develop"
    assert entry["blocked"] is False
    assert entry["status"] == "in_progress"
    history = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    forced = [a for a in history[TICKET]["actions"] if a["action"] == "forced_advance"]
    assert forced[-1]["details"]["cleared_block"] is True
    assert any("BLOCKED" in reason for reason in forced[-1]["details"]["bypassed"])
    capsys.readouterr()
    mgr.show_state(TICKET)
    out = capsys.readouterr().out
    assert "PIPELINE BLOCKED" not in out
    assert "Blocked: False" in out


def test_refused_continue_keeps_block(pipeline, tmp_path, capsys):
    """A refused continue after BLOCKED does not clear the block."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "BLOCKED", step="plan")
    capsys.readouterr()
    assert mgr.continue_step(TICKET) == 1
    entry = _entry(tmp_path)
    assert entry["blocked"] is True
    assert entry["current_step"] == "plan"


def test_fresh_in_progress_step_is_not_interrupted(pipeline, tmp_path):
    """After continue, a just-started step is in progress but not interrupted (PRO-407, D).

    The earlier rule (in_progress with zero cycles) reported every new step as
    interrupted. The clock decides now: a step is interrupted only after
    INTERRUPT_AFTER_HOURS without an update.
    """
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "COMPLETED", step="plan")
    _pass_dor(mgr)
    mgr.continue_step(TICKET)
    assert mgr._detect_interruption(TICKET) is None
    stamp = datetime.fromisoformat(_entry(tmp_path)["last_updated"])
    later = stamp + timedelta(hours=pipeline.INTERRUPT_AFTER_HOURS + 1)
    interruption = mgr._detect_interruption(TICKET, now=later)
    assert interruption is not None
    assert interruption["interrupted_step"] == "develop"
    assert "no update" in interruption["reason"]
    _handoff(mgr, "COMPLETED", step="develop")
    assert mgr._detect_interruption(TICKET, now=later) is None


def test_what_missed_reports_actual_status_not_hardcoded_text(
    pipeline, tmp_path, capsys
):
    """The not-interrupted message reflects the stored status."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "COMPLETED", step="plan")
    _pass_dor(mgr)
    mgr.continue_step(TICKET)
    _handoff(mgr, "COMPLETED", step="develop")
    capsys.readouterr()
    mgr.what_missed(TICKET)
    assert (
        "Pipeline status: in_progress, but not interrupted" in capsys.readouterr().out
    )


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


def test_cli_handoff_blocked_then_completed_round_trip(
    pipeline, tmp_path, monkeypatch, capsys
):
    """The handoff CLI drives the same transitions as the manager."""
    base = [
        "pipeline.py",
        "handoff",
        TICKET,
        "--from",
        "developer",
        "--to",
        "tester",
        "--step",
        "plan",
    ]
    monkeypatch.setattr(
        sys, "argv", [*base, "--status", "BLOCKED", "--issue", "tests fail"]
    )
    pipeline.main()
    assert _entry(tmp_path)["blocked"] is True
    monkeypatch.setattr(sys, "argv", [*base, "--status", "COMPLETED"])
    pipeline.main()
    assert _entry(tmp_path)["blocked"] is False
    capsys.readouterr()


def test_completed_step_awaiting_continue_is_not_interrupted(pipeline, tmp_path):
    """A COMPLETED step is not stale even when old: its work is reported done (PRO-407, D).

    An IN_PROGRESS handoff after the completion re-opens the step, so the stale rule
    applies to it again.
    """
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "COMPLETED", step="plan")
    _pass_dor(mgr)
    mgr.continue_step(TICKET)
    _handoff(mgr, "COMPLETED", step="develop")
    later = datetime.fromisoformat(_entry(tmp_path)["last_updated"]) + timedelta(
        hours=pipeline.INTERRUPT_AFTER_HOURS + 5
    )
    assert mgr._detect_interruption(TICKET, now=later) is None
    _handoff(mgr, "IN_PROGRESS", step="develop")
    assert mgr._detect_interruption(TICKET, now=later + timedelta(minutes=1)) is not None
