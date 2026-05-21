import logging
from datetime import datetime, timedelta

import openpyxl
import pytest
import yaml
from src_timesheetalgo.TimeSheetAlgo import (
    DATE_FORMAT,
    ROW_OFFSET,
    TIMESHEET_SHEETS,
    ConfigError,
    TimeSheetProcessor,
    _read_yaml,
    check_file_existence,
    configure_logging,
    detect_environment,
    load_config,
    parse_date,
)

pytestmark = pytest.mark.unit

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
# Shared fixtures (mock CSV/excel, processor, frozen time) are provided by `tests/conftest.py` to centralize test setup.


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
# 1. Tests for load_config function
###########################################################################


# 1.1. Valid configuration loading: Test loading a valid config file.
def test_load_config_valid(tmp_path, monkeypatch):
    """
    Test Case 1.1:
    - Setup: Create a valid config.yaml file with year at root level.
    - Expected: Returns configuration dictionary with correct paths and year.
    """
    # Create config file
    config_file = tmp_path / "config.yaml"
    config_content = {
        "year": 2025,
        "environments": {
            "development": {
                "file_paths": {
                    "timelog_path": "timelog.csv",
                    "timesheet_path": "timesheet.xlsx",
                },
                "logging": {"level": "INFO", "format": "%(message)s"},
            }
        },
        "default_environment": "development",
    }
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)

    # Mock detect_environment to return 'development'
    def mock_detect(base_path):
        return "development"

    # patching at import location
    monkeypatch.setattr("src_timesheetalgo.TimeSheetAlgo.detect_environment", mock_detect)

    config = load_config(str(config_file))
    assert config["timelog_path"].endswith("timelog.csv")
    assert config["timesheet_path"].endswith("timesheet.xlsx")
    assert config["year"] == 2025
    assert config["environment"] == "development"


# 1.2. Missing config file: Test error handling for missing config file.
def test_load_config_file_not_found():
    """
    Test Case 1.2:
    - Setup: Provide non-existent config file path.
    - Expected: Raises ConfigError.
    """
    with pytest.raises(ConfigError, match="Config file not found"):
        load_config("/nonexistent/path/config.yaml")


