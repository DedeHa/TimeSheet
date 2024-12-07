"""
TYPE:   !/usr/bin/env python3 

FILENAME :        TimeSheetAlgo.py             

AUTHOR :    Dennis Hartel        

START DATE :    07.12.2024

DESCRIPTION :   Automatic timelog organisation with extract of timelogdata and document in time balance sheet

"""
#Configuration--------------------------------------------------------#

import time
import csv
import openpyxl
from datetime import datetime as dt, timedelta as td

# Constants
TIMESHEET_PATH = '01_Timealarm/2023_FDTech_Dennis_Hartel.xlsm'
TIMELOG_PATH = '01_Timealarm/FDTech_timelog.csv'
AZE_TEMPLATE_PATH = '02_AZE_TimeSheets/template_timesheet_test.xlsx'
AZE_SHEET_PATH = '02_AZE_TimeSheets/'

class ALGO_TIMESHEET:  
    def __init__(self):
        self.bo_status_overwrite = 2
        self.int_row_indexoffset = 4
        self.timelog = []
        self.timesheet = None
        self.obj_date_startpoint = None
        self.obj_date_endpoint = None
        self.obj_newtimedata = []

    def fct_che_pre_req(self):
        """Check prerequisites and load files."""
        print('--- Check Pre-Requisites ---')
        # Check Timelog
        try:
            with open(TIMELOG_PATH, encoding="utf-8") as obj_csv_timelog:
                obj_list_timelog = list(csv.reader(obj_csv_timelog))
                self.timelog = obj_list_timelog[1:]  # Exclude header
        except FileNotFoundError:
            print("Error: No Timelog File found.")
            exit()

        # Check Timesheet
        try:
            self.timesheet = openpyxl.load_workbook(TIMESHEET_PATH, data_only=False, keep_vba=True)
        except FileNotFoundError:
            print("Error: No Timesheet File found.")
            exit()

    def fct_req_algo_para(self):
        """Request start and end dates from the user."""
        def get_date_input(prompt):
            for _ in range(3):
                user_input = input(prompt)
                try:
                    return dt.strptime(user_input, '%d.%m.%Y')
                except ValueError:
                    print(f"Invalid date format. Please try again.")
            return None

        self.obj_date_startpoint = get_date_input("Please enter the Startdate <dd.mm.yyyy>: ")
        self.obj_date_endpoint = get_date_input("Please enter the Enddate <dd.mm.yyyy>: ")

    def fct_algo_para_def_start(self):
        """Define default start date based on the last recorded date in the timesheet."""
        for sheet in reversed(self.timesheet.worksheets[:12]): 
            for i in range(self.int_row_indexoffset + 30, self.int_row_indexoffset, -1):
                if sheet.cell(row=i, column=5).value:
                    break
            if sheet.cell(row=i, column=5).value:
                int_year_prevvalue = self.timesheet.worksheets[0].cell(row=3, column=2).value.year
                int_month_prevvalue = self.timesheet.index(sheet) + 1
                int_day_prevvalue = i - self.int_row_indexoffset
                self.obj_date_startpoint = dt(int_year_prevvalue, int_month_prevvalue, int_day_prevvalue)
                print(f"Default startdate identified: {self.obj_date_startpoint.date()}")
                if input("Please confirm: <y/n>: ").lower() == 'n':
                    exit()
                break

    def fct_sel_timelog(self):
        """Select the relevant time log data."""
        print('--- Selected dates ---')
        for log_entry in self.timelog:
            log_date = dt.strptime(log_entry[0], '%d.%m.%Y')
            if self.obj_date_startpoint <= log_date <= self.obj_date_endpoint:
                self.obj_newtimedata.append(log_entry)
        if not self.obj_newtimedata:
            print("Error: No data identified.")
            exit()

    def fct_store_data(self):
        """Store the selected timelog data into the timesheet."""
        print('--- Log time data ---')
        for i in self.obj_newtimedata:
            log_date = dt.strptime(i[0], '%d.%m.%Y')
            int_row_index = self.int_row_indexoffset + log_date.day
            int_sel_month = log_date.month - 1

            sheet = self.timesheet.worksheets[int_sel_month]
            obj_cell_starttime = sheet.cell(row=int_row_index, column=5)    
            obj_cell_endtime = sheet.cell(row=int_row_index, column=6)

            if obj_cell_starttime.value and self.bo_status_overwrite == 2:
                print("Data already present!")
                if input("Confirm overwrite <y/n>: ").lower() == 'n':
                    continue

            if obj_cell_starttime.value is None:
                obj_cell_starttime.value = i[1]
                obj_cell_endtime.value = i[2]

def main():
    algo = ALGO_TIMESHEET()
    algo.fct_req_algo_para()
    algo.fct_che_pre_req()
    algo.fct_sel_timelog()
    algo.fct_store_data()
    algo.timesheet.save(TIMESHEET_PATH)

if __name__ == "__main__":
    main()
