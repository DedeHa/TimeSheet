"""
TYPE:   !/usr/bin/env python3 

FILENAME :        AZESheetAlgo.py             

AUTHOR :    Dennis Hartel        

START DATE :    08.10.2022

DESCRIPTION :   Automatic extract from time balance sheet and creation of AZE documents

"""
#Configuration--------------------------------------------------------#

import sys, os, time
import csv, argparse
import openpyxl

from datetime import datetime as dt
from datetime import timedelta as td
from distutils.util import strtobool


obj_newtimedata = []


#EndConfiguration-----------------------------------------------------#

class algo_check:
    # Class methods
    def __init__(self):
        # Starttime for programmexecution measurement
        self.db_time_programstart = time.time() 
        self.db_time_programend = 0
    
    def end(self):
        self.db_time_programend = time.time()
        return self.db_time_programend - self.db_time_programstart

class aze_algo:  
    # class attribute
    int_position_date = 0
    int_position_starttime = 1
    int_position_endtime = 2
    int_row_indexoffset = 2

    str_path_timelog = '01_Timealarm/timelog.csv'
    str_path_timesheet = '01_Timealarm/2022_ADCU_Dennis_Hartel.xlsm'
    str_path_azetemplate = '02_AZE_TimeSheets/template_timesheet_test.xlsx'
    str_path_azesheet = '02_AZE_TimeSheets/timesheet.xlsx'

    # class methods
    # constructor
    def __init__(self):
        timelog = 0
        timesheet = 0
        azetemplate = 0
        obj_date_startpoint = 0
        obj_date_endpoint = 0
        
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
        try:  
            # TRUE
            # Open timesheet xlsm with parameters (data_only = Keep formula, keep_vba = Keep VBA program)
            #self.azetemplate = openpyxl.load_workbook(self.str_path_azetemplate, data_only=False, keep_vba=True) 
            self.azetemplate = openpyxl.load_workbook(self.str_path_azetemplate) 
        except:
            # FALSE
            print("Failure detected! No AZE-Timesheet File found. TimeSheetAlgo will be cancaled")
            exit()
            
    # +++++++++++++++++++++++++++++++++++++++++
    # fct_sel_timelog - Select date information
    #++++++++++++++++++++++++++++++++++++++++++

    def fct_sel_timelog(self):     
        print('--- Selected dates ---')
        
        obj_sel_data = []

        # Determine/evaluate and select timeframe from timelog
        for i in self.timelog:

            # Convert list raw date string into date
            obj_sel_date = dt.strptime(i[0],'%d.%m.%Y')
                    
            # Identify start date in list, check working day and define start index
            if obj_sel_date >= self.obj_date_startpoint and obj_sel_date <= self.obj_date_endpoint: #and obj_sel_date.weekday() <= 4:        
                obj_sel_data.extend([i])
        
        self.timelog_sel = obj_sel_data

        # Check if any failure/no data received
        if not self.timelog_sel:
            print("Failure detected! No data identified!")
            exit()
        
    # destructor
    #def __del__(self):
    #   self.timesheet.save(self.str_path_timesheet)

    # fct_sel_timelog - Determine/evaluate and select timeframe from timelog
    
    # fct_store_data - Store/document timelog data in timesheet

    # ++++++++++++++++++++++++++++++++++++++++++
    # fct_create_aze_sheet - Store selected data 
    #+++++++++++++++++++++++++++++++++++++++++++

    def fct_create_aze_sheet(self):     
        print('--- Store selected data ---')
        
        # Open timelog csv and exclude header
        obj_wb_AZEsheet = self.azetemplate
        obj_newtimedata = self.timelog_sel

        #sheet = obj_wb_AZEsheet.active
        row = 0    

        # Define required cells for data storage
        # Cell definition = [Xy]; [X=column, y=row]
        # Cols = Date1[By]; Date2[Cy]; Starttime[Dy]; Endtime [Ey]
        # Rows = Row1[X9]; Row2[X13]; Row3[X17]; Row4[X21]; Row[5X24]
        obj_list_datacells = [
            ['B9', 'C9', 'D9', 'E9'],
            ['B13', 'C13', 'D13', 'E13'],
            ['B17', 'C17', 'D17', 'E17'],
            ['B21', 'C21', 'D21', 'E21'],
            ['B24', 'C24', 'D24', 'E24']        
        ]

        print(obj_list_datacells, obj_list_datacells[0], obj_list_datacells[1], obj_list_datacells[2], obj_list_datacells[3])
    
        # Iterate through selected timelog data
        for i in obj_newtimedata:

         
            # Iterate through final timelog data
            obj_wb_AZEsheet['blanko']['B9'].value = i[0]
            obj_wb_AZEsheet['blanko']['C9'].value = i[0]
            obj_wb_AZEsheet['blanko']['D9'].value = i[1]
            obj_wb_AZEsheet['blanko']['E9'].value = i[2]

        
        # Define required cells for data storage
        # Cell definition = [Xy]; [X=column, y=row]
        # Remark[Bx=2y]; Type[Cx=3y]; Starttime [Ey]; Endtime [Fy]
        '''
        obj_cell_date1 = sheet.cell(row=9, column=2)      
        obj_cell_date2 = sheet.cell(row=9, column=3)
        obj_cell_starttime = sheet.cell(row=9, column=4)    
        obj_cell_endtime = sheet.cell(row=9, column=5)
        
        obj_cell_date1.value = i[0]    
        obj_cell_date2.value = i[0] 
        obj_cell_starttime.value = i[1]   
        obj_cell_endtime.value = i[2]
        '''
            
        obj_wb_AZEsheet.save(self.str_path_azesheet)
  
def main():
    
    algo1 = aze_algo()
    algo1.fct_req_algo_para()

    # Starttime for programmexecution measurement
    Test = algo_check()
    
    # Debugging variable
    
    algo1.fct_che_pre_req()
    algo1.fct_sel_timelog()
    algo1.fct_create_aze_sheet()
    #del aze_algo1
    #aze_algo1.init_timesheet()

    # Endtime for programmexecution measurement
    print(Test.end())
    
if __name__ == '__main__':
    main()