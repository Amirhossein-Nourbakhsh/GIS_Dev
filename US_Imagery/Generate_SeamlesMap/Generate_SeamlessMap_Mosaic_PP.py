#-------------------------------------------------------------------------------
# Name:        Extract_Footprint.py
# Purpose:     Create seamless map of Mosaic US imagery
# Author:      Hamid Kiavarz
# Created:     06/2020
#-------------------------------------------------------------------------------
import arcpy, os ,timeit      
import json
import logging
from arcpy.sa import *
from multiprocessing import Pool
import os.path
import logging

# arcpy.CheckOutExtension("Spatial")

# def get_spatial_res(imagepath):

#     cellsizeX = int(str(arcpy.GetRasterProperties_management(imagepath,'CELLSIZEX')))
#     cellsizeY = int(str(arcpy.GetRasterProperties_management(imagepath,'CELLSIZEY')))
#     if cellsizeY > cellsizeX:
#         return str(cellsizeY)
#     else:
#         return str(cellsizeX)
   
# def get_filesize(imagepath):
#     return str(os.stat(imagepath).st_size)
# def get_imagepath(imagepath,ext):
#     imagepath = imagepath.replace('.TAB',ext)
#     return imagepath
# def get_year(filename,netpath):
#     x = netpath.split('\\')
#     years = ['2000','2001','2002','2003','2004','2005','2006','2007','2008','2009','2010','2011','2012','2013','2014','2015','2016','2017','2018','2019']
#     no_years = ['199x','200x','201x']
#     for item in x:
#         if item in years:
#             return item
#             break
#     # if item is not in the years list
#     for item in x:
#         if item in no_years:
#              return item
        
# def get_ImageName(inputFile):
#     fileName = ""
#     if os.path.exists(inputFile):
#         tab_File = open(inputFile, 'r')
#         all_lines = tab_File.readlines()
        
#         for line in all_lines:
#             if 'File' in line:
#                 # fileName = line.split('"')[1::2]
#                 fileName = line.split('"')[1]
#                 break
#     return fileName
# def get_Image_Metadata(imagepath,extension,FID):
#     originalFID = 'NA'
#     bits = 'NA'
#     width = 'NA'
#     length = 'NA'
#     ext = 'NA'
#     geoRef = 'Y'
#     fileSize = 'NA'
#     spatial_res = 'NA'
    
#     originalFID = str(FID)
#     bits = arcpy.GetRasterProperties_management(imagepath,'VALUETYPE')
#     width = arcpy.GetRasterProperties_management(imagepath,'COLUMNCOUNT')
#     length = arcpy.GetRasterProperties_management(imagepath,'ROWCOUNT')
#     ext = extension.split('.')[1]
#     fileSize = get_filesize(imagepath)
#     spatial_res = get_spatial_res(imagepath)
#     desc = arcpy.Describe(imagepath)
#     year = get_year(desc.baseName,desc.path)
    
#     return [originalFID, bits, width, length, ext, geoRef, fileSize, imagepath, spatial_res, year]
# def get_Footprint(inputRaster):
#     try:
#         ws = arcpy.env.scratchFolder
#         arcpy.env.workspace = ws
#         srWGS84 = arcpy.SpatialReference('WGS 1984')
#         tmpGDB =os.path.join(ws,r"temp.gdb")
#         if not os.path.exists(tmpGDB):
#             arcpy.CreateFileGDB_management(ws,r"temp.gdb")

#         # Calcuate Footprint geometry
#         resampleRaster = os.path.join(ws,'resampleRaster' + '.tif')
#         bin_Raster = os.path.join(ws,'bin_Raster' + '.tif')
#         polygon_with_holes= os.path.join(tmpGDB,'polygon_with_holes')
#         out_Vertices = os.path.join(tmpGDB,'Out_Vertices')

#         arcpy.AddMessage('Start resampling the input raster...')
#         start1 = timeit.default_timer()
#         rasterProp = arcpy.GetRasterProperties_management(inputRaster, "CELLSIZEX")
#         resampleRaster = arcpy.Resample_management(inputRaster,resampleRaster ,4, "NEAREST")
#         inputSR = arcpy.Describe(resampleRaster).spatialReference
#         end1 = timeit.default_timer()
#         arcpy.AddMessage(('End resampling the input raster. Duration:', round(end1 -start1,4)))
        
 
#         arcpy.AddMessage('Start creating binary raster (Raster Calculator)...')
#         start2 = timeit.default_timer()
#         expression = 'Con(' + '"' + 'resampleRaster' + '.tif' + '"' + ' >= 10 , 1)'
#         bin_Raster = arcpy.gp.RasterCalculator_sa(expression, bin_Raster)
#         end2 = timeit.default_timer()
#         arcpy.AddMessage(('End creating binary raster. Duration:', round(end2 -start2,4)))

