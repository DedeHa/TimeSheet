"""
TYPE:   !/usr/bin/env python3 

FILENAME :        Start.py             

AUTHOR :    Dennis Hartel        

START DATE :    26.01.2022

DESCRIPTION :   Automatic timelog organisation with extract of timelogdata, document in time balance sheet and creation of forwarding documents

PUBLIC FUNCTIONS :

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
    
    # Open timelog csv and exclude header
    with open("timelog.csv") as file_csv_timelog:
        obj_list_timelog = list(csv.reader(file_csv_timelog))
        obj_list_timelog.pop(0)

    # Determine/evaluate and select timeframe from timelog
    print('--- Selected dates ---')
    for i in obj_list_timelog:

        # Convert list raw date string into date
        obj_sel_date = dt.strptime(i[0],'%d.%m.%Y')
                
        # Identify start date in list, check working day and define start index
        if obj_sel_date >= obj_date_startpoint and obj_sel_date.weekday() <= 4:        
            obj_newtimedata.extend([i])
             
    # Store/document timelog data in timesheet
    print('--- Log time data ---')

    # Open timelog csv and exclude header
    obj_wb_timesheet = openpyxl.load_workbook('2020_ADCU_Dennis_Hartel.xlsm', data_only=False, keep_vba=True)
  
    # Iterate through selected timelog data
    for i in obj_newtimedata:

        # Convert list raw date string into date
        # row: startindex = 5 + day of the month
        int_row_index = int_row_startindex + dt.strptime(i[0],'%d.%m.%Y').day
       
        # Iterate worksheet/months in timesheet
        for sheet in obj_wb_timesheet.worksheets[0:12]:
            
            # Identify worksheet/month for selected timelog data
            # month: worksheet_index - 1
            if obj_sel_date.month-1 != obj_wb_timesheet.index(sheet):
                continue
            else:    
                # Define required cells for check and documentation
                # Remark[Bx]; Type[Cx]; Starttime [Ex]; Endtime [Fx]
                obj_cell_remark = sheet.cell(row=int_row_index, column=2)      
                obj_cell_type = sheet.cell(row=int_row_index, column=3)
                obj_cell_starttime = sheet.cell(row=int_row_index, column=5)    
                obj_cell_endtime = sheet.cell(row=int_row_index, column=6)
                
                # Check for national holiday, sick - k and flextime - g
                if (obj_cell_remark.value != None) or (obj_cell_type.value != None):
                    # Remove list items for not required times
                    obj_newtimedata.remove(i)
                    continue
                else:                
                    # Store timelog data in timesheet for "Kommen"
                    obj_cell_starttime.value = i[1]
                    
                    # Store timelog data in timesheet for "Gehen"
                    obj_cell_endtime.value = i[2]
  
    # Close workbook timesheet    
    obj_wb_timesheet.save('2020_ADCU_Dennis_Hartel.xlsm')
    
    # Store/document data SAP-Sheet
    print('--- Store data ---')

    # Open timelog csv and exclude header
    #obj_wb_AZEsheet = openpyxl.load_workbook('AZE_template.xlsx')

    # Iterate through final timelog data
    #j = obj_newtimedata[0]
    #obj_wb_AZEsheet['B9'].value = i[0]
    #obj_wb_AZEsheet['C9'].value = i[0]
    #obj_wb_AZEsheet['D9'].value = i[1]
    #obj_wb_AZEsheet['E9'].value = i[2]

    #obj_wb_AZEsheet.save('AZE_template.xlsx')
    
    #sheet.cell(row=int_row_startindex + dt.strptime(i[0],'%d.%m.%Y').day, column=5).value = dt.strptime(i[1],'%H:%M:%S')
    #sheet.cell(row=int_row_startindex + dt.strptime(i[0],'%d.%m.%Y').day, column=6).value = dt.strptime(i[2],'%H:%M:%S')
    
    #sheet_obj['E6'].value = dt.strptime('08:01:57','%H:%M:%S')
    #sheet_obj['F6'].value = dt.strptime('17:02:54','%H:%M:%S')

    '''
    # iterate worksheet months in timesheet
    for sheet in obj_wb_timesheet.worksheets[0:12]:  
        print(sheet.title)
        for iter_row in sheet.iter_rows(min_row=5, min_col=1, max_row=35, max_col=1):
            #print(iter_row[0].row)
            # iterate rows in month 
            for iter_cell in iter_row:
                if iter_cell.value == obj_date_startpoint:  
                    sheet.cell(row=iter_row[0].row, column=5).value = dt.strptime('08:01:57','%H:%M:%S')
                    sheet.cell(row=iter_row[0].row, column=6).value = dt.strptime('17:02:54','%H:%M:%S')
                    
                    print(iter_cell.value.date(),
                        iter_cell.value.weekday(),
                        iter_cell.value.strftime('%A'))
    '''   

    #print(obj_wb_timesheet.sheetnames)
    #print(sheet_obj.cell(row = 6, column = 1).value)         
        
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