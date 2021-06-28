#-------------------------------------------------------------------------------
# Purpose:     This script parses FIM related information (e.g. prov, city, year
#              volume, etc..) from the Geosearch folder inventory and exports the 
#              data by state to excel to create a master list of FIMs.
#              The script also creates a "questionable sheet" to note directories that
#              do not meet the pattern specified in the script. Review the script 
#              and make adjustments if needed. 
#-------------------------------------------------------------------------------

import os
import re
import win32com.client as win32

class Metadata_Export_Process():

    def meta_data_extract (self, path):
        """ 
        Obtain the list of directories found in specified path.
        Loop through the list of directories to parse metadata. Parsing depends 
        on folder structure (number of delimiters). 
        Add parsed data to list (parsed_metadata).        
        """ 
        directory_paths = [] 
        for root, directories, files in os.walk(path):
            for item in directories:
                directory = os.path.join(root, item)
                directory_paths.append(directory)

        parsed_metadata = []              # List of parsed file paths to export to excel

        for item in directory_paths:
            delimiter_count = item.count("\\")
            if delimiter_count == 8:
                path = item                                   # \\10.6.246.73\Sanborn\Alaska\Anchorage\1916 C\Volume 2
                prov = item.split("\\",8)[4]                  # Alaska
                city = item.split("\\",8)[5]                  # Anchorage
                year = item.split("\\",8)[6]                  # 1916 C
                vol  = item.split("\\",8)[7]                  # Volume 2
                description = desc_decode(year)               # C - Colour
                sheets = no_of_files(path)                    # Number of files in each subdirectory
                converted_name = city + " " + re.sub(r"C|rev|rep","", year).strip() +"@@@" + prov + "@" + city  + "@" + re.sub(r"C|rev|rep","", year).strip() + "@" + vol_formatted(vol)  #Match ERIS folder naming convention

                parsed_metadata.append({"prov":prov, "city":city, "year":year, "dir_path": path, 'vol': vol, "desc": description, "no_of_files": sheets,
                'converted_name': converted_name, "questionable": ""})

            elif delimiter_count == 7:
                path = item                
                prov = item.split("\\",7)[4]
                city = item.split("\\",7)[5]
                year = item.split("\\",7)[6]
                vol  = item.split("\\",7)[7]
                if vol == "JPEG":
                    vol = ""
                description = desc_decode(year)
                sheets = no_of_files(path)
                converted_name = city + " " + re.sub(r"C|rev|rep","", year).strip() +"@@@" + prov + "@" + city  + "@" + re.sub(r"C|rev|rep","", year).strip() + "@" + vol_formatted(vol)

                parsed_metadata.append({"prov":prov, "city":city, "year":year, "dir_path": path, 'vol': vol, "desc": description, "no_of_files": sheets,
                'converted_name': converted_name, "questionable": ""})

            elif delimiter_count == 6:
                path = item 
                prov = item.split("\\",6)[4]
                city = item.split("\\",6)[5]
                year = item.split("\\",6)[6]
                vol  = vol_parse(year)
                description = desc_decode(year)
                sheets = no_of_files(path)  
                converted_name = city + " " + re.sub(r"C|rev|rep","", year).strip() +"@@@" + prov + "@" + city  + "@" + re.sub(r"C|rev|rep","", year).strip() + "@" + vol_formatted(vol)

                parsed_metadata.append({"prov":prov, "city":city, "year":year, "dir_path": path, 'vol': vol, "desc": description, "no_of_files": sheets,
                'converted_name': converted_name, "questionable": ""})

            elif delimiter_count == 5:
                path = item        
                prov = item.split("\\",5)[4]
                city = item.split("\\",5)[5]
                year = re.findall(r"\d+", city)
                vol  = vol_parse(year)
                description = desc_decode(year)
                sheets = no_of_files(path)  
                converted_name = city + " " +"@@@" + prov + "@" + city  + "@" + re.sub(r"\[|\]|'", "",str(year)) + "@" + vol_formatted(vol)  

                if len(year) > 0:
                    parsed_metadata.append({"prov":prov, "city":city, "year":year, "dir_path": path, 'vol': vol, "desc": description, "no_of_files": sheets,
                    'converted_name': converted_name, "questionable": ""})
                # else:
                #     questionable_path = item                    
                #     parsed_metadata.append({"prov":"", "city":"", "year":"", "dir_path": "", 'vol': "", "desc": "", "no_of_files": "",
                #     'converted_name': "", "questionable": questionable_path}) 

            
            #Some FIMs might not have a regular pattern, set these paths to a questionable list for manual verification
            else:
                questionable_path = item
 
                parsed_metadata.append({"prov":"", "city":"", "year":"", "dir_path": "", 'vol': "", "desc": "", "no_of_files": "",
                'converted_name': "", "questionable": questionable_path}) 

        return parsed_metadata
            
    def createxlsx(self, outxlsx, metadata_dict):
        """
        Export parsed metadata to excel
        outxlsx: output excel file
        metadata_dict: dictionary of metadata to be exported to output file
    
        """
        #Open excel application
        excel = win32.Dispatch("Excel.Application")
        excel.Visible = 1    
        if os.path.exists(outxlsx):
            wb = excel.Workbooks.Open(outxlsx)   
        else: 
            wb = excel.Workbooks.Add()  
            wb = excel.ActiveWorkbook.SaveAs(Filename=outxlsx)      

        #Create new worksheets per state
        ws1 = wb.Sheets.Add(Before = None , After = wb.Sheets(excel.Sheets.count))
        ws1.Name = province
        ws2 = wb.Sheets.Add(Before = None , After = wb.Sheets(excel.Sheets.count))
        ws2.Name = province + " - Questionable"
                                                
        # Add table headers to Sheet1 (ws1)
        ws1.Cells(1,1).Value = "Province"
        ws1.Cells(1,2).Value = "City"                                                    
        ws1.Cells(1,3).Value = "Year"  
        ws1.Cells(1,4).Value = "Volume"         
        ws1.Cells(1,5).Value = "Vol_Year"                                         
        ws1.Cells(1,6).Value = "No of Sheets"                                             
        ws1.Cells(1,7).Value = "Description"
        ws1.Cells(1,8).Value = "Converted Name"
        ws1.Cells(1,9).Value = "Missing year"
        ws1.Cells(1,10).Value = "Missing sheet"
        ws1.Cells(1,11).Value = "Colour"
        ws1.Cells(1,12).Value = "GS better quality"
        ws1.Cells(1,13).Value = "Additional Comments"
        ws1.Cells(1,14).Value = "Path"
            
        # Loop through each dictionary item in metadata_dict to put data into excel
        row = 2
        for item in metadata_dict:                                                    
            ws1.Cells(row,1).Value = item["prov"]                                 
            ws1.Cells(row,2).Value = item["city"]                                              
            ws1.Cells(row,3).Value = item["year"]   
            ws1.Cells(row,4).Value = item["vol"]     
            # ws1.Cells(row,5).Value = item["vol_year"]                                          
            ws1.Cells(row,6).Value = item["no_of_files"]
            ws1.Cells(row,7).Value = item["desc"]
            ws1.Cells(row,8).Value = item["converted_name"]
            ws1.Cells(row,14).Value = item["dir_path"]
            row +=1

        #Format excel sheet
        #Autofit field length
        ws1.Columns.AutoFit()

        #Left justify fields
        ws1.Cells.HorizontalAlignment = -4131

        #Bold headers
        i=1
        for i in range(1,15):
            ws1.Cells(1,i).Font.Bold = True
            i += 1

        # Add table headers to Sheet2 (Questionable)
        ws2.Cells(1,1).Value = "Path"

        # Loop through each dictionary item in metadata_dict to put data into excel
        row = 2
        for item in metadata_dict:                                                    
            ws2.Cells(row,1).Value = item["questionable"]                                 
            row +=1                                                             

        #Format excel sheet
        #Autofit field length
        ws2.Columns.AutoFit()

        # Bold header names
        i=1
        for i in range(1,2):
            ws2.Cells(1,i).Font.Bold = True
            i += 1


