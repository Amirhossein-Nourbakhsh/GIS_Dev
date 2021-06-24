#-------------------------------------------------------------------------------
# Purpose:     This script parses FIM related information (e.g. prov, city, year
#              volume, etc..) from the Geosearch folder inventory and exports the 
#              data by state to excel to create a master list of FIMs.
#              The script also creates a "questionable sheet" to note directories that
#              do not meet the pattern specifid in the script. Review the script 
#              and make adjustments if needed. 
#-------------------------------------------------------------------------------

def desc_decode(code):
    # Decode Geosearch codes to describe condition of FIM
    if " rev" in code:
        description = code.replace(" rev", "Revised")
        description = re.findall(r"\D+", description)
    elif " C" in code: 
        description = code.replace(" C", "Colour")
        description = re.findall(r"\D+", description)
    elif " rep" in code:
        description = code.replace(" rep", "Reprinted")
        description = re.findall(r"\D+", description)
    else:
        description = ""
    return description

def vol_parse(year):
    #Some years may have Vol 1 attached, parse vol from year
    if "Vol 1" in year:
        vol_parse = "Vol 1"
    else:
        vol_parse = ""
    return vol_parse

def vol_formatted(vol):
    #Format volume to match ERIS naming convention
    if "Volume." in vol:
        vol_cleaned = vol.split("Volume. ",1)[1]
    elif "Volume" in vol:
        vol_cleaned = vol.split("Volume ",1)[1]
    elif "Vol." in vol:
        vol_cleaned = vol.split("Vol. ",1)[1]
    elif "Vol" in vol:
        vol_cleaned = vol.split("Vol ",1)[1]
    else:
        vol_cleaned = vol
        
    if vol_cleaned.count(" ") > 0:
        vol_cleaned = vol_cleaned.split(" ",1)[0]
    else:
        vol_cleaned = vol_cleaned
    return vol_cleaned

def no_of_sheets(file_path):
    #Count number of sheets in each directory
    no_of_sheets = 0
    for root, directories, files in os.walk(file_path):
        files[:] = [f for f in files if f not in ["Thumbs.db"]]
        for item in files:
            sheet_path = os.path.join(root, item)
            if os.path.isfile(sheet_path):
                no_of_sheets += 1
    return no_of_sheets


import os
import urllib
import re
import win32com.client as win32


province = "Iowa"    #Change prov 
gs_path = (r"\\10.6.246.73\Sanborn")
path = os.path.join(gs_path, province)

#Loop through path to obtain list of filepaths
file_paths = [] 
for root, directories, files in os.walk(path):
    for item in directories:
        filepath = os.path.join(root, item)
        file_paths.append(filepath)

#Loop through the list of filepaths to parse metadata and append data to a dictionary
resultlist = []              # List of parsed filepaths to export to excel
resultlist_questionable = [] #List of questionable paths to be manually verified

for item in file_paths:
    delimiter_count = item.count("\\")
    if delimiter_count == 8:
        path = item                                   # \\10.6.246.73\Sanborn\Alaska\Anchorage\1916 C\Volume 2
        prov = item.split("\\",8)[4]                  # Alaska
        city = item.split("\\",8)[5]                  # Anchorage
        year = item.split("\\",8)[6]                  # 1916 C
        vol  = item.split("\\",8)[7]                  # Volume 2
        description = desc_decode(year)               # C - Colour
        sheets = no_of_sheets(path)                   # Number of files in each subdirectory
        vol_for_converted_name = vol_formatted(vol)   # 2
        year_for_converted_name = year.replace(" C","")
        converted_name = city + " " + year +"@@@" + prov + "@" + city  + "@" + year_for_converted_name + "@" + vol_for_converted_name  #Match ERIS folder naming convention

        resultlist.append({"prov":prov, "city":city, "year":year, "dir_path": path, 'vol': vol, "desc": description, "no_of_sheets": sheets,
        'converted_name': converted_name}) 

    elif delimiter_count == 7:
        path = item                
        prov = item.split("\\",7)[4]
        city = item.split("\\",7)[5]
        year = item.split("\\",7)[6]
        vol  = item.split("\\",7)[7]
        if vol == "JPEG":
            vol = ""
        description = desc_decode(year)
        sheets = no_of_sheets(path)
        vol_for_converted_name = vol_formatted(vol)
        year_for_converted_name = year.replace(" C","")
        converted_name = city + " " + year +"@@@" + prov + "@" + city  + "@" + year_for_converted_name + "@" + vol_for_converted_name 

        resultlist.append({"prov":prov, "city":city, "year":year, "dir_path": path, 'vol': vol, "desc": description, "no_of_sheets": sheets,
        'converted_name': converted_name}) 

    elif delimiter_count == 6:
        path = item 
        prov = item.split("\\",6)[4]
        city = item.split("\\",6)[5]
        year = item.split("\\",6)[6]
        vol  = vol_parse(year)
        description = desc_decode(year)
        sheets = no_of_sheets(path)  
        vol_for_converted_name = vol_formatted(vol)
        year_for_converted_name = year.replace(" C","")
        converted_name = city + " " + year +"@@@" + prov + "@" + city  + "@" + year_for_converted_name + "@" + vol_for_converted_name  

        resultlist.append({"prov":prov, "city":city, "year":year, "dir_path": path, 'vol': vol, "desc": description, "no_of_sheets": sheets,
        'converted_name': converted_name}) 

    elif delimiter_count == 5:
        path = item        
        prov = item.split("\\",5)[4]
        city = item.split("\\",5)[5]
        year = re.findall(r"\d+", city)
        vol  = vol_parse(year)
        description = desc_decode(year)
        sheets = no_of_sheets(path)  
        vol_for_converted_name = vol_formatted(vol)
        converted_name = city + " " + str(year) +"@@@" + prov + "@" + city  + "@" + str(year) + "@" + vol_for_converted_name  

        if len(year) > 0:
            resultlist.append({"prov":prov, "city":city, "year":year, "dir_path": path, 'vol': vol, "desc": description, "no_of_sheets": sheets,
            'converted_name': converted_name}) 
    
    #Some FIMS might not have a regular pattern, set these paths to a questionable list for manual verification
    else:
        path = item

        resultlist_questionable.append({"dir_path": path})
           

