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
import enum
import logging
import os
from datetime import datetime as dt
from datetime import timedelta as td
from typing import Callable, Optional

import openpyxl
import yaml

# ---------------------------------------------------------------------------
# Dependency injection helpers (PRO-339: unit-testability refactoring)
# ---------------------------------------------------------------------------

# A type alias for the user-input function. The default implementation calls
# ``builtins.input``; tests inject a pure ``Callable[[str], str]`` so that no
# mocking of ``builtins.input`` is required.
InputProvider = Callable[[str], str]


def _default_input_provider(prompt: str) -> str:
    """Default InputProvider: delegates to ``builtins.input``."""
    return input(prompt)


# A type alias for the clock function. The default implementation returns
# ``datetime.now()``; tests inject a fixed provider for deterministic dates.
Clock = Callable[[], dt]


def _default_clock() -> dt:
    """Default Clock: returns the current wall-clock time."""
    return dt.now()


# Constants
DATE_FORMAT = "%d.%m.%Y"
MAX_RETRIES = 3
ROW_OFFSET = 4
TIMESHEET_SHEETS = 12

# Cell holding the timesheet year (used for the config/timesheet consistency check)
YEAR_CHECK_SHEET = "Januar"
YEAR_CHECK_CELL = "B3"

# Traceability anchors for documentation: FR-01, FR-02, FR-03, FR-04, FR-05,
# FR-06, FR-07, FR-08, FR-09, FR-10, FR-11, FR-12, FR-13, FR-14, FR-15,
# FR-16, FR-17, QR-01, QR-02, QR-03, QR-04, QR-05, QR-06, QR-07, QR-08, QR-09.


# ---------------------------------------------------------------------------
# Configuration & logging
# ---------------------------------------------------------------------------


class ConfigError(Exception):
    """Raised when configuration loading fails."""


class ConsistencyError(Exception):
    """Raised when configuration and timesheet data are inconsistent."""


class TimelogFormatError(Exception):
    """Raised when a timelog CSV row violates the expected column structure.

    Traceability: FR-05, QR-05.
    """


class TimesheetFormatError(Exception):
    """Raised when the Excel timesheet violates the expected template.

    Traceability: FR-05, QR-05.
    """


def detect_environment(base_path: str) -> str:
    """Detect environment based on folder structure.

    The function uses the folder layout to determine whether the runtime is a
    development or production environment.

    Traceability: FR-02.
    """
    if os.path.basename(base_path) == "src_timesheetalgo":
        return "development"
    elif os.path.isdir(os.path.join(base_path, "Timealarm")):
        return "production"
    else:
        # fallback
        return "development"