# 1.3. Invalid YAML format: Test error handling for invalid YAML.
def test_load_config_invalid_yaml(tmp_path, monkeypatch):
    """
    Test Case 1.3:
    - Setup: Create a config file with invalid YAML syntax.
    - Expected: Raises ConfigError.
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text("invalid: yaml: content: [")  # Invalid YAML

    # Mock detect_environment to avoid folder structure issues
    def mock_detect(base_path):
        return "development"

    # patching at import location
    monkeypatch.setattr("src_timesheetalgo.TimeSheetAlgo.detect_environment", mock_detect)

    with pytest.raises(ConfigError, match="Invalid YAML format"):
        load_config(str(config_file))


# 1.4. Missing environments key: Test error handling for missing environments.
def test_load_config_missing_environments(tmp_path, monkeypatch):
    """
    Test Case 1.4:
    - Setup: Config file without 'environments' key.
    - Expected: Raises KeyError.
    """
    config_file = tmp_path / "config.yaml"
    config_content = {"year": 2025, "default_environment": "development"}
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)

    # Mock detect_environment to return 'development'
    def mock_detect(base_path):
        return "development"

    # patching at import location
    monkeypatch.setattr("src_timesheetalgo.TimeSheetAlgo.detect_environment", mock_detect)

    with pytest.raises(KeyError):
        load_config(str(config_file))


# 1.5. Invalid environment name: Test error handling for non-existent environment.
def test_load_config_invalid_environment(tmp_path, monkeypatch):
    """
    Test Case 1.5:
    - Setup: Auto-detected environment doesn't exist in config.
    - Expected: Raises ConfigError.
    """
    config_file = tmp_path / "config.yaml"
    config_content = {
        "year": 2025,
        "environments": {
            "development": {
                "file_paths": {
                    "timelog_path": "timelog.csv",
                    "timesheet_path": "timesheet.xlsx",
                }
            }
        },
        "default_environment": "development",
    }
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)

    # Mock detect_environment at the import location
    monkeypatch.setattr("src_timesheetalgo.TimeSheetAlgo.detect_environment", lambda x: "invalid")

    with pytest.raises(ConfigError, match="Environment 'invalid' not found"):
        load_config(str(config_file))


# 1.6. Missing file_paths in environment: Test error handling for missing file paths.
def test_load_config_missing_file_paths(tmp_path, monkeypatch):
    """
    Test Case 1.6:
    - Setup: Environment config without 'file_paths' key.
    - Expected: Raises ConfigError.
    """
    config_file = tmp_path / "config.yaml"
    config_content = {
        "year": 2025,
        "environments": {"development": {"logging": {"level": "INFO"}}},
        "default_environment": "development",
    }
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)

    # Mock detect_environment to return 'development'
    def mock_detect(base_path):
        return "development"

    # patching at import location
    monkeypatch.setattr("src_timesheetalgo.TimeSheetAlgo.detect_environment", mock_detect)

    # Should raise KeyError when accessing file_paths
    with pytest.raises(KeyError):
        load_config(str(config_file))


# 1.7. Missing required file path keys: Test error handling for incomplete file paths.
def test_load_config_incomplete_file_paths(tmp_path, monkeypatch):
    """
    Test Case 1.7:
    - Setup: Environment with only one file path (missing timesheet_path).
    - Expected: Raises KeyError.
    """
    config_file = tmp_path / "config.yaml"
    config_content = {
        "year": 2025,
        "environments": {
            "development": {
                "file_paths": {"timelog_path": "timelog.csv"}  # Missing timesheet_path
            }
        },
        "default_environment": "development",
    }
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)

    # Mock detect_environment to return 'development'
    def mock_detect(base_path):
        return "development"

    # patching at import location
    monkeypatch.setattr("src_timesheetalgo.TimeSheetAlgo.detect_environment", mock_detect)

    # Should raise KeyError when accessing timesheet_path
    with pytest.raises(KeyError):
        load_config(str(config_file))


# 1.8. Multiple environments: Test loading specific environment from config.
def test_load_config_multiple_environments(tmp_path, monkeypatch):
    """
    Test Case 1.8:
    - Setup: Config with multiple environments.
    - Expected: Loads correct environment based on auto-detection.
    """
    config_file = tmp_path / "config.yaml"
    config_content = {
        "year": 2025,
        "environments": {
            "development": {
                "file_paths": {
                    "timelog_path": "dev_timelog.csv",
                    "timesheet_path": "dev_timesheet.xlsx",
                }
            },
            "production": {
                "file_paths": {
                    "timelog_path": "prod_timelog.csv",
                    "timesheet_path": "prod_timesheet.xlsx",
                }
            },
        },
        "default_environment": "development",
    }
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)

    # Mock detect_environment at the import location to return 'production'
    monkeypatch.setattr("src_timesheetalgo.TimeSheetAlgo.detect_environment", lambda x: "production")

    # Test loading production environment
    config = load_config(str(config_file))
    assert config["timelog_path"].endswith("prod_timelog.csv")
    assert config["timesheet_path"].endswith("prod_timesheet.xlsx")
    assert config["environment"] == "production"


# 1.9. Auto-detection of environment: Test that environment is auto-detected correctly.
def test_load_config_environment_auto_detection(tmp_path, monkeypatch):
    """
    Test Case 1.9:
    - Setup: Config with multiple environments.
    - Expected: Loads development when detect_environment returns 'development'.
    """
    config_file = tmp_path / "config.yaml"
    config_content = {
        "year": 2025,
        "environments": {
            "development": {
                "file_paths": {
                    "timelog_path": "dev_timelog.csv",
                    "timesheet_path": "dev_timesheet.xlsx",
                }
            },
            "production": {
                "file_paths": {
                    "timelog_path": "prod_timelog.csv",
                    "timesheet_path": "prod_timesheet.xlsx",
                }
            },
        },
        "default_environment": "production",
    }
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)

    # Mock detect_environment to return 'development'
    def mock_detect(base_path):
        return "development"

    # patching at import location
    monkeypatch.setattr("src_timesheetalgo.TimeSheetAlgo.detect_environment", mock_detect)

    # Test loading without specifying environment (auto-detects development)
    config = load_config(str(config_file))
    assert config["timelog_path"].endswith("dev_timelog.csv")
    assert config["environment"] == "development"


# 1.10. Invalid config structure: Test error handling for non-dict config.
def test_load_config_invalid_structure(tmp_path, monkeypatch):
    """
    Test Case 1.10:
    - Setup: Config file with non-dictionary content.
    - Expected: Raises ConfigError.
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text("- item1\n- item2\n")  # YAML list instead of dict

    # Mock detect_environment to avoid folder structure issues
    def mock_detect(base_path):
        return "development"

    # patching at import location
    monkeypatch.setattr("src_timesheetalgo.TimeSheetAlgo.detect_environment", mock_detect)

    with pytest.raises(ConfigError, match="Config root must be a mapping"):
        load_config(str(config_file))


