import pytest
from datetime import datetime as dt
from unittest import mock
from ALGO_TIMESHEET import ALGO_TIMESHEET  # assuming your class is in ALGO_TIMESHEET.py


@pytest.fixture
def mock_timesheet(tmpdir):
    # Create a mock timesheet file with minimum valid content
    file = tmpdir.join("mock_timesheet.xlsm")
    file.write('''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"> ... </workbook>''')
    return str(file)


@pytest.fixture
def mock_timelog(tmpdir):
    # Create a mock timelog CSV file
    file = tmpdir.join("mock_timelog.csv")
    file.write('''Date,StartTime,EndTime
    01.09.2023,08:00,17:00
    02.09.2023,08:00,17:00
    ''')
    return str(file)


# Test case: Handle missing timelog or timesheet file
def test_missing_files(monkeypatch):
    # Mock missing file paths
    algo = ALGO_TIMESHEET()

    with pytest.raises(SystemExit):
        algo.fct_che_pre_req()  # Expect SystemExit if files are missing


# Test case: Date input validation
@mock.patch('builtins.input', side_effect=["01.09.2023", "02.09.2023"])
def test_date_input_valid(mock_input):
    algo = ALGO_TIMESHEET()
    algo.fct_req_algo_para()

    assert algo.obj_date_startpoint == dt.strptime("01.09.2023", "%d.%m.%Y")
    assert algo.obj_date_endpoint == dt.strptime("02.09.2023", "%d.%m.%Y")


# Test case: Invalid date input
@mock.patch('builtins.input', side_effect=["invalid_date", "01.09.2023", "invalid_date", "02.09.2023"])
def test_date_input_invalid(mock_input):
    algo = ALGO_TIMESHEET()

    algo.fct_req_algo_para()

    assert algo.obj_date_startpoint == dt.strptime("01.09.2023", "%d.%m.%Y")
    assert algo.obj_date_endpoint == dt.strptime("02.09.2023", "%d.%m.%Y")


# Test case: Timelog selection within date range
def test_timelog_selection(mock_timelog, mock_timesheet):
    algo = ALGO_TIMESHEET()

    # Set mock paths for timelog and timesheet
    algo.str_path_timelog = mock_timelog
    algo.str_path_timesheet = mock_timesheet

    # Mock the selected start and end dates
    algo.obj_date_startpoint = dt.strptime("01.09.2023", "%d.%m.%Y")
    algo.obj_date_endpoint = dt.strptime("02.09.2023", "%d.%m.%Y")

    # Run pre-req checks and timelog selection
    algo.fct_che_pre_req()
    algo.fct_sel_timelog()

    # Verify that all log entries within the range are selected
    assert len(algo.obj_newtimedata) == 2  # both entries should be selected
    assert algo.obj_newtimedata[0] == ['01.09.2023', '08:00', '17:00']


# Test case: Timesheet data storage
@mock.patch('builtins.input', side_effect=["y"])
def test_timesheet_data_storage(mock_input, mock_timelog, mock_timesheet):
    algo = ALGO_TIMESHEET()

    # Set mock paths for timelog and timesheet
    algo.str_path_timelog = mock_timelog
    algo.str_path_timesheet = mock_timesheet

    # Mock the selected start and end dates
    algo.obj_date_startpoint = dt.strptime("01.09.2023", "%d.%m.%Y")
    algo.obj_date_endpoint = dt.strptime("02.09.2023", "%d.%m.%Y")

    # Pre-req check and timelog selection
    algo.fct_che_pre_req()
    algo.fct_sel_timelog()

    # Simulate storing data
    algo.fct_store_data()

    # Check if the timesheet contains the correct data (mock assertions will depend on mocking framework)
    sheet = algo.timesheet.worksheets[0]  # Assume the first sheet is the correct one
    assert sheet.cell(row=5, column=5).value == '08:00'  # Assuming date corresponds to row 5
    assert sheet.cell(row=5, column=6).value == '17:00'


# Test case: Handle overwrite prompt
@mock.patch('builtins.input', side_effect=["n"])  # Simulate user saying no to overwrite
def test_overwrite_prompt(mock_input, mock_timelog, mock_timesheet):
    algo = ALGO_TIMESHEET()

    # Set mock paths for timelog and timesheet
    algo.str_path_timelog = mock_timelog
    algo.str_path_timesheet = mock_timesheet

    # Mock the selected start and end dates
    algo.obj_date_startpoint = dt.strptime("01.09.2023", "%d.%m.%Y")
    algo.obj_date_endpoint = dt.strptime("02.09.2023", "%d.%m.%Y")

    # Pre-req check and timelog selection
    algo.fct_che_pre_req()
    algo.fct_sel_timelog()

    # Simulate storing data and denying overwrite
    algo.fct_store_data()

    # Check if no data was overwritten due to user denial
    sheet = algo.timesheet.worksheets[0]
    assert sheet.cell(row=5, column=5).value is None  # The cell should remain empty if overwrite was denied
