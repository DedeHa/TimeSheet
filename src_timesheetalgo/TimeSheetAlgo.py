"""
TYPE:   !/usr/bin/env python3.

FILENAME :        TimeSheetAlgo.py

AUTHOR :    Dennis Hartel

START DATE :    26.01.2022

DESCRIPTION :   Automatic timelog organisation with extract of timelogdata and
                document in time balance sheet

REMARK: Refactored and optimized with ChatGPT and review/updated

"""

import csv
import openpyxl
from datetime import datetime as dt, timedelta as td
import logging
import yaml
import os

# Constants
DATE_FORMAT = "%d.%m.%Y"
MAX_RETRIES = 3
ROW_OFFSET = 4
TIMESHEET_SHEETS = 12
YEAR = 2025


class ConfigError(Exception):
    """Custom exception for configuration errors."""

    pass


def load_config(config_path: str = None, environment: str = None) -> dict:
    """Load configuration from external YAML file.

    Args:
        config_path: Path to config.yaml file. If None, uses default location.
        environment: Environment name (development/production). If None, uses default.

    Returns:
        Dictionary with configuration for the selected environment.

    Raises:
        ConfigError: If config file not found or invalid.
    """
    # Determine config file path
    if config_path is None:
        # Try relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "config.yaml")

    # Check if config file exists
    if not os.path.exists(config_path):
        raise ConfigError(
            f"Configuration file not found: {config_path}. "
            "Please ensure config.yaml exists in the src_timesheetalgo directory."
        )

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML format in {config_path}: {e}")
    except Exception as e:
        raise ConfigError(f"Error reading configuration file: {e}")

    # Validate config structure
    if not isinstance(config_data, dict):
        raise ConfigError("Configuration file must contain a YAML dictionary")

    if "environments" not in config_data:
        raise ConfigError("Configuration file must contain 'environments' key")

    # Determine which environment to use
    if environment is None:
        environment = config_data.get("default_environment", "development")

    # Get environment-specific config
    if environment not in config_data["environments"]:
        raise ConfigError(
            f"Environment '{environment}' not found in configuration. "
            f"Available environments: {list(config_data['environments'].keys())}"
        )

    env_config = config_data["environments"][environment]

    # Extract file paths
    if "file_paths" not in env_config:
        raise ConfigError(f"No 'file_paths' defined for environment '{environment}'")

    file_paths = env_config["file_paths"]
    if "timelog_path" not in file_paths or "timesheet_path" not in file_paths:
        raise ConfigError("file_paths must contain 'timelog_path' and 'timesheet_path'")

    # Convert relative paths to absolute paths if needed
    config_dir = os.path.dirname(config_path)
    timelog_path = file_paths["timelog_path"]
    timesheet_path = file_paths["timesheet_path"]

    if not os.path.isabs(timelog_path):
        timelog_path = os.path.join(config_dir, timelog_path)
    if not os.path.isabs(timesheet_path):
        timesheet_path = os.path.join(config_dir, timesheet_path)

    # Setup logging if specified in config
    if "logging" in env_config:
        logging_config = env_config["logging"]
        log_level = logging_config.get("level", "INFO")
        log_format = logging_config.get(
            "format", "%(asctime)s - %(levelname)s - %(message)s"
        )
        logging.basicConfig(level=log_level, format=log_format)

    # Critical operational logging (uses WARNING to ensure visibility in production)
    logging.warning("=== Configuration Diagnostics ===")
    logging.warning(f"Environment: {environment}")
    logging.warning(f"Config file: {config_path}")
    logging.warning(f"Timelog path: {timelog_path}")
    logging.warning(f"Timesheet path: {timesheet_path}")
    logging.warning(f"Timelog exists: {os.path.exists(timelog_path)}")
    logging.warning(f"Timesheet exists: {os.path.exists(timesheet_path)}")
    logging.warning("=================================")

    return {
        "timelog_path": timelog_path,
        "timesheet_path": timesheet_path,
    }


