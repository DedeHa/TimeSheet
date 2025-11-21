import pytest
import openpyxl
from datetime import datetime, timedelta
from TimeSheetAlgo import (
    parse_date,
    check_file_existence,
    TimeSheetProcessor,
    DATE_FORMAT,
    ROW_OFFSET,
    TIMESHEET_SHEETS,
)

# Mock data
MOCK_TIMELOG = [
    ["01.01.2025", "08:00", "16:00"],
    ["15.01.2025", "09:00", "17:00"],
    ["31.01.2025", "10:00", "18:00"],
]

MOCK_TIMESHEET = openpyxl.Workbook()
MOCK_TIMESHEET.create_sheet("January")
for i in range(1, 32):
    MOCK_TIMESHEET["January"].append(
        ["", "", "", "", datetime(2025, 1, i), ""]
    )  # Fill column 5 with date values


# Fixtures
@pytest.fixture
def mock_processor(mock_csv_file, mock_excel_file):
    """Fixture to provide a mocked TimeSheetProcessor instance with loaded files."""
    config = {
        "timelog_path": str(mock_csv_file),
        "timesheet_path": str(mock_excel_file),
    }
    processor = TimeSheetProcessor(config)
    processor.load_files()
    return processor


@pytest.fixture
def mock_csv_file(tmp_path):
    """Fixture to create a temporary CSV file."""
    csv_file = tmp_path / "timelog.csv"
    csv_file.write_text("Date,Start,End\n15.03.2025,09:00,17:00\n")
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
# Helper Function: Create a dummy workbook for testing
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
    wb.worksheets[0].cell(row=3, column=2, value=datetime(2025, 1, 1))
    return wb


###########################################################################
# 1. Tests for parse_date function
###########################################################################


# 1.1. Valid date input: Test that a valid date string is correctly parsed.
@pytest.mark.parametrize(
    "input_date, expected",
    [
        ("15.03.2025", datetime.strptime("15.03.2025", DATE_FORMAT)),
    ],
)
def test_parse_date_valid(monkeypatch, input_date, expected):
    """
    Test Case 1.1:
    - Input: Valid date string.
    - Expected: Returns a valid datetime object.
    """
    monkeypatch.setattr("builtins.input", lambda prompt: input_date)
    result = parse_date("Enter date: ")
    assert result == expected


# 1.2. Invalid date input: Test that repeated invalid date inputs lead to a ValueError.
@pytest.mark.parametrize(
    "inputs",
    [
        (["invalid", "wrong", "bad"]),
    ],
)
def test_parse_date_invalid(monkeypatch, inputs):
    """
    Test Case 1.2:
    - Input: Three invalid date strings.
    - Expected: Raises a ValueError after maximum retries.
    """
    monkeypatch.setattr("builtins.input", lambda prompt: next(iter(inputs)))
    with pytest.raises(ValueError):
        parse_date("Enter date: ")


###########################################################################
# 2. Tests for check_file_existence function
###########################################################################


# 2.1. Valid CSV file: Ensure a properly formatted CSV file is loaded correctly.
def test_check_file_existence_csv(mock_csv_file):
    """
    Test Case 2.1:
    - Setup: Create a temporary CSV file with a header and one data row.
    - Expected: Returns CSV data (excluding the header).
    """
    data = check_file_existence(str(mock_csv_file), "csv")
    assert len(data) == 1
    assert data[0] == ["15.03.2025", "09:00", "17:00"]


# 2.2. Non-existent CSV file: Ensure a missing CSV file raises FileNotFoundError.
def test_check_file_existence_csv_not_found(tmp_path):
    """
    Test Case 2.2:
    - Setup: Provide a non-existent CSV file path.
    - Expected: Raises FileNotFoundError.
    """
    non_existent = tmp_path / "nonexistent.csv"
    with pytest.raises(FileNotFoundError):
        check_file_existence(str(non_existent), "csv")


# 2.3. Valid Excel file: Ensure a valid Excel workbook is loaded correctly.
def test_check_file_existence_excel(mock_excel_file):
    """
    Test Case 2.3:
    - Setup: Create a temporary Excel file using openpyxl.
    - Expected: Returns an openpyxl.Workbook object.
    """
    wb_loaded = check_file_existence(str(mock_excel_file), "excel")
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
        check_file_existence(str(non_existent), "excel")


###########################################################################
# 3. Tests for TimeSheetProcessor class methods
###########################################################################


# 3.1. Test load_files(): Check that CSV and Excel files are loaded properly.
def test_load_files(mock_processor):
    """
    Test Case 3.1:
    - Setup: Use mock_processor fixture.
    - Expected: timelog and timesheet are loaded correctly.
    """
    assert len(mock_processor.timelog) == 1
    assert isinstance(mock_processor.timesheet, openpyxl.Workbook)


