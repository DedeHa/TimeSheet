"""
TYPE:   !/usr/bin/env python3 

FILENAME :        TimeSheetAlgo.py             

AUTHOR :    Dennis Hartel        

START DATE :    26.01.2022

DESCRIPTION :   Automatic timelog organisation with extract of timelogdata and document in time balance sheet

"""
#Configuration--------------------------------------------------------#

import sys, os, time
import csv, argparse
import openpyxl
import AZESheetAlgo

from datetime import datetime as dt
from datetime import timedelta as td
from distutils.util import strtobool

#EndConfiguration-----------------------------------------------------#

class ALGO_CHECK:
    # Class methods
    # constructor
    def __init__(self):
        # Starttime for programmexecution measurement
        self.db_time_programstart = time.time() 
        self.db_time_programend = 0
    
    def end(self):
        self.db_time_programend = time.time()
        return self.db_time_programend - self.db_time_programstart

class ALGO_TIMESHEET:  
    # class attribute
    int_position_date = 0
    int_position_starttime = 1
    int_position_endtime = 2
    int_row_indexoffset = 4

    str_path_timelog = '01_Timealarm/FDTech_timelog.csv'
    str_path_timesheet = '01_Timealarm/2023_FDTech_Dennis_Hartel.xlsm'
    str_path_azetemplate = '02_AZE_TimeSheets/template_timesheet_test.xlsx'
    str_path_azesheet = '02_AZE_TimeSheets/'

    timelog = 0
    timesheet = 0
    azetemplate = 0
    obj_date_startpoint = 0
    obj_date_endpoint = 0

    obj_newtimedata = []

    # class methods

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # fct_che_pre_req - Check pre-requisits and setup files/documents
    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    
    def fct_che_pre_req(self):
        print('--- Check Pre-Requisits ---')
        
        # Initiate/Check Timelog
        try:
        # TRUE
        # Open timelog csv and exclude header
            with open(self.str_path_timelog) as obj_csv_timelog:
                obj_list_timelog = list(csv.reader(obj_csv_timelog))
                obj_list_timelog.pop(0)
                self.timelog = obj_list_timelog
        except:
            # FALSE
            print("Failure detected! No Timelog File found. TimeSheetAlgo will be cancaled")
            exit()

        # Initiate/Check TimeSheet
        try:  
            # TRUE
            # Open timesheet xlsm with parameters (data_only = Keep formula, keep_vba = Keep VBA program)
            self.timesheet = openpyxl.load_workbook(self.str_path_timesheet, data_only=False, keep_vba=True)
        except:
            # FALSE
            print("Failure detected! No TimeSheet File found. TimeSheetAlgo will be cancaled")
            exit()

        # Initiate/Check AZE-Template
        '''
        try:  
            # TRUE
            # Open timesheet xlsm with parameters (data_only = Keep formula, keep_vba = Keep VBA program)
            #self.azetemplate = openpyxl.load_workbook(self.str_path_azetemplate, data_only=False, keep_vba=True) 
            self.azetemplate = openpyxl.load_workbook(self.str_path_azetemplate) 
        except:
            # FALSE
            print("Failure detected! No AZE-Timesheet File found. TimeSheetAlgo will be cancaled")
            exit()
        '''

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++
    # fct_req_algo_para - Request date algo parameter input
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++

    def fct_req_algo_para(self):
        print('--- Request Date Input ---')

        # Request startdate with three attemps or derive detfault data
        for i in range(2, -1, -1):
            str_date_startpoint = input("Please enter the Startdate <dd.mm.yyyy>: ")
        
            # Check       
            try:
                # TRUE
                self.obj_date_startpoint = dt.strptime(str_date_startpoint,'%d.%m.%Y')
                print("Startdate: ", self.obj_date_startpoint.date())
                break
            except:
                # FALSE
                print("That is not a date. Try again. Remaining Attemps: ", i)

        # Request enddate with three attemps or derive detfault data
        for i in range(2, -1, -1):
            str_date_endpoint = input("Please enter the Enddate <dd.mm.yyyy>: ")
        
            # Check       
            try:
                # TRUE
                self.obj_date_endpoint = dt.strptime(str_date_endpoint,'%d.%m.%Y')
                print("Enddate: ", self.obj_date_endpoint.date())
                break
            except:
                # FALSE
                print("That is not a date. Try again. Remaining Attemps: ", i)

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++
    # fct_algo_para_def_start - Define default startdate
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++

    def fct_algo_para_def_start(self):

        # Define default start date and identify/find last documented timedata
        # Iterate through timesheet months 
        for sheet in reversed(self.timesheet.worksheets[0:12]): 
            # Iterrate through timesheet month dates
            for i in range(self.int_row_indexoffset + 30, self.int_row_indexoffset, -1):
                # Check if cell value is empty and stop iteration
                if sheet.cell(row=i, column=5).value != None:
                    break
            
            # Check if cell value is empty and stop iteration
            if sheet.cell(row=i, column=5).value != None:
                
                # Document previous date
                # Define each previous date attributes (Year, Month, Day)
                # Derive year from default value in Januar Sheet
                int_year_prevvalue = self.timesheet.worksheets[0].cell(row=3, column=2).value.year
                # Derive month from selected sheet, sheet(index 0based + 1
                int_month_prevvalue = self.timesheet.index(sheet) + 1
                # Derive day from row in sheet - row-offset
                int_day_prevvalue = i - self.int_row_indexoffset
                
                # Assemble previous date attributes 
                self.obj_date_startpoint = dt(int_year_prevvalue, int_month_prevvalue, int_day_prevvalue) 
                print("Default startdate identified:", self.obj_date_startpoint.date())

                try:  
                    # TRUE
                    # Request confirmation of default value            
                    if strtobool(input("Please confirm: <y/n>: ")) == False:
                        exit()
                except:
                    # FALSE
                    print("Failure detected! No confirmation received!")
                    exit()
                break

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++
    # fct_algo_para_def_end - Define default enddate
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++

    def fct_algo_para_def_end(self):
        # Define default end date and identify/find last documented timedata
        self.obj_date_endpoint = dt.now() - td(1)
        print("Default enddate identified:", self.obj_date_endpoint.date())

        try:  
            # TRUE
            # Request confirmation of default value            
            if strtobool(input("Please confirm: <y/n>: ")) == False:
                exit()
        except:
            # FALSE
            print("Failure detected! No confirmation received!")
            exit()

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Determine/evaluate and select timeframe from timelog
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++
    
    def fct_sel_timelog(self):
        print('--- Selected dates ---')
        
        for i in self.timelog:

            # Convert list raw date string into date
            obj_sel_date = dt.strptime(i[0],'%d.%m.%Y')
                
            # Identify start date in list, check working day and define start index
            if obj_sel_date >= self.obj_date_startpoint and obj_sel_date <= self.obj_date_endpoint: #and obj_sel_date.weekday() <= 4:        
                self.obj_newtimedata.extend([i])

        # Check if any failure/no data received
        if not self.obj_newtimedata:
            print("Failure detected! No data identified!")
            exit()

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Store/document timelog data in timesheet
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++
    
    def fct_store_data(self):
        print('--- Log time data ---')
 
        # Iterate through selected timelog data
        for i in self.obj_newtimedata:

            # Define index for storing data
            # row: startindex = Timesheet Header + Day of the Month
            int_row_index = self.int_row_indexoffset + dt.strptime(i[0],'%d.%m.%Y').day
            
            # Shift variable index from 1 to 0
            # month: selected_month(index_0) = selected_date.month(index_1) - 1
            int_sel_month = dt.strptime(i[0],'%d.%m.%Y').month-1

            # Iterate worksheet/months in timesheet
            for sheet in self.timesheet.worksheets[0:12]:
                
                # Identify worksheet/month for selected timelog data
                # month: selected_month  
                if int_sel_month != self.timesheet.index(sheet):
                    continue
                else:    
                    # Define required cells for data storage
                    # Cell definition = [Xy]; [X=column, y=row]
                    # Remark[Bx=2y]; Type[Cx=3y]; Starttime [Ey]; Endtime [Fy]
                    obj_cell_remark = sheet.cell(row=int_row_index, column=2)      
                    obj_cell_type = sheet.cell(row=int_row_index, column=3)
                    obj_cell_starttime = sheet.cell(row=int_row_index, column=5)    
                    obj_cell_endtime = sheet.cell(row=int_row_index, column=6)
                    
                    # Check for national holiday, sick - k and flextime - g
                    if (obj_cell_remark.value != None) or (obj_cell_type.value != None):
                        continue
                    else:                
                        # Store timelog data in timesheet for "Kommen"
                        obj_cell_starttime.value = i[1]
                        
                        # Store timelog data in timesheet for "Gehen"
                        obj_cell_endtime.value = i[2]

def main():
  
    # Initialize class
    algo1 = ALGO_TIMESHEET()

    # Request date algo parameter input
    algo1.fct_req_algo_para()

    # Starttime for programmexecution measurement
    timesheet_check = ALGO_CHECK()

    # Check pre-requisits 
    algo1.fct_che_pre_req() 

    # Check correct parameter
    if algo1.obj_date_startpoint == 0:
        algo1.fct_algo_para_def_start()

    if algo1.obj_date_endpoint == 0:
        algo1.fct_algo_para_def_end()

    # Select and store data
    algo1.fct_sel_timelog()
    algo1.fct_store_data()

    # Close workbook timesheet    
    algo1.timesheet.save(algo1.str_path_timesheet)

    # Endtime for programmexecution measurement
    print(timesheet_check.end())
    
if __name__ == "__main__":
    main()