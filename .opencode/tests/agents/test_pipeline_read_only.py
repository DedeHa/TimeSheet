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


def _expected_exit(argv: list[str]) -> int:
    """Read commands exit 0. `reset` without --force is a refused confirmation: exit 1."""
    return 1 if argv[0] == "reset" else 0


def _run_cli(pipeline, monkeypatch, argv: list[str]) -> int:
    """Run one CLI invocation and return its exit code (0 when it returns normally)."""
    monkeypatch.setattr(sys, "argv", ["pipeline.py", *argv])
    try:
        pipeline.main()
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    return 0


@pytest.mark.parametrize("argv", READ_COMMANDS, ids=lambda a: " ".join(a))
def test_read_command_on_unknown_ticket_creates_nothing(
    pipeline, tmp_path, monkeypatch, capsys, argv
):
    """FR-22: a read command on an unknown ticket leaves no state or history behind."""
    before = _snapshot(tmp_path)
    assert before == {"state.json": None, "history.json": None}
    assert _run_cli(pipeline, monkeypatch, argv) == _expected_exit(argv)
    capsys.readouterr()
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("argv", READ_COMMANDS, ids=lambda a: " ".join(a))
def test_read_command_on_unknown_ticket_keeps_existing_files_byte_identical(
    pipeline, tmp_path, monkeypatch, capsys, argv
):
    """FR-22: with files present for another ticket, the bytes do not change."""
    _seed_known_ticket(tmp_path)
    before = _snapshot(tmp_path)
    assert _run_cli(pipeline, monkeypatch, argv) == _expected_exit(argv)
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


WRITE_COMMANDS = [
    ["set-mode", UNKNOWN, "automated"],
    ["dor", UNKNOWN, "--json", '{"D1": "pass"}'],
    ["waive", UNKNOWN, "D3", "--reason", "why", "--by", "PO"],
    ["continue", UNKNOWN],
    ["resume", UNKNOWN, "--force"],
    ["reset", UNKNOWN, "--force"],
    ["handoff", UNKNOWN, "--from", "architect", "--to", "developer", "--status", "COMPLETED"],
]

CORRUPT_CONTENTS = [b"{not json", b"[1, 2]", b"", b"\xff\xfe\x00 not utf-8", b"\"text\""]


@pytest.mark.parametrize("content", CORRUPT_CONTENTS, ids=["truncated", "list", "empty", "binary", "string"])
@pytest.mark.parametrize("corrupt", ["state.json", "history.json"])
@pytest.mark.parametrize("argv", READ_COMMANDS + WRITE_COMMANDS, ids=lambda a: " ".join(a))
def test_corrupt_file_fails_closed(
    pipeline, tmp_path, monkeypatch, capsys, argv, corrupt, content
):
    """FR-22: a corrupt state or history file makes every command exit 1 and changes nothing.

    The corrupt file keeps its exact bytes (read or write attempt), the other file is not
    created, and the tool never reports a fresh plan or not_started state.
    """
    (tmp_path / corrupt).write_bytes(content)
    before = _snapshot(tmp_path)
    code = _run_cli(pipeline, monkeypatch, argv)
    out = capsys.readouterr().out
    assert code == 1, out
    assert "It was not modified" in out
    assert "not_started" not in out
    assert _snapshot(tmp_path) == before
    assert not list(tmp_path.glob("*.tmp")), "no temporary file may be left behind"


def test_corrupt_state_read_does_not_show_default_plan(pipeline, tmp_path, monkeypatch, capsys):
    """A corrupt state file is reported as an error, not shown as a fresh plan."""
    (tmp_path / "state.json").write_bytes(b"{truncated")
    assert _run_cli(pipeline, monkeypatch, ["show", "state", KNOWN]) == 1
    out = capsys.readouterr().out
    assert "Current Step: plan" not in out
    assert "Pipeline State:" not in out


def test_failed_write_keeps_existing_file_and_leaves_no_temp(
    pipeline, tmp_path, monkeypatch, capsys
):
    """J (architect 14): a write that fails midway leaves the old file and no temp file."""
    _seed_known_ticket(tmp_path)
    before = _snapshot(tmp_path)

    def broken_dump(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(pipeline.json, "dump", broken_dump)
    code = _run_cli(pipeline, monkeypatch, ["set-mode", "PRO-999", "automated"])
    assert code == 1
    assert "disk full" in capsys.readouterr().out
    assert _snapshot(tmp_path) == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["history.json", "state.json"]


def test_successful_write_leaves_only_the_target_files(pipeline, tmp_path, monkeypatch, capsys):
    """J (architect 14): an atomic write replaces the file and leaves no temp behind."""
    assert _run_cli(pipeline, monkeypatch, ["set-mode", "PRO-999", "automated"]) == 0
    capsys.readouterr()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["history.json", "state.json"]
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["PRO-999"]["development_mode"] == "automated"


def test_read_commands_do_not_create_the_home_directory(tmp_path, monkeypatch, capsys):
    """J (tester 4): read commands never create ~/.opencode; the first write does.

    HOME points at a directory that does not exist, and the module is loaded under it
    without redirecting STATE_PATH, so the real default paths are exercised.
    """
    home = tmp_path / "fresh-home"
    monkeypatch.setenv("HOME", str(home))
    spec = importlib.util.spec_from_file_location("pipeline_home_under_test", PIPELINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.STATE_PATH == home / ".opencode" / "pipeline-state.json"

    for argv in READ_COMMANDS:
        monkeypatch.setattr(sys, "argv", ["pipeline.py", *argv])
        try:
            module.main()
        except SystemExit:
            pass  # reset without --force exits 1 by design; the point is no directory
    capsys.readouterr()
    assert not (home / ".opencode").exists()

    monkeypatch.setattr(sys, "argv", ["pipeline.py", "set-mode", UNKNOWN, "automated"])
    module.main()
    capsys.readouterr()
    assert (home / ".opencode" / "pipeline-state.json").is_file()
