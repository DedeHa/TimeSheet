"""Shared pytest fixtures for all test levels.

Level-specific fixtures live in tests/<level>/conftest.py and cascade on top of
the fixtures defined here (root -> level -> test).
"""

import os
import sys
from datetime import datetime

import openpyxl
import pytest

# Ensure repository root is on sys.path so tests can import the local package
# `src_timesheetalgo` regardless of where pytest is invoked from.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.TimeSheetAlgo import (  # noqa: E402
    ROW_OFFSET,
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
        """Contextmanager for freezing time when freezegun is unavailable."""
        warnings.warn(
            "freezegun not installed; time freezing disabled. "
            "Install it with 'pip install freezegun' for deterministic test runs.",
            stacklevel=2,
        )
        yield


@pytest.fixture(autouse=True)
def frozen_time():
    """Freeze time so date defaults (e.g. ``now() - 1 day``) are deterministic."""
    with freeze_time("2025-12-23"):
        yield


def create_dummy_workbook():
    """Create a dummy workbook mimicking the timesheet structure.

    - ``TIMESHEET_SHEETS`` worksheets (month 1..12 -> index 0..11).
    - A year value in cell (3, 2) of the first sheet.
    """
    wb = openpyxl.Workbook()
    for i in range(TIMESHEET_SHEETS):
        if i == 0:
            ws = wb.active
            ws.title = "Month1"
        else:
            wb.create_sheet(title=f"Month{i+1}")
    wb.worksheets[0].cell(row=3, column=2, value=datetime(2025, 1, 1))
    return wb


@pytest.fixture
def mock_workbook():
    """Create a mock workbook with the timesheet structure."""
    return create_dummy_workbook()


@pytest.fixture
def mock_excel_file(tmp_path, mock_workbook):
    """Create a temporary Excel file for testing."""
    path = tmp_path / "timesheet.xlsx"
    mock_workbook.save(path)
    return path


@pytest.fixture
def mock_csv_file(tmp_path):
    """Create a temporary CSV timelog file for testing."""
    csv_file = tmp_path / "timelog.csv"
    csv_file.write_text("Date,Start,End\n15.03.2025,09:00,17:00\n")
    return csv_file


@pytest.fixture
def mock_processor(mock_csv_file, mock_excel_file):
    """Create a TimeSheetProcessor with mock files, already loaded."""
    config = {
        "timelog_path": str(mock_csv_file),
        "timesheet_path": str(mock_excel_file),
        "year": 2025,
    }
    processor = TimeSheetProcessor(config)
    processor.load_files()
    return processor


@pytest.fixture
def make_processor(tmp_path):
    """Build TimeSheetProcessor instances over a fresh dummy workbook (factory).

    Avoids the repeated "build workbook -> poke cells -> assign timelog"
    boilerplate. The workbook is held in memory; no real files are read.

    Args (all optional):
        timelog: list of ``[date, start, end]`` rows assigned to ``processor.timelog``.
        timesheet_cells: list of ``(sheet_index, day, start, end)`` tuples used to
            pre-populate existing data (``end`` may be ``None`` to set only start).
        year: configured work year (default 2025).
    """

    def _make(timelog=None, timesheet_cells=None, year=2025):
        wb = create_dummy_workbook()
        for sheet_idx, day, start, end in timesheet_cells or []:
            ws = wb.worksheets[sheet_idx]
            ws.cell(row=ROW_OFFSET + day, column=5, value=start)
            if end is not None:
                ws.cell(row=ROW_OFFSET + day, column=6, value=end)
        config = {
            "timelog_path": "dummy.csv",
            "timesheet_path": str(tmp_path / "timesheet.xlsx"),
            "year": year,
        }
        processor = TimeSheetProcessor(config)
        processor.timesheet = wb
        processor.timelog = timelog or []
        return processor

    return _make
