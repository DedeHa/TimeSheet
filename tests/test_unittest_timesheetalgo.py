import pytest
import csv
import openpyxl
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open
from src_timesheetalgo.TimeSheetAlgo import (
    parse_date,
    check_file_existence,
    TimeSheetProcessor,
    DATE_FORMAT,
    ROW_OFFSET,
    TIMESHEET_SHEETS
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
    MOCK_TIMESHEET["January"].append(["", "", "", "", datetime(2023, 1, i), ""])  # Fill column 5 with date values

# Fixtures
@pytest.fixture
def mock_processor():
    """Fixture to provide a mocked TimeSheetProcessor instance."""
    processor = TimeSheetProcessor({"timelog_path": "dummy.csv", "timesheet_path": "dummy.xlsx"})
    processor.timesheet = MOCK_TIMESHEET
    return processor

@pytest.fixture
def mock_csv_file(tmp_path):
    """Fixture to create a temporary CSV file."""
    csv_file = tmp_path / "timelog.csv"
    csv_file.write_text("Date,Start,End\n15.03.2023,09:00,17:00\n")
    return csv_file

@pytest.fixture
def mock_excel_file(tmp_path):
    """Fixture to create a temporary Excel file."""
    excel_file = tmp_path / "timesheet.xlsx"
    wb = create_dummy_workbook()
    wb.save(str(excel_file))
    return excel_file

@pytest.fixture
def mock_workbook():
    """Fixture to create a dummy workbook."""
    return create_dummy_workbook()

###########################################################################
# 1. Tests for parse_date function
###########################################################################

# 1.1. Valid date input: Test that a valid date string is correctly parsed.
def test_parse_date_valid(monkeypatch):
    """
    Test Case 1.1:
    - Input: "15.03.2023"
    - Expected: Returns a valid datetime object.
    """
    monkeypatch.setattr('builtins.input', lambda prompt: "15.03.2023")
    result = parse_date("Enter date: ")
    expected = datetime.strptime("15.03.2023", DATE_FORMAT)
    assert result == expected

# 1.2. Invalid date input: Test that repeated invalid date inputs lead to a ValueError.
def test_parse_date_invalid(monkeypatch):
    """
    Test Case 1.2:
    - Input: Three invalid date strings.
    - Expected: Raises a ValueError after maximum retries.
    """
    inputs = iter(["invalid", "wrong", "bad"])
    monkeypatch.setattr('builtins.input', lambda prompt: next(inputs))
    with pytest.raises(ValueError):
        parse_date("Enter date: ")

###########################################################################
# 2. Tests for check_file_existence function
###########################################################################

# 2.1. Valid CSV file: Ensure a properly formatted CSV file is loaded correctly.
def test_check_file_existence_csv(tmp_path):
    """
    Test Case 2.1:
    - Setup: Create a temporary CSV file with a header and one data row.
    - Expected: Returns CSV data (excluding the header).
    """
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("header1,header2\nvalue1,value2\n")
    data = check_file_existence(str(csv_file), 'csv')
    assert len(data) == 1
    assert data[0] == ["value1", "value2"]

# 2.2. Non-existent CSV file: Ensure a missing CSV file raises FileNotFoundError.
def test_check_file_existence_csv_not_found(tmp_path):
    """
    Test Case 2.2:
    - Setup: Provide a non-existent CSV file path.
    - Expected: Raises FileNotFoundError.
    """
    non_existent = tmp_path / "nonexistent.csv"
    with pytest.raises(FileNotFoundError):
        check_file_existence(str(non_existent), 'csv')

# 2.3. Valid Excel file: Ensure a valid Excel workbook is loaded correctly.
def test_check_file_existence_excel(mock_excel_file):
    """
    Test Case 2.3:
    - Setup: Create a temporary Excel file using openpyxl.
    - Expected: Returns an openpyxl.Workbook object.
    """
    wb_loaded = check_file_existence(str(mock_excel_file), 'excel')
    assert isinstance(wb_loaded, openpyxl.Workbook)

# 2.4. Non-existent Excel file: Ensure a missing Excel file raises FileNotFoundError.
def test_check_file_existence_excel_not_found(tmp_path):
    """
    Test Case 2.4:
    - Setup: Provide a non-existent Excel file path.
    - Expected: Raises FileNotFoundError.
    """
    non_existent = tmp_path / "nonexistent.xlsx"
    with pytest.raises(FileNotFoundError):
        check_file_existence(str(non_existent), 'excel')

###########################################################################
# 3. Helper Function: Create a dummy workbook for testing
###########################################################################

def create_dummy_workbook():
    """
    Helper:
    - Creates a dummy Excel workbook mimicking the expected timesheet structure.
    - Contains TIMESHEET_SHEETS worksheets.
    - Sets a value in cell (3,2) of the first sheet for year extraction.
    - Populates at least one date cell in column 5 of each sheet.
    """
    wb = openpyxl.Workbook()
    for i in range(TIMESHEET_SHEETS):
        if i == 0:
            ws = wb.active
            ws.title = "Month1"
        else:
            wb.create_sheet(title=f"Month{i+1}")
    wb.worksheets[0].cell(row=3, column=2, value=datetime(2023, 1, 1))
    for idx, ws in enumerate(wb.worksheets):
        ws.cell(row=ROW_OFFSET + 1, column=5, value=datetime(2023, idx + 1, 1))
    return wb

###########################################################################
# 4. Tests for TimeSheetProcessor class methods
###########################################################################

# 4.1. Test load_files(): Check that CSV and Excel files are loaded properly.
def test_load_files(mock_csv_file, mock_excel_file):
    """
    Test Case 4.1:
    - Setup: Create temporary CSV and Excel files.
    - Expected: timelog and timesheet are loaded correctly.
    """
    config = {
        "timelog_path": str(mock_csv_file),
        "timesheet_path": str(mock_excel_file)
    }
    processor = TimeSheetProcessor(config)
    processor.load_files()
    
    assert len(processor.timelog) == 1
    assert isinstance(processor.timesheet, openpyxl.Workbook)

# 4.2. Test request_date_input() with valid inputs.
def test_request_date_input_valid(mock_excel_file, mock_csv_file, monkeypatch):
    """
    Test Case 4.2:
    - Setup: Use valid user inputs for start and end dates.
    - Expected: obj_date_startpoint and obj_date_endpoint are set to parsed datetime values.
    """
    wb = create_dummy_workbook()
    excel_file = mock_excel_file
    csv_file = mock_csv_file
    
    config = {
        "timelog_path": str(csv_file),
        "timesheet_path": str(excel_file)
    }
    processor = TimeSheetProcessor(config)
    processor.timesheet = wb
    inputs = iter(["15.03.2023", "20.03.2023"])
    monkeypatch.setattr('builtins.input', lambda prompt: next(inputs))
    
    processor.request_date_input()
    expected_start = datetime.strptime("15.03.2023", DATE_FORMAT)
    expected_end = datetime.strptime("20.03.2023", DATE_FORMAT)
    assert processor.obj_date_startpoint == expected_start
    assert processor.obj_date_endpoint == expected_end

# 4.3. Test request_date_input() with invalid inputs triggering fallback.
def test_request_date_input_invalid(mock_excel_file, mock_csv_file, monkeypatch):
    """
    Test Case 4.3:
    - Setup: Simulate invalid user input so that fallback functions are used.
    - Expected: Default start date from workbook and default end date (yesterday) are set.
    """
    wb = create_dummy_workbook()
    excel_file = mock_excel_file
    csv_file = mock_csv_file
    
    config = {
        "timelog_path": str(csv_file),
        "timesheet_path": str(excel_file)
    }
    processor = TimeSheetProcessor(config)
    processor.timesheet = wb
    monkeypatch.setattr('builtins.input', lambda prompt: "invalid")
    
    processor.request_date_input()
    expected_start = datetime(2023, 1, 1)
    expected_end = datetime.now() - timedelta(days=1)
    assert processor.obj_date_startpoint == expected_start
    assert processor.obj_date_endpoint.date() == expected_end.date()

# 4.4. Test select_timelog_data(): Check that only entries within the date range are selected.
def test_select_timelog_data(mock_processor):
    """
    Test Case 4.4:
    - Setup: Provide timelog entries with dates before, within, and after a specified range.
    - Expected: Only entries within the boundaries (inclusive) are selected.
    """
    processor = mock_processor
    processor.timelog = [
        ["10.03.2023", "08:00", "16:00"],
        ["15.03.2023", "09:00", "17:00"],
        ["20.03.2023", "10:00", "18:00"]
    ]
    processor.obj_date_startpoint = datetime.strptime("12.03.2023", DATE_FORMAT)
    processor.obj_date_endpoint = datetime.strptime("18.03.2023", DATE_FORMAT)
    
    processor.select_timelog_data()
    assert len(processor.timedata) == 1
    assert processor.timedata[0][0] == "15.03.2023"

# 4.5. Test select_timelog_data() when no entries fall within the range.
def test_select_timelog_data_no_entries(mock_processor):
    """
    Test Case 4.5:
    - Setup: Provide timelog entries outside the specified date range.
    - Expected: Raises ValueError indicating no data found.
    """
    processor = mock_processor
    processor.timelog = [
        ["10.03.2023", "08:00", "16:00"],
        ["15.03.2023", "09:00", "17:00"],
        ["20.03.2023", "10:00", "18:00"]
    ]
    processor.obj_date_startpoint = datetime.strptime("21.03.2023", DATE_FORMAT)
    processor.obj_date_endpoint = datetime.strptime("25.03.2023", DATE_FORMAT)
    with pytest.raises(ValueError):
        processor.select_timelog_data()

# 4.6. Test store_data() without overwrite: When the target cell already has data and user declines.
def test_store_data_no_overwrite(monkeypatch, mock_processor):
    """
    Test Case 4.6:
    - Setup: Provide a timelog entry with a pre-populated target cell.
    - Input: Simulate user entering "n" (decline overwrite).
    - Expected: Existing data remains unchanged.
    """
    processor = mock_processor
    processor.timedata = [["05.01.2023", "09:00", "17:00"]]
    
    sheet = processor.timesheet.worksheets[0]
    row = ROW_OFFSET + 5
    sheet.cell(row=row, column=5, value="08:00")
    
    monkeypatch.setattr('builtins.input', lambda prompt: "n")
    processor.store_data()
    
    assert sheet.cell(row=row, column=5).value == "08:00"

# 4.7. Test store_data() with overwrite: When the target cell has data and user confirms.
def test_store_data_with_overwrite(monkeypatch, mock_processor):
    """
    Test Case 4.7:
    - Setup: Provide a timelog entry with a pre-populated target cell.
    - Input: Simulate user entering "y" (confirm overwrite).
    - Expected: Target cell is overwritten with new start and end times.
    """
    processor = mock_processor
    processor.timedata = [["05.01.2023", "09:00", "17:00"]]
    
    sheet = processor.timesheet.worksheets[0]
    row = ROW_OFFSET + 5
    sheet.cell(row=row, column=5, value="08:00")
    
    monkeypatch.setattr('builtins.input', lambda prompt: "y")
    processor.store_data()
    
    assert sheet.cell(row=row, column=5).value == "09:00"
    assert sheet.cell(row=row, column=6).value == "17:00"

###########################################################################
# 5. Tests for confirm_overwrite method
###########################################################################

# 5.1. Test confirm_overwrite() returns True when input is "y".
def test_confirm_overwrite_yes(monkeypatch):
    """
    Test Case 5.1:
    - Input: " y " (with extra spaces)
    - Expected: Returns True.
    """
    processor = TimeSheetProcessor({"timelog_path": "dummy.csv", "timesheet_path": "dummy.xlsx"})
    monkeypatch.setattr('builtins.input', lambda prompt: " y ")
    result = processor.confirm_overwrite()
    assert result is True

# 5.2. Test confirm_overwrite() returns False when input is "n".
def test_confirm_overwrite_no(monkeypatch):
    """
    Test Case 5.2:
    - Input: "n"
    - Expected: Returns False.
    """
    processor = TimeSheetProcessor({"timelog_path": "dummy.csv", "timesheet_path": "dummy.xlsx"})
    monkeypatch.setattr('builtins.input', lambda prompt: "n")
    result = processor.confirm_overwrite()
    assert result is False

###########################################################################
# 6. Test for save_timesheet method
###########################################################################

# 6.1. Test save_timesheet(): Verify that the workbook's save() method is called.
def test_save_timesheet(monkeypatch, mock_workbook, tmp_path):
    """
    Test Case 6.1:
    - Setup: Override the workbook's save() method.
    - Expected: The fake save method is called.
    """
    wb = mock_workbook
    save_called = False

    def fake_save(path):
        nonlocal save_called
        save_called = True

    monkeypatch.setattr(wb, "save", fake_save)
    
    processor = TimeSheetProcessor({
        "timelog_path": "dummy.csv",
        "timesheet_path": str(tmp_path / "timesheet.xlsx")
    })
    processor.timesheet = wb
    processor.save_timesheet()
    assert save_called is True
