"""
TYPE:   !/usr/bin/env python3 

FILENAME :        TimeSheetAlgo.py             

AUTHOR :    Dennis Hartel        

START DATE :    26.01.2022

DESCRIPTION :   Automatic timelog organisation with extract of timelogdata and document in time balance sheet

REMARK: Refactored and optimized with ChatGPT and review/updated 

"""
import time
import csv
import openpyxl
from datetime import datetime as dt, timedelta as td
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
DATE_FORMAT = '%d.%m.%Y'
MAX_RETRIES = 3
ROW_OFFSET = 4
TIMESHEET_SHEETS = 12
YEAR = 2023

# File Paths
CONFIG = {
    "timelog_path": 'src_timesheetalgo/FDTech_timelog.csv',
    "timesheet_path": 'src_timesheetalgo/2023_FDTech_Dennis_Hartel.xlsm',
}


def parse_date(input_prompt, retries=MAX_RETRIES):
    """Parse date with retries."""
    for attempt in range(retries):
        date_str = input(input_prompt)
        try:
            return dt.strptime(date_str, DATE_FORMAT)
        except ValueError:
            logging.warning(f"Invalid date format. Attempts left: {retries - attempt - 1}")
    raise ValueError("Maximum retries reached. Exiting...")


def check_file_existence(filepath, filetype):
    """Check and load files."""
    try:
        if filetype == 'csv':
            with open(filepath, encoding='utf-8') as file:
                return list(csv.reader(file))[1:]  # Skip header
        elif filetype == 'excel':
            # Open timesheet xlsm with parameters (data_only = Keep formula, keep_vba = Keep VBA program)
            return openpyxl.load_workbook(filepath, data_only=False, keep_vba=True)
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        raise


class TimeSheetProcessor:
    def __init__(self, config):
        self.timelog_path = config['timelog_path']
        self.timesheet_path = config['timesheet_path']
        self.timelog = []
        self.timedata = []
        self.timesheet = None
        self.obj_date_startpoint = None
        self.obj_date_endpoint = None

    def load_files(self):
        """Load timelog and timesheet files."""
        logging.info("Loading files...")
        self.timelog = check_file_existence(self.timelog_path, 'csv')
        self.timesheet = check_file_existence(self.timesheet_path, 'excel')

    def request_date_input(self):
        """Request start and end date from user."""
        logging.info("Requesting date input...")
        self.obj_date_startpoint = self._get_date("Enter Start Date (dd.mm.yyyy): ", fallback=self.set_default_start_date)
        self.obj_date_endpoint = self._get_date("Enter End Date (dd.mm.yyyy): ", fallback=self.set_default_end_date)

    def _get_date(self, prompt, fallback):
        """Get a date from user input or fallback to default."""
        try:
            return parse_date(prompt)
        except Exception as e:
            logging.warning(f"Error parsing date: {e}. Falling back to default date.")
            return fallback()

    def set_default_start_date(self):
        """Set default start date based on timesheet contents."""
        # Iterate through timesheet months
        for sheet in reversed(self.timesheet.worksheets[:TIMESHEET_SHEETS]):
            for i in range(ROW_OFFSET + 30, ROW_OFFSET, -1):
                date_cell = sheet.cell(row=i, column=5).value
                if date_cell:
                    # Document previous date
                    # Define each previous date attributes (Year, Month, Day)
                    # Derive year from default value in Januar Sheet
                    year = self.timesheet.worksheets[0].cell(row=3, column=2).value.year
                    
                    # Derive month from selected sheet, sheet(index 0based + 1
                    month = self.timesheet.index(sheet) + 1
                    
                    # Derive day from the date cell value
                    day = date_cell.day
                    # Assemble previous date attributes
                    default_start_date = dt(year, month, day)
                    logging.info(f"Default start date identified: {default_start_date.date()}")
                    return default_start_date
        else:
            # If no date is found, set a default start date
            default_start_date = dt(YEAR, 1, 1)
            logging.info(f"No valid date found. Default start date set to: {default_start_date.date()}")
            return default_start_date
        
        # If no date is found, raise an exception
        raise ValueError("Unable to determine default start date.")

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
            entry for entry in self.timelog
            if start <= dt.strptime(entry[0], DATE_FORMAT) <= end
        ]
        if not self.timedata:
            raise ValueError("No data found for the selected dates.")

    def store_data(self):
        """Store selected timelog data into the timesheet."""
        logging.info("Storing timelog data into timesheet...")
        for entry in self.timedata:
            
            # Define index for storing data
            date, start_time, end_time = dt.strptime(entry[0], DATE_FORMAT), entry[1], entry[2]
            
            # row: startindex = Timesheet Header + Day of the Month
            # month: selected_month(index_0) = selected_date.month(index_1) - 1
            row, month_idx = ROW_OFFSET + date.day, date.month - 1
            sheet = self.timesheet.worksheets[month_idx]

            start_cell, end_cell = sheet.cell(row=row, column=5), sheet.cell(row=row, column=6)

            if start_cell.value and not self.confirm_overwrite():
                logging.info(f"Skipping existing data for {date.date()}.")
                break

            start_cell.value, end_cell.value = start_time, end_time

    def confirm_overwrite(self):
        """Prompt user to confirm overwriting data."""
        response = input("Data exists. Overwrite? (y/n): ").strip().lower()
        return response == 'y'

    def save_timesheet(self):
        """Save the modified timesheet."""
        logging.info("Saving timesheet...")
        self.timesheet.save(self.timesheet_path)

# Main execution
if __name__ == "__main__":      # pragma: no cover
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
