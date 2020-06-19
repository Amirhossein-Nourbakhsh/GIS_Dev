#-------------------------------------------------------------------------------
# Name:        Extract_Footprint.py
# Purpose:     Create seamless map of Mosaic US imagery
# Author:      Hamid Kiavarz
# Created:     06/2020
#-------------------------------------------------------------------------------
import arcpy, os ,timeit
import cx_Oracle
import json
from arcpy.sa import *
import pandas as pd
arcpy.CheckOutExtension("Spatial")

if __name__ == '__main__':
    
    # raster_Folder = r'\\cabcvan1nas003\doqq\osa\AK\FAIRBANKS NORTH STAR\2006'
    # raster_Folder = r'\\cabcvan1nas003\doqq\osa\CA\Los Angeles\2009'
    
    # raster_Folder = r'C:\Users\HKiavarz\AppData\Local\Temp\scratch'
    ws =  arcpy.env.scratchFolder
    arcpy.env.workspace = ws
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage(ws)

    try:
        inputRaster = arcpy.GetParameterAsText(0)
        arcpy.AddMessage(inputRaster)
        tmpGDB =os.path.join(ws,r"temp.gdb")
        if not os.path.exists(tmpGDB):
            arcpy.CreateFileGDB_management(ws,r"temp.gdb")
        # inputRaster = 'ortho_e1-1_s_nc171.sid'
        # rasterName = 'ortho_1-2_1n_s_ca037_2009_1.sid'
        # rasterName = 'ortho1-1_1n_s_ak090_2006.sid'
        # inputRaster= os.path.join(raster_Folder,rasterName)
        inputSR = arcpy.Describe(inputRaster).spatialReference
        resampleRaster = os.path.join(ws,'resample.tif')
        bin_Raster = os.path.join(ws,'bin_Raster.tif')
        outputpolygon_with_holes= os.path.join(tmpGDB,'polygon_with_holes')
        out_Vertices = os.path.join(tmpGDB,'Out_Vertices')
        

        arcpy.AddMessage('Start resampling the input raster...')
        start1 = timeit.default_timer()
        rasterProp = arcpy.GetRasterProperties_management(inputRaster, "CELLSIZEX")
        # int(str(rasterProp))*4
        resample = arcpy.Resample_management(inputRaster,resampleRaster ,4, "NEAREST")
        end1 = timeit.default_timer()
        arcpy.AddMessage(('End resampling the input raster. Duration:', round(end1 -start1,4)))
        
 
        arcpy.AddMessage('Start creating binary raster (Raster Calculator)...')
        start2 = timeit.default_timer()
        expression = 'Con(' + '"' + 'resample.tif' + '"' + ' >= 10 , 1)'
        arcpy.AddMessage(bin_Raster)
        bin_Raster = arcpy.gp.RasterCalculator_sa(expression, bin_Raster)
       
        end2 = timeit.default_timer()
        arcpy.AddMessage(('End creating binary raster. Duration:', round(end2 -start2,4)))

        ## Convert binary raster to polygon       
        arcpy.AddMessage('Start creating prime polygon from raster...')
        start3 = timeit.default_timer()       
        outputpolygon_with_holes = arcpy.RasterToPolygon_conversion(in_raster= bin_Raster, out_polygon_features=outputpolygon_with_holes, simplify="SIMPLIFY", raster_field="Value", create_multipart_features="SINGLE_OUTER_PART", max_vertices_per_feature="")
        end3 = timeit.default_timer()
        arcpy.AddMessage(('End creating polygon. Duration:', round(end3 -start3,4)))


        arcpy.AddMessage('Start extracting exterior ring (outer outline) of polygon...')
        start4 = timeit.default_timer()      
        sql_clause = (None, 'ORDER BY Shape_Area DESC')
        geom = arcpy.Geometry()
        row = arcpy.da.SearchCursor(outputpolygon_with_holes,('SHAPE@'),None,None,False,sql_clause).next()
        geom = row[0]
        end4 = timeit.default_timer()
        arcpy.AddMessage(('End extracting polygon. Duration:', round(end4 -start4,4)))
        
        
        arcpy.AddMessage('Start extracting exterior points...')
        start5 = timeit.default_timer()      
        outer_coords = []
        for island in geom.getPart():
            arcpy.AddMessage("Vertices in island: {0}".format(island.count))
            for point in island:
                # coords.append = (point.X,point.Y)
                if not isinstance(point, type(None)):
                    newPoint = (point.X,point.Y)
                    if len(outer_coords) == 0:
                        outer_coords.append(newPoint)
                    elif not newPoint == outer_coords[0]:   
                        outer_coords.append((newPoint))
                    elif len(outer_coords) > 50:
                        outer_coords.append((newPoint))
                        break
        
        # points_FC = arcpy.CreateFeatureclass_management(tmpGDB,"points_FC", "POINT", "", "DISABLED", "DISABLED", inputSR)
        # i = 0
        # with arcpy.da.InsertCursor(points_FC,["SHAPE@XY"]) as cursor: 
        #     for coord in outer_coords:
        #         cursor.insertRow([coord]) 
        #         i+= 1
        #         if i > 2:
        #             break       
        #     del cursor
        
        ### Create footprint  featureclass -- > polygon 
        footprint_FC = arcpy.CreateFeatureclass_management(tmpGDB,"footprint_FC", "POLYGON", "", "DISABLED", "DISABLED", inputSR)
        cursor = arcpy.da.InsertCursor(footprint_FC, ['SHAPE@'])
        cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in outer_coords]),inputSR)])
        del cursor
        end5 = timeit.default_timer()
        arcpy.AddMessage(('End extracting exterior points. Duration:', round(end5 -start5,4)))
        
        
        
        arcpy.AddMessage('Start simplifying footprint polygon...')
        start6 = timeit.default_timer() 
        arcpy.Generalize_edit(footprint_FC, '100 Meter')
        end6 = timeit.default_timer()
        arcpy.AddMessage(('End simplifying footprint polygon. Duration:', round(end6 -start6,4)))
    except:
        msgs = "ArcPy ERRORS:\n %s\n"%arcpy.GetMessages(2)
        arcpy.AddError(msgs)
        raise