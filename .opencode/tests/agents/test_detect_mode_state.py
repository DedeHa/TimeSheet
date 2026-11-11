"""detect_mode.py shares pipeline.py's state file (PRO-407, tester finding F1).

The script must reuse pipeline.py's fail-closed reader and atomic writer: a corrupt
file exits 1 and keeps its bytes, reads never create ~/.opencode, and a mode write goes
through os.replace from a unique temporary file in the same directory. HOME is
redirected to tmp_path before the script is loaded, so nothing touches the real home.
"""

from __future__ import annotations

import importlib.util
import itertools
import os
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".opencode" / "scripts" / "detect_mode.py"
_COUNTER = itertools.count()


@pytest.fixture
def mode(tmp_path, monkeypatch):
    """Load detect_mode.py fresh with HOME pointing at tmp_path/home."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    spec = importlib.util.spec_from_file_location(
        f"detect_mode_state_{next(_COUNTER)}", _SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.STATE_PATH == home / ".opencode" / "pipeline-state.json"
    return module


def _run(module, monkeypatch, *argv: str) -> int:
    """Run the script's main() with the given command-line arguments."""
    monkeypatch.setattr(sys, "argv", ["detect_mode.py", *argv])
    return module.main()


CORRUPT_CONTENTS = [b"{not json", b"[1, 2, 3]", b"\xff\xfe garbage", b'"just a string"']


@pytest.mark.parametrize("content", CORRUPT_CONTENTS)
def test_show_on_corrupt_state_exits_1_and_keeps_bytes(
    mode, monkeypatch, capsys, content
):
    """--show reports a corrupt state file (exit 1) and keeps it."""
    state_dir = mode.STATE_PATH.parent
    state_dir.mkdir()
    mode.STATE_PATH.write_bytes(content)
    assert _run(mode, monkeypatch, "PRO-1", "--show") == 1
    assert "It was not modified" in capsys.readouterr().err
    assert mode.STATE_PATH.read_bytes() == content
    assert sorted(p.name for p in state_dir.iterdir()) == ["pipeline-state.json"]


@pytest.mark.parametrize("content", CORRUPT_CONTENTS)
def test_mode_write_on_corrupt_state_exits_1_and_keeps_bytes(
    mode, monkeypatch, capsys, content
):
    """A mode write refuses a corrupt state file: exit 1, bytes kept."""
    state_dir = mode.STATE_PATH.parent
    state_dir.mkdir()
    mode.STATE_PATH.write_bytes(content)
    assert _run(mode, monkeypatch, "PRO-1", "run in automated") == 1
    assert "It was not modified" in capsys.readouterr().err
    assert mode.STATE_PATH.read_bytes() == content
    assert sorted(p.name for p in state_dir.iterdir()) == ["pipeline-state.json"]


def test_show_on_fresh_home_does_not_create_directory(mode, monkeypatch, capsys):
    """Reading the mode from a fresh HOME reports the default only."""
    assert _run(mode, monkeypatch, "PRO-1", "--show") == 0
    assert capsys.readouterr().out.strip() == "interactive"
    assert not mode.STATE_PATH.parent.exists()


def test_no_mode_message_on_fresh_home_does_not_create_directory(
    mode, monkeypatch, capsys
):
    """A message without a mode keyword only reads the state."""
    assert _run(mode, monkeypatch, "PRO-1", "no mode here") == 0
    assert "current mode: interactive" in capsys.readouterr().out
    assert not mode.STATE_PATH.parent.exists()


def test_mode_write_creates_directory_lazily(mode, monkeypatch):
    """The first write creates ~/.opencode and stores the mode."""
    assert _run(mode, monkeypatch, "PRO-1", "run in automated") == 0
    assert mode.STATE_PATH.parent.is_dir()
    assert mode.get_mode("PRO-1") == "automated"


def test_mode_write_uses_atomic_replace(mode, monkeypatch):
    """The mode write uses os.replace from a unique temp file."""
    calls = []
    original_replace = os.replace

    def spy(src, dst):
        calls.append((Path(src), Path(dst)))
        return original_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy)
    assert _run(mode, monkeypatch, "PRO-1", "run in automated") == 0
    assert len(calls) == 1
    src, dst = calls[0]
    assert dst == mode.STATE_PATH
    assert src.parent == mode.STATE_PATH.parent
    assert src.name != "pipeline-state.json.tmp"
    assert not src.exists()


def test_failed_replace_keeps_previous_state(mode, monkeypatch):
    """A failed replace keeps the previous state and leaves no temp file."""
    state_dir = mode.STATE_PATH.parent
    state_dir.mkdir()
    previous = b'{"PRO-1": {"development_mode": "interactive"}}'
    mode.STATE_PATH.write_bytes(previous)

    def failing(src, dst):
        raise OSError("simulated failure")

    monkeypatch.setattr(os, "replace", failing)
    with pytest.raises(OSError):
        _run(mode, monkeypatch, "PRO-1", "run in automated")
    assert mode.STATE_PATH.read_bytes() == previous
    assert sorted(p.name for p in state_dir.iterdir()) == ["pipeline-state.json"]
