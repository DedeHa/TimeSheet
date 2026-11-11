"""Isolation guard for the agent-team test suite (PRO-407, tester finding 1).

pipeline.py and detect_mode.py resolve ~/.opencode when they are imported. This
conftest loads before any test module, so it points HOME at a session temp directory
first. The original home's pipeline files are fingerprinted at session start, and the
session fails at finish if either one changed, so a test that writes to the real
state can never pass silently.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import pytest

GUARDED_FILES = ("pipeline-state.json", "pipeline-history.json")

# Resolve the real home before HOME is overridden.
ORIGINAL_HOME = Path(os.path.expanduser("~"))
SESSION_HOME = Path(tempfile.mkdtemp(prefix="agents-tests-home-"))
os.environ["HOME"] = str(SESSION_HOME)


def _guarded_paths() -> list[Path]:
    """Return the real pipeline files that must not change during the session."""
    return [ORIGINAL_HOME / ".opencode" / name for name in GUARDED_FILES]


def _fingerprint(path: Path) -> Optional[Tuple[int, int]]:
    """Return (mtime_ns, size) for a file, or None when it does not exist."""
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


BASELINE = {str(path): _fingerprint(path) for path in _guarded_paths()}


def pytest_sessionfinish(session, exitstatus):
    """Fail the session if the original home's pipeline files were modified."""
    changed = [
        str(path)
        for path in _guarded_paths()
        if _fingerprint(path) != BASELINE[str(path)]
    ]
    shutil.rmtree(SESSION_HOME, ignore_errors=True)
    if changed:
        sys.stderr.write(
            "\nISOLATION FAILURE: agent tests modified the real home during this session:\n"
            + "".join(f"  - {path}\n" for path in changed)
            + "Tests must redirect STATE_PATH and HISTORY_PATH to tmp_path.\n"
        )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


@pytest.fixture(scope="session")
def session_home() -> Path:
    """The temporary HOME used for this session (never the real home)."""
    return SESSION_HOME
