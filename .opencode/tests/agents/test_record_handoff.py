"""Unit tests for pipeline.py handoff recording (PRO-407, AC-6; FR-25)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

PIPELINE_PATH = Path(__file__).resolve().parents[3] / ".opencode" / "scripts" / "pipeline.py"


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    """Load pipeline.py with state redirected to tmp_path."""
    spec = importlib.util.spec_from_file_location("pipeline_under_test", PIPELINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(module, "HISTORY_PATH", tmp_path / "history.json")
    return module


def _manager(pipeline):
    return pipeline.PipelineManager()


def test_record_handoff_appends_history_with_full_schema(pipeline, tmp_path):
    """V1: a handoff is stored as action 'handoff' with all schema fields."""
    mgr = _manager(pipeline)
    mgr.record_handoff(
        "PRO-407",
        from_agent="architect",
        to_agent="developer",
        step="plan",
        status="COMPLETED",
        artifacts=["docs/PRO-407_Implementation_Plan.md"],
        accomplishments=["Plan drafted"],
        issues=[],
        next_steps=["Implement rollout step 1"],
        mode="automated",
        cycle=1,
    )
    history = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    actions = history["PRO-407"]["actions"]
    handoffs = [a for a in actions if a["action"] == "handoff"]
    assert len(handoffs) == 1
    details = handoffs[0]["details"]
    for key in ("ticket", "from", "to", "step", "status", "artifacts", "accomplishments",
                "issues", "next_steps", "mode", "cycle", "max_cycles"):
        assert key in details
    assert details["from"] == "architect"
    assert details["to"] == "developer"
    assert details["max_cycles"] == 3


def test_record_handoff_uses_persisted_mode_when_not_given(pipeline):
    """Mode defaults to the persisted development_mode."""
    mgr = _manager(pipeline)
    mgr.set_mode("PRO-407", "automated")
    handoff = mgr.record_handoff("PRO-407", "tester", "po", "plan", "COMPLETED")
    assert handoff["mode"] == "automated"


@pytest.mark.parametrize(
    "from_agent,to_agent,status",
    [("", "developer", "COMPLETED"), ("architect", "", "COMPLETED"), ("architect", "developer", "")],
)
def test_record_handoff_rejects_missing_required_fields(pipeline, from_agent, to_agent, status):
    """V4: from, to, and status are required."""
    mgr = _manager(pipeline)
    with pytest.raises(ValueError):
        mgr.record_handoff("PRO-407", from_agent, to_agent, "step", status)


def test_render_handoff_comment_contains_all_sections(pipeline):
    """V2: rendered comment includes every template section."""
    handoff = {
        "from": "architect",
        "to": "developer",
        "step": "implementation-planning",
        "status": "COMPLETED",
        "artifacts": ["docs/PRO-407_Implementation_Plan.md"],
        "accomplishments": ["Plan drafted"],
        "issues": [],
        "next_steps": ["Implement step 1"],
        "mode": "automated",
        "cycle": 1,
        "max_cycles": 3,
    }
    body = pipeline.PipelineManager.render_handoff_comment(handoff)
    assert body.startswith("Handoff: architect → developer (Step: implementation-planning)")
    for section in ("Artifacts:", "Status: COMPLETED", "Accomplishments:",
                    "Issues / Blockers:", "Next Steps:", "Metadata: Mode: automated | Cycle: 1/3"):
        assert section in body
    assert "* None" in body  # empty issues list is rendered explicitly


def test_render_handoff_comment_without_cycle(pipeline):
    """Cycle is reported as n/a when not supplied."""
    handoff = {
        "from": "po", "to": "architect", "step": "", "status": "COMPLETED",
        "artifacts": [], "accomplishments": [], "issues": [], "next_steps": [],
        "mode": "interactive", "cycle": None, "max_cycles": 3,
    }
    body = pipeline.PipelineManager.render_handoff_comment(handoff)
    assert "Step: n/a" in body
    assert "Cycle: n/a" in body


def test_handoff_cli_writes_history_and_prints_comment(pipeline, tmp_path, monkeypatch, capsys):
    """V3: the handoff subcommand records history and prints the comment, using tmp state."""
    monkeypatch.setattr(
        "sys.argv",
        ["pipeline.py", "handoff", "PRO-407", "--from", "developer", "--to", "tester",
         "--step", "plan", "--status", "COMPLETED",
         "--artifact", "docs/PRO-407_Implementation_Plan.md",
         "--next-step", "Run tests", "--cycle", "2"],
    )
    pipeline.main()
    out = capsys.readouterr().out
    assert "Handoff: developer → tester (Step: plan)" in out
    assert "Cycle: 2/3" in out
    history = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert any(a["action"] == "handoff" for a in history["PRO-407"]["actions"])


def test_handoff_step_must_equal_current_step(pipeline, tmp_path):
    """E: a handoff for a step other than the current one is refused, nothing is written."""
    mgr = _manager(pipeline)
    mgr.set_mode("PRO-407", "automated")
    before = (tmp_path / "state.json").read_bytes(), (tmp_path / "history.json").read_bytes()
    with pytest.raises(ValueError, match="must equal the current step 'plan'"):
        mgr.record_handoff("PRO-407", "developer", "tester", "develop", "COMPLETED")
    assert (tmp_path / "state.json").read_bytes() == before[0]
    assert (tmp_path / "history.json").read_bytes() == before[1]


def test_handoff_step_mismatch_on_unknown_ticket_creates_nothing(pipeline, tmp_path):
    """E: a mismatched handoff on a ticket with no state creates no state or history."""
    with pytest.raises(ValueError):
        _manager(pipeline).record_handoff("PRO-999", "developer", "tester", "complete", "COMPLETED")
    assert not (tmp_path / "state.json").exists()
    assert not (tmp_path / "history.json").exists()


def test_handoff_without_step_uses_current_step(pipeline, tmp_path):
    """E: an omitted step is the current step, so the handoff is recorded for it."""
    handoff = _manager(pipeline).record_handoff("PRO-407", "architect", "developer", "", "COMPLETED")
    assert handoff["step"] == "plan"


def test_cli_handoff_step_mismatch_exits_one_and_keeps_files(
    pipeline, tmp_path, monkeypatch, capsys
):
    """E + H: the CLI reports the mismatch, exits 1, and leaves the existing files unchanged."""
    _manager(pipeline).set_mode("PRO-407", "automated")
    before = (tmp_path / "state.json").read_bytes(), (tmp_path / "history.json").read_bytes()
    monkeypatch.setattr(
        "sys.argv",
        ["pipeline.py", "handoff", "PRO-407", "--from", "developer", "--to", "tester",
         "--step", "develop", "--status", "COMPLETED"],
    )
    with pytest.raises(SystemExit) as exc:
        pipeline.main()
    assert exc.value.code == 1
    assert "must equal the current step" in capsys.readouterr().out
    assert (tmp_path / "state.json").read_bytes() == before[0]
    assert (tmp_path / "history.json").read_bytes() == before[1]
