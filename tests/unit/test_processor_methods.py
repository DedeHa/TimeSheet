"""Unit tests for TimeSheetProcessor methods exercised in isolation.

Covers load_files, request_date_input, select_timelog_data and save_timesheet.
The overwrite-decision methods live in test_overwrite.py; the multi-step
pipeline (store_data wired with select/save) lives at the integration level.
"""

from datetime import datetime, timedelta

import openpyxl
import pytest

from src_timesheetalgo.TimeSheetAlgo import DATE_FORMAT, TimeSheetProcessor

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# load_files
# ---------------------------------------------------------------------------


def test_load_files(mock_processor):
    """load_files populates timelog (list) and timesheet (workbook)."""
    assert len(mock_processor.timelog) == 1
    assert isinstance(mock_processor.timesheet, openpyxl.Workbook)


# ---------------------------------------------------------------------------
# request_date_input
# ---------------------------------------------------------------------------


def test_request_date_input_valid(mock_processor, monkeypatch):
    """Valid start/end strings are parsed onto the processor."""
    inputs = iter(["15.03.2025", "20.03.2025"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

    mock_processor.request_date_input()

    assert mock_processor.obj_date_startpoint == datetime(2025, 3, 15)
    assert mock_processor.obj_date_endpoint == datetime(2025, 3, 20)


def test_request_date_input_invalid_uses_defaults(mock_processor, monkeypatch):
    """Invalid input falls back to default start (Jan 1) and end (yesterday)."""
    monkeypatch.setattr("builtins.input", lambda prompt: "invalid")

    mock_processor.request_date_input()

    assert mock_processor.obj_date_startpoint == datetime(2025, 1, 1)
    assert (
        mock_processor.obj_date_endpoint.date()
        == (datetime.now() - timedelta(days=1)).date()
    )


def test_request_date_input_empty_uses_defaults(mock_processor, monkeypatch):
    """Empty input (just Enter) falls back to the default dates."""
    monkeypatch.setattr("builtins.input", lambda prompt: "")

    mock_processor.request_date_input()

    assert mock_processor.obj_date_startpoint == datetime(2025, 1, 1)
    assert (
        mock_processor.obj_date_endpoint.date()
        == (datetime.now() - timedelta(days=1)).date()
    )


def test_request_date_input_eof_uses_defaults(mock_processor, monkeypatch):
    """An EOFError on input (e.g. piped EOF) falls back to the default dates."""

    def raise_eof(prompt):
        raise EOFError()

    monkeypatch.setattr("builtins.input", raise_eof)

    mock_processor.request_date_input()

    assert mock_processor.obj_date_startpoint == datetime(2025, 1, 1)
    assert (
        mock_processor.obj_date_endpoint.date()
        == (datetime.now() - timedelta(days=1)).date()
    )


def test_request_date_input_specific_default_from_sheet(mock_processor, monkeypatch):
    """The default start date reflects the latest worked day in the workbook."""
    mock_processor.timesheet.worksheets[6].cell(
        row=5, column=5, value=datetime(2025, 7, 1)
    )  # July (index 6), day 1 -> row ROW_OFFSET + 1
    monkeypatch.setattr("builtins.input", lambda prompt: "invalid")

    mock_processor.request_date_input()

    assert mock_processor.obj_date_startpoint == datetime(2025, 7, 1)


# ---------------------------------------------------------------------------
# select_timelog_data
# ---------------------------------------------------------------------------


def test_select_timelog_data_in_range(mock_processor):
    """Only entries within the inclusive date range are selected."""
    mock_processor.timelog = [
        ["10.03.2025", "08:00", "16:00"],
        ["15.03.2025", "09:00", "17:00"],
        ["20.03.2025", "10:00", "18:00"],
    ]
    mock_processor.obj_date_startpoint = datetime.strptime("12.03.2025", DATE_FORMAT)
    mock_processor.obj_date_endpoint = datetime.strptime("18.03.2025", DATE_FORMAT)

    mock_processor.select_timelog_data()

    assert len(mock_processor.timedata) == 1
    assert mock_processor.timedata[0][0] == "15.03.2025"


def test_select_timelog_data_empty_raises(mock_processor):
    """No matching entries raises ValueError."""
    mock_processor.timelog = [["10.03.2025", "08:00", "16:00"]]
    mock_processor.obj_date_startpoint = datetime.strptime("15.03.2025", DATE_FORMAT)
    mock_processor.obj_date_endpoint = datetime.strptime("20.03.2025", DATE_FORMAT)

    with pytest.raises(ValueError, match="No data found"):
        mock_processor.select_timelog_data()


# ---------------------------------------------------------------------------
# save_timesheet
# ---------------------------------------------------------------------------


def test_save_timesheet_calls_save(monkeypatch, mock_workbook, tmp_path):
    """save_timesheet delegates to workbook.save with the configured path."""
    saved = {}

    def fake_save(path):
        saved["path"] = path

    monkeypatch.setattr(mock_workbook, "save", fake_save)

    path = str(tmp_path / "timesheet.xlsx")
    processor = TimeSheetProcessor(
        {"timelog_path": "dummy.csv", "timesheet_path": path, "year": 2025}
    )
    processor.timesheet = mock_workbook
    processor.save_timesheet()

    assert saved["path"] == path


# ---------------------------------------------------------------------------
# PRO-262: select_timelog_data range boundary / equivalence analysis
# ---------------------------------------------------------------------------
#
# The filter keeps rows with start <= date <= end (inclusive both ends). These
# pin the boundary partitions (just-before / on-start / on-end / just-after),
# the degenerate single-day and inverted ranges, the empty-input class, and a
# malformed row (robustness gap).


def test_select_timelog_data_range_inclusive_both_ends(mock_processor):
    """Entries on the start and end dates are kept; the neighbours are excluded."""
    mock_processor.timelog = [
        ["09.03.2025", "08:00", "16:00"],  # day before start -> excluded
        ["10.03.2025", "08:00", "16:00"],  # on start         -> included
        ["18.03.2025", "10:00", "18:00"],  # on end           -> included
        ["19.03.2025", "10:00", "18:00"],  # day after end    -> excluded
    ]
    mock_processor.obj_date_startpoint = datetime.strptime("10.03.2025", DATE_FORMAT)
    mock_processor.obj_date_endpoint = datetime.strptime("18.03.2025", DATE_FORMAT)

    mock_processor.select_timelog_data()

    assert [row[0] for row in mock_processor.timedata] == ["10.03.2025", "18.03.2025"]


def test_select_timelog_data_single_day_range(mock_processor):
    """A start == end range selects exactly the entry on that day."""
    mock_processor.timelog = [
        ["14.03.2025", "08:00", "16:00"],
        ["15.03.2025", "09:00", "17:00"],
        ["16.03.2025", "10:00", "18:00"],
    ]
    mock_processor.obj_date_startpoint = datetime.strptime("15.03.2025", DATE_FORMAT)
    mock_processor.obj_date_endpoint = datetime.strptime("15.03.2025", DATE_FORMAT)

    mock_processor.select_timelog_data()

    assert [row[0] for row in mock_processor.timedata] == ["15.03.2025"]


def test_select_timelog_data_inverted_range_raises(mock_processor):
    """An inverted range (start > end) matches nothing and raises ValueError."""
    mock_processor.timelog = [["15.03.2025", "09:00", "17:00"]]
    mock_processor.obj_date_startpoint = datetime.strptime("20.03.2025", DATE_FORMAT)
    mock_processor.obj_date_endpoint = datetime.strptime("10.03.2025", DATE_FORMAT)

    with pytest.raises(ValueError, match="No data found"):
        mock_processor.select_timelog_data()


def test_select_timelog_data_empty_timelog_raises(mock_processor):
    """An empty timelog (header-only CSV) raises ValueError."""
    mock_processor.timelog = []
    mock_processor.obj_date_startpoint = datetime.strptime("01.01.2025", DATE_FORMAT)
    mock_processor.obj_date_endpoint = datetime.strptime("31.12.2025", DATE_FORMAT)

    with pytest.raises(ValueError, match="No data found"):
        mock_processor.select_timelog_data()


def test_select_timelog_data_malformed_row_propagates(mock_processor):
    """A row whose date cannot be parsed aborts the whole selection.

    Documents a robustness gap (PRO-262): select_timelog_data validates no
    individual row, so a single corrupt timelog line raises a parsing
    ValueError rather than being skipped.
    """
    mock_processor.timelog = [["not-a-date", "09:00", "17:00"]]
    mock_processor.obj_date_startpoint = datetime.strptime("01.01.2025", DATE_FORMAT)
    mock_processor.obj_date_endpoint = datetime.strptime("31.12.2025", DATE_FORMAT)

    with pytest.raises(ValueError, match="does not match format"):
        mock_processor.select_timelog_data()
