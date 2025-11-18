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
from pathlib import Path

# Constants
DATE_FORMAT = "%d.%m.%Y"
MAX_RETRIES = 3
ROW_OFFSET = 4
TIMESHEET_SHEETS = 12
YEAR = 2025


def load_config():
    """Load configuration from YAML file with fallback to defaults."""
    # Default configuration
    default_config = {
        "timelog_path": "FDTech_timelog.csv",
        "timesheet_path": "2025_FDTech_Dennis_Hartel.xlsm",
    }
    
    default_logging = {
        "level": "INFO",
        "format": "%(asctime)s - %(levelname)s - %(message)s"
    }
    
    # Configure basic logging first to ensure logging works
    logging.basicConfig(
        level=logging.INFO,
        format=default_logging['format'],
        force=True  # Force reconfiguration
    )
    
    def determine_environment():
        """Determine environment based on current working directory name only."""
        current_dir = Path.cwd()
        current_dir_name = current_dir.name
        
        # Check only the current directory name (not full path)
        if current_dir_name == "01_Zeiten":
            return "production"
        elif current_dir_name == "src_timesheetalgo":
            return "development"
        else:
            # Fallback: check if we're running from src_timesheetalgo directory
            script_dir = Path(__file__).parent
            if script_dir.name == "src_timesheetalgo":
                return "development"
            else:
                return "development"  # Default fallback
    
    try:
        # Get the directory of the current script
        script_dir = Path(__file__).parent
        config_path = script_dir / "config.yaml"
        
        # Load YAML configuration
        with open(config_path, 'r', encoding='utf-8') as file:
            yaml_config = yaml.safe_load(file)
        
        # Determine environment based on folder structure
        env = determine_environment()
        logging.info(f"Detected environment: {env} (based on directory structure)")
        
        if env in yaml_config.get('environments', {}):
            env_config = yaml_config['environments'][env]
            
            # Reconfigure logging with YAML settings
            logging_config = env_config.get('logging', default_logging)
            logging.basicConfig(
                level=getattr(logging, logging_config.get('level', 'INFO')),
                format=logging_config.get('format', default_logging['format']),
                force=True  # Force reconfiguration
            )
            
            # Return file paths configuration
            return env_config.get('file_paths', default_config)
        else:
            logging.warning(f"Environment '{env}' not found in config. Using defaults.")
            raise KeyError(f"Environment '{env}' not found")
            
    except (FileNotFoundError, yaml.YAMLError, KeyError) as e:
        logging.warning(f"Failed to load config.yaml: {e}. Using defaults.")
        return default_config


# Load configuration
CONFIG = load_config()


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
            # Open timesheet xlsm with parameters:
            # data_only = Keep formula, keep_vba = Keep VBA program
            return openpyxl.load_workbook(filepath, data_only=False, keep_vba=True)
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
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
        
        # Calculate default dates first (this will log them)
        default_start = self.set_default_start_date()
        
        # Try to get user input, but use defaults if no input provided
        try:
            start_input = input("Enter Start Date (dd.mm.yyyy) or press Enter for default: ").strip()
            if start_input:
                self.obj_date_startpoint = dt.strptime(start_input, DATE_FORMAT)
                logging.info(f"Using provided start date: {self.obj_date_startpoint.date()}")
            else:
                self.obj_date_startpoint = default_start
        except (ValueError, EOFError):
            self.obj_date_startpoint = default_start
        
        # Calculate default end date (this will log it)
        default_end = self.set_default_end_date()
        
        try:
            end_input = input("Enter End Date (dd.mm.yyyy) or press Enter for default: ").strip()
            if end_input:
                self.obj_date_endpoint = dt.strptime(end_input, DATE_FORMAT)
                logging.info(f"Using provided end date: {self.obj_date_endpoint.date()}")
            else:
                self.obj_date_endpoint = default_end
        except (ValueError, EOFError):
            self.obj_date_endpoint = default_end

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
            response = input("Data exists. Overwrite? (y/n) or press Enter for yes: ").strip().lower()
            return response in ["y", "yes", ""]  # Default to yes if empty input
        except EOFError:
            logging.info("No input provided, defaulting to overwrite (yes)")
            return True

    def save_timesheet(self):
        """Save the modified timesheet with backup and error handling."""
        logging.info("Saving timesheet...")
        try:
            # Try to save directly first
            self.timesheet.save(self.timesheet_path)
            logging.info(f"Timesheet saved successfully to {self.timesheet_path}")
        except PermissionError as e:
            # If permission denied, try saving with a timestamp suffix
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.timesheet_path.replace('.xlsm', f'_backup_{timestamp}.xlsm')
            logging.warning(f"Permission denied for original file. Saving backup to {backup_path}")
            self.timesheet.save(backup_path)
            logging.info(f"Backup timesheet saved successfully to {backup_path}")
        except Exception as e:
            logging.error(f"Failed to save timesheet: {e}")
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