# 3.2. Test request_date_input() with valid inputs.
def test_request_date_input_valid(mock_processor, monkeypatch):
    """
    Test Case 3.2:
    - Setup: Use valid user inputs for start and end dates.
    - Expected: obj_date_startpoint and obj_date_endpoint are set to parsed
      datetime values.
    """
    inputs = iter(["15.03.2025", "20.03.2025"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

    mock_processor.request_date_input()
    expected_start = datetime.strptime("15.03.2025", DATE_FORMAT)
    expected_end = datetime.strptime("20.03.2025", DATE_FORMAT)
    assert mock_processor.obj_date_startpoint == expected_start
    assert mock_processor.obj_date_endpoint == expected_end


# 3.3. Test request_date_input() with invalid inputs triggering fallback and
# default date extraction
def test_request_date_input_invalid_default(mock_processor, monkeypatch):
    """
    Test Case 3.3:
    - Setup: Simulate invalid user input so that fallback functions are used.
      without specific date.
    - Expected: Default start date from workbook and default end date
      (yesterday) are set.
    """
    monkeypatch.setattr("builtins.input", lambda prompt: "invalid")

    mock_processor.request_date_input()
    expected_start = datetime(2025, 1, 1)
    expected_end = datetime.now() - timedelta(days=1)
    assert mock_processor.obj_date_startpoint == expected_start
    assert mock_processor.obj_date_endpoint.date() == expected_end.date()


# 3.4. Test request_date_input() with invalid inputs triggering fallback
# with specific date
def test_request_date_input_invalid_specific(mock_processor, monkeypatch):
    """
    Test Case 3.3:
    - Setup: Simulate invalid user input so that fallback functions are used
      with a specific date.
    - Expected: Default start date from workbook are set with specific start date
    """
    mock_processor.timesheet.worksheets[6].cell(
        row=ROW_OFFSET + 1, column=5, value=datetime(2025, 7, 1)
    )
    monkeypatch.setattr("builtins.input", lambda prompt: "invalid")

    mock_processor.request_date_input()
    expected_start = datetime(2025, 7, 1)
    assert mock_processor.obj_date_startpoint == expected_start

    # for idx, ws in enumerate(wb.worksheets):
    # ws.cell(row=ROW_OFFSET + 1, column=5, value=datetime(2023, idx + 1, 1))


# 3.5. Test request_date_input() with empty inputs (default paths)
def test_request_date_input_empty_inputs(mock_processor, monkeypatch):
    """
    Test Case 3.5:
    - Setup: Simulate empty user input (just pressing Enter).
    - Expected: Default dates are used for both start and end.
    """
    monkeypatch.setattr("builtins.input", lambda prompt: "")

    mock_processor.request_date_input()
    expected_start = datetime(2025, 1, 1)
    expected_end = datetime.now() - timedelta(days=1)
    assert mock_processor.obj_date_startpoint == expected_start
    assert mock_processor.obj_date_endpoint.date() == expected_end.date()


# 3.6. Test set_default_start_date() with non-datetime year cell
def test_set_default_start_date_fallback_year(mock_processor):
    """
    Test Case 3.6:
    - Setup: Set year cell to non-datetime value to trigger YEAR fallback.
    - Expected: Uses YEAR constant when year_cell is not datetime.
    """
    # Set year cell to non-datetime value
    mock_processor.timesheet.worksheets[0].cell(row=3, column=2, value="2025")

    # Add some time data to trigger the date finding logic
    mock_processor.timesheet.worksheets[6].cell(
        row=ROW_OFFSET + 15, column=5, value="09:00"
    )

    result = mock_processor.set_default_start_date()
    assert result.year == 2025  # Should use YEAR constant
    assert result.month == 7  # July (worksheet index 6 + 1)
    assert result.day == 15  # Row offset calculation


# 3.7. Test confirm_overwrite() with EOFError
def test_confirm_overwrite_eoferror(monkeypatch):
    """
    Test Case 3.7:
    - Setup: Simulate EOFError in input (e.g., Ctrl+D).
    - Expected: Returns True (default to overwrite).
    """

    def mock_input_eoferror(prompt):
        raise EOFError()

    processor = TimeSheetProcessor(
        {"timelog_path": "dummy.csv", "timesheet_path": "dummy.xlsx"}
    )
    monkeypatch.setattr("builtins.input", mock_input_eoferror)
    result = processor.confirm_overwrite()
    assert result is True


# 3.8. Test _get_date method (currently unused but should be covered)
def test_get_date_method(mock_processor, monkeypatch):
    """
    Test Case 3.8:
    - Setup: Test the _get_date method with both success and fallback scenarios.
    - Expected: Returns parsed date on success, fallback result on failure.
    """
    # Test successful parsing
    monkeypatch.setattr("builtins.input", lambda prompt: "15.03.2025")
    result = mock_processor._get_date("Enter date: ", lambda: datetime(2025, 1, 1))
    assert result == datetime(2025, 3, 15)

    # Test fallback on exception
    monkeypatch.setattr("builtins.input", lambda prompt: "invalid")
    fallback_date = datetime(2025, 12, 31)
    result = mock_processor._get_date("Enter date: ", lambda: fallback_date)
    assert result == fallback_date


# 3.9. Test select_timelog_data(): Check that only entries within the date range
# are selected.
def test_select_timelog_data(mock_processor):
    """
    Test Case 3.4:
    - Setup: Provide timelog entries with dates before, within, and after a
      specified range.
    - Expected: Only entries within the boundaries (inclusive) are selected.
    """
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


# 3.6. Test select_timelog_data() when no entries fall within the range.
def test_select_timelog_data_no_entries(mock_processor):
    """
    Test Case 3.5:
    - Setup: Provide timelog entries outside the specified date range.
    - Expected: Raises ValueError indicating no data found.
    """
    mock_processor.timelog = [
        ["10.03.2025", "08:00", "16:00"],
        ["15.03.2025", "09:00", "17:00"],
        ["20.03.2025", "10:00", "18:00"],
    ]
    mock_processor.obj_date_startpoint = datetime.strptime("21.03.2025", DATE_FORMAT)
    mock_processor.obj_date_endpoint = datetime.strptime("25.03.2025", DATE_FORMAT)
    with pytest.raises(ValueError):
        mock_processor.select_timelog_data()


# 3.7. Test store_data() without overwrite: When the target cell already has data and
# user declines.
def test_store_data_no_overwrite(monkeypatch, mock_processor):
    """
    Test Case 3.6:
    - Setup: Provide a timelog entry with a pre-populated target cell.
    - Input: Simulate user entering "n" (decline overwrite).
    - Expected: Existing data remains unchanged.
    """
    mock_processor.timedata = [["05.01.2025", "09:00", "17:00"]]

    sheet = mock_processor.timesheet.worksheets[0]
    row = ROW_OFFSET + 5
    sheet.cell(row=row, column=5, value="08:00")

    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    mock_processor.store_data()

    assert sheet.cell(row=row, column=5).value == "08:00"


# 3.8. Test store_data() with overwrite: When target cell has data and user confirms.
def test_store_data_with_overwrite(monkeypatch, mock_processor):
    """
    Test Case 3.7:
    - Setup: Provide a timelog entry with a pre-populated target cell.
    - Input: Simulate user entering "y" (confirm overwrite).
    - Expected: Target cell is overwritten with new start and end times.
    """
    mock_processor.timedata = [["05.01.2025", "09:00", "17:00"]]

    sheet = mock_processor.timesheet.worksheets[0]
    row = ROW_OFFSET + 5
    sheet.cell(row=row, column=5, value="08:00")

    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    mock_processor.store_data()

    assert sheet.cell(row=row, column=5).value == "09:00"
    assert sheet.cell(row=row, column=6).value == "17:00"


###########################################################################
# 4. Tests for confirm_overwrite method
###########################################################################


# 4.1. Test confirm_overwrite() returns True when input is "y".
@pytest.mark.parametrize(
    "user_input, expected",
    [
        (" y ", True),
        ("n", False),
    ],
)
def test_confirm_overwrite(monkeypatch, user_input, expected):
    """
    Test Case 4.1 & 4.2:
    - Input: User input for overwrite confirmation.
    - Expected: Returns True for "y" and False for "n".
    """
    processor = TimeSheetProcessor(
        {"timelog_path": "dummy.csv", "timesheet_path": "dummy.xlsx"}
    )
    monkeypatch.setattr("builtins.input", lambda prompt: user_input)
    result = processor.confirm_overwrite()
    assert result == expected


###########################################################################
# 5. Test for save_timesheet method
###########################################################################


# 5.1. Test save_timesheet(): Verify that the workbook's save() method is called.
def test_save_timesheet(monkeypatch, mock_workbook, tmp_path):
    """
    Test Case 5.1:
    - Setup: Override the workbook's save() method.
    - Expected: The fake save method is called.
    """
    wb = mock_workbook
    save_called = False

    def fake_save(path):
        nonlocal save_called
        save_called = True

    monkeypatch.setattr(wb, "save", fake_save)

    processor = TimeSheetProcessor(
        {
            "timelog_path": "dummy.csv",
            "timesheet_path": str(tmp_path / "timesheet.xlsx"),
        }
    )
    processor.timesheet = wb
    processor.save_timesheet()
    assert save_called is True
