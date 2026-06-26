"""Integration tests for the TimeSheetProcessor pipeline.

These run multiple steps (select -> store -> save) against the in-memory dummy
12-sheet workbook, verifying the data model end-to-end: month sheet index =
date.month - 1, row = ROW_OFFSET + day, start in column 5, end in column 6.
No real project resources are touched here (that is the system level).
"""

import pytest

from src_timesheetalgo.TimeSheetAlgo import ROW_OFFSET

pytestmark = pytest.mark.integration


def test_pipeline_single_entry(processor_with_timelog):
    """A single in-range entry is stored at the correct sheet/row/columns."""
    processor = processor_with_timelog(
        [["15.01.2025", "09:00", "17:00"]], "15.01.2025", "15.01.2025"
    )

    processor.select_timelog_data()
    processor.store_data()

    sheet = processor.timesheet.worksheets[0]  # January
    assert sheet.cell(row=ROW_OFFSET + 15, column=5).value == "09:00"
    assert sheet.cell(row=ROW_OFFSET + 15, column=6).value == "17:00"


def test_pipeline_distributes_across_months(processor_with_timelog):
    """Entries are routed to the correct month worksheets."""
    processor = processor_with_timelog(
        [
            ["15.01.2025", "09:00", "17:00"],  # January  -> index 0
            ["20.02.2025", "08:30", "16:30"],  # February -> index 1
            ["10.06.2025", "10:00", "18:00"],  # June     -> index 5
        ],
        "01.01.2025",
        "30.06.2025",
    )

    processor.select_timelog_data()
    assert len(processor.timedata) == 3
    processor.store_data()

    sheets = processor.timesheet.worksheets
    assert sheets[0].cell(row=ROW_OFFSET + 15, column=5).value == "09:00"
    assert sheets[1].cell(row=ROW_OFFSET + 20, column=5).value == "08:30"
    assert sheets[5].cell(row=ROW_OFFSET + 10, column=5).value == "10:00"


def test_pipeline_week_of_varied_times(processor_with_timelog):
    """A realistic week of varied hours is stored correctly across rows."""
    week = [
        ["10.03.2025", "08:00", "17:00"],
        ["11.03.2025", "09:00", "17:30"],
        ["12.03.2025", "07:30", "16:00"],
        ["13.03.2025", "09:30", "18:00"],
        ["14.03.2025", "08:00", "15:00"],
    ]
    processor = processor_with_timelog(week, "10.03.2025", "14.03.2025")

    processor.select_timelog_data()
    assert len(processor.timedata) == 5
    processor.store_data()

    march = processor.timesheet.worksheets[2]
    for date_str, start, end in week:
        day = int(date_str.split(".")[0])
        assert march.cell(row=ROW_OFFSET + day, column=5).value == start
        assert march.cell(row=ROW_OFFSET + day, column=6).value == end


def test_pipeline_full_workflow_with_save(processor_with_timelog, monkeypatch):
    """The full pipeline runs and save_timesheet is invoked exactly once."""
    processor = processor_with_timelog(
        [["12.03.2025", "09:00", "17:00"], ["15.03.2025", "08:30", "16:30"]],
        "10.03.2025",
        "20.03.2025",
    )

    processor.select_timelog_data()
    processor.store_data()

    march = processor.timesheet.worksheets[2]
    assert march.cell(row=ROW_OFFSET + 12, column=5).value == "09:00"
    assert march.cell(row=ROW_OFFSET + 15, column=5).value == "08:30"

    save_calls = []
    monkeypatch.setattr(
        processor.timesheet, "save", lambda path: save_calls.append(path)
    )
    processor.save_timesheet()

    assert len(save_calls) == 1


def test_pipeline_ignores_remark_column(processor_with_timelog):
    """A 4th 'Remark' column is ignored; only start/end reach the worksheet."""
    processor = processor_with_timelog(
        [["12.03.2025", "09:00", "17:00", "Project X"]], "12.03.2025", "12.03.2025"
    )

    processor.select_timelog_data()
    processor.store_data()

    march = processor.timesheet.worksheets[2]
    assert march.cell(row=ROW_OFFSET + 12, column=5).value == "09:00"
    assert march.cell(row=ROW_OFFSET + 12, column=6).value == "17:00"
