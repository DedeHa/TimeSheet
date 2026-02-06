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
import logging
import os
from datetime import datetime as dt
from datetime import timedelta as td
from typing import Optional

import openpyxl
import yaml

# Constants
DATE_FORMAT = "%d.%m.%Y"
MAX_RETRIES = 3
ROW_OFFSET = 4
TIMESHEET_SHEETS = 12


# ---------------------------------------------------------------------------
# Configuration & logging
# ---------------------------------------------------------------------------


class ConfigError(Exception):
    """Raised when configuration loading fails."""


def detect_environment(base_path: str) -> str:
    """
    Detect environment based on folder structure.

    - If current folder is 'src_timesheetalgo', use 'development'.
    - If 'Timealarm' folder exists in current folder, use 'production'.
    """
    if os.path.basename(base_path) == "src_timesheetalgo":
        return "development"
    elif os.path.isdir(os.path.join(base_path, "Timealarm")):
        return "production"
    else:
        # fallback
        return "development"


def load_config(config_path: Optional[str] = None) -> dict:
    """
    Load config.yaml and return paths + logging settings + year.
    Environment is auto-detected based on folder structure.
    Year is a required configuration item at the root level.
    """
    config_path = config_path or os.path.join(os.path.dirname(__file__), "config.yaml")
    config = _read_yaml(config_path)
    base_dir = os.path.dirname(config_path)

    # Year is required at root level - no fallback
    if "year" not in config:
        raise ConfigError(
            "Missing required 'year' configuration at root level in config.yaml. "
            "Please add 'year' to the root of config.yaml."
        )

    # Auto-detect environment
    env_name = detect_environment(base_dir)

    if env_name not in config["environments"]:
        raise ConfigError(f"Environment '{env_name}' not found in config.yaml")

    env_config = config["environments"][env_name]

    return {
        "environment": env_name,
        "timelog_path": os.path.join(
            base_dir, env_config["file_paths"]["timelog_path"]
        ),
        "timesheet_path": os.path.join(
            base_dir, env_config["file_paths"]["timesheet_path"]
        ),
        "logging": env_config.get("logging", {}),
        "year": config["year"],
    }


def _read_yaml(path: str) -> dict:
    if not os.path.exists(path):
        raise ConfigError(f"Config file not found: {path}")

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError("Invalid YAML format") from e
    except OSError as e:
        raise ConfigError("Unable to read config file") from e

    if not isinstance(data, dict):
        raise ConfigError("Config root must be a mapping")

    return data


def configure_logging(logging_cfg: dict) -> None:
    level_name = logging_cfg.get("level", "INFO").upper()
    log_format = logging_cfg.get("format", "%(asctime)s - %(levelname)s - %(message)s")

    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(level=level, format=log_format)


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
            config (dict): Dictionary containing file paths, year, and logging settings.
        """
        self.timelog_path = config["timelog_path"]
        self.timesheet_path = config["timesheet_path"]
        self.year = config["year"]
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
                logging.info(f"Start date: {self.obj_date_startpoint.date()}")
            else:
                self.obj_date_startpoint = self.set_default_start_date()
        except (ValueError, EOFError):
            logging.info("Using default start date...")
            self.obj_date_startpoint = self.set_default_start_date()

        try:
            end_input = input(
                "Enter End Date (dd.mm.yyyy) or press Enter for default: "
            ).strip()
            if end_input:
                self.obj_date_endpoint = dt.strptime(end_input, DATE_FORMAT)
                logging.info(f"End date: {self.obj_date_endpoint.date()}")
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
                    # Use the configured year from config
                    year = self.year

                    # Get month from sheet index (0-based + 1)
                    month = self.timesheet.worksheets.index(sheet) + 1

                    # The day is the row number minus the offset
                    day = i - ROW_OFFSET

                    # Create the date
                    default_start_date = dt(year, month, day)
                    logging.info(f"Default start date: {default_start_date.date()}")
                    return default_start_date

        # If no date is found, set a default start date
        default_start_date = dt(self.year, 1, 1)
        logging.warning(
            f"No valid date found. Default start date set to: "
            f"{default_start_date.date()}"
        )
        return default_start_date

    def set_default_end_date(self):
        """Set default end date to yesterday."""
        default_end_date = dt.now() - td(days=1)
        logging.info(f"Default end date: {default_end_date.date()}")
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


if __name__ == "__main__":  # pragma: no cover
    try:
        CONFIG = load_config()
    except ConfigError as e:
        logging.basicConfig(level=logging.ERROR)
        logging.error("Configuration error: %s", e)
        raise SystemExit(1) from None

    configure_logging(CONFIG["logging"])

    logging.info("CWD: %s", os.getcwd())

    logging.info("Environment: %s", CONFIG["environment"])
    logging.info("Timelog path: %s", CONFIG["timelog_path"])
    logging.info("Timesheet path: %s", CONFIG["timesheet_path"])
    logging.info("Work year: %d", CONFIG["year"])

    processor = TimeSheetProcessor(CONFIG)

    try:
        processor.load_files()
        processor.request_date_input()
        processor.select_timelog_data()
        processor.store_data()
        processor.save_timesheet()
        logging.info("Processing complete.")
    except Exception as e:
        logging.error("An error occurred: %s", e)
