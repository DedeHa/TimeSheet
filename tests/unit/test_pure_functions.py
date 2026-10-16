"""Unit tests for the extracted pure functions.

``filter_timelog_entries``, ``calculate_default_start_date`` and
``map_entry_to_cell`` are pure: they take plain Python data and return plain
Python data — no file I/O, no mocks, no instance state.
"""

from datetime import datetime

import pytest

from src.TimeSheetAlgo import (
    ROW_OFFSET,
    TIMESHEET_SHEETS,
    calculate_default_start_date,
    filter_timelog_entries,
    map_entry_to_cell,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# filter_timelog_entries
# ---------------------------------------------------------------------------


def _row(date_str, start="09:00", end="17:00"):
    return [date_str, start, end]


def test_filter_inclusive_both_ends():
    """Entries on the boundary dates are included."""
    rows = [
        _row("14.03.2025"),
        _row("15.03.2025"),
        _row("16.03.2025"),
        _row("17.03.2025"),
    ]
    result = filter_timelog_entries(rows, datetime(2025, 3, 15), datetime(2025, 3, 16))
    assert result == [_row("15.03.2025"), _row("16.03.2025")]


def test_filter_empty_input():
    """An empty input yields an empty output."""
    assert (
        filter_timelog_entries([], datetime(2025, 1, 1), datetime(2025, 12, 31)) == []
    )


def test_filter_no_matches():
    """Entries outside the range are excluded."""
    rows = [_row("01.01.2025"), _row("31.12.2025")]
    assert (
        filter_timelog_entries(rows, datetime(2025, 6, 1), datetime(2025, 6, 30)) == []
    )


def test_filter_single_day_range():
    """A single-day range includes only that day."""
    rows = [_row("15.03.2025"), _row("16.03.2025")]
    result = filter_timelog_entries(rows, datetime(2025, 3, 15), datetime(2025, 3, 15))
    assert result == [_row("15.03.2025")]


def test_filter_full_year():
    """All entries in the year are included."""
    rows = [_row("01.01.2025"), _row("15.06.2025"), _row("31.12.2025")]
    result = filter_timelog_entries(rows, datetime(2025, 1, 1), datetime(2025, 12, 31))
    assert result == rows


# ---------------------------------------------------------------------------
# calculate_default_start_date
# ---------------------------------------------------------------------------


def _make_workbook_with_day(sheet_idx, day, start="09:00"):
    import openpyxl

    wb = openpyxl.Workbook()
    for i in range(TIMESHEET_SHEETS):
        if i == 0:
            wb.active.title = f"Month{i+1}"
        else:
            wb.create_sheet(title=f"Month{i+1}")
    wb.worksheets[sheet_idx].cell(row=ROW_OFFSET + day, column=5, value=start)
    return wb


def test_calculate_default_start_date_finds_latest_worked_day():
    """The latest worked day across all sheets is returned."""
    wb = _make_workbook_with_day(0, 5)  # Jan 5
    wb.worksheets[5].cell(row=ROW_OFFSET + 15, column=5, value="09:00")  # Jun 15
    result = calculate_default_start_date(wb, 2025)
    assert (result.year, result.month, result.day) == (2025, 6, 15)


def test_calculate_default_start_date_no_data_returns_jan_1():
    """With no worked days, the default start date is Jan 1 of the year."""
    import openpyxl

    wb = openpyxl.Workbook()
    for i in range(TIMESHEET_SHEETS):
        if i == 0:
            wb.active.title = f"Month{i+1}"
        else:
            wb.create_sheet(title=f"Month{i+1}")
    result = calculate_default_start_date(wb, 2025)
    assert result == datetime(2025, 1, 1)


def test_calculate_default_start_date_day_31_boundary():
    """A worked day on the 31st is detected (PRO-262 boundary)."""
    wb = _make_workbook_with_day(0, 31)
    result = calculate_default_start_date(wb, 2025)
    assert (result.year, result.month, result.day) == (2025, 1, 31)


def test_calculate_default_start_date_month_boundary():
    """A worked day on the 1st of a month is detected."""
    wb = _make_workbook_with_day(11, 1)  # Dec 1
    result = calculate_default_start_date(wb, 2025)
    assert (result.year, result.month, result.day) == (2025, 12, 1)


# ---------------------------------------------------------------------------
# map_entry_to_cell
# ---------------------------------------------------------------------------


def test_map_entry_to_cell_january_15():
    """January 15 maps to sheet 0, row ROW_OFFSET+15."""
    row, month_idx, start, end = map_entry_to_cell(["15.01.2025", "09:00", "17:00"])
    assert row == ROW_OFFSET + 15
    assert month_idx == 0
    assert start == "09:00"
    assert end == "17:00"


def test_map_entry_to_cell_december_31():
    """December 31 maps to sheet 11, row ROW_OFFSET+31."""
    row, month_idx, start, end = map_entry_to_cell(["31.12.2025", "08:00", "16:00"])
    assert row == ROW_OFFSET + 31
    assert month_idx == 11
    assert start == "08:00"
    assert end == "16:00"


def test_map_entry_to_cell_june_30():
    """June 30 maps to sheet 5, row ROW_OFFSET+30."""
    row, month_idx, _, _ = map_entry_to_cell(["30.06.2025", "09:00", "17:00"])
    assert row == ROW_OFFSET + 30
    assert month_idx == 5


def test_map_entry_to_cell_custom_offset():
    """A custom row_offset is respected."""
    row, _, _, _ = map_entry_to_cell(["15.03.2025", "09:00", "17:00"], row_offset=10)
    assert row == 10 + 15
