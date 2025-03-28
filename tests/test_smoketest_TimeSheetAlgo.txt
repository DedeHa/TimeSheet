import pytest
from unittest.mock import patch, mock_open
from datetime import datetime as dt, timedelta as td
import openpyxl
from src_timesheetalgo.TimeSheetAlgo import (
    TimeSheetProcessor,
    parse_date,
    check_file_existence,
    ROW_OFFSET,
    CONFIG,
    DATE_FORMAT,
)

# Mock data
MOCK_TIMELOG = [
    ["01.01.2023", "08:00", "16:00"],
    ["15.01.2023", "09:00", "17:00"],
    ["31.01.2023", "10:00", "18:00"],
]

MOCK_TIMESHEET = openpyxl.Workbook()
MOCK_TIMESHEET.create_sheet("January")
for i in range(1, 32):
    MOCK_TIMESHEET["January"].append(
        ["", "", "", "", dt(2023, 1, i), ""]
    )  # Fill column 5 with date values


# Fixtures
@pytest.fixture
def mock_processor():
    """Fixture to provide a mocked TimeSheetProcessor instance."""
    processor = TimeSheetProcessor(CONFIG)
    processor.timesheet = MOCK_TIMESHEET
    return processor


def test_parse_date_valid():
    """Test parse_date with valid input."""
    with patch("builtins.input", return_value="01.01.2023"):
        assert parse_date("Enter a date: ") == dt.strptime("01.01.2023", DATE_FORMAT)


def test_parse_date_invalid():
    """Test parse_date with 2x invalid input and a third correct input."""
    with patch("builtins.input", side_effect=["invalid", "01-01-2023", "01.01.2023"]):
        assert parse_date("Enter a date: ") == dt.strptime("01.01.2023", DATE_FORMAT)


def test_parse_date_exceed_retries():
    """Test parse_date exceeding retries."""
    with patch("builtins.input", side_effect=["invalid", "01-01-2023", "not a date"]):
        with pytest.raises(ValueError, match="Maximum retries reached"):
            parse_date("Enter a date: ")


def test_check_file_existence_csv():
    mock_csv = "Date,Start Time,End Time\n01.01.2023,08:00,16:00\n"
    with patch("builtins.open", mock_open(read_data=mock_csv)):
        data = check_file_existence("test.csv", "csv")
        assert len(data) == 1
        assert data[0] == ["01.01.2023", "08:00", "16:00"]


def test_check_file_existence_excel():
    """Test check_file_existence for Excel files."""
    with patch("openpyxl.load_workbook", return_value=MOCK_TIMESHEET):
        workbook = check_file_existence("test.xlsm", "excel")
        assert isinstance(workbook, openpyxl.Workbook)


def test_load_files(mock_processor):
    """Test the load_files method."""
    mock_processor.timelog = MOCK_TIMELOG
    mock_processor.timesheet = MOCK_TIMESHEET
    with patch(
        "src_timesheetalgo.TimeSheetAlgo.check_file_existence",
        side_effect=[MOCK_TIMELOG, MOCK_TIMESHEET],
    ):
        mock_processor.load_files()
        assert mock_processor.timelog == MOCK_TIMELOG
        assert mock_processor.timesheet == MOCK_TIMESHEET


def test_select_timelog_data(mock_processor):
    """Test the select_timelog_data method."""
    mock_processor.timelog = MOCK_TIMELOG
    mock_processor.obj_date_startpoint = dt.strptime("01.01.2023", DATE_FORMAT)
    mock_processor.obj_date_endpoint = dt.strptime("31.01.2023", DATE_FORMAT)
    mock_processor.select_timelog_data()
    assert len(mock_processor.timedata) == 3
    assert mock_processor.timedata[0] == ["01.01.2023", "08:00", "16:00"]
    assert mock_processor.timedata[2] == ["31.01.2023", "10:00", "18:00"]


def test_store_data(mock_processor):
    """Test the store_data method."""
    mock_processor.timelog = MOCK_TIMELOG

    mock_processor.timesheet = MOCK_TIMESHEET
    sheet = mock_processor.timesheet.active
    rows = [[""] * 6 for _ in range(31)]
    for row in rows:
        sheet.append(row)
    mock_processor.timedata = mock_processor.timelog

    with patch(
        "builtins.input", return_value="y"
    ):  # Mock user input for overwrite confirmation
        mock_processor.store_data()

    assert sheet.cell(row=ROW_OFFSET + 1, column=5).value == "08:00"
    assert sheet.cell(row=ROW_OFFSET + 1, column=6).value == "16:00"
    assert sheet.cell(row=ROW_OFFSET + 15, column=5).value == "09:00"
    assert sheet.cell(row=ROW_OFFSET + 15, column=6).value == "17:00"
    assert sheet.cell(row=ROW_OFFSET + 31, column=5).value == "10:00"
    assert sheet.cell(row=ROW_OFFSET + 31, column=6).value == "18:00"


def test_confirm_overwrite():
    """Test confirm_overwrite method."""
    with patch("builtins.input", return_value="y"):
        processor = TimeSheetProcessor(CONFIG)
        assert processor.confirm_overwrite() is True


def test_set_default_start_date(mock_processor):
    """Test set_default_start_date method."""
    mock_processor.timesheet = MOCK_TIMESHEET
    mock_processor.timesheet.worksheets[0].cell(row=3, column=2).value = dt(2023, 1, 1)
    default_date = mock_processor.set_default_start_date()
    assert default_date.date() == dt.strptime("01.01.2023", DATE_FORMAT)


def test_set_default_end_date(mock_processor):
    """Test set_default_end_date method."""
    default_date = mock_processor.set_default_end_date()
    assert default_date.date() == (dt.now() - td(days=1)).date()


def test_save_timesheet(mock_processor):
    """Test save_timesheet method."""
    with patch.object(MOCK_TIMESHEET, "save", return_value=None) as mock_save:
        mock_processor.save_timesheet()
        mock_save.assert_called_once_with(CONFIG["timesheet_path"])


def test_main_execution():
    """Test the main execution flow."""
    processor = TimeSheetProcessor(CONFIG)
    with patch.object(processor, "load_files"), patch.object(
        processor, "request_date_input"
    ), patch.object(processor, "select_timelog_data"), patch.object(
        processor, "store_data"
    ), patch.object(
        processor, "save_timesheet"
    ):
        processor.load_files()
        processor.request_date_input()
        processor.select_timelog_data()
        processor.store_data()
        processor.save_timesheet()
