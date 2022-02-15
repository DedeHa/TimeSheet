"""
TYPE:   !/usr/bin/env python3 

FILENAME :        Start.py             

AUTHOR :    Dennis Hartel        

START DATE :    26.01.2022

DESCRIPTION :   Automatic timelog organisation with extract of timelogdata, document in time balance sheet and creation of forwarding documents

PUBLIC FUNCTIONS :

NOTES :
    Variable declaration naming convention
    <mandatory: type>_<optional: unit><mandatory: varaible_name> - e.g. str_date_startpoint

        type    |    description
        ---------------------------
        obj     |   complex datatype
        str     |   string
        int     |   integer
        db      |   double       
        bo       |   boolean

CHANGES :
    REF NO  VERSION DATE    WHO     DETAIL
            A.00.01 220126  DH      Function CalcHuffman corrected

"""
#Configuration--------------------------------------------------------#

import sys, os, time
import csv, argparse
import openpyxl

import pandas as pd

from datetime import datetime as dt
from datetime import timedelta as td


int_position_date = 0
int_position_starttime = 1
int_position_endtime = 2

obj_newtimedata = []

#EndConfiguration-----------------------------------------------------#

def main(arguments):
    # Starttime for programmexecution measurement
    db_time_programstart = time.time()
    
    # Test variables
    str_date_startpoint = '02.06.2020'
    str_date_todaypoint = '05.06.2020'
    obj_date_startpoint = dt.strptime(str_date_startpoint, '%d.%m.%Y')
    obj_date_todaypoint = dt.strptime(str_date_todaypoint, '%d.%m.%Y')
        
    # Determine date of today
    print(dt.strptime(str_date_startpoint, '%d.%m.%Y'))
    
    # Change date format
    #print(str_date_startpoint.replace('.', '/'))

    # Open timelog csv and exclude header
    with open("timelog.csv") as file_csv_timelog:
        obj_list_timelog = list(csv.reader(file_csv_timelog))
        obj_list_timelog.pop(0)

    # Determine, evaluate and select timeframe from timelog
    print('--- Selected Dates ---')
    for i in obj_list_timelog:

        # Convert list raw date string into date
        obj_sel_date = dt.strptime(i[0],'%d.%m.%Y')
                
        # Identify start date in list, check working day and define start index
        if obj_sel_date >= obj_date_startpoint and obj_sel_date.weekday() <= 4:        
            obj_newtimedata.extend([i])
            print(obj_sel_date.date(),
                obj_sel_date.weekday(),
                obj_sel_date.strftime('%A'))

            print(obj_newtimedata)

    # Open timelog csv and exclude header
    obj_wb_timesheet = openpyxl.load_workbook('2020_ADCU_Dennis_Hartel.xlsm', data_only=True, keep_vba=True)
    sheet_obj = obj_wb_timesheet['Juni']
    
    # iterate worksheets in timesheet
    for sheet in obj_wb_timesheet.worksheets[0:12]:  
        print(sheet.title)
        for row in sheet.iter_rows(min_row=5, min_col=1, max_row=35, max_col=1):
            # Iterate rows in month 
            for cell in row:

                if cell.value == obj_date_startpoint:  
                    print(cell.value.date(),
                        cell.value.weekday(),
                        cell.value.strftime('%A'))

    sheet_obj['F1'].value = 'Test'
    print(sheet_obj['F1'].value)
    
    obj_wb_timesheet.save('2020_ADCU_Dennis_Hartel.xlsm')

    #print(obj_wb_timesheet.sheetnames)
    #print(sheet_obj.cell(row = 6, column = 1).value)         
        
    '''
    if i[0] == str_date_startpoint: 
        int_startdate_index = obj_list_timelog.index(i)
        bo_selected = True

    if bo_selected == True:
        if dt.strptime(i[0],'%d.%m.%Y').weekday() <= 4:
            print(dt.strptime(i[0],'%d.%m.%Y').strftime('%A'),
                dt.strptime(i[0],'%d.%m.%Y').weekday(),
                obj_list_timelog[obj_list_timelog.index(i)])
    
    if i[0] == str_date_todaypoint:
        bo_selected == False
        int_enddate_index = obj_list_timelog.index(i)
        print('Startindex: ', int_startdate_index)  
        print('Endindex: ', int_enddate_index) 
        break
    '''
    # Open timesheet excel as pd and select required colums
    '''
    obj_pd_timesheet = pd.read_excel(
        'Test.xlsx', 
        header=3,
        usecols=['Date', 'Bemerkungen', 'G', 'Kommen', 'Gehen'])
    
    data_test = obj_list_timelog[76]
    obj_pd_timesheet['Date'][1] = dt.strptime(data_test[0],'%d.%m.%Y').date()
    obj_pd_timesheet['Kommen'][1] = dt.strptime(data_test[1],'%H:%M:%S').time()
    obj_pd_timesheet['Gehen'][1] = dt.strptime(data_test[2],'%H:%M:%S').time()
        
    print(obj_pd_timesheet)
    '''
    # Print/Extract data for date
    #print('Startdate: '+obj_list_timelog[int_startdate_index][int_position_date])
    #print('Starttime: '+obj_list_timelog[int_startdate_index][int_position_starttime])
    #print('Endtime: '+obj_list_timelog[int_startdate_index][int_position_endtime])

    # Load the xlsx file
    #excel_data = pd.read_excel('Test.xlsx')

    # Read the values of the file in the dataframe
    #data = pd.DataFrame(excel_data, columns=['Sales Date', 'Sales Person', 'Amount'])
    
    # Print the content
    #print("The content of the file is:\n", data)

    # Endtime for programmexecution measurement
    db_time_programend = time.time()
    print(db_time_programend - db_time_programstart)
    
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))