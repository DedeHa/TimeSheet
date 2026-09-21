"""Tests for the pipeline mode detection script."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".opencode" / "scripts" / "detect_mode.py"
_SPEC = importlib.util.spec_from_file_location("detect_mode", _SCRIPT)
_DETECT_MODE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_DETECT_MODE)

# Ensure scripts directory is on path for cross-module imports
_SCRIPTS_DIR = _REPO / ".opencode" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


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
    state_path = state_dir / "pipeline-state.json"
    history_path = state_dir / "pipeline-history.json"

    # Load pipeline module and patch its paths
    pipeline_spec = importlib.util.spec_from_file_location(
        "pipeline", _SCRIPTS_DIR / "pipeline.py"
    )
    pipeline_module = importlib.util.module_from_spec(pipeline_spec)
    pipeline_spec.loader.exec_module(pipeline_module)

    # Patch the pipeline module's STATE_PATH and HISTORY_PATH before creating manager
    monkeypatch.setattr(pipeline_module, "STATE_PATH", state_path)
    monkeypatch.setattr(pipeline_module, "HISTORY_PATH", history_path)

    # Create initial entry via pipeline manager (not detect_mode.py)
    manager = pipeline_module.PipelineManager()
    manager.init("PRO-123")

    # Now test detect_mode persistence
    entry = _DETECT_MODE.set_mode("PRO-123", "automated")
    assert entry["development_mode"] == "automated"
    assert _DETECT_MODE.get_mode("PRO-123") == "automated"
    assert _DETECT_MODE.get_mode("PRO-999") == "interactive"
    assert (
        json.loads(_DETECT_MODE.STATE_PATH.read_text())["PRO-123"]["development_mode"]
        == "automated"
    )


def test_set_mode_creates_entry_when_init(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """set_mode with create_if_missing=True creates an entry."""
    state_dir = tmp_path / ".opencode"
    state_dir.mkdir()
    state_path = state_dir / "pipeline-state.json"
    monkeypatch.setattr(_DETECT_MODE, "STATE_PATH", state_path)

    entry = _DETECT_MODE.set_mode("PRO-123", "automated", create_if_missing=True)
    assert entry["development_mode"] == "automated"
    assert json.loads(state_path.read_text())["PRO-123"]["development_mode"] == "automated"


def test_set_mode_does_not_create_entry_without_init(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """set_mode without create_if_missing should not create an entry."""
    state_dir = tmp_path / ".opencode"
    state_dir.mkdir()
    state_path = state_dir / "pipeline-state.json"
    monkeypatch.setattr(_DETECT_MODE, "STATE_PATH", state_path)

    entry = _DETECT_MODE.set_mode("PRO-123", "automated", create_if_missing=False)
    assert entry["development_mode"] == "automated"
    # State file should NOT exist because no entry was created
    assert not state_path.exists()