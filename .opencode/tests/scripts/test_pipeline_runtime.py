"""Runtime tests for the agent pipeline state machine."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".opencode" / "scripts" / "pipeline.py"
_SPEC = importlib.util.spec_from_file_location("pipeline_runtime", _SCRIPT)
_PIPELINE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PIPELINE)


@pytest.fixture
def pipeline_manager(tmp_path, monkeypatch):
    """Return a pipeline manager backed by temp state files."""
    state_dir = tmp_path / ".opencode"
    state_dir.mkdir()
    state_path = state_dir / "pipeline-state.json"
    history_path = state_dir / "pipeline-history.json"
    monkeypatch.setattr(_PIPELINE, "STATE_PATH", state_path)
    monkeypatch.setattr(_PIPELINE, "HISTORY_PATH", history_path)
    return _PIPELINE.PipelineManager()


def test_default_entry_uses_canonical_workflow_state(pipeline_manager):
    """Every new entry should initialize the canonical workflow state."""
    entry = pipeline_manager._ensure_entry("PRO-100")
    assert entry["workflow_state"] == "backlog"
    assert entry["current_step"] == "plan"
    assert entry["cycle_counts"] == {"plan": 0, "develop": 0, "complete": 0}


def test_get_entry_returns_none_when_missing(pipeline_manager):
    """Read-only access should not create entries."""
    entry = pipeline_manager._get_entry("PRO-999")
    assert entry is None
    assert not pipeline_manager.state


def test_continue_step_requires_completed_current_step(pipeline_manager):
    """A step cannot be advanced until its current cycle is complete."""
    ticket = "PRO-101"
    entry = pipeline_manager._ensure_entry(ticket)
    entry["current_step"] = "develop"
    entry["workflow_state"] = "develop"
    entry["status"] = "in_progress"
    pipeline_manager._save_state()

    valid, reason = pipeline_manager._validate_transition(ticket, "complete")
    assert valid is False
    assert "has not been completed" in reason


def test_recover_ticket_reports_interruption_and_suggested_action(pipeline_manager):
    """Recovery output should identify missed work and the next valid action."""
    ticket = "PRO-102"
    entry = pipeline_manager._ensure_entry(ticket)
    entry["current_step"] = "develop"
    entry["workflow_state"] = "develop"
    entry["status"] = "in_progress"
    entry["cycle_counts"] = {"plan": 1, "develop": 0, "complete": 0}
    pipeline_manager._save_state()

    recovery = pipeline_manager.recover_ticket(ticket)
    assert recovery["recovery"]["is_interrupted"] is True
    assert recovery["recovery"]["suggested_action"] == "resume"
    assert recovery["recovery"]["missed_work"]["step"] == "develop"


def test_handoff_payload_includes_standard_fields(pipeline_manager):
    """Handoff payloads should be structured and reused across agent dispatches."""
    payload = pipeline_manager.generate_handoff_payload("PRO-103")
    required = {
        "ticket",
        "current_step",
        "workflow_state",
        "status",
        "development_mode",
        "story_points",
        "cycle_counts",
        "last_action",
        "required_next_step",
    }
    assert required.issubset(payload.keys())


def test_set_mode_persists_to_state_file(pipeline_manager):
    """Mode selection should persist to the pipeline state file."""
    pipeline_manager.set_mode("PRO-104", "automated")
    assert pipeline_manager._get_entry("PRO-104")["development_mode"] == "automated"
    assert _PIPELINE.STATE_PATH.exists()


def test_init_creates_state_entry(pipeline_manager):
    """Init command should create a state entry."""
    pipeline_manager.init("PRO-105")
    entry = pipeline_manager._get_entry("PRO-105")
    assert entry is not None
    assert entry["current_step"] == "plan"
    assert entry["status"] == "not_started"