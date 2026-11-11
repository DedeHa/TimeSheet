"""Checks that the agent suite runs under the isolated HOME (PRO-407, tester finding 1)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

PIPELINE_PATH = (
    Path(__file__).resolve().parents[3] / ".opencode" / "scripts" / "pipeline.py"
)


def test_home_is_redirected_to_session_directory(session_home):
    """HOME points at the session temp directory, not the real home."""
    assert Path.home() == session_home
    assert session_home.is_dir()


def test_pipeline_paths_resolve_under_session_home(session_home):
    """pipeline.py imported in this session writes under the session home."""
    spec = importlib.util.spec_from_file_location(
        "pipeline_isolation_check", PIPELINE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert str(module.STATE_PATH).startswith(str(session_home))
    assert str(module.HISTORY_PATH).startswith(str(session_home))