#         # Convert binary raster to polygon       
#         arcpy.AddMessage('Start creating prime polygon from raster...')
#         start3 = timeit.default_timer()  
#         # arcpy.RasterToPolygon_conversion(bin_Raster, 'primePolygon.shp', "SIMPLIFY", "VALUE")
#         polygon_with_holes =  arcpy.RasterToPolygon_conversion(in_raster= bin_Raster, out_polygon_features=polygon_with_holes, simplify="SIMPLIFY", raster_field="Value", create_multipart_features="SINGLE_OUTER_PART", max_vertices_per_feature="")
#         end3 = timeit.default_timer()
#         arcpy.AddMessage(('End creating polygon. Duration:', round(end3 -start3,4)))

#         ### extract the main polygon (with maximum area) which includes several donuts
#         arcpy.AddMessage('Start extracting exterior ring (outer outline) of polygon...')
#         start4 = timeit.default_timer()      
#         sql_clause = (None, 'ORDER BY Shape_Area DESC')
#         geom = arcpy.Geometry()
#         row = arcpy.da.SearchCursor(polygon_with_holes,('SHAPE@'),None,None,False,sql_clause).next()
#         geom = row[0]
#         end4 = timeit.default_timer()
#         arcpy.AddMessage(('End extracting polygon. Duration:', round(end4 -start4,4)))
        
#         ### extract the exterior points from main polygon to generate pure polygon from ouer line of main polygon
#         arcpy.AddMessage('Start extracting exterior points ...')
#         start5 = timeit.default_timer()      
#         outer_coords = []
#         for island in geom.getPart():
#             # arcpy.AddMessage("Vertices in island: {0}".format(island.count))
#             for point in island:
#                 # coords.append = (point.X,point.Y)
#                 if not isinstance(point, type(None)):
#                     newPoint = (point.X,point.Y)
#                     if len(outer_coords) == 0:
#                         outer_coords.append(newPoint)
#                     elif not newPoint == outer_coords[0]:   
#                         outer_coords.append((newPoint))
#                     elif len(outer_coords) > 50:
#                         outer_coords.append((newPoint))
#                         break
        
#         # # # # points_FC = arcpy.CreateFeatureclass_management(tmpGDB,"points_FC", "POINT", "", "DISABLED", "DISABLED", inputSR)
#         # # # # i = 0
#         # # # # with arcpy.da.InsertCursor(points_FC,["SHAPE@XY"]) as cursor: 
#         # # # #     for coord in outer_coords:
#         # # # #         cursor.insertRow([coord]) 
#         # # # #         i+= 1
#         # # # #         if i > 2:
#         # # # #             break       
#         # # # #     del cursor
        
#         ### Create footprint  featureclass -- > polygon 
#         footprint_FC = arcpy.CreateFeatureclass_management(tmpGDB,"footprint_FC", "POLYGON", "", "DISABLED", "DISABLED", inputSR)
#         cursor = arcpy.da.InsertCursor(footprint_FC, ['SHAPE@'])
#         cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in outer_coords]),inputSR)])
#         del cursor
#         end5 = timeit.default_timer()
#         arcpy.AddMessage(('End extracting exterior points and inserted as FC. Duration:', round(end5 -start5,4)))
        