# Export data to excel 
# Get application object
excel = win32.Dispatch("Excel.Application")
excel.Visible = 1    
if os.path.exists(r"C:\Users\czhou\Documents\GEOSEARCH\FIM\Geosearch_Fim.xlsx"):
    excel = excel.Workbooks.Open(r"C:\Users\czhou\Documents\GEOSEARCH\FIM\Geosearch_Fim.xlsx")   
else: 
    excel.Workbooks.Add()  
    excel.ActiveWorkbook.SaveAs(Filename=r"C:\Users\czhou\Documents\GEOSEARCH\FIM\Geosearch_Fim.xlsx")      

#Create new worksheets per state

sheet1 = excel.Sheets.Add(Before = None , After = excel.Sheets(excel.Sheets.count))
sheet1.Name = province
sheet2 = excel.Sheets.Add(Before = None , After = excel.Sheets(excel.Sheets.count))
sheet2.Name = province + " - Questionable"
                                           
# Add table headers to Sheet1
sheet1.Cells(1,1).Value = "Province"
sheet1.Cells(1,2).Value = "City"                                                    
sheet1.Cells(1,3).Value = "Year"  
sheet1.Cells(1,4).Value = "Volume"         
sheet1.Cells(1,5).Value = "Vol_Year"                                         
sheet1.Cells(1,6).Value = "No of Sheets"                                             
sheet1.Cells(1,7).Value = "Description"
sheet1.Cells(1,8).Value = "Converted Name"
sheet1.Cells(1,9).Value = "Missing year"
sheet1.Cells(1,10).Value = "Missing sheet"
sheet1.Cells(1,11).Value = "Colour"
sheet1.Cells(1,12).Value = "GS better quality"
sheet1.Cells(1,13).Value = "Additional Comments"
sheet1.Cells(1,14).Value = "Path"

    
# Loop through each dictionary item in resultlist to put data into excel
row = 2
for item in resultlist:                                                    
    sheet1.Cells(row,1).Value = item["prov"]                                 
    sheet1.Cells(row,2).Value = item["city"]                                              
    sheet1.Cells(row,3).Value = item["year"]   
    sheet1.Cells(row,4).Value = item["vol"]     
    # sheet1.Cells(row,5).Value = item["vol_year"]                                          
    sheet1.Cells(row,6).Value = item["no_of_sheets"]
    sheet1.Cells(row,7).Value = item["desc"]
    sheet1.Cells(row,8).Value = item["converted_name"]
    sheet1.Cells(row,13).Value = item["dir_path"]
    row +=1

#Format excel sheet
#Autofit field length
sheet1.Columns.AutoFit()

#Left justify fields
sheet1.Cells.HorizontalAlignment = -4131

#Bold headers
i=1
for i in range(1,15):
    sheet1.Cells(1,i).Font.Bold = True
    i += 1
   
# Add table headers to Sheet2 (Questionable)
sheet2.Cells(1,1).Value = "Path"

# Loop through each dictionary item in resultlist_questionable to put data into excel
row = 2
for item in resultlist_questionable:                                                    
    sheet2.Cells(row,1).Value = item["dir_path"]                                 
    row +=1                                                             

#Format excel sheet
#Autofit field length
sheet2.Columns.AutoFit()

# Bold header names
i=1
for i in range(1,2):
    sheet2.Cells(1,i).Font.Bold = True
    i += 1

#Save excel file
#excel.ActiveWorkbook.Save()