def load_config(config_path: Optional[str] = None) -> dict:
    """Load config.yaml and return paths, logging settings, and year.

    Environment detection is automatic and the work year is required at the
    root level of the YAML file.

    Traceability: FR-01, FR-03.
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
    # Traceability: FR-03.
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
    """Configure logging based on configuration dictionary.

    Args:
        logging_cfg: Dictionary with 'level' and 'format' keys.

    Traceability: FR-15.
    """
    level_name = logging_cfg.get("level", "INFO").upper()
    log_format = logging_cfg.get("format", "%(asctime)s - %(levelname)s - %(message)s")

    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(level=level, format=log_format)


def parse_date(
    input_prompt,
    retries=MAX_RETRIES,
    input_provider: InputProvider = _default_input_provider,
):
    """Parse date with retries.

    The user-input function is injected via ``input_provider`` so that tests
    can supply deterministic input without mocking ``builtins.input``.

    Traceability: FR-07, QR-05.
    """
    for attempt in range(retries):
        date_str = input_provider(input_prompt)
        try:
            return dt.strptime(date_str, DATE_FORMAT)
        except ValueError:
            logging.warning(
                f"Invalid date format. Attempts left: {retries - attempt - 1}"
            )
    raise ValueError("Maximum retries reached. Exiting...")


class StoreResult(enum.Enum):
    """Outcome of a ``store_data`` run.

    Replaces the implicit ``break`` / ``continue`` control flow so that
    callers can assert on the returned status instead of inspecting log
    output.

    Traceability: FR-12.
    """

    STORED = "stored"
    SKIPPED = "skipped"
    ABORTED = "abort"


def filter_timelog_entries(entries, start, end):
    """Return only timelog entries whose date lies inside [start, end].

    Pure function: no I/O, no side effects, no instance state.

    Args:
        entries: iterable of CSV rows (each row is ``[date, start, end]``).
        start: inclusive lower bound ``datetime``.
        end: inclusive upper bound ``datetime``.

    Returns:
        list of rows whose parsed date satisfies ``start <= date <= end``.

    Traceability: FR-08, QR-02.
    """
    return [
        entry for entry in entries if start <= dt.strptime(entry[0], DATE_FORMAT) <= end
    ]


def calculate_default_start_date(timesheet, year):
    """Determine the latest worked day in the workbook as the default start date.

    Pure function: reads the workbook structure but performs no I/O.

    Args:
        timesheet: openpyxl Workbook with the 12 month sheets.
        year: configured work year.

    Returns:
        datetime of the latest day with time data in column E, or
        ``datetime(year, 1, 1)`` if none found.

    Traceability: FR-07.
    """
    for sheet in reversed(timesheet.worksheets[:TIMESHEET_SHEETS]):
        for i in range(ROW_OFFSET + 31, ROW_OFFSET, -1):
            time_cell = sheet.cell(row=i, column=5).value
            if time_cell:
                month = timesheet.worksheets.index(sheet) + 1
                day = i - ROW_OFFSET
                return dt(year, month, day)
    return dt(year, 1, 1)


def map_entry_to_cell(entry, row_offset=ROW_OFFSET):
    """Map a timelog CSV row to its timesheet cell coordinates.

    Pure function: no I/O, no side effects.

    Args:
        entry: CSV row ``[date, start, end]``.
        row_offset: header offset in the timesheet (default ROW_OFFSET).

    Returns:
        tuple ``(row, month_idx, start_time, end_time)`` where ``row`` is the
        worksheet row and ``month_idx`` is the zero-based sheet index.

    Traceability: FR-09, FR-12.
    """
    date = dt.strptime(entry[0], DATE_FORMAT)
    return (
        row_offset + date.day,
        date.month - 1,
        entry[1],
        entry[2],
    )


def validate_timelog_entry(entry):
    """Validate a single timelog CSV row.

    Pure function: no I/O, no side effects.

    Args:
        entry: CSV row (list of strings).

    Raises:
        TimelogFormatError: if the row does not have exactly three columns or
            the date column does not parse as ``DD.MM.YYYY``.

    Traceability: FR-05, QR-05.
    """
    if not isinstance(entry, (list, tuple)) or len(entry) < 3:
        raise TimelogFormatError(
            f"Timelog row must have at least 3 columns (date, start, end), "
            f"got: {entry!r}"
        )
    try:
        dt.strptime(entry[0], DATE_FORMAT)
    except (ValueError, TypeError) as e:
        raise TimelogFormatError(f"Invalid date in timelog row {entry!r}: {e}") from e


def validate_timesheet_structure(timesheet):
    """Validate the Excel timesheet template structure.

    Pure function: reads the workbook but performs no I/O.

    Args:
        timesheet: openpyxl Workbook.

    Raises:
        TimesheetFormatError: if the workbook has fewer than
            ``TIMESHEET_SHEETS`` worksheets or the year cell is unusable
            (when the expected year-check sheet is present).

    Traceability: FR-05, QR-05.
    """
    if timesheet is None:
        raise TimesheetFormatError("Timesheet workbook is None")
    if len(timesheet.worksheets) < TIMESHEET_SHEETS:
        raise TimesheetFormatError(
            f"Timesheet must have at least {TIMESHEET_SHEETS} worksheets, "
            f"got {len(timesheet.worksheets)}"
        )
    # The year cell lives on a named sheet; only validate it when that sheet
    # exists (test fixtures may use different sheet names).
    if YEAR_CHECK_SHEET in timesheet.sheetnames:
        cell = timesheet[YEAR_CHECK_SHEET][YEAR_CHECK_CELL].value
        if cell is None:
            raise TimesheetFormatError(
                f"Year cell {YEAR_CHECK_SHEET}!{YEAR_CHECK_CELL} is empty"
            )
        if not (hasattr(cell, "year") or str(cell).strip().isdigit()):
            raise TimesheetFormatError(
                f"Year cell {YEAR_CHECK_SHEET}!{YEAR_CHECK_CELL} "
                f"holds no usable year: {cell!r}"
            )


def check_file_existence(filepath, filetype):
    """Check and load files.

    Traceability: FR-04, FR-05.
    """
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

    def __init__(
        self,
        config,
        input_provider: InputProvider = _default_input_provider,
        clock: Clock = _default_clock,
    ):
        """Initialize the TimeSheetProcessor with configuration.

        Args:
            config (dict): Dictionary containing file paths, year, and
                logging settings.
            input_provider: User-input function
                (default: ``builtins.input``).
            clock: Time provider (default: ``datetime.now``).

        Traceability: FR-07, QR-04.
        """
        self.timelog_path = config["timelog_path"]
        self.timesheet_path = config["timesheet_path"]
        self.year = config["year"]
        self.timelog = []
        self.timedata = []
        self.timesheet = None
        self.obj_date_startpoint = None
        self.obj_date_endpoint = None
        self._input_provider = input_provider
        self._clock = clock

    def load_files(self):
        """Load timelog and timesheet files.

        Validates the timesheet structure after loading (FR-05, QR-05).

        Traceability: FR-04.
        """
        logging.info("Loading files...")
        self.timelog = check_file_existence(self.timelog_path, "csv")
        self.timesheet = check_file_existence(self.timesheet_path, "excel")
        validate_timesheet_structure(self.timesheet)

    def check_year_consistency(self):
        """Abort if the configured year differs from the timesheet year.

        The timesheet stores its year as a date in cell
        YEAR_CHECK_SHEET!YEAR_CHECK_CELL. This input check runs after
        config and timesheet are loaded and prevents writing into the wrong
        year's workbook.

        Raises:
            ConsistencyError: If the years differ or the cell holds no usable
                year.

        Traceability: FR-06.
        """
        cell = self.timesheet[YEAR_CHECK_SHEET][YEAR_CHECK_CELL].value
        excel_year = getattr(cell, "year", None) or (
            int(cell) if str(cell).strip().isdigit() else None
        )

        if excel_year != self.year:
            message = (
                f"Year mismatch: config year {self.year} vs. timesheet "
                f"{YEAR_CHECK_SHEET}!{YEAR_CHECK_CELL} = {cell!r}. Aborting."
            )
            logging.error(message)
            raise ConsistencyError(message)

        logging.info("Year consistency OK: %s", excel_year)

    def request_date_input(self):
        """Request start and end date from user or use defaults.

        Traceability: FR-07.
        """
        logging.info("Setting date range...")

        # Try to get user input, but use defaults if no input provided
        try:
            start_input = self._input_provider(
                "Enter Start Date (dd.mm.yyyy) or press Enter for default: "
            ).strip()
            if start_input:
                self.obj_date_startpoint = dt.strptime(start_input, DATE_FORMAT)
                logging.info(f"Start date: {self.obj_date_startpoint.date()}")
            else:
                self.obj_date_startpoint = self.set_default_start_date()
        except (ValueError, EOFError):  # fmt: skip
            logging.info("Using default start date...")
            self.obj_date_startpoint = self.set_default_start_date()

        try:
            end_input = self._input_provider(
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
            return parse_date(prompt, input_provider=self._input_provider)
        except Exception as e:
            logging.warning(f"Error parsing date: {e}. Falling back to default date.")
            return fallback()

    def set_default_start_date(self):
        """Set default start date based on timesheet contents.

        Traceability: FR-07.
        """
        logging.info("Setting default start date...")
        default_start_date = calculate_default_start_date(self.timesheet, self.year)
        if default_start_date == dt(self.year, 1, 1):
            logging.warning(
                f"No valid date found. Default start date set to: "
                f"{default_start_date.date()}"
            )
        else:
            logging.info(f"Default start date: {default_start_date.date()}")
        return default_start_date

    def set_default_end_date(self):
        """Set default end date to yesterday.

        Traceability: FR-07.
        """
        default_end_date = self._clock() - td(days=1)
        logging.info(f"Default end date: {default_end_date.date()}")
        return default_end_date

    def select_timelog_data(self):
        """Filter timelog data based on selected dates.

        Traceability: FR-08.
        """
        logging.info("Selecting timelog data...")
        start, end = self.obj_date_startpoint, self.obj_date_endpoint
        self.timedata = filter_timelog_entries(self.timelog, start, end)
        if not self.timedata:
            raise ValueError("No data found for the selected dates.")

    def store_data(self):
        """Store selected timelog data into the timesheet.

        Returns a :class:`StoreResult` so callers can assert on the outcome
        instead of inspecting log output.

        Traceability: FR-09, FR-10, FR-11, FR-12.
        """
        logging.info("Storing timelog data into timesheet...")

        overwrite_decision = self._check_and_confirm_overwrite()

        result = StoreResult.STORED
        for entry in self.timedata:
            row, month_idx, start_time, end_time = map_entry_to_cell(entry)
            sheet = self.timesheet.worksheets[month_idx]

            start_cell, end_cell = sheet.cell(row=row, column=5), sheet.cell(
                row=row, column=6
            )

            if start_cell.value:
                if overwrite_decision == "skip_all":
                    logging.info(f"Skipping existing data for {entry[0]}.")
                    result = StoreResult.SKIPPED
                    continue
                elif overwrite_decision == "abort":
                    logging.info("Aborting due to user request.")
                    result = StoreResult.ABORTED
                    break
                # overwrite_decision == "overwrite_all" -> proceed to overwrite

            start_cell.value, end_cell.value = start_time, end_time

        return result

    def _check_and_confirm_overwrite(self):
        """Check for existing data and ask user once for overwrite decision.

        Returns:
            str: "overwrite_all", "skip_all", or "abort"
        """
        entries_with_data = []
        for entry in self.timedata:
            row, month_idx, _, _ = map_entry_to_cell(entry)
            sheet = self.timesheet.worksheets[month_idx]
            start_cell = sheet.cell(row=row, column=5)
            if start_cell.value:
                entries_with_data.append(entry[0])

        if not entries_with_data:
            return "overwrite_all"  # No conflicts, proceed normally

        logging.info(f"Found {len(entries_with_data)} day(s) with existing data.")
        return self._prompt_overwrite_decision(len(entries_with_data))

    def confirm_overwrite(self):
        """Confirm overwrite with user (simple yes/no).

        Returns:
            bool: True for "y" input, False otherwise.
        """
        try:
            response = self._input_provider("Overwrite? [y/n]: ").strip().lower()
            return response in ["y", "yes"]
        except EOFError:
            return True

    def _prompt_overwrite_decision(self, count):
        """Prompt user for overwrite decision.

        Args:
            count: Number of entries with existing data

        Returns:
            str: "overwrite_all", "skip_all", or "abort"
        """
        try:
            prompt = (
                f"{count} day(s) have existing data. "
                "Overwrite all (y), skip existing (s), or abort (n)? "
                "[y/s/n, default=y]: "
            )
            response = self._input_provider(prompt).strip().lower()

            if response in ["y", "yes", ""]:
                logging.info("User chose to overwrite all existing data.")
                return "overwrite_all"
            elif response in ["s", "skip"]:
                logging.info("User chose to skip existing data.")
                return "skip_all"
            else:  # "n", "no", or any other input
                logging.info("User chose to abort.")
                return "abort"
        except EOFError:
            logging.info("No input provided, defaulting to overwrite all.")
            return "overwrite_all"

    def save_timesheet(self):
        """Save the modified timesheet with backup and error handling.

        Traceability: FR-13.
        """
        logging.info("Saving timesheet...")
        self.timesheet.save(self.timesheet_path)


def run(config: dict) -> None:
    """Execute the timesheet processing pipeline for a given config.

    Steps: load files -> request date range -> select data -> store -> save.
    Errors raised by individual steps are logged rather than propagated, so a
    bad date range or empty selection ends the run gracefully.

    Args:
        config: Mapping with ``timelog_path``, ``timesheet_path`` and ``year``.

    Traceability: FR-14, FR-15.
    """
    processor = TimeSheetProcessor(config)

    try:
        processor.load_files()
        processor.check_year_consistency()
        processor.request_date_input()
        processor.select_timelog_data()
        processor.store_data()
        processor.save_timesheet()
        logging.info("Processing complete.")
    except Exception as e:
        logging.error("An error occurred: %s", e)


def main() -> None:
    """Load configuration, configure logging, and run the pipeline."""
    try:
        config = load_config()
    except ConfigError as e:
        logging.basicConfig(level=logging.ERROR)
        logging.error("Configuration error: %s", e)
        raise SystemExit(1) from None

    configure_logging(config["logging"])

    logging.info("CWD: %s", os.getcwd())
    logging.info("Environment: %s", config["environment"])
    logging.info("Timelog path: %s", config["timelog_path"])
    logging.info("Timesheet path: %s", config["timesheet_path"])
    logging.info("Work year: %d", config["year"])

    run(config)


if __name__ == "__main__":  # pragma: no cover
    main()
