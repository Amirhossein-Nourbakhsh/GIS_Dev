# ----------------------------------------------------------------------------------------
# This script appends all IMAGE_BOUNDARY.shp from USA FIM into individual state footprint feature class.
# CREATED: 20201029
# ----------------------------------------------------------------------------------------

import arcpy
import os
import sys
import re
import xlsxwriter
import xlrd
import traceback

# FILE PARAMETERS
fimdir = r"\\Cabcvan1fpr009\fim_data_usa"
xlsxpath = r"\\cabcvan1gis006\GISData\FIMS_USA\master\MASTER_ALL_STATES.xlsx"
dir = r"\\CABCVAN1FPR009\USA_FIPs\US FIM Footprints\2020_12_08"
gdb = "FIM_US_STATES.gdb"
states = []

# READ XLSX
print(datetime.datetime.now())
print("...read xlsx...")
xlsx = xlrd.open_workbook(xlsxpath)
xlsxsheet = xlsx.sheet_by_index(0)
vnodict = {}
vnamedict = {}

for i in range(1,xlsxsheet.nrows):    
    row = xlsxsheet.row_values(i)
    if row[8].upper() != "Y":               # ENSURE VOLUME IS NOT A DUPLICATE
        volumeno = row[0].upper().strip()
        volumename = row[3].upper().strip()
        state = row[1].upper().strip()

        if volumeno in vnodict: 
            vnodict[volumeno].append(row)
        else:
            vnodict[volumeno] = row

        if volumename in vnamedict:
            vnamedict[volumename].append(row)
        else:
            vnamedict[volumename] = row

        vnodict[volumeno].append(f"\\\\Cabcvan1fpr009\\fim_data_usa\\FIM_DATA_{state}")
        vnamedict[volumename].append(f"\\\\Cabcvan1fpr009\\fim_data_usa\\FIM_DATA_{state}")

# SET ENVIRONMENT
arcpy.env.overwriteOutput = True
arcpy.env.outputMFlag = "Disabled"
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference("WGS 1984")

# CREATE GDB AND FC
print(datetime.datetime.now())
print("...create gdb...")
footprintgdb = os.path.join(dir, gdb)
arcpy.CreateFileGDB_management(dir,gdb)

codeblock = """
def calculate(field):
    if field.split('@')[-1]:
        return (field.split('@')[-1]).zfill(2).upper()
    else:
        return None"""

# FIX & APPEND  IMAGE BOUNDARIES
print(datetime.datetime.now())
print("...create state fc, add fields, fix volume names and append image_boundaries...")
volcnt = 1
footprintfc = ""
state = ""

for (folder, subfolder, files) in os.walk(fimdir):
    # print("-------------")
    # print(folder)
    # print(subfolder)
    # print(files)

    if not any(substr in folder for substr in ["_ARCHIVE", "FIM_DATA_MX"]): #and any(substr in folder for substr in ["FIM_DATA_MO"]):
        if folder.count("\\") == 4:
            state = folder.split("\\")[-1].split("_")[-1].upper().strip()
            footprintfc = os.path.join(footprintgdb,f"FIM_{state}_footprint")
            print(footprintfc)
            arcpy.CreateFeatureclass_management(footprintgdb, f"FIM_{state}_footprint", "POLYGON")

            # ADD FIELDS
            arcpy.AddFields_management(footprintfc, [
                                    ["VOLUMENAME", "TEXT", "VOLUMENAME", 254],
                                    ["IMAGE_NO", "TEXT"],
                                    ["STATE", "TEXT"],
                                    ["CITY", "TEXT"],
                                    ["YEAR", "TEXT"],
                                    ["VOLUME", "TEXT"],
                                    ["VOLUMEPATH", "TEXT", "VOLUMEPATH", 254],
                                    ["VOLUMENO", "TEXT"]
                                ])

        for file in files:
            if file.endswith("IMAGE_BOUNDARY.shp"):
                try:
                    imageboundary = os.path.join(folder, file)
                    volno = folder.split("\\")[-1].strip().upper()
                    
                    if vnodict.get(volno) != None:
                        # FIX VOLUME NAME IN IMAGE_BOUNDARY.shp
                        volname = [row.getValue("VOLUMENAME") for row in arcpy.SearchCursor(imageboundary)][0]
                        fixedvolname = vnodict.get(volno)[3]
                        if volname.upper().strip() != fixedvolname.upper().strip():
                            print("----------")
                            print(folder)
                            print(f"{volname} --to-- {fixedvolname}")
                            arcpy.DeleteField_management(imageboundary, "VOLUMENAME")
                            arcpy.AddField_management(imageboundary, "VOLUMENAME", "TEXT", None, None, 255)
                            arcpy.CalculateField_management(imageboundary, "VOLUMENAME", '"' + fixedvolname + '"')

                        # APPEND IMAGE BOUNDARIES TO FOOTPRINTS
                        arcpy.Append_management(imageboundary, footprintfc, "NO_TEST")
                        volcnt = volcnt + 1

                except Exception as exc:
                    print("----------")
                    print(f"...something wrong: {volno} - {folder}")
                    print(volname)
                    print(f"fixed to: {fixedvolname}")
                    print(vnodict.get(volno))
                    print(traceback.print_exc())
                    raise

# CALCULATE FIELDS IN FOOTPRINTS
print(datetime.datetime.now())
print("...populate fields...")

arcpy.env.workspace = footprintgdb
fclist =  arcpy.ListFeatureClasses()

for fc in fclist:
    # if "FIM_MO_" in fc:
        print(fc)
        footprintcursor = arcpy.UpdateCursor(fc)

        for row in footprintcursor:
            try:
                vname = row.getValue("VOLUMENAME").upper().strip()
                row.setValue("VOLUMENO", vnamedict.get(vname)[0].upper())
                row.setValue("VOLUMEPATH", vnamedict.get(vname)[10].upper())
                footprintcursor.updateRow(row)
            except Exception as exc:
                print("----------")
                vname = row.getValue("VOLUMENAME").upper().strip()
                print(vname)
                print(vnamedict.get(vname))
                print(traceback.print_exc())
                print(arcpy.GetMessages())
                break

        try:
            arcpy.CalculateFields_management(fc, "PYTHON3", [
                                            ["STATE", "(!VOLUMENAME!.split('@')[-4]).upper()"],
                                            ["CITY", "(!VOLUMENAME!.split('@')[-3]).upper()"],
                                            ["YEAR", "(!VOLUMENAME!.split('@')[-2]).upper()"],
                                            ["VOLUME", "calculate(!VOLUMENAME!)"]
                                        ], codeblock)
        except arcpy.ExecuteError:
            print("----------")
            print(arcpy.GetMessages())
            break

print ("==================================================")
print (datetime.datetime.now())
print (volcnt)
print ("DONE")