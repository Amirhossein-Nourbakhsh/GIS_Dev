
from imp import reload
import arcpy, os, sys
from datetime import datetime
import timeit,time
import shutil
import psr_config
sys.path.insert(1,os.path.join(os.getcwd(),'DB_Framework'))
import models
reload(sys)
def Generate_FloodReport(orderObj):
    arcpy.AddMessage('  -- Start generating PSR flood report...')
    start = timeit.default_timer()   
    ### set scratch folder
    scratchfolder =  arcpy.env.scratchFolder
    arcpy.env.workspace = scratchfolder
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage('      - scratch folder: %s' %scratchfolder)
    ### set paths
    orderGeo_GCS_shp= os.path.join(scratchfolder,"orderGeo_GCS_shp.shp")
    orderGeo_PCS_shp= os.path.join(scratchfolder,"orderGeometry_PCS.shp")
    bufferSHP_flood = os.path.join(scratchfolder,"buffer_wetland.shp")
    flood_clip = os.path.join(scratchfolder,"flood_clip") 
    tempGDB = os.path.join(scratchfolder,r"temp.gdb")
    ### calculate order geometry in PCS
    centre_point = orderObj.geometry.trueCentroid
    sr = arcpy.GetUTMFromLocation(centre_point.X,centre_point.Y)
    orderGeometry_PCS = orderObj.geometry.projectAs(sr)
    ### extract buffer size for flood report
    psr_list = orderObj.getPSR()
    if len(psr_list) > 0:
        flood_radius = next(psrObj.search_radius for psrObj in psr_list if psrObj.type == 'flood')
        bufferDist_flood = str(flood_radius) + ' MILES'
         
        arcpy.Buffer_analysis(orderGeometry_PCS, bufferSHP_flood, bufferDist_flood) ### create buffer map based on order geometry
        arcpy.Clip_analysis(psr_config.data_flood, bufferSHP_flood, flood_clip) ### clip flood map by oreder geometry
        
        arcpy.Statistics_analysis(flood_clip, os.path.join(scratchfolder,"summary_flood.dbf"), [['FLD_ZONE','FIRST'], ['ZONE_SUBTY','FIRST']],'ERIS_CLASS')
        arcpy.Sort_management(os.path.join(scratchfolder,"summary_flood.dbf"), os.path.join(scratchfolder,"summary1_flood.dbf"), [["ERIS_CLASS", "ASCENDING"]])

    else:
        arcpy.AddWarning('There is no floorplain PSR for this Order!')