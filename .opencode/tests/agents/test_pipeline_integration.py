"""End-to-end pipeline CLI flow (PRO-407, ticket Testing Strategy: integration level).

Drives pipeline.main() with sys.argv monkeypatched, one process per command, so every
step reads and writes the state and history files exactly as the agents do. All files
live in tmp_path; the real ~/.opencode is never touched.

Deviation from the literal flow in the test plan: the first `continue` needs a COMPLETED
handoff for the plan step (the handoff gate and the completed-cycle rule both require
it), so the flow records one before `continue`.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PIPELINE_PATH = (
    Path(__file__).resolve().parents[3] / ".opencode" / "scripts" / "pipeline.py"
)
TICKET = "PRO-407"
ALL_PASS = json.dumps({f"D{i}": "pass" for i in range(1, 8)})


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    """Load pipeline.py with state and history redirected to tmp_path."""
    spec = importlib.util.spec_from_file_location(
        "pipeline_integration_under_test", PIPELINE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(module, "HISTORY_PATH", tmp_path / "history.json")
    return module


def run(pipeline, monkeypatch, *argv: str) -> None:
    """Run one CLI invocation exactly as a shell would."""
    monkeypatch.setattr(sys, "argv", ["pipeline.py", *argv])
    pipeline.main()


def _state(tmp_path) -> dict:
    return json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))[TICKET]


def _action_names(tmp_path) -> list[str]:
    history = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    return [a["action"] for a in history[TICKET]["actions"]]


def _files(tmp_path) -> dict:
    return {
        name: (tmp_path / name).read_bytes() if (tmp_path / name).exists() else None
        for name in ("state.json", "history.json")
    }


@pytest.mark.integration
def test_full_cli_flow_blocks_resumes_and_records_history(
    pipeline, tmp_path, monkeypatch, capsys
):
    """set-mode -> handoff -> dor -> continue -> handoff -> continue -> BLOCKED -> resume."""
    run(pipeline, monkeypatch, "set-mode", TICKET, "automated")
    assert _state(tmp_path)["development_mode"] == "automated"

    run(
        pipeline,
        monkeypatch,
        "handoff",
        TICKET,
        "--from",
        "architect",
        "--to",
        "developer",
        "--step",
        "plan",
        "--status",
        "COMPLETED",
    )
    run(pipeline, monkeypatch, "dor", TICKET, "--json", ALL_PASS)
    capsys.readouterr()

    run(pipeline, monkeypatch, "continue", TICKET)
    assert _state(tmp_path)["current_step"] == "develop"
    assert _state(tmp_path)["status"] == "in_progress"
    run(pipeline, monkeypatch, "show", "state", TICKET)
    assert "INTERRUPTED PIPELINE DETECTED" in capsys.readouterr().out

    run(
        pipeline,
        monkeypatch,
        "handoff",
        TICKET,
        "--from",
        "developer",
        "--to",
        "tester",
        "--step",
        "develop",
        "--status",
        "COMPLETED",
    )
    run(pipeline, monkeypatch, "continue", TICKET)
    assert _state(tmp_path)["current_step"] == "complete"

    run(
        pipeline,
        monkeypatch,
        "handoff",
        TICKET,
        "--from",
        "tester",
        "--to",
        "product-owner",
        "--step",
        "complete",
        "--status",
        "BLOCKED",
        "--issue",
        "acceptance test fails",
    )
    capsys.readouterr()

    run(pipeline, monkeypatch, "show", "state", TICKET)
    out = capsys.readouterr().out
    assert "PIPELINE BLOCKED" in out
    assert "Escalation Level: 1" in out
    assert "INTERRUPTED PIPELINE DETECTED" not in out
    assert _state(tmp_path)["blocked"] is True

    run(pipeline, monkeypatch, "resume", TICKET)
    out = capsys.readouterr().out
    assert "needs to be reset or completed" in out
    assert _state(tmp_path)["blocked"] is True
    assert "interruption_cleared" not in _action_names(tmp_path)

    run(pipeline, monkeypatch, "resume", TICKET, "--force")
    out = capsys.readouterr().out
    assert "Pipeline resumed successfully" in out
    assert _state(tmp_path)["blocked"] is False
    assert _state(tmp_path)["status"] == "resumed"

    run(pipeline, monkeypatch, "show", "state", TICKET)
    out = capsys.readouterr().out
    assert "PIPELINE BLOCKED" not in out
    assert "Blocked: False" in out


@pytest.mark.integration
def test_full_cli_flow_history_is_ordered(pipeline, tmp_path, monkeypatch, capsys):
    """The history records every action of the flow in the order it happened."""
    run(pipeline, monkeypatch, "set-mode", TICKET, "automated")
    run(
        pipeline,
        monkeypatch,
        "handoff",
        TICKET,
        "--from",
        "architect",
        "--to",
        "developer",
        "--step",
        "plan",
        "--status",
        "COMPLETED",
    )
    run(pipeline, monkeypatch, "dor", TICKET, "--json", ALL_PASS)
    run(pipeline, monkeypatch, "continue", TICKET)
    run(
        pipeline,
        monkeypatch,
        "handoff",
        TICKET,
        "--from",
        "developer",
        "--to",
        "tester",
        "--step",
        "develop",
        "--status",
        "COMPLETED",
    )
    run(pipeline, monkeypatch, "continue", TICKET)
    run(
        pipeline,
        monkeypatch,
        "handoff",
        TICKET,
        "--from",
        "tester",
        "--to",
        "product-owner",
        "--step",
        "complete",
        "--status",
        "BLOCKED",
    )
    run(pipeline, monkeypatch, "resume", TICKET, "--force")
    capsys.readouterr()

    assert _action_names(tmp_path) == [
        "pipeline_created",  # set-mode creates the entry
        "handoff",  # architect -> developer, plan COMPLETED
        "dor_recorded",
        "dor_gate",  # develop gate passed
        "step_advance",  # plan -> develop
        "handoff",  # developer -> tester, develop COMPLETED
        "step_advance",  # develop -> complete
        "handoff",  # tester -> PO, BLOCKED
        "interruption_cleared",
    ]
    history = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    gate = [a for a in history[TICKET]["actions"] if a["action"] == "dor_gate"][0]
    assert gate["details"]["result"] == "passed"


@pytest.mark.integration
def test_read_only_commands_on_unknown_ticket_write_nothing(
    pipeline, tmp_path, monkeypatch, capsys
):
    """what-missed and check-stuck on a ticket with no history leave no files behind."""
    unknown = "PRO-999"
    before = _files(tmp_path)
    run(pipeline, monkeypatch, "what-missed", unknown)
    run(pipeline, monkeypatch, "check-stuck", unknown)
    run(pipeline, monkeypatch, "show", "state", unknown)
    capsys.readouterr()
    assert _files(tmp_path) == before == {"state.json": None, "history.json": None}


@pytest.mark.integration
def test_reconcile_gate_runs_without_state(pipeline, tmp_path, monkeypatch, capsys):
    """The reconcile gate passes for a reconciled diff and writes no state."""
    run(
        pipeline,
        monkeypatch,
        "reconcile",
        TICKET,
        "--changed",
        "tests/unit/test_a.py",
        "--changed",
        "docs/TESTING.md",
    )
    assert "reconciled" in capsys.readouterr().out
    assert _files(tmp_path) == {"state.json": None, "history.json": None}
