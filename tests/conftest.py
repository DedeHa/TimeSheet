import os
import sys
from datetime import datetime

import openpyxl
import pytest

# Ensure repository root is on sys.path so tests can import local package src_timesheetalgo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src_timesheetalgo.TimeSheetAlgo import (
    TIMESHEET_SHEETS,
    TimeSheetProcessor,
)

# Make freezegun optional so tests don't hard-fail when it isn't installed.
try:
    from freezegun import freeze_time  # type: ignore

    _HAS_FREEZEGUN = True
except Exception:  # pragma: no cover - fallback path in user envs without freezegun
    _HAS_FREEZEGUN = False
    import contextlib
    import warnings

    @contextlib.contextmanager
    def freeze_time(_):
        warnings.warn(
            "freezegun not installed; time freezing disabled. Install it with 'pip install freezegun' for deterministic test runs.",
            UserWarning,
        )
        yield


@pytest.fixture(autouse=True)
def frozen_time():
    """Freeze time for deterministic tests."""
    with freeze_time("2025-12-23"):
        yield


def create_dummy_workbook():
    """Create a dummy workbook mimicking the timesheet structure."""
    wb = openpyxl.Workbook()
    # Ensure we have TIMESHEET_SHEETS worksheets
    for i in range(TIMESHEET_SHEETS):
        if i == 0:
            ws = wb.active
            ws.title = "Month1"
        else:
            wb.create_sheet(title=f"Month{i+1}")
    # Set a year cell used by TimeSheetProcessor
    wb.worksheets[0].cell(row=3, column=2, value=datetime(2025, 1, 1))
    return wb


@pytest.fixture
def mock_workbook():
    return create_dummy_workbook()


@pytest.fixture
def mock_excel_file(tmp_path, mock_workbook):
    path = tmp_path / "timesheet.xlsx"
    mock_workbook.save(path)
    return path


@pytest.fixture
def mock_csv_file(tmp_path):
    csv_file = tmp_path / "timelog.csv"
    csv_file.write_text("Date,Start,End\n15.03.2025,09:00,17:00\n")
    return csv_file


@pytest.fixture
def mock_processor(mock_csv_file, mock_excel_file):
    config = {
        "timelog_path": str(mock_csv_file),
        "timesheet_path": str(mock_excel_file),
    }
    processor = TimeSheetProcessor(config)
    processor.load_files()
    return processor


@pytest.fixture
def real_resource_copy(tmp_path):
    """Helper to copy real resource files into tmp_path when available.
    Returns a dict with paths if available, else None.
    """
    import shutil
    from pathlib import Path

    result = {}
    timelog_src = Path("sup/2025_extract.csv")
    timesheet_src = Path("src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm")
    if timelog_src.exists() and timesheet_src.exists():
        timelog_dst = tmp_path / "timelog_copy.csv"
        timesheet_dst = tmp_path / "timesheet_copy.xlsm"
        shutil.copy2(timelog_src, timelog_dst)
        shutil.copy2(timesheet_src, timesheet_dst)
        result["timelog_path"] = str(timelog_dst)
        result["timesheet_path"] = str(timesheet_dst)
        result["backup_path"] = str(tmp_path / "backup.xlsm")
        return result
    return None