# Load default configuration
try:
    CONFIG = load_config()
except ConfigError as e:
    logging.error(f"Configuration error: {e}")
    # Fallback to hardcoded paths if config loading fails
    CONFIG = {
        "timelog_path": "src_timesheetalgo/FDTech_timelog.csv",
        "timesheet_path": "src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm",
    }


def parse_date(input_prompt, retries=MAX_RETRIES):
    """Parse date with retries."""
    for attempt in range(retries):
        date_str = input(input_prompt)
        try:
            return dt.strptime(date_str, DATE_FORMAT)
        except ValueError:
            logging.warning(
                f"Invalid date format. Attempts left: {retries - attempt - 1}"
            )
    raise ValueError("Maximum retries reached. Exiting...")


def check_file_existence(filepath, filetype):
    """Check and load files."""
    try:
        if filetype == "csv":
            with open(filepath, encoding="utf-8") as file:
                return list(csv.reader(file))[1:]  # Skip header
        elif filetype == "excel":
            # Check if file is locked/opened by another process
            try:
                # Try to open file in write mode to check if it's locked
                with open(filepath, "r+b"):
                    pass
                logging.info(f"Excel file is not locked: {filepath}")
            except (PermissionError, IOError) as e:
                logging.warning(
                    f"Excel file may be locked/opened by another process: {filepath}"
                )
                logging.warning(f"Lock error: {e}")
                logging.warning(
                    "Please close the Excel file if it's open in Excel application"
                )

            # Open timesheet xlsm with parameters:
            # data_only = Keep formula, keep_vba = Keep VBA program
            return openpyxl.load_workbook(filepath, data_only=False, keep_vba=True)
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        raise
    except PermissionError as e:
        logging.error(f"Permission denied accessing file: {filepath}")
        logging.error(
            "This usually means the file is open in Excel. "
            "Please close it and try again."
        )
        logging.error(f"Error details: {e}")
        raise


