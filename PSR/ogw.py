from imp import reload
import arcpy, os, sys
import timeit
import shutil
import psr_utility as utility
import psr_config as config
sys.path.insert(1,os.path.join(os.getcwd(),'DB_Framework'))
reload(sys)
import models
def generate_ogw_report(order_obj):
    arcpy.AddMessage('  -- Start generating PSR Oil, Gas and Water wells map report...')
    start = timeit.default_timer() 
    ### set scratch folder
    arcpy.env.workspace = config.scratch_folder
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage('      - scratch folder: %s' % config.scratch_folder)
    # find centre point(s) of order geometry
    in_rows = arcpy.SearchCursor(config.order_geometry_pcs_shp)
    point = arcpy.Point()
    array = arcpy.Array()
    feature_list = []
    arcpy.CreateFeatureclass_management(config.scratch_folder, os.path.basename(config.order_centre_point_pcs), "POINT", "", "DISABLED", "DISABLED", config.spatial_ref_pcs)
    cursor = arcpy.InsertCursor(config.order_centre_point_pcs)
    feat = cursor.newRow()
    for in_row in in_rows:
        # Set X and Y for start and end points
        point.X = in_row.xCenUTM
        point.Y = in_row.yCenUTM
        array.add(point)

        centerpoint = arcpy.Multipoint(array)
        array.removeAll()
        feature_list.append(centerpoint)
        feat.shape = point
        cursor.insertRow(feat)
    arcpy.AddField_management(config.order_centre_point_pcs, "Lon_X", "DOUBLE", "12", "6", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(config.order_centre_point_pcs, "Lat_Y", "DOUBLE", "12", "6", "", "", "NULLABLE", "NON_REQUIRED", "")
    del feat
    del cursor
    del in_row
    del in_rows
    del point
    del array
    # prepare for elevation calculation
    arcpy.CalculateField_management(config.order_centre_point_pcs, 'Lon_X', Lon_X, "PYTHON_9.3", "")
    arcpy.CalculateField_management(config.order_centre_point_pcs, 'Lat_Y', Lat_Y, "PYTHON_9.3", "")
    # arcpy.ImportToolbox(PSR_config.tbx)
    # orderCentreSHP = getElevation(orderCentreSHP,["Lon_X","Lat_Y","Id"])##orderCentreSHP = arcpy.inhouseElevation_ERIS(orderCentreSHP).getOutput(0)
    # Call_Google = ''
    # rows = arcpy.SearchCursor(orderCentreSHP)
    # for row in rows:
    #     if row.Elevation == -999:
    #         Call_Google = 'YES'
    #         break
    #     else:
    #         print row.Elevation
    # del row
    # del rows

    
    
    end = timeit.default_timer()
    arcpy.AddMessage((' -- End generating PSR Oil, Gas and Water wells report. Duration:', round(end -start,4)))