# 1.11. Missing year at root level: Test error handling for missing year.
def test_load_config_missing_year(tmp_path, monkeypatch):
    """
    Test Case 1.11:
    - Setup: Config file without 'year' at root level.
    - Expected: Raises ConfigError.
    """
    config_file = tmp_path / "config.yaml"
    config_content = {
        "environments": {
            "development": {
                "file_paths": {
                    "timelog_path": "timelog.csv",
                    "timesheet_path": "timesheet.xlsx",
                }
            }
        }
    }
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)

    # Mock detect_environment to avoid folder structure issues
    def mock_detect(base_path):
        return "development"

    # patching at import location
    monkeypatch.setattr("src_timesheetalgo.TimeSheetAlgo.detect_environment", mock_detect)

    with pytest.raises(ConfigError, match="Missing required 'year' configuration"):
        load_config(str(config_file))


###########################################################################
# 1.12. Test detect_environment() helper function
###########################################################################


# 1.12a. Test detect_environment with src_timesheetalgo folder
def test_detect_environment_src_timesheetalgo(monkeypatch, tmp_path):
    """
    Test Case 1.12a:
    - Setup: Base path is src_timesheetalgo folder.
    - Expected: Returns 'development'.
    """

    # Create a folder named 'src_timesheetalgo'
    src_folder = tmp_path / "src_timesheetalgo"
    src_folder.mkdir()

    env = detect_environment(str(src_folder))
    assert env == "development"


# 1.12b. Test detect_environment with Timealarm folder
def test_detect_environment_timealarm_folder(tmp_path):
    """
    Test Case 1.12b:
    - Setup: Timealarm folder exists in base path.
    - Expected: Returns 'production'.
    """

    # Create Timealarm folder in base path
    timealarm_folder = tmp_path / "Timealarm"
    timealarm_folder.mkdir()

    env = detect_environment(str(tmp_path))
    assert env == "production"


# 1.12c. Test detect_environment fallback
def test_detect_environment_fallback(tmp_path):
    """
    Test Case 1.12c:
    - Setup: Neither src_timesheetalgo nor Timealarm folder exists.
    - Expected: Returns 'development' (fallback).
    """

    # Use a random folder that doesn't match criteria
    env = detect_environment(str(tmp_path))
    assert env == "development"


###########################################################################
# 1.13. Test _read_yaml() helper function
###########################################################################


