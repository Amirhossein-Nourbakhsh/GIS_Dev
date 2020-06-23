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
import re
from multiprocessing import Pool

arcpy.CheckOutExtension("Spatial")

def get_year(filename,netpath):
    for parse in re.split("\s|(?<!\d)[,.](?!\d)|\\\| |_|\.|\-",netpath):
        if len(parse) == 4 and unicode(parse,'utf-8').isnumeric() and '19' in parse:
            return parse
            break
        else:
            for parse in filename.split('_'):
                if len(parse) == 2 and unicode(parse,'utf-8').isnumeric():
                    if parse in ['00','01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','16','17','18','19']:
                        return '20'+parse
                        break
                    else:
                        return '19'+parse
                        break
def get_Footprint(inputRaster):
    try:
        ws = arcpy.env.scratchFolder
        arcpy.env.workspace = ws
        arcpy.env.overwriteOutput = True   
        tmpGDB =os.path.join(ws,r"temp.gdb")
        if not os.path.exists(tmpGDB):
            arcpy.CreateFileGDB_management(ws,r"temp.gdb")
        arcpy.AddMessage(inputRaster[0])

        resampleRaster = os.path.join(ws,'resample' + inputRaster[1] + '.tif')
        bin_Raster = os.path.join(ws,'bin_Raster' + inputRaster[1] + '.tif')
        outputpolygon_with_holes= os.path.join(tmpGDB,'polygon_with_holes_'+ inputRaster[1])
        out_Vertices = os.path.join(tmpGDB,'Out_Vertices')
        

        arcpy.AddMessage('Start resampling the input raster...')
        start1 = timeit.default_timer()
        print(resampleRaster)
        rasterProp = arcpy.GetRasterProperties_management(inputRaster[0], "CELLSIZEX")
        resample = arcpy.Resample_management(inputRaster[0],resampleRaster ,4, "NEAREST")
        inputSR = arcpy.Describe(resampleRaster).spatialReference
        end1 = timeit.default_timer()
        arcpy.AddMessage(('End resampling the input raster. Duration:', round(end1 -start1,4)))
        
 
        arcpy.AddMessage('Start creating binary raster (Raster Calculator)...')
        start2 = timeit.default_timer()
        expression = 'Con(' + '"' + 'resample' + inputRaster[1] + '.tif' + '"' + ' >= 10 , 1)'
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
        
        
        arcpy.AddMessage('Start extracting exterior points and inserting as FC...')
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
        
        # # points_FC = arcpy.CreateFeatureclass_management(tmpGDB,"points_FC", "POINT", "", "DISABLED", "DISABLED", inputSR)
        # # i = 0
        # # with arcpy.da.InsertCursor(points_FC,["SHAPE@XY"]) as cursor: 
        # #     for coord in outer_coords:
        # #         cursor.insertRow([coord]) 
        # #         i+= 1
        # #         if i > 2:
        # #             break       
        # #     del cursor
        
        ### Create footprint  featureclass -- > polygon 
        footprint_FC = arcpy.CreateFeatureclass_management(tmpGDB,"footprint_FC_" + inputRaster[1], "POLYGON", "", "DISABLED", "DISABLED", inputSR)
        cursor = arcpy.da.InsertCursor(footprint_FC, ['SHAPE@'])
        cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in outer_coords]),inputSR)])
        del cursor
        end5 = timeit.default_timer()
        arcpy.AddMessage(('End extracting exterior points and inserted as FC. Duration:', round(end5 -start5,4)))
        
        
        
        arcpy.AddMessage('Start simplifying footprint polygon...')
        start6 = timeit.default_timer() 
        arcpy.Generalize_edit(footprint_FC, '100 Meter')
        end6 = timeit.default_timer()
        arcpy.AddMessage(('End simplifying footprint polygon. Duration:', round(end6 -start6,4)))
    except:
        msgs = "ArcPy ERRORS:\n %s\n"%arcpy.GetMessages(2)
        arcpy.AddError(msgs)
        raise

if __name__ == '__main__':
    
    ws =  arcpy.env.scratchFolder
    arcpy.env.workspace = ws
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage(ws)
    inputRaster = arcpy.GetParameterAsText(0)
    footprint_FC = r'F:\Aerial_US\USImagery\Data\Seamless_Map.gdb\Aerial_Footprint_Mosaic'
    
    startTotal = timeit.default_timer()
    
    params = [[r'\\cabcvan1nas003\doqq\201x\MA\BARNSTABLE\2014\ortho_1-1_1n_s_ma001_2014_1.sid', 'a'],[r'\\cabcvan1nas003\doqq\201x\MA\FRANKLIN\2014\ortho_1-1_1n_s_ma011_2014_1.sid','b']]
    pool = Pool(processes=2)
    pool.map(get_Footprint, params)
    # get_Footprint(r'\\cabcvan1nas003\doqq\201x\MA\BARNSTABLE\2014\ortho_1-1_1n_s_ma001_2014_1.sid')
    # year = get_year('ortho_1-1_1n_s_ma003_2014_1','\\nas2520\doqq\201x\MA\BERKSHIRE\2014\ortho_1-1_1n_s_ma003_2014_1.TAB')
    pool.close()
    
    endTotal= timeit.default_timer()
    arcpy.AddMessage(('Total Duration:', round(endTotal -startTotal,4)))
    
    
    