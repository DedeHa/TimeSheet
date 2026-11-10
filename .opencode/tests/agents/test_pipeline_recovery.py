"""Recovery command tests for pipeline.py (PRO-407, AC-2).

Covers what-missed, check-stuck, dry-run, resume, and history. STATE_PATH and
HISTORY_PATH are redirected to tmp_path so the real ~/.opencode is never touched.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

PIPELINE_PATH = Path(__file__).resolve().parents[3] / ".opencode" / "scripts" / "pipeline.py"
TICKET = "PRO-407"


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    """Load pipeline.py with state and history redirected to tmp_path."""
    spec = importlib.util.spec_from_file_location("pipeline_recovery_under_test", PIPELINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(module, "HISTORY_PATH", tmp_path / "history.json")
    return module


def _write_state(tmp_path, entry: dict) -> None:
    """Write a ticket entry to the redirected state file."""
    base = {
        "development_mode": "automated",
        "current_step": "develop",
        "cycle_counts": {"plan": 1, "develop": 0, "complete": 0},
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "status": "in_progress",
        "blocked": False,
        "escalation_level": 0,
        "interrupted": False,
        "interrupted_step": None,
        "interrupted_at": None,
    }
    base.update(entry)
    (tmp_path / "state.json").write_text(json.dumps({TICKET: base}), encoding="utf-8")


def _read_state(tmp_path) -> dict:
    return json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))[TICKET]


def test_what_missed_reports_no_interruption_for_healthy_pipeline(pipeline, tmp_path, capsys):
    """what-missed on a pipeline with cycles recorded reports nothing missed."""
    _write_state(tmp_path, {"status": "in_progress", "cycle_counts": {"develop": 2}})
    pipeline.PipelineManager().what_missed(TICKET)
    out = capsys.readouterr().out
    assert "No interrupted pipeline found" in out


def test_what_missed_reports_interrupted_step_with_zero_cycles(pipeline, tmp_path, capsys):
    """what-missed names the step that never ran when status is in_progress."""
    _write_state(tmp_path, {"status": "in_progress", "current_step": "develop",
                            "cycle_counts": {"develop": 0}})
    pipeline.PipelineManager().what_missed(TICKET)
    out = capsys.readouterr().out
    assert "=== What Was Missed: PRO-407 ===" in out
    assert "Step: develop" in out
    assert "Status: INCOMPLETE" in out
    assert "Use 'resume'" in out


def test_check_stuck_flags_pipeline_stuck_for_over_a_day(pipeline, tmp_path, capsys):
    """check-stuck escalates to CRITICAL after 24 hours without progress."""
    old = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    _write_state(tmp_path, {"status": "in_progress", "current_step": "develop",
                            "cycle_counts": {"develop": 0}, "last_updated": old})
    pipeline.PipelineManager().check_stuck(TICKET)
    out = capsys.readouterr().out
    assert "STUCK PIPELINE DETECTED" in out
    assert "CRITICAL" in out


def test_check_stuck_reports_healthy_pipeline(pipeline, tmp_path, capsys):
    """check-stuck does not alarm on a pipeline that has made progress."""
    _write_state(tmp_path, {"status": "in_progress", "cycle_counts": {"develop": 1}})
    pipeline.PipelineManager().check_stuck(TICKET)
    assert "No stuck pipelines detected" in capsys.readouterr().out


def test_dry_run_resume_does_not_change_state(pipeline, tmp_path, capsys):
    """dry-run prints the preview and leaves the state file byte-identical."""
    _write_state(tmp_path, {"status": "in_progress", "cycle_counts": {"develop": 0}})
    before = (tmp_path / "state.json").read_text(encoding="utf-8")
    pipeline.PipelineManager().dry_run(TICKET, "resume")
    out = capsys.readouterr().out
    assert "Would resume at step: develop" in out
    assert "no changes made" in out
    assert (tmp_path / "state.json").read_text(encoding="utf-8") == before


def test_resume_without_force_refuses_interrupted_pipeline(pipeline, tmp_path, capsys):
    """Without --force a interrupted pipeline is not resumed and state is unchanged."""
    _write_state(tmp_path, {"status": "in_progress", "cycle_counts": {"develop": 0}})
    pipeline.PipelineManager().resume(TICKET, force=False)
    out = capsys.readouterr().out
    assert "needs to be reset or completed" in out
    assert "Pipeline resumed successfully" not in out
    assert _read_state(tmp_path)["status"] == "in_progress"


def test_resume_with_force_clears_interruption(pipeline, tmp_path, capsys):
    """resume --force must leave the pipeline no longer reported as interrupted."""
    _write_state(tmp_path, {"status": "in_progress", "cycle_counts": {"develop": 0}})
    mgr = pipeline.PipelineManager()
    mgr.resume(TICKET, force=True)
    assert "Pipeline resumed successfully" in capsys.readouterr().out
    assert mgr._detect_interruption(TICKET) is None
    history = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    actions = [a["action"] for a in history[TICKET]["actions"]]
    assert "interruption_cleared" in actions


def test_resume_on_healthy_pipeline_is_a_no_op(pipeline, tmp_path, capsys):
    """resume on a pipeline with progress keeps status and reports success."""
    _write_state(tmp_path, {"status": "in_progress", "cycle_counts": {"develop": 2}})
    pipeline.PipelineManager().resume(TICKET)
    out = capsys.readouterr().out
    assert "Resuming pipeline at step: develop" in out
    assert "Pipeline resumed successfully" in out
    assert _read_state(tmp_path)["status"] == "in_progress"


def test_history_lists_recorded_actions(pipeline, tmp_path, capsys):
    """history prints recorded actions in order after set-mode."""
    mgr = pipeline.PipelineManager()
    mgr.set_mode(TICKET, "automated")
    capsys.readouterr()
    mgr.get_history(TICKET)
    out = capsys.readouterr().out
    assert "=== Pipeline History: PRO-407 ===" in out
    assert "pipeline_created" in out


def test_history_reports_unknown_ticket(pipeline, tmp_path, capsys):
    """history on an unknown ticket reports no history without writing one."""
    pipeline.PipelineManager().get_history("PRO-999")
    assert "No history found for PRO-999" in capsys.readouterr().out


@pytest.mark.parametrize(
    "argv,expected",
    [
        (["pipeline.py", "what-missed", TICKET], "No interrupted pipeline found"),
        (["pipeline.py", "check-stuck", TICKET], "No stuck pipelines detected"),
        (["pipeline.py", "history", TICKET], "No history found"),
        (["pipeline.py", "dry-run", TICKET, "resume"], "no changes made"),
    ],
)
def test_cli_dispatches_recovery_commands(pipeline, tmp_path, monkeypatch, capsys, argv, expected):
    """The CLI wires each recovery subcommand to its manager method."""
    _write_state(tmp_path, {"status": "in_progress", "cycle_counts": {"develop": 1}})
    monkeypatch.setattr(sys, "argv", argv)
    pipeline.main()
    assert expected in capsys.readouterr().out


def test_cli_show_state_alias_resolves(pipeline, tmp_path, monkeypatch, capsys):
    """'show state' is rewritten to the showstate subcommand."""
    _write_state(tmp_path, {"status": "in_progress", "cycle_counts": {"develop": 1}})
    monkeypatch.setattr(sys, "argv", ["pipeline.py", "show", "state", TICKET])
    pipeline.main()
    assert "=== Pipeline State: PRO-407 ===" in capsys.readouterr().out
