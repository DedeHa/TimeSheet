"""Read-only guarantees for pipeline.py inspection commands (PRO-407, FR-22).

`show`, `what-missed`, `check-stuck`, `dry-run`, `history`, `get-mode`, and the
non-forced `reset` warning must not create state or history entries for a ticket
that has never been seen. STATE_PATH and HISTORY_PATH are redirected to tmp_path.
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
UNKNOWN = "PRO-999"
KNOWN = "PRO-407"

READ_COMMANDS = [
    ["show", "state", UNKNOWN],
    ["what-missed", UNKNOWN],
    ["check-stuck", UNKNOWN],
    ["dry-run", UNKNOWN, "resume"],
    ["dry-run", UNKNOWN, "continue"],
    ["dry-run", UNKNOWN, "what_missed"],
    ["history", UNKNOWN],
    ["get-mode", UNKNOWN],
    ["reset", UNKNOWN],
]


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    """Load pipeline.py with state and history redirected to tmp_path."""
    spec = importlib.util.spec_from_file_location(
        "pipeline_read_only_under_test", PIPELINE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(module, "HISTORY_PATH", tmp_path / "history.json")
    return module


def _snapshot(tmp_path) -> dict:
    """Return the raw bytes of both files, or None when a file does not exist."""
    result = {}
    for name in ("state.json", "history.json"):
        path = tmp_path / name
        result[name] = path.read_bytes() if path.exists() else None
    return result


def _seed_known_ticket(tmp_path) -> None:
    """Write a state and history for a different ticket so the files are non-empty."""
    state = {
        KNOWN: {
            "development_mode": "automated",
            "current_step": "develop",
            "cycle_counts": {"plan": 1, "develop": 0, "complete": 0},
            "last_updated": "2026-11-10T10:00:00+00:00",
            "status": "in_progress",
            "blocked": False,
            "escalation_level": 0,
            "interrupted": False,
            "interrupted_step": None,
            "interrupted_at": None,
        }
    }
    history = {
        KNOWN: {
            "created": "2026-11-10T10:00:00+00:00",
            "last_updated": "2026-11-10T10:00:00+00:00",
            "actions": [
                {
                    "timestamp": "2026-11-10T10:00:00+00:00",
                    "action": "pipeline_created",
                    "details": {},
                }
            ],
            "transitions": [],
        }
    }
    (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")
    (tmp_path / "history.json").write_text(json.dumps(history), encoding="utf-8")


def _run_cli(pipeline, monkeypatch, argv: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["pipeline.py", *argv])
    pipeline.main()


@pytest.mark.parametrize("argv", READ_COMMANDS, ids=lambda a: " ".join(a))
def test_read_command_on_unknown_ticket_creates_nothing(
    pipeline, tmp_path, monkeypatch, capsys, argv
):
    """FR-22: a read command on an unknown ticket leaves no state or history behind."""
    before = _snapshot(tmp_path)
    assert before == {"state.json": None, "history.json": None}
    _run_cli(pipeline, monkeypatch, argv)
    capsys.readouterr()
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("argv", READ_COMMANDS, ids=lambda a: " ".join(a))
def test_read_command_on_unknown_ticket_keeps_existing_files_byte_identical(
    pipeline, tmp_path, monkeypatch, capsys, argv
):
    """FR-22: with files present for another ticket, the bytes do not change."""
    _seed_known_ticket(tmp_path)
    before = _snapshot(tmp_path)
    _run_cli(pipeline, monkeypatch, argv)
    capsys.readouterr()
    assert _snapshot(tmp_path) == before


def test_peek_entry_returns_default_without_storing(pipeline, tmp_path):
    """_peek_entry hands back a default entry and does not add it to state."""
    mgr = pipeline.PipelineManager()
    entry = mgr._peek_entry(UNKNOWN)
    assert entry["current_step"] == "plan"
    assert entry["status"] == "not_started"
    assert UNKNOWN not in mgr.state
    assert not (tmp_path / "state.json").exists()


def test_get_entry_still_creates_for_write_paths(pipeline, tmp_path):
    """Writes keep creating the entry and recording pipeline_created."""
    mgr = pipeline.PipelineManager()
    mgr._get_entry(UNKNOWN)
    assert UNKNOWN in json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    history = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert [a["action"] for a in history[UNKNOWN]["actions"]] == ["pipeline_created"]