def test_read_yaml_oserror(tmp_path, monkeypatch):
    """
    Test Case 1.13:
    - Setup: Mock open to raise OSError (e.g., permission denied).
    - Expected: Raises ConfigError with 'Unable to read config file' message.
    """

    config_file = tmp_path / "config.yaml"
    config_file.write_text("test: data")

    def raise_oserror(path, *args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", raise_oserror)

    with pytest.raises(ConfigError, match="Unable to read config file"):
        _read_yaml(str(config_file))


###########################################################################
# 2. Tests for configure_logging() utility function
###########################################################################


# 2.1. Test configure_logging with custom level
def test_configure_logging_custom_level(caplog):
    """
    Test Case 2.1:
    - Setup: Custom logging configuration with DEBUG level.
    - Expected: Logging is configured with DEBUG level.
    """

    config = {"level": "DEBUG", "format": "%(levelname)s - %(message)s"}

    # Clear any existing handlers before testing
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    configure_logging(config)

    # Verify that the logging config was applied by checking handlers exist
    assert len(root_logger.handlers) > 0


# 2.2. Test configure_logging with default level
def test_configure_logging_default_level(caplog):
    """
    Test Case 2.2:
    - Setup: Logging configuration with missing 'level' key.
    - Expected: Uses default INFO level.
    """

    config = {"format": "%(message)s"}

    # Clear any existing handlers before testing
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Should not raise exception with missing 'level' key
    configure_logging(config)

    # Verify basicConfig was called with default INFO level
    assert len(root_logger.handlers) > 0


# 2.3. Test configure_logging with invalid level
def test_configure_logging_invalid_level(caplog):
    """
    Test Case 2.3:
    - Setup: Logging configuration with invalid level name.
    - Expected: Falls back to INFO level (getattr default).
    """

    config = {"level": "INVALID_LEVEL", "format": "%(message)s"}

    # Clear any existing handlers before testing
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Should not raise exception with invalid level
    configure_logging(config)

    # Verify basicConfig was called
    assert len(root_logger.handlers) > 0


# 2.4. Test configure_logging with default format
def test_configure_logging_default_format(caplog):
    """
    Test Case 2.4:
    - Setup: Logging configuration with missing 'format' key.
    - Expected: Uses default format string.
    """

    config = {"level": "WARNING"}

    # Clear any existing handlers before testing
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Should not raise exception with missing 'format' key
    configure_logging(config)

    # Verify basicConfig was called
    assert len(root_logger.handlers) > 0


###########################################################################
# 3. Tests for parse_date function
###########################################################################


# 3.1. Valid date input: Test that a valid date string is correctly parsed.
@pytest.mark.parametrize(
    "input_date, expected",
    [
        ("15.03.2025", datetime.strptime("15.03.2025", DATE_FORMAT)),
    ],
)
def test_parse_date_valid(monkeypatch, input_date, expected):
    """
    Test Case 2.1:
    - Input: Valid date string.
    - Expected: Returns a valid datetime object.
    """
    monkeypatch.setattr("builtins.input", lambda prompt: input_date)
    result = parse_date("Enter date: ")
    assert result == expected


# 2.2. Invalid date input: Test that repeated invalid date inputs lead to a ValueError.
@pytest.mark.parametrize(
    "inputs",
    [
        (["invalid", "wrong", "bad"]),
    ],
)
def test_parse_date_invalid(monkeypatch, inputs):
    """
    Test Case 2.2:
    - Input: Three invalid date strings.
    - Expected: Raises a ValueError after maximum retries.
    """
    monkeypatch.setattr("builtins.input", lambda prompt: next(iter(inputs)))
    with pytest.raises(ValueError):
        parse_date("Enter date: ")


# 2.3. Test parse_date with retries=0: Ensure immediate ValueError.
def test_parse_date_retries_zero(monkeypatch):
    """
    Test Case 2.3:
    - Setup: Call parse_date with retries=0 and invalid input.
    - Expected: Raises ValueError immediately without retries.
    """
    monkeypatch.setattr("builtins.input", lambda prompt: "invalid")
    with pytest.raises(ValueError) as excinfo:
        parse_date("Enter date: ", retries=0)
    assert "Maximum retries reached" in str(excinfo.value)


###########################################################################
# 3. Tests for check_file_existence function
###########################################################################


# 3.1. Valid CSV file: Ensure a properly formatted CSV file is loaded correctly.
def test_check_file_existence_csv(mock_csv_file):
    """
    Test Case 3.1:
    - Setup: Create a temporary CSV file with a header and one data row.
    - Expected: Returns CSV data (excluding the header).
    """
    data = check_file_existence(str(mock_csv_file), "csv")
    assert len(data) == 1
    assert data[0] == ["15.03.2025", "09:00", "17:00"]


# 3.2. Non-existent CSV file: Ensure a missing CSV file raises FileNotFoundError.
def test_check_file_existence_csv_not_found(tmp_path):
    """
    Test Case 2.2:
    - Setup: Provide a non-existent CSV file path.
    - Expected: Raises FileNotFoundError.
    """
    non_existent = tmp_path / "nonexistent.csv"
    with pytest.raises(FileNotFoundError):
        check_file_existence(str(non_existent), "csv")


# 3.3. Valid Excel file: Ensure a valid Excel workbook is loaded correctly.
def test_check_file_existence_excel(mock_excel_file):
    """
    Test Case 2.3:
    - Setup: Create a temporary Excel file using openpyxl.
    - Expected: Returns an openpyxl.Workbook object.
    """
    wb_loaded = check_file_existence(str(mock_excel_file), "excel")
    assert isinstance(wb_loaded, openpyxl.Workbook)


# 3.4. Non-existent Excel file: Ensure a missing Excel file raises FileNotFoundError.
def test_check_file_existence_excel_not_found(tmp_path):
    """
    Test Case 2.4:
    - Setup: Provide a non-existent Excel file path.
    - Expected: Raises FileNotFoundError.
    """
    non_existent = tmp_path / "nonexistent.xlsx"
    with pytest.raises(FileNotFoundError):
        check_file_existence(str(non_existent), "excel")


# 3.5. Permission denied on CSV file: Ensure PermissionError is raised
# for inaccessible CSV.
def test_check_file_existence_csv_permission_denied(tmp_path, monkeypatch):
    """
    Test Case 2.5:
    - Setup: Create a CSV file and mock the open function to raise PermissionError.
    - Expected: Raises PermissionError.
    """
    csv_file = tmp_path / "timelog.csv"
    csv_file.write_text("Date,Start,End\n15.03.2025,09:00,17:00\n")

    def mock_open_permission_error(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open_permission_error)
    with pytest.raises(PermissionError):
        check_file_existence(str(csv_file), "csv")


# 3.6. Permission denied on Excel file: Ensure PermissionError is raised
# for inaccessible Excel.
def test_check_file_existence_excel_permission_denied(tmp_path, monkeypatch):
    """
    Test Case 2.6:
    - Setup: Create an Excel file and mock openpyxl.load_workbook
      to raise PermissionError.
    - Expected: Raises PermissionError.
    """
    excel_file = tmp_path / "timesheet.xlsx"
    wb = create_dummy_workbook()
    wb.save(str(excel_file))

    def mock_load_workbook_permission_error(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("openpyxl.load_workbook", mock_load_workbook_permission_error)
    with pytest.raises(PermissionError):
        check_file_existence(str(excel_file), "excel")


# 3.7. Excel lock: Simulate file lock when opening in 'r+b' and ensure warnings are logged and workbook loads.
def test_check_file_existence_excel_locked_logs(tmp_path, monkeypatch, caplog):
    """
    Test Case 3.7:
    - Setup: Create a temporary Excel file and simulate a PermissionError when opening in 'r+b'.
    - Expected: Warning logs about lock and workbook is still returned.
    """
    excel_file = tmp_path / "timesheet.xlsx"
    wb = create_dummy_workbook()
    wb.save(str(excel_file))

    orig_open = open

    def fake_open(path, mode="r", *args, **kwargs):
        if mode == "r+b":
            raise PermissionError("file locked")
        return orig_open(path, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr("openpyxl.load_workbook", lambda *a, **k: wb)

    with caplog.at_level(logging.WARNING):
        result = check_file_existence(str(excel_file), "excel")
        assert isinstance(result, openpyxl.Workbook)
        assert "Excel file may be locked/opened by another process" in caplog.text
        assert "Lock error" in caplog.text


# 3.8. CSV PermissionError routed via module-level open: ensure PermissionError except block is executed
def test_check_file_existence_csv_permission_denied_module_patch(
    tmp_path, monkeypatch, caplog
):
    csv_file = tmp_path / "timelog.csv"
    csv_file.write_text("Date,Start,End\n15.03.2025,09:00,17:00\n")

    def raise_perm(*args, **kwargs):
        raise PermissionError("Permission denied from module open")

    # Patch the built-in open used by the module to ensure the except PermissionError branch is exercised
    monkeypatch.setattr("builtins.open", raise_perm)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(PermissionError):
            check_file_existence(str(csv_file), "csv")
        assert "Permission denied accessing file" in caplog.text
        assert "Error details" in caplog.text


# 3.9. Excel PermissionError via module load_workbook patch: ensure logging and re-raise
def test_check_file_existence_excel_permission_denied_module_patch(
    tmp_path, monkeypatch, caplog
):
    excel_file = tmp_path / "timesheet.xlsx"
    wb = create_dummy_workbook()
    wb.save(str(excel_file))

    def raise_perm(*args, **kwargs):
        raise PermissionError("Permission denied from load_workbook")

    monkeypatch.setattr(
        "src_timesheetalgo.TimeSheetAlgo.openpyxl.load_workbook", raise_perm
    )

    with caplog.at_level(logging.ERROR):
        with pytest.raises(PermissionError):
            check_file_existence(str(excel_file), "excel")
        assert "Permission denied accessing file" in caplog.text
        assert "Error details" in caplog.text


###########################################################################
# 4. Tests for TimeSheetProcessor class methods
###########################################################################


# 4.1. Test load_files(): Check that CSV and Excel files are loaded properly.
def test_load_files(mock_processor):
    """
    Test Case 3.1:
    - Setup: Use mock_processor fixture.
    - Expected: timelog and timesheet are loaded correctly.
    """
    assert len(mock_processor.timelog) == 1
    assert isinstance(mock_processor.timesheet, openpyxl.Workbook)


# 4.2. Test request_date_input() with valid inputs.
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


# 4.3. Test request_date_input() with invalid inputs triggering fallback and
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


# 4.4. Test request_date_input() with invalid inputs triggering fallback
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
        {"timelog_path": "dummy.csv", "timesheet_path": "dummy.xlsx", "year": 2025}
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


# 4.8. Test store_data() with overwrite: When target cell has data and user confirms.
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


# 4.9. _get_date exception fallback: parse_date raises and fallback is used.
def test__get_date_exception_fallback(monkeypatch, caplog, mock_processor):
    """
    Test Case 4.9:
    - Setup: Monkeypatch parse_date to raise Exception.
    - Expected: Warning logged and fallback value returned.
    """

    def raise_exc(prompt):
        raise Exception("parse failed")

    monkeypatch.setattr("src_timesheetalgo.TimeSheetAlgo.parse_date", raise_exc)

    called = {"fallback": False}

    def fallback():
        called["fallback"] = True
        return datetime(2025, 1, 2)

    with caplog.at_level(logging.WARNING):
        result = mock_processor._get_date("prompt", fallback)
        assert called["fallback"] is True
        assert result == datetime(2025, 1, 2)
        assert "Error parsing date" in caplog.text


###########################################################################
# 5. Tests for confirm_overwrite method
###########################################################################


# 5.1. Test confirm_overwrite() returns True when input is "y".
@pytest.mark.parametrize(
    "user_input, expected",
    [
        (" y ", True),
        ("n", False),
    ],
)
def test_confirm_overwrite(monkeypatch, user_input, expected):
    """
    Test Case 5.1 & 5.2:
    - Input: User input for overwrite confirmation.
    - Expected: Returns True for "y" and False for "n".
    """
    processor = TimeSheetProcessor(
        {"timelog_path": "dummy.csv", "timesheet_path": "dummy.xlsx", "year": 2025}
    )
    monkeypatch.setattr("builtins.input", lambda prompt: user_input)
    result = processor.confirm_overwrite()
    assert result == expected


# 6.1. Test save_timesheet(): Verify that the workbook's save() method is called.
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
            "year": 2025,
        }
    )
    processor.timesheet = wb
    processor.save_timesheet()
    assert save_called is True


# 5.3. Test check_file_existence with locked Excel file: Ensure warnings are logged.
def test_check_file_existence_excel_lock_logs(tmp_path, monkeypatch, caplog):
    """
    Test Case 5.3:
    - Setup: Simulate a locked Excel file by raising PermissionError in "r+b" mode.
    - Expected: Logs warnings and still returns the loaded workbook.
    """
    excel_file = tmp_path / "timesheet.xlsx"
    wb = create_dummy_workbook()
    wb.save(str(excel_file))

    orig_open = open

    def fake_open(filepath, mode="r", *args, **kwargs):
        # Only raise for the write-check open mode used in check_file_existence
        if mode == "r+b":
            raise PermissionError("File is locked")
        return orig_open(filepath, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)

    with caplog.at_level(logging.WARNING):
        wb_loaded = check_file_existence(str(excel_file), "excel")
        assert isinstance(wb_loaded, openpyxl.Workbook)
        assert "Excel file may be locked" in caplog.text
        assert "Lock error" in caplog.text
        assert "Please close the Excel file" in caplog.text


###########################################################################
# 6. Additional tests for improved coverage
###########################################################################


# 6.1. Test _prompt_overwrite_decision with skip option
def test_prompt_overwrite_decision_skip(monkeypatch, mock_processor):
    """
    Test Case 6.1:
    - Setup: _prompt_overwrite_decision called with 'skip' input.
    - Expected: Returns 'skip_all'.
    """
    monkeypatch.setattr("builtins.input", lambda prompt: "s")
    result = mock_processor._prompt_overwrite_decision(2)
    assert result == "skip_all"


# 6.2. Test _prompt_overwrite_decision with abort option
def test_prompt_overwrite_decision_abort(monkeypatch, mock_processor):
    """
    Test Case 6.2:
    - Setup: _prompt_overwrite_decision called with 'abort' input.
    - Expected: Returns 'abort'.
    """
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    result = mock_processor._prompt_overwrite_decision(2)
    assert result == "abort"


# 6.3. Test _prompt_overwrite_decision with empty input (default)
def test_prompt_overwrite_decision_empty(monkeypatch, mock_processor):
    """
    Test Case 6.3:
    - Setup: _prompt_overwrite_decision called with empty input.
    - Expected: Returns 'overwrite_all' (default).
    """
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    result = mock_processor._prompt_overwrite_decision(2)
    assert result == "overwrite_all"


# 6.4. Test _prompt_overwrite_decision with EOFError
def test_prompt_overwrite_decision_eoferror(monkeypatch, mock_processor, caplog):
    """
    Test Case 6.4:
    - Setup: _prompt_overwrite_decision called with EOFError.
    - Expected: Returns 'overwrite_all' and logs info.
    """
    monkeypatch.setattr(
        "builtins.input", lambda prompt: (_ for _ in ()).throw(EOFError())
    )
    with caplog.at_level(logging.INFO):
        result = mock_processor._prompt_overwrite_decision(2)
        assert result == "overwrite_all"
        assert "No input provided" in caplog.text


# 6.5. Test _check_and_confirm_overwrite with no conflicts
def test_check_and_confirm_overwrite_no_conflicts(monkeypatch, mock_processor):
    """
    Test Case 6.5:
    - Setup: _check_and_confirm_overwrite with no overlapping data.
    - Expected: Returns 'overwrite_all' without prompting.
    """
    mock_processor.timedata = [["15.03.2025", "09:00", "17:00"]]
    # Initialize timesheet without data in that cell
    result = mock_processor._check_and_confirm_overwrite()
    assert result == "overwrite_all"


# 6.6. Test _check_and_confirm_overwrite with conflicts and user confirms
def test_check_and_confirm_overwrite_with_conflicts(
    monkeypatch, mock_processor, caplog
):
    """
    Test Case 6.6:
    - Setup: _check_and_confirm_overwrite with overlapping data.
    - Expected: Prompts user and returns their choice.
    """
    mock_processor.timedata = [["05.01.2025", "09:00", "17:00"]]
    # Add existing data at the target cell
    sheet = mock_processor.timesheet.worksheets[0]
    row = ROW_OFFSET + 5
    sheet.cell(row=row, column=5, value="08:00")

    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    with caplog.at_level(logging.INFO):
        result = mock_processor._check_and_confirm_overwrite()
        assert result == "overwrite_all"
        assert "Found 1 day(s) with existing data" in caplog.text


# 6.7. Test store_data() with skip decision
def test_store_data_with_skip(monkeypatch, mock_processor, caplog):
    """
    Test Case 6.7:
    - Setup: store_data with conflicting data and skip decision.
    - Expected: Existing data is preserved.
    """
    mock_processor.timedata = [["05.01.2025", "09:00", "17:00"]]
    sheet = mock_processor.timesheet.worksheets[0]
    row = ROW_OFFSET + 5
    original_value = "08:00"
    sheet.cell(row=row, column=5, value=original_value)

    monkeypatch.setattr("builtins.input", lambda prompt: "s")
    with caplog.at_level(logging.INFO):
        mock_processor.store_data()
        assert sheet.cell(row=row, column=5).value == original_value
        assert "Skipping existing data" in caplog.text


# 6.8. Test store_data() with abort decision
def test_store_data_with_abort(monkeypatch, mock_processor, caplog):
    """
    Test Case 6.8:
    - Setup: store_data with conflicting data and abort decision.
    - Expected: Operation is aborted and data is preserved.
    """
    mock_processor.timedata = [["05.01.2025", "09:00", "17:00"]]
    sheet = mock_processor.timesheet.worksheets[0]
    row = ROW_OFFSET + 5
    original_value = "08:00"
    sheet.cell(row=row, column=5, value=original_value)

    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    with caplog.at_level(logging.INFO):
        mock_processor.store_data()
        assert sheet.cell(row=row, column=5).value == original_value
        assert "Aborting due to user request" in caplog.text


# 6.9. Test select_timelog_data with empty result triggers error
def test_select_timelog_data_empty_result(mock_processor):
    """
    Test Case 6.9:
    - Setup: No timelog entries in date range.
    - Expected: Raises ValueError with appropriate message.
    """
    mock_processor.timelog = [["10.03.2025", "08:00", "16:00"]]
    mock_processor.obj_date_startpoint = datetime.strptime("15.03.2025", DATE_FORMAT)
    mock_processor.obj_date_endpoint = datetime.strptime("20.03.2025", DATE_FORMAT)

    with pytest.raises(ValueError, match="No data found"):
        mock_processor.select_timelog_data()


# 6.10. Test confirm_overwrite with various inputs
@pytest.mark.parametrize(
    "user_input, expected",
    [
        ("yes", True),
        ("YES", True),
        ("y", True),
        ("no", False),
        ("NO", False),
        ("n", False),
        ("", False),
        ("invalid", False),
    ],
)
def test_confirm_overwrite_parametrized(monkeypatch, user_input, expected):
    """
    Test Case 6.10:
    - Setup: Various user inputs for confirm_overwrite.
    - Expected: Correct boolean return values.
    """
    processor = TimeSheetProcessor(
        {"timelog_path": "dummy.csv", "timesheet_path": "dummy.xlsx", "year": 2025}
    )
    monkeypatch.setattr("builtins.input", lambda prompt: user_input)
    result = processor.confirm_overwrite()
    assert result == expected


# 6.11. Test _get_date with successful parse
def test_get_date_success(monkeypatch, mock_processor):
    """
    Test Case 6.11:
    - Setup: Valid date input.
    - Expected: Returns parsed datetime.
    """
    monkeypatch.setattr("builtins.input", lambda prompt: "15.03.2025")
    result = mock_processor._get_date("Enter date: ", lambda: datetime(2025, 1, 1))
    assert result == datetime(2025, 3, 15)


# 6.12. Test set_default_start_date with specific date in sheet
def test_set_default_start_date_with_data(mock_processor):
    """
    Test Case 6.12:
    - Setup: Timesheet contains time data in specific position.
    - Expected: Returns the correct date based on sheet data.
    """
    # Add time data to June (index 5) at day 15
    mock_processor.timesheet.worksheets[5].cell(
        row=ROW_OFFSET + 15, column=5, value="09:00"
    )
    result = mock_processor.set_default_start_date()
    assert result.month == 6
    assert result.day == 15


# 6.13. Test parse_date with mixed valid/invalid inputs
def test_parse_date_with_retry(monkeypatch):
    """
    Test Case 6.13:
    - Setup: Invalid then valid date input.
    - Expected: Returns parsed datetime on retry.
    """
    inputs = iter(["invalid", "valid", "15.03.2025"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    result = parse_date("Enter date: ", retries=3)
    assert result == datetime(2025, 3, 15)


# 6.14. Test load_config with default environment detection
def test_load_config_default_environment(tmp_path, monkeypatch):
    """
    Test Case 6.14:
    - Setup: Config with default_environment fallback.
    - Expected: Uses detected environment.
    """
    config_file = tmp_path / "config.yaml"
    config_content = {
        "year": 2025,
        "environments": {
            "development": {
                "file_paths": {
                    "timelog_path": "dev_timelog.csv",
                    "timesheet_path": "dev_timesheet.xlsx",
                }
            }
        },
        "default_environment": "development",
    }
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)

    monkeypatch.setattr("src_timesheetalgo.TimeSheetAlgo.detect_environment", lambda x: "development")
    config = load_config(str(config_file))
    assert config["environment"] == "development"
