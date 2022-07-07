"""
TYPE:   !/usr/bin/env python3 

FILENAME :        Start.py             

AUTHOR :    Dennis Hartel        

START DATE :    26.01.2022

DESCRIPTION :   Automatic timelog organisation with extract of timelogdata, document in time balance sheet and creation of forwarding documents

"""
#Configuration--------------------------------------------------------#

import sys, os, time
import csv, argparse
import openpyxl

from datetime import datetime as dt
from datetime import timedelta as td

int_position_date = 0
int_position_starttime = 1
int_position_endtime = 2
int_row_startindex = 4

obj_newtimedata = []
str_wb_timesheet = '2022_ADCU_Dennis_Hartel.xlsm'

#EndConfiguration-----------------------------------------------------#

def main(arguments):
    
    '''
    # fct_req_algo_para
    # Request startdate algo parameter input
    for i in range(3, 0, -1):
        str_date_startpoint = input("Please enter the Startdate <dd.mm.yyyy>: ")

        try:
            obj_date_startpoint = dt.strptime(str_date_startpoint,'%d.%m.%Y')
            print("Startdate: ", obj_date_startpoint.date())
            break
        except:
            print("That is not a date. Remaining Attemps: ", i)
            print("Try again or default values will be used ")

    # Request enddate algo parameter input
    for i in range(3, 0, -1):
        str_date_endpoint = input("Please enter the Enddate <dd.mm.yyyy>: ")

        try:
            obj_date_endpoint = dt.strptime(str_date_startpoint,'%d.%m.%Y')
            print("Startdate: ", obj_date_endpoint.date())
            break
        except:
            print("That is not a date. Remaining Attemps: ", i)
            print("Try again or default values will be used ")
    '''
    
    # Starttime for programmexecution measurement
    db_time_programstart = time.time()
       
    '''
    # Define default Start-/End Date and identify/find last documented timedata
    # Iterate through timesheet months 
    for sheet in reversed(obj_wb_timesheet.worksheets[0:12]): 
        # Iterrate through timesheet month dates
        for i in range(int_row_startindex + 30, int_row_startindex, -1):
            # Check if cell value is empty and stop iteration
            if sheet.cell(row=i, column=5).value != None:
                break
        
        # Check if cell value is empty and stop iteration
        if sheet.cell(row=i, column=5).value != None:
            
            # Document previous date
            # Define each previous date attributes (Year, Month, Day)
            # Derive year from default value in Januar Sheet
            int_year_prevvalue = obj_wb_timesheet.worksheets[0].cell(row=3, column=2).value.year
            # Derive month from selected sheet
            int_month_prevvalue = obj_wb_timesheet.index(sheet) + 1
            # Derive day from row in sheet
            int_day_prevvalue = i - int_row_startindex
            
            # Assemble previous date attributes 
            obj_date_prevvalue = dt(int_year_prevvalue, int_month_prevvalue, int_day_prevvalue)
                
            print(obj_date_prevvalue)
            break
    '''

    str_date_startpoint = '01.01.2022'
    obj_date_startpoint = dt.strptime(str_date_startpoint, '%d.%m.%Y')
        
    str_date_endpoint = '30.01.2022'
    obj_date_endpoint = dt.strptime(str_date_endpoint, '%d.%m.%Y')

    # Determine date of today
    # print(dt.strptime(str_date_startpoint, '%d.%m.%Y'))
    
    # Open timelog csv and exclude header
    with open("timelog.csv") as fil_csv_timelog:
        obj_list_timelog = list(csv.reader(fil_csv_timelog))
        obj_list_timelog.pop(0)

    # Determine/evaluate and select timeframe from timelog
    print('--- Selected dates ---')
    for i in obj_list_timelog:

        # Convert list raw date string into date
        obj_sel_date = dt.strptime(i[0],'%d.%m.%Y')
                
        # Identify start date in list, check working day and define start index
        if obj_sel_date >= obj_date_startpoint and obj_sel_date <= obj_date_endpoint: #and obj_sel_date.weekday() <= 4:        
            obj_newtimedata.extend([i])
             
    # Store/document timelog data in timesheet
    print('--- Log time data ---')

    # Open timesheet xlsm with parameters (data_only = Keep formula, keep_vba = Keep VBA program)
    obj_wb_timesheet = openpyxl.load_workbook(str_wb_timesheet, data_only=False, keep_vba=True)
  
    # Iterate through selected timelog data
    for i in obj_newtimedata:

        # Define index for storing data
        # row: startindex = Timesheet Header + Day of the Month
        int_row_index = int_row_startindex + dt.strptime(i[0],'%d.%m.%Y').day
        
        # Shift variable index from 1 to 0
        # month: selected_month(index_0) = selected_date.month(index_1) - 1
        int_sel_month = dt.strptime(i[0],'%d.%m.%Y').month-1

        # Iterate worksheet/months in timesheet
        for sheet in obj_wb_timesheet.worksheets[0:12]:
            
            # Identify worksheet/month for selected timelog data
            # month: selected_month  
            if int_sel_month != obj_wb_timesheet.index(sheet):
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

    # Close workbook timesheet    
    obj_wb_timesheet.save(str_wb_timesheet)

    '''
    # Store/document data SAP-Sheet
    print('--- Store data ---')

    # Open timelog csv and exclude header
    obj_wb_AZEsheet = openpyxl.load_workbook('template_timesheet_test.xlsx')

    # Iterate through final timelog data
    #j = obj_newtimedata[0]
    obj_wb_AZEsheet['blanko']['B9'].value = i[0]
    obj_wb_AZEsheet['blanko']['C9'].value = i[0]
    obj_wb_AZEsheet['blanko']['D9'].value = i[1]
    obj_wb_AZEsheet['blanko']['E9'].value = i[2]

    obj_wb_AZEsheet.save('template_timesheet - Kopie.xlsx')
    '''

    # Endtime for programmexecution measurement
    db_time_programend = time.time()
    print(db_time_programend - db_time_programstart)
    
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))