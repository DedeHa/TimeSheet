import pytest
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime as dt, timedelta as td
import openpyxl
from src_timesheetalgo.TimeSheetAlgo import TimeSheetProcessor, parse_date, check_file_existence, ROW_OFFSET, CONFIG, DATE_FORMAT

# Mock data
MOCK_TIMELOG = [
    ["01.01.2023", "08:00", "16:00"],
    ["02.01.2023", "08:30", "16:30"],
    ["03.01.2023", "09:00", "17:00"],
]

MOCK_TIMESHEET = openpyxl.Workbook()
MOCK_TIMESHEET.create_sheet("January")
for i in range(1, 32):
    MOCK_TIMESHEET["January"].append(["", "", "", "", "", ""])  # Fill rows with empty data


@pytest.fixture
def mock_processor():
    """Fixture to provide a mocked TimeSheetProcessor instance."""
    processor = TimeSheetProcessor(CONFIG)
    processor.timelog = MOCK_TIMELOG
    processor.timesheet = MOCK_TIMESHEET
    processor.obj_date_startpoint = dt.strptime("01.01.2023", DATE_FORMAT)
    processor.obj_date_endpoint = dt.strptime("03.01.2023", DATE_FORMAT)
    return processor


def test_parse_date_valid():
    """Test parse_date with valid input."""
    with patch("builtins.input", return_value="01.01.2023"):
        assert parse_date("Enter a date: ") == dt.strptime("01.01.2023", DATE_FORMAT)


def test_parse_date_invalid():
    """Test parse_date with invalid input."""
    with patch("builtins.input", side_effect=["invalid", "01-01-2023", "01.01.2023"]):
        assert parse_date("Enter a date: ") == dt.strptime("01.01.2023", DATE_FORMAT)


def test_parse_date_exceed_retries():
    """Test parse_date exceeding retries."""
    with patch("builtins.input", side_effect=["invalid", "01-01-2023", "not a date"]):
        with pytest.raises(ValueError, match="Maximum retries reached"):
            parse_date("Enter a date: ")


def test_check_file_existence_csv():
    """Test check_file_existence for CSV files."""
    mock_csv_data = "Date,Start Time,End Time\n01.01.2023,08:00,16:00\n"
    with patch("builtins.open", mock_open(read_data=mock_csv_data)), patch("csv.reader") as mock_csv:
        mock_csv.return_value = [["Date", "Start Time", "End Time"], ["01.01.2023", "08:00", "16:00"]]
        assert check_file_existence("test.csv", "csv") == [["01.01.2023", "08:00", "16:00"]]


def test_check_file_existence_excel():
    """Test check_file_existence for Excel files."""
    with patch("openpyxl.load_workbook", return_value=MOCK_TIMESHEET):
        workbook = check_file_existence("test.xlsm", "excel")
        assert isinstance(workbook, openpyxl.Workbook)


def test_load_files(mock_processor):
    """Test the load_files method."""
    with patch("src_timesheetalgo.TimeSheetAlgo.check_file_existence", side_effect=[MOCK_TIMELOG, MOCK_TIMESHEET]):
        mock_processor.load_files()
        assert mock_processor.timelog == MOCK_TIMELOG
        assert mock_processor.timesheet == MOCK_TIMESHEET


def test_select_timelog_data(mock_processor):
    """Test the select_timelog_data method."""
    mock_processor.select_timelog_data()
    assert len(mock_processor.obj_newtimedata) == 3
    assert mock_processor.obj_newtimedata[0] == ["01.01.2023", "08:00", "16:00"]


def test_store_data(mock_processor):
    """Test the store_data method."""
    mock_processor.select_timelog_data()
    with patch("src_timesheetalgo.TimeSheetAlgo.input", return_value="y"):
        mock_processor.store_data()
        sheet = mock_processor.timesheet["January"]
        assert sheet.cell(row=ROW_OFFSET + 1, column=5).value == "08:00"
        assert sheet.cell(row=ROW_OFFSET + 1, column=6).value == "16:00"


def test_confirm_overwrite():
    """Test confirm_overwrite method."""
    with patch("builtins.input", return_value="y"):
        processor = TimeSheetProcessor(CONFIG)
        assert processor.confirm_overwrite() is True


def test_set_default_start_date(mock_processor):
    """Test set_default_start_date method."""
    mock_processor.timesheet = MOCK_TIMESHEET
    mock_processor.set_default_start_date()
    assert mock_processor.obj_date_startpoint == dt(2023, 1, 30)  # Assuming valid data exists


def test_set_default_end_date(mock_processor):
    """Test set_default_end_date method."""
    mock_processor.set_default_end_date()
    assert mock_processor.obj_date_endpoint == dt.now() - td(days=1)


def test_save_timesheet(mock_processor):
    """Test save_timesheet method."""
    with patch.object(MOCK_TIMESHEET, "save", return_value=None) as mock_save:
        mock_processor.save_timesheet()
        mock_save.assert_called_once_with(CONFIG["timesheet_path"])


def test_main_execution():
    """Test the main execution flow."""
    processor = TimeSheetProcessor(CONFIG)
    with patch.object(processor, "load_files"), patch.object(processor, "request_date_input"), \
            patch.object(processor, "select_timelog_data"), patch.object(processor, "store_data"), \
            patch.object(processor, "save_timesheet"):
        processor.load_files()
        processor.request_date_input()
        processor.select_timelog_data()
        processor.store_data()
        processor.save_timesheet()