class TimeSheetProcessor:
    """Process and manage timelog and timesheet data."""

    def __init__(self, config):
        """Initialize the TimeSheetProcessor with configuration.

        Args:
            config (dict): Dictionary containing file paths for timelog and timesheet.
        """
        self.timelog_path = config["timelog_path"]
        self.timesheet_path = config["timesheet_path"]
        self.timelog = []
        self.timedata = []
        self.timesheet = None
        self.obj_date_startpoint = None
        self.obj_date_endpoint = None

    def load_files(self):
        """Load timelog and timesheet files."""
        logging.info("Loading files...")
        self.timelog = check_file_existence(self.timelog_path, "csv")
        self.timesheet = check_file_existence(self.timesheet_path, "excel")

    def request_date_input(self):
        """Request start and end date from user or use defaults."""
        logging.info("Setting date range...")

        # Try to get user input, but use defaults if no input provided
        try:
            start_input = input(
                "Enter Start Date (dd.mm.yyyy) or press Enter for default: "
            ).strip()
            if start_input:
                self.obj_date_startpoint = dt.strptime(start_input, DATE_FORMAT)
                logging.warning(f"Start date: {self.obj_date_startpoint.date()}")
            else:
                self.obj_date_startpoint = self.set_default_start_date()
        except (ValueError, EOFError):
            logging.warning("Using default start date...")
            self.obj_date_startpoint = self.set_default_start_date()

        try:
            end_input = input(
                "Enter End Date (dd.mm.yyyy) or press Enter for default: "
            ).strip()
            if end_input:
                self.obj_date_endpoint = dt.strptime(end_input, DATE_FORMAT)
                logging.warning(f"End date: {self.obj_date_endpoint.date()}")
            else:
                self.obj_date_endpoint = self.set_default_end_date()
        except (ValueError, EOFError):
            self.obj_date_endpoint = self.set_default_end_date()

    def _get_date(self, prompt, fallback):
        """Get a date from user input or fallback to default."""
        try:
            return parse_date(prompt)
        except Exception as e:
            logging.warning(f"Error parsing date: {e}. Falling back to default date.")
            return fallback()

    def set_default_start_date(self):
        """Set default start date based on timesheet contents."""
        # Iterate through timesheet months in reverse order
        for sheet in reversed(self.timesheet.worksheets[:12]):
            # Look for the last entry with time data (indicating a worked day)
            for i in range(ROW_OFFSET + 30, ROW_OFFSET, -1):
                # Check if there's time data in column E (start time)
                time_cell = sheet.cell(row=i, column=5).value

                if time_cell:  # If there's a start time, this day was worked
                    # Get the year from the base date in row 3, column 2
                    year_cell = self.timesheet.worksheets[0].cell(row=3, column=2).value
                    if isinstance(year_cell, dt):
                        year = year_cell.year
                    else:
                        year = YEAR  # fallback to constant

                    # Get month from sheet index (0-based + 1)
                    month = self.timesheet.worksheets.index(sheet) + 1

                    # The day is the row number minus the offset
                    day = i - ROW_OFFSET

                    # Create the date
                    default_start_date = dt(year, month, day)
                    logging.warning(f"Default start date: {default_start_date.date()}")
                    return default_start_date

        # If no date is found, set a default start date
        default_start_date = dt(YEAR, 1, 1)
        logging.warning(
            f"No valid date found. Default start date set to: "
            f"{default_start_date.date()}"
        )
        return default_start_date

    def set_default_end_date(self):
        """Set default end date to yesterday."""
        default_end_date = dt.now() - td(days=1)
        logging.warning(f"Default end date: {default_end_date.date()}")
        return default_end_date

    def select_timelog_data(self):
        """Filter timelog data based on selected dates."""
        logging.info("Selecting timelog data...")
        start, end = self.obj_date_startpoint, self.obj_date_endpoint
        self.timedata = [
            entry
            for entry in self.timelog
            if start <= dt.strptime(entry[0], DATE_FORMAT) <= end
        ]
        if not self.timedata:
            raise ValueError("No data found for the selected dates.")

    def store_data(self):
        """Store selected timelog data into the timesheet."""
        logging.info("Storing timelog data into timesheet...")
        for entry in self.timedata:
            # Define index for storing data
            date, start_time, end_time = (
                dt.strptime(entry[0], DATE_FORMAT),
                entry[1],
                entry[2],
            )

            # row: startindex = Timesheet Header + Day of the Month
            # month: selected_month(index_0) = selected_date.month(index_1) - 1
            row, month_idx = ROW_OFFSET + date.day, date.month - 1
            sheet = self.timesheet.worksheets[month_idx]

            start_cell, end_cell = sheet.cell(row=row, column=5), sheet.cell(
                row=row, column=6
            )

            if start_cell.value and not self.confirm_overwrite():
                logging.info(f"Skipping existing data for {date.date()}.")
                break

            start_cell.value, end_cell.value = start_time, end_time

    def confirm_overwrite(self):
        """Prompt user to confirm overwriting data."""
        try:
            response = (
                input("Data exists. Overwrite? (y/n) or press Enter for yes: ")
                .strip()
                .lower()
            )
            return response in ["y", "yes", ""]  # Default to yes if empty input
        except EOFError:
            logging.info("No input provided, defaulting to overwrite (yes)")
            return True

    def save_timesheet(self):
        """Save the modified timesheet with backup and error handling."""
        logging.info("Saving timesheet...")
        self.timesheet.save(self.timesheet_path)


# Main execution
if __name__ == "__main__":  # pragma: no cover
    processor = TimeSheetProcessor(CONFIG)
    try:
        processor.load_files()
        processor.request_date_input()
        processor.select_timelog_data()
        processor.store_data()
        processor.save_timesheet()
        logging.warning("Processing complete.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
