"""System tests: drive the real TimeSheetProcessor against real-file copies.

This replaces the old VerificationTester, which re-implemented the algorithm.
Here we run the shipped code end-to-end and then re-open the saved workbook to
verify the data really landed where it should.
"""

import csv
from datetime import datetime

import openpyxl
import pytest

from src_timesheetalgo.TimeSheetAlgo import (
    ROW_OFFSET,
    TimeSheetProcessor,
    check_file_existence,
)

pytestmark = pytest.mark.system


def _first_january_entry(csv_path):
    """Return the first ``[date, start, end]`` row in January from the CSV."""
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.reader(f))[1:]  # skip header
    for row in rows:
        if len(row) >= 3 and row[0].endswith(".01.2025"):
            return row
    return None


def test_real_csv_loads(real_resource_copy):
    """The real timelog CSV loads into well-formed rows."""
    if real_resource_copy is None:
        pytest.skip("Real resource files not available")

    data = check_file_existence(real_resource_copy["timelog_path"], "csv")
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(len(row) >= 3 for row in data)


def test_real_excel_loads(real_resource_copy):
    """The real timesheet workbook loads with at least 12 month worksheets."""
    if real_resource_copy is None:
        pytest.skip("Real resource files not available")

    wb = check_file_existence(real_resource_copy["timesheet_path"], "excel")
    assert isinstance(wb, openpyxl.Workbook)
    assert len(wb.worksheets) >= 12


def test_real_pipeline_writes_and_persists(real_resource_copy, monkeypatch):
    """Run the real pipeline for one January day and confirm it was saved."""
    if real_resource_copy is None:
        pytest.skip("Real resource files not available")

    entry = _first_january_entry(real_resource_copy["timelog_path"])
    if entry is None:
        pytest.skip("No January 2025 entry in the real CSV")
    date_str, start, end = entry[0], entry[1], entry[2]
    day = int(date_str.split(".")[0])

    # Any overwrite prompt should proceed.
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")

    processor = TimeSheetProcessor(dict(real_resource_copy))
    processor.load_files()
    processor.obj_date_startpoint = datetime(2025, 1, day)
    processor.obj_date_endpoint = datetime(2025, 1, day)
    processor.select_timelog_data()
    processor.store_data()
    processor.save_timesheet()

    # Re-open the saved file and verify the cell really holds the CSV value.
    reloaded = openpyxl.load_workbook(
        real_resource_copy["timesheet_path"], keep_vba=True
    )
    cell = reloaded.worksheets[0].cell(row=ROW_OFFSET + day, column=5)
    assert cell.value == start
    assert reloaded.worksheets[0].cell(row=ROW_OFFSET + day, column=6).value == end
