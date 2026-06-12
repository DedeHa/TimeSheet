"""System-level fixtures.

System tests are black-box: they copy the real project resources into a
temporary directory and drive the shipped TimeSheetProcessor / run() / main().
They skip cleanly when the real resources are not present (e.g. on CI without
the data files).
"""

import shutil
from pathlib import Path

import pytest

from src_timesheetalgo.TimeSheetAlgo import run

# Real resources, resolved relative to the repository root (pytest rootdir).
_TIMELOG_SRC = Path("sup/2025_extract.csv")
_TIMESHEET_SRC = Path("src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm")


@pytest.fixture
def real_resource_copy(tmp_path):
    """Copy the real CSV + xlsm into ``tmp_path``.

    Returns a dict of copy paths, or ``None`` when either source is missing so
    callers can skip.
    """
    if not (_TIMELOG_SRC.exists() and _TIMESHEET_SRC.exists()):
        return None

    timelog_dst = tmp_path / "timelog_copy.csv"
    timesheet_dst = tmp_path / "timesheet_copy.xlsm"
    shutil.copy2(_TIMELOG_SRC, timelog_dst)
    shutil.copy2(_TIMESHEET_SRC, timesheet_dst)
    return {
        "timelog_path": str(timelog_dst),
        "timesheet_path": str(timesheet_dst),
        "year": 2025,
    }


@pytest.fixture
def cli_runner(real_resource_copy, monkeypatch):
    """Drive the real ``run()`` pipeline in-process against the copies.

    Skips if resources are unavailable. Returns ``run_cli(answers)`` which feeds
    ``answers`` (strings) to ``input()`` and returns the saved timesheet path.
    Once ``answers`` is exhausted, further prompts default to ``"y"`` so an
    unexpected overwrite prompt never raises StopIteration.
    """
    if real_resource_copy is None:
        pytest.skip("Real resource files not available")

    def _run_cli(answers):
        it = iter(answers)
        monkeypatch.setattr("builtins.input", lambda prompt="": next(it, "y"))
        run(dict(real_resource_copy))
        return real_resource_copy["timesheet_path"]

    return _run_cli