def desc_decode(descriptor):
    """ For some parsed paths, the year field may have descriptors such as "C", "rev" and "rep"
        e.g. 1946 C
        Decode descriptors to describe condition of FIM
        C:   Colour
        rev: Revised
        rep: Reprinted

        This function first decodes the descriptors and then uses a regular expression
        to parse non-numerical values to remove year info from the string 
    """
    if " rev" in descriptor:
        description = descriptor.replace(" rev", "Revised")
        description = re.findall(r"\D+", description)
    elif " C" in descriptor: 
        description = descriptor.replace(" C", "Colour")
        description = re.findall(r"\D+", description)
    elif " rep" in descriptor:
        description = descriptor.replace(" rep", "Reprinted")
        description = re.findall(r"\D+", description)
    else:
        description = ""
    return description

def vol_parse(year):
    """In some cases, the year field may have the volume information included (e.g. 1946 Vol 1) 
       Parse volume information from year
    """
    if "Vol 1" in year:
        vol_parse = "Vol 1"
    else:
        vol_parse = ""
    return vol_parse

def vol_formatted(vol):
    """This function formats volume to match ERIS FIM naming convention to only have the volume number
    For instance, Volume 2 is listed as @2 at the end. See below.
    Borough Of Richmond 1917 Volume 2@@@New York@Borough of Richmond@1917@2

    This function cleans out different variations of Volume and only takes the number 
    """
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

def no_of_files(file_path):
    """Count number of files in each directory (file_path) 
    """
    no_of_files = 0
    for root, directories, files in os.walk(file_path):
        files[:] = [f for f in files if f not in ["Thumbs.db"]]
        for item in files:
            sheet_path = os.path.join(root, item)
            if os.path.isfile(sheet_path):
                no_of_files += 1
    return no_of_files


# ===============================================================================================================
if __name__ == '__main__':

    province = "Hawaii"    #Change prov 
    path = os.path.join(r"\\10.6.246.73\Sanborn", province)
    outxlsx = r"\\10.6.246.73\Sanborn\GSFIM_Parsed_Metadata.xlsx"

    metadata_export = Metadata_Export_Process()
    print "...Extracting metadata for the state of " + province
    metadata_dict = metadata_export.meta_data_extract (path)
    metadata_export.createxlsx(outxlsx, metadata_dict)
    print "...Process finished - parsed data exported to Excel"
    
# ===============================================================================================================




