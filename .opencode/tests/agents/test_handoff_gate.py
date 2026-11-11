"""Handoffs feed the state machine (PRO-407, AC-2 and AC-6).

`continue` advances only when the most recent handoff for the ticket is COMPLETED.
`--force` bypasses this handoff rule only (never the DoR gate) and records a
`forced_advance` history action. Handoff
status is validated against COMPLETED, BLOCKED, and IN_PROGRESS.
STATE_PATH and HISTORY_PATH are redirected to tmp_path.
"""

from __future__ import annotations

import importlib.util
import json
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
        "pipeline_gate_under_test", PIPELINE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(module, "HISTORY_PATH", tmp_path / "history.json")
    return module


def _history_actions(tmp_path) -> list[dict]:
    history = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    return history[TICKET]["actions"]


def _step(tmp_path) -> str:
    return json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))[TICKET][
        "current_step"
    ]


def _handoff(mgr, status: str, step: str = "plan"):
    return mgr.record_handoff(TICKET, "architect", "developer", step, status)


def _pass_dor(mgr) -> None:
    """Record a fully passing DoR checklist so only the handoff gate is under test."""
    mgr.record_dor(
        TICKET,
        {dor_id: "pass" for dor_id in ("D1", "D2", "D3", "D4", "D5", "D6", "D7")},
    )


@pytest.mark.parametrize("bad", ["DONE", "APPROVED", "", "in progress", "COMPLETE"])
def test_handoff_rejects_unknown_status(pipeline, tmp_path, bad):
    """Only COMPLETED, BLOCKED, and IN_PROGRESS are accepted; nothing is recorded."""
    mgr = pipeline.PipelineManager()
    with pytest.raises(ValueError):
        mgr.record_handoff(TICKET, "architect", "developer", "plan", bad)
    assert not (tmp_path / "history.json").exists()
    assert not (tmp_path / "state.json").exists()


@pytest.mark.parametrize(
    "given,stored",
    [
        ("completed", "COMPLETED"),
        ("Blocked", "BLOCKED"),
        ("in_progress", "IN_PROGRESS"),
    ],
)
def test_handoff_normalises_status_case(pipeline, tmp_path, given, stored):
    """Status is case-insensitive and stored in upper case."""
    handoff = _handoff(pipeline.PipelineManager(), given)
    assert handoff["status"] == stored


def test_continue_refused_without_any_handoff(pipeline, tmp_path, capsys):
    """No handoff recorded: the step does not advance."""
    mgr = pipeline.PipelineManager()
    mgr.set_mode(TICKET, "automated")
    capsys.readouterr()
    mgr.continue_step(TICKET)
    assert "Cannot continue" in capsys.readouterr().out
    assert _step(tmp_path) == "plan"


def test_continue_refused_after_blocked_handoff(pipeline, tmp_path, capsys):
    """Last handoff BLOCKED: the step does not advance."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "COMPLETED", step="plan")
    _handoff(mgr, "BLOCKED", step="plan")
    capsys.readouterr()
    mgr.continue_step(TICKET)
    assert "Cannot continue" in capsys.readouterr().out
    assert _step(tmp_path) == "plan"


def test_continue_refused_after_in_progress_handoff(pipeline, tmp_path, capsys):
    """Last handoff IN_PROGRESS is not completion: the step does not advance."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "COMPLETED", step="plan")
    _handoff(mgr, "IN_PROGRESS", step="plan")
    capsys.readouterr()
    mgr.continue_step(TICKET)
    assert _step(tmp_path) == "plan"


def test_continue_accepted_after_completed_handoff(pipeline, tmp_path, capsys):
    """Last handoff COMPLETED: the step advances and records step_advance."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "COMPLETED", step="plan")
    _pass_dor(mgr)
    capsys.readouterr()
    mgr.continue_step(TICKET)
    assert "Pipeline advanced to: develop" in capsys.readouterr().out
    assert _step(tmp_path) == "develop"
    assert _history_actions(tmp_path)[-1]["action"] == "step_advance"


def test_continue_uses_most_recent_handoff_only(pipeline, tmp_path, capsys):
    """An earlier COMPLETED does not satisfy the gate once a later BLOCKED is recorded."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "COMPLETED", step="plan")
    _handoff(mgr, "BLOCKED", step="plan")
    _handoff(mgr, "COMPLETED", step="plan")
    _pass_dor(mgr)
    capsys.readouterr()
    mgr.continue_step(TICKET)
    assert _step(tmp_path) == "develop"


def test_reset_starts_a_new_run_for_the_gate(pipeline, tmp_path, capsys):
    """A handoff recorded before a reset does not satisfy the gate after it."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "COMPLETED", step="plan")
    mgr.reset(TICKET, force=True)
    capsys.readouterr()
    mgr.continue_step(TICKET)
    assert "Cannot continue" in capsys.readouterr().out
    assert _step(tmp_path) == "plan"


def test_force_advance_bypasses_gate_and_records_forced_advance(
    pipeline, tmp_path, capsys
):
    """--force advances past a refused gate and records what was bypassed."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "BLOCKED", step="plan")
    _pass_dor(mgr)
    capsys.readouterr()
    assert mgr.continue_step(TICKET, force=True) == 0
    assert _step(tmp_path) == "develop"
    forced = [a for a in _history_actions(tmp_path) if a["action"] == "forced_advance"]
    assert len(forced) == 1
    assert forced[0]["details"]["from"] == "plan"
    assert forced[0]["details"]["to"] == "develop"
    assert forced[0]["details"]["bypassed"]


def test_force_advance_not_recorded_when_gate_passes(pipeline, tmp_path, capsys):
    """--force with a satisfied gate does not claim a bypass."""
    mgr = pipeline.PipelineManager()
    _handoff(mgr, "COMPLETED", step="plan")
    _pass_dor(mgr)
    mgr.continue_step(TICKET, force=True)
    assert "forced_advance" not in [a["action"] for a in _history_actions(tmp_path)]


def test_cli_continue_refuses_then_accepts(pipeline, tmp_path, monkeypatch, capsys):
    """The continue subcommand applies the same gate as the manager."""
    import sys

    monkeypatch.setattr(sys, "argv", ["pipeline.py", "continue", TICKET])
    with pytest.raises(SystemExit) as refused:
        pipeline.main()
    assert refused.value.code == 1
    assert "Cannot continue" in capsys.readouterr().out
    _handoff(pipeline.PipelineManager(), "COMPLETED", step="plan")
    _pass_dor(pipeline.PipelineManager())
    monkeypatch.setattr(sys, "argv", ["pipeline.py", "continue", TICKET])
    pipeline.main()
    assert _step(tmp_path) == "develop"