#         arcpy.AddMessage('Start simplifying footprint polygon...')
#         start6 = timeit.default_timer() 
#         arcpy.Generalize_edit(footprint_FC, '100 Meter')
#         finalGeometry = (arcpy.da.SearchCursor(footprint_FC,('SHAPE@')).next())[0]
#         end6 = timeit.default_timer()
#         arcpy.AddMessage(('End simplifying footprint polygon. Duration:', round(end6 -start6,4)))
#         footprint_WGS84 = finalGeometry.projectAs(srWGS84)
#         return(footprint_WGS84)
#     except:
#         msgs = "ArcPy ERRORS:\n %s\n"%arcpy.GetMessages(2)
#         arcpy.AddError(msgs)
#         raise
# def UpdateSeamlessFC(DQQQ_footprint_FC,metaData,ft_Polygon):
#     arcpy.AddMessage('Start Uploading to seamless FC...')
#     start7 = timeit.default_timer() 
#     srWGS84 = arcpy.SpatialReference('WGS 1984')
#     insertRow = arcpy.da.InsertCursor(DQQQ_footprint_FC, ['Original_FID','BITS','WIDTH','LENGTH','EXT','GEOREF','FILESIZE','IMAGEPATH','SPATIAL_RESOLUTION','YEAR','SHAPE@'])
#     rowtuple=[str(metaData[0]),str(metaData[1]),str(metaData[2]),str(metaData[3]),str(metaData[4]),str(metaData[5]),str(metaData[6]),str(metaData[7]),str(metaData[8]),str(metaData[9]),ft_Polygon]
#     insertRow.insertRow(rowtuple)
#     end7 = timeit.default_timer()
#     arcpy.AddMessage(('End Uploading to seamless FC. Duration:', round(end7 -start7,4)))
#     del insertRow
# def apply_process(inputParam):
#     print('FID: ' + inputParam[0] + ' - processing Dataset: ' + inputParam[1])
    # startDataset = timeit.default_timer()   
    # arcpy.AddMessage('-------------------------------------------------------------------------------------------------')
    # arcpy.AddMessage('Start FID: ' + str(FID) + ' - processing Dataset: ' + tabfile_Path)
    
    # # fileName = get_ImageName(tabfile_Path)
    # # if len(fileName) > 0:
    # #     ext = '.' + fileName.split('.')[1]
    # #     image_Path = tabfile_Path.replace('.TAB',ext)
    # #     ### start cerating seamless map 
    # #     # metaData = get_Image_Metadata(image_Path,ext,row[0])
    # #     # footprint_Polygon = get_Footprint(image_Path)
    # #     # UpdateSeamlessFC(DQQQ_footprint_FC,metaData,footprint_Polygon)
    # # else:
    # #         arcpy.AddWarning("FID : {} - Path or Images is not valid or available".format(row[0]))
    # #         logger.warning("FID : {} - Path or Images is not valid or available for :  {} ".format(row[0], row[1]))
    # endDataset = timeit.default_timer()
    # arcpy.AddMessage(('End FID: ' + str(row[0]) + ' - processed Dataset. Duration:', round(endDataset - startDataset,4)))
    
def my_func(x):
      print(x*x)
      
if __name__ == '__main__':
    params = [2,3,4]
    pool = Pool(processes=3)
    pool.map(my_func, params) 
    
    # ws =  arcpy.env.scratchFolder
    # arcpy.env.workspace = ws
    # arcpy.env.overwriteOutput = True   
    # arcpy.AddMessage(ws)
    # inputRaster = arcpy.GetParameterAsText(0)
    # DQQQ_footprint_FC = r'F:\Aerial_US\USImagery\Data\Seamless_Map.gdb\Aerial_Footprint_Mosaic_test'
    # logfile = r'F:\Aerial_US\USImagery\logs\US_Imagery_SeamlessMap.txt'
    # DQQQ_ALL_FC = r'F:\Aerial_US\USImagery\Data\DOQQ_ALL.shp'
    
    # logger = logging.getLogger(__name__)
    # logger.setLevel(logging.WARNING)
    # handler = logging.FileHandler(logfile)
    # handler.setLevel(logging.WARNING)
    # logger.addHandler(handler)
    
    # startTotal = timeit.default_timer()
    
    # params =[]
    # expression = "FID >= 201 AND FID <= 203"
    # expression = "FID = 35"
    # rows =  arcpy.da.SearchCursor(DQQQ_ALL_FC,["FID", 'TABLE_'],where_clause=expression) as dqq_cursor:
    # rows = arcpy.da.SearchCursor(DQQQ_ALL_FC,["FID", 'TABLE_'],where_clause=expression)
    # for row in rows:
    #     tabfile_Path = row[1].replace('nas2520','cabcvan1nas003')
    #     params.append([str(row[0]),tabfile_Path])
        
        # startDataset = timeit.default_timer()   
        # arcpy.AddMessage('-------------------------------------------------------------------------------------------------')
        # arcpy.AddMessage('Start FID: ' + str(row[0]) + ' - processing Dataset: ' + row[1])
        
        # fileName = get_ImageName(tabfile_Path)
        # if len(fileName) > 0:
            
        #     ### check if path of image is exist
        #     ext = '.' + fileName.split('.')[1]
        #     image_Path = tabfile_Path.replace('.TAB',ext)
           
        #     metaData = get_Image_Metadata(image_Path,ext,row[0])
        #     footprint_Polygon = get_Footprint(image_Path)
        #     UpdateSeamlessFC(DQQQ_footprint_FC,metaData,footprint_Polygon)
        # else:
        #      arcpy.AddWarning("FID : {} - Path or Images is not valid or available".format(row[0]))
        #      logger.warning("FID : {} - Path or Images is not valid or available for :  {} ".format(row[0], row[1]))
        # endDataset = timeit.default_timer()
        # arcpy.AddMessage(('End FID: ' + str(row[0]) + ' - processed Dataset. Duration:', round(endDataset - startDataset,4)))
    # pool = Pool(processes=3)
    # pool.map(apply_process, params)       
              
    # endTotal= timeit.default_timer()
    # arcpy.AddMessage(('Total Duration:', round(endTotal -startTotal,4)))
    
    
    