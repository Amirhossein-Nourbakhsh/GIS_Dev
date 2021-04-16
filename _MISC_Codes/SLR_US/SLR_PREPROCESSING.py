import arcpy
import datetime
import os
import traceback
import zipfile

# FOLDERS TO UPDATE/CREATE
folder = r"\\cabcvan1gis005\MISC_DataManagement\Data\US\_FED\SLR\2020_09_01"
raw = "_RAW"
unzip = "_UNZIP"

# OTHER PARAMETERS
gdb = "SLR.gdb"
gdb_final = "SLR_final2.gdb"
buff_dist = "1 Meters"

# # UNZIP FILES
# print("==============================")
# print(datetime.datetime.now())
# print("...unzipping files...")
# for zip in os.listdir(os.path.join(folder, raw)):
#     print(zip)
#     with zipfile.ZipFile(os.path.join(folder, raw, zip), 'r') as zip_ref:
#         zip_ref.extractall(os.path.join(folder, unzip))

# SET ENVIRONMENT
arcpy.env.overwriteOutput = True
arcpy.env.outputMFlag = "Disabled"
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference("WGS 1984")

# # CREATE GDB
# arcpy.CreateFileGDB_management(folder,gdb)
arcpy.CreateFileGDB_management(folder,gdb_final)

# # ADD FIELD AND CREATE DICTIONARY TO ORGANIZE DATA
# keyslr = "slr_%sft"
# keylow = "low_%sft"
# slrdict = {}
# print("==============================")
# for wgdb in os.listdir(os.path.join(folder, unzip)):
#     if wgdb.endswith(".gdb"):
#         arcpy.env.workspace = os.path.join(folder, unzip, wgdb)
#         fclist =  arcpy.ListFeatureClasses()
        
#         for fc in fclist:
#             print("------------------------------")
#             # # REPAIR GEOMETRY              
#             # print ("...repairing geometry...")
#             # print (datetime.datetime.now())
#             # try:
#             #     arcpy.CheckGeometry_management(fc, os.path.join(folder,str(fc) + "_CheckGeometry"))
#             #     arcpy.RepairGeometry_management(fc, "DELETE_NULL")

#             # ADD FIELD AND FEATURE CLASS NAME, EASIER FOR QA
#             print(datetime.datetime.now())
#             print("...adding fcname field...")
#             arcpy.AddField_management(os.path.join(folder, unzip, wgdb, fc), "ERIS_FC_NAME", "TEXT")
#             arcpy.MakeFeatureLayer_management(fc, "fc")
#             arcpy.CalculateField_management("fc", "ERIS_FC_NAME", "'" + str(fc) + "'", "PYTHON3")

#             # CREATE DICT
#             print(datetime.datetime.now())
#             print("...creating dict...")
#             for i in range(0,11):                 # FOR ALL DEPTHS 0FT-10FT
#                 if keyslr%i in fc:
#                     if keyslr%i in slrdict:       # APPEND VALUE TO KEY
#                         slrdict[keyslr%i].append(os.path.join(folder, unzip, wgdb, fc))
#                     else:                         # ADD NEW {KEY: VALUE}
#                         slrdict[keyslr%i] = [os.path.join(folder, unzip, wgdb, fc)]
#                 elif keylow%i in fc:
#                     if keylow%i in slrdict:
#                         slrdict[keylow%i].append(os.path.join(folder, unzip, wgdb, fc))
#                     else:
#                         slrdict[keylow%i] = [os.path.join(folder, unzip, wgdb, fc)]                    

# # MERGE ORGANIZED DATA
# print("==============================")
# for key, values in slrdict.items():
#     fc_merge = os.path.join(folder,gdb,key)

#     print("------------------------------")
#     print(datetime.datetime.now())
#     print("...merging...")
#     print(key)
#     arcpy.Merge_management(values, os.path.join(folder,gdb,key))

#     # EDIT FIELDS
#     print (datetime.datetime.now())
#     print ("...merging grid fields...")
#     arcpy.AddField_management(os.path.join(folder,gdb,key), "GRID_CODE_MERGE", "TEXT")
#     fieldList = arcpy.ListFields(fc_merge)
#     for field in fieldList:
#         if "GRID" in str(field.name.upper()) and "GRID_CODE_MERGE" not in str(field.name.upper()):
#             print (str(field.name))
#             arcpy.MakeFeatureLayer_management(fc_merge, "FC_MERGE_LYR", str(field.name) + " IS NOT NULL")
#             # arcpy.CalculateField_management("FC_MERGE_LYR", "GRID_CODE_MERGE", "[" + str(field.name) + "]")   #FOR PYTHON 2.7
#             arcpy.CalculateField_management("FC_MERGE_LYR", "GRID_CODE_MERGE", "!" + str(field.name) + "!", "PYTHON3")
#             arcpy.DeleteField_management(fc_merge, str(field.name))

# BUFFER/DISSOLVE FEATURES
print("==============================")
arcpy.env.workspace = os.path.join(folder, gdb)
fclist =  arcpy.ListFeatureClasses()

for fc in fclist:
    fc_merge = os.path.join(folder,gdb,fc)
    fc_buff = os.path.join(folder,gdb_final,fc + "_buffer")
    fc_final = os.path.join(folder,gdb_final,fc)


    print("------------------------------")
    try:
        print (datetime.datetime.now())
        print ("...buffering/dissolving...")
        print(fc)
        # arcpy.Buffer_analysis(fc_dissolve, fc_buff, buff_dist)#, None, None, "ALL") # FOR PYTHON 2.7
        arcpy.PairwiseBuffer_analysis(fc_merge, fc_final, buff_dist, "ALL")
    except Exception as exc:
        print(traceback.print_exc())
        try:
            print (datetime.datetime.now())
            print ("...buffer/dissolve failed...try buffering only...")
            # arcpy.Buffer_analysis(fc_dissolve, fc_buff, buff_dist) #FOR PYTHON 2.7
            arcpy.PairwiseBuffer_analysis(fc_merge, fc_buff, buff_dist)

            print (datetime.datetime.now())
            print ("...dissolving only...")
            # arcpy.Dissolve_management(in_features=fc_merge, out_feature_class=fc_dissolve, dissolve_field="", statistics_fields="", multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")  #FOR PYTHON 2.7. NOT WORKING PROPERLY, OUTPUT FROM THE SCRIPT IS NOT DISSOLVED PROPERLY EVEN THOUGH MANUAL DISSOLVE ON ARCMAP WORKS FINE.
            arcpy.PairwiseDissolve_analysis(fc_buff,fc_final)

            arcpy.DeleteFeatures_management(fc_buff)
        except:
            print("...failed again...skip to next fc instead.")

# # SIMPLIFY POLYGON
# print ("...Starting SIMPLIFY POLYGON geoprocessing tool.")
# print (datetime.datetime.now())
# arcpy.SimplifyPolygon_cartography(FC_MERGE,FC_SIMPLIFY,"POINT_REMOVE", "1 Meters",0, "RESOLVE_ERRORS")
# arcpy.SmoothPolygon_cartography(FC_SIMPLIFY,"PAEK","1 Meters")
    
print ("==================================================")
print (datetime.datetime.now())
print ("DONE")