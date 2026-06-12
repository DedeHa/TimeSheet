"""Integration tests for date/row boundary behaviour of the pipeline."""

import pytest

from src_timesheetalgo.TimeSheetAlgo import ROW_OFFSET

pytestmark = pytest.mark.integration


def test_first_day_of_month(processor_with_timelog):
    """Day 1 lands on row ROW_OFFSET + 1 (=5)."""
    processor = processor_with_timelog(
        [["01.01.2025", "08:00", "16:00"]], "01.01.2025", "01.01.2025"
    )
    processor.select_timelog_data()
    processor.store_data()

    assert (
        processor.timesheet.worksheets[0].cell(row=ROW_OFFSET + 1, column=5).value
        == "08:00"
    )


def test_last_day_of_month(processor_with_timelog):
    """Day 31 lands on row ROW_OFFSET + 31 (=35)."""
    processor = processor_with_timelog(
        [["31.01.2025", "10:00", "18:00"]], "01.01.2025", "31.01.2025"
    )
    processor.select_timelog_data()
    processor.store_data()

    assert (
        processor.timesheet.worksheets[0].cell(row=ROW_OFFSET + 31, column=5).value
        == "10:00"
    )


def test_month_boundary_routes_to_two_sheets(processor_with_timelog):
    """31 Jan and 01 Feb are routed to worksheets[0] and worksheets[1]."""
    processor = processor_with_timelog(
        [["31.01.2025", "08:00", "16:00"], ["01.02.2025", "09:00", "17:00"]],
        "31.01.2025",
        "01.02.2025",
    )
    processor.select_timelog_data()
    processor.store_data()

    assert (
        processor.timesheet.worksheets[0].cell(row=ROW_OFFSET + 31, column=5).value
        == "08:00"
    )
    assert (
        processor.timesheet.worksheets[1].cell(row=ROW_OFFSET + 1, column=5).value
        == "09:00"
    )


def test_cross_year_entries_excluded(processor_with_timelog):
    """A previous-year entry is filtered out; only the in-year entry is stored."""
    processor = processor_with_timelog(
        [["30.12.2024", "09:00", "17:00"], ["15.01.2025", "08:30", "16:30"]],
        "01.01.2025",
        "31.12.2025",
    )
    processor.select_timelog_data()
    assert len(processor.timedata) == 1
    assert processor.timedata[0][0] == "15.01.2025"

    processor.store_data()
    # The 2025 entry is written; the 2024 entry never reaches December.
    assert (
        processor.timesheet.worksheets[0].cell(row=ROW_OFFSET + 15, column=5).value
        == "08:30"
    )
    assert (
        processor.timesheet.worksheets[11].cell(row=ROW_OFFSET + 30, column=5).value
        is None
    )
