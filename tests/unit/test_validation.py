"""Unit tests for the validation functions.

``validate_timelog_entry`` and ``validate_timesheet_structure`` are pure
functions that raise typed exceptions on invalid input.
"""

import openpyxl
import pytest

from src.TimeSheetAlgo import (
    TIMESHEET_SHEETS,
    TimelogFormatError,
    TimesheetFormatError,
    validate_timelog_entry,
    validate_timesheet_structure,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# validate_timelog_entry
# ---------------------------------------------------------------------------


def test_validate_timelog_entry_valid():
    """A valid 3-column row with a parseable date does not raise."""
    validate_timelog_entry(["15.03.2025", "09:00", "17:00"])


def test_validate_timelog_entry_too_few_columns():
    """A row with fewer than 3 columns raises TimelogFormatError."""
    with pytest.raises(TimelogFormatError, match="3 columns"):
        validate_timelog_entry(["15.03.2025"])


def test_validate_timelog_entry_invalid_date():
    """A row with an unparseable date raises TimelogFormatError."""
    with pytest.raises(TimelogFormatError, match="Invalid date"):
        validate_timelog_entry(["not-a-date", "09:00", "17:00"])


def test_validate_timelog_entry_non_list():
    """A non-iterable entry raises TimelogFormatError."""
    with pytest.raises(TimelogFormatError):
        validate_timelog_entry("15.03.2025")


# ---------------------------------------------------------------------------
# validate_timesheet_structure
# ---------------------------------------------------------------------------


def _make_valid_workbook():
    wb = openpyxl.Workbook()
    for i in range(TIMESHEET_SHEETS):
        if i == 0:
            wb.active.title = f"Month{i+1}"
        else:
            wb.create_sheet(title=f"Month{i+1}")
    return wb


def test_validate_timesheet_structure_valid():
    """A workbook with 12 sheets and a valid year cell passes."""
    wb = _make_valid_workbook()
    wb.worksheets[0].cell(row=3, column=2, value=2025)
    validate_timesheet_structure(wb)


def test_validate_timesheet_structure_none():
    """A None workbook raises TimesheetFormatError."""
    with pytest.raises(TimesheetFormatError, match="None"):
        validate_timesheet_structure(None)


def test_validate_timesheet_structure_too_few_sheets():
    """A workbook with fewer than 12 sheets raises TimesheetFormatError."""
    wb = openpyxl.Workbook()
    wb.create_sheet(title="Only1")
    with pytest.raises(TimesheetFormatError, match="at least 12"):
        validate_timesheet_structure(wb)


def test_validate_timesheet_structure_empty_year_cell():
    """A workbook with the year-check sheet but an empty year cell raises."""
    wb = _make_valid_workbook()
    # Rename first sheet to "Januar" to trigger year-cell check
    wb.worksheets[0].title = "Januar"
    with pytest.raises(TimesheetFormatError, match="empty"):
        validate_timesheet_structure(wb)


def test_validate_timesheet_structure_non_numeric_year():
    """A workbook with a non-numeric year cell raises TimesheetFormatError."""
    wb = _make_valid_workbook()
    wb.worksheets[0].title = "Januar"
    wb.worksheets[0].cell(row=3, column=2, value="not-a-year")
    with pytest.raises(TimesheetFormatError, match="no usable year"):
        validate_timesheet_structure(wb)
