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
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Constants
DATE_FORMAT = "%d.%m.%Y"
MAX_RETRIES = 3
ROW_OFFSET = 4
TIMESHEET_SHEETS = 12
YEAR = 2025

# File Paths
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
                with open(filepath, 'r+b') as test_file:
                    pass
                logging.info(f"Excel file is not locked: {filepath}")
            except (PermissionError, IOError) as e:
                logging.warning(f"Excel file may be locked/opened by another process: {filepath}")
                logging.warning(f"Lock error: {e}")
                logging.warning("Please close the Excel file if it's open in Excel application")
            
            # Open timesheet xlsm with parameters:
            # data_only = Keep formula, keep_vba = Keep VBA program
            return openpyxl.load_workbook(filepath, data_only=False, keep_vba=True)
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        raise
    except PermissionError as e:
        logging.error(f"Permission denied accessing file: {filepath}")
        logging.error(f"This usually means the file is open in Excel. Please close it and try again.")
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
                logging.info(
                    f"Using provided start date: {self.obj_date_startpoint.date()}"
                )
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
                logging.info(
                    f"Using provided end date: {self.obj_date_endpoint.date()}"
                )
            else:
                self.obj_date_endpoint = self.set_default_end_date()
        except (ValueError, EOFError):
            logging.info("Using default end date...")
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
                    logging.info(
                        f"Default start date identified: {default_start_date.date()}"
                    )
                    return default_start_date

        # If no date is found, set a default start date
        default_start_date = dt(YEAR, 1, 1)
        logging.info(
            f"No valid date found. Default start date set to: {default_start_date.date()}"
        )
        return default_start_date

    def set_default_end_date(self):
        """Set default end date to yesterday."""
        default_end_date = dt.now() - td(days=1)
        logging.info(f"Default end date identified: {default_end_date.date()}")
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
        """Save the modified timesheet."""
        logging.info("Saving timesheet...")
        try:
            # Check if file is still locked before saving
            try:
                with open(self.timesheet_path, 'r+b') as test_file:
                    pass
                logging.info("File is available for writing")
            except (PermissionError, IOError) as e:
                logging.error(f"Cannot save - file is locked: {self.timesheet_path}")
                logging.error(f"Please close the Excel file if it's open and try again")
                logging.error(f"Error: {e}")
                raise
            
            self.timesheet.save(self.timesheet_path)
            logging.info("Timesheet saved successfully")
        except PermissionError as e:
            logging.error(f"Failed to save timesheet - permission denied: {e}")
            logging.error("The Excel file may be open in Excel application. Please close it and try again.")
            raise


# Main execution
if __name__ == "__main__":  # pragma: no cover
    processor = TimeSheetProcessor(CONFIG)
    try:
        processor.load_files()
        processor.request_date_input()
        processor.select_timelog_data()
        processor.store_data()
        processor.save_timesheet()
        logging.info("Processing complete.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
