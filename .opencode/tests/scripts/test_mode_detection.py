"""Tests for the pipeline mode detection script."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".opencode" / "scripts" / "detect_mode.py"
_SPEC = importlib.util.spec_from_file_location("detect_mode", _SCRIPT)
_DETECT_MODE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_DETECT_MODE)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("run in automated", "automated"),
        ("run automated mode", "automated"),
        ("go ahead", "automated"),
        ("proceed directly", "automated"),
        ("just run it", "automated"),
        ("without confirmation", "automated"),
        ("run in interactive", "interactive"),
        ("run interactive mode", "interactive"),
        ("pause between steps", "interactive"),
        ("confirm before each step", "interactive"),
        ("ask me before proceeding", "interactive"),
        ("no mode here", None),
    ],
)
def test_detect_mode_conversational_patterns(message: str, expected: str | None):
    """Mode detection should accept conversational user phrasing."""
    assert _DETECT_MODE.detect_mode(message)["mode"] == expected


def test_detect_mode_confidence_levels():
    """Specific mode phrases should be high confidence, hints low confidence."""
    assert _DETECT_MODE.detect_mode("run in automated")["confidence"] == "high"
    assert _DETECT_MODE.detect_mode("go ahead")["confidence"] == "low"


def test_detect_mode_matched_phrase():
    """Detection should report the phrase that triggered the match."""
    result = _DETECT_MODE.detect_mode("Please run in automated mode")
    assert result["matched"] == "run in automated"


def test_mode_persistence_round_trip(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Mode should persist to and load from the state file."""
    state_dir = tmp_path / ".opencode"
    state_dir.mkdir()
    monkeypatch.setattr(_DETECT_MODE, "STATE_PATH", state_dir / "pipeline-state.json")
    entry = _DETECT_MODE.set_mode("PRO-123", "automated")
    assert entry["development_mode"] == "automated"
    assert _DETECT_MODE.get_mode("PRO-123") == "automated"
    assert _DETECT_MODE.get_mode("PRO-999") == "interactive"
    assert (
        json.loads(_DETECT_MODE.STATE_PATH.read_text())["PRO-123"]["development_mode"]
        == "automated"
    )
