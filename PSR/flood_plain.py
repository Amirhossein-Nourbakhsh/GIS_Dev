from imp import reload
import arcpy, os, sys
from datetime import datetime
import timeit,time
import shutil
import psr_utility 
import psr_config 
sys.path.insert(1,os.path.join(os.getcwd(),'DB_Framework'))
import models
reload(sys)
def Generate_FloodReport(order_obj):
    arcpy.AddMessage('  -- Start generating PSR flood report...')
    start = timeit.default_timer()   
    ### set scratch folder
    scratchfolder =  arcpy.env.scratchFolder
    arcpy.env.workspace = scratchfolder
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage('      - scratch folder: %s' %scratchfolder)
    ### set paths
    buffer_flood_shp = os.path.join(scratchfolder,"buffer_flood.shp")
    flood_clip_fc = os.path.join(scratchfolder,'temp.gdb',"flood_clip") 
    order_geometry_pcs_shp =  os.path.join(scratchfolder,"order_geometry_pcs.shp")
    tempGDB = os.path.join(scratchfolder,r"temp.gdb")
    ### set geometry layer file
    if order_obj.geometry.type.lower()== 'point':
        order_geom_lyrfile = psr_config.orderGeomlyrfile_point
    elif order_obj.geometry.type.lower() =='polyline':
        order_geom_lyrfile = psr_config.orderGeomlyrfile_polyline
    else: #polygon
        order_geom_lyrfile = psr_config.orderGeomlyrfile_polygon
    ### calculate order geometry in PCS
    centre_point = order_obj.geometry.trueCentroid
    spatial_ref_pcs = arcpy.GetUTMFromLocation(centre_point.X,centre_point.Y)
    order_geometry_pcs = order_obj.geometry.projectAs(spatial_ref_pcs)
    arcpy.CopyFeatures_management(order_geometry_pcs, order_geometry_pcs_shp)
    ### extract buffer size for flood report
    psr_list = order_obj.getPSR()
    if len(psr_list) > 0:
        flood_radius = next(psrObj.search_radius for psrObj in psr_list if psrObj.type == 'flood')
        bufferDist_flood = str(flood_radius) + ' MILES'
         
        arcpy.Buffer_analysis(order_geometry_pcs, buffer_flood_shp, bufferDist_flood) ### create buffer map based on order geometry
        arcpy.Clip_analysis(psr_config.data_flood, buffer_flood_shp, flood_clip_fc) ### clip flood map by buffered oreder geometry
        
        arcpy.Statistics_analysis(flood_clip_fc, os.path.join(scratchfolder,"summary_flood.dbf"), [['FLD_ZONE','FIRST'], ['ZONE_SUBTY','FIRST']],'ERIS_CLASS')
        arcpy.Sort_management(os.path.join(scratchfolder,"summary_flood.dbf"), os.path.join(scratchfolder,"summary1_flood.dbf"), [["ERIS_CLASS", "ASCENDING"]])
        
        mxd_flood = arcpy.mapping.MapDocument(psr_config.mxdfile_flood)
        df_flood = arcpy.mapping.ListDataFrames(mxd_flood,"Flood*")[0]
        df_flood.spatialReference = spatial_ref_pcs
        
        df_floodsmall = arcpy.mapping.ListDataFrames(mxd_flood,"Study*")[0]
        df_floodsmall.spatialReference = spatial_ref_pcs
        del df_floodsmall
        
        psr_utility.add_layer_to_mxd("buffer_flood",df_flood,psr_config.bufferlyrfile, 1.1)
        psr_utility.add_layer_to_mxd("order_geometry_pcs", df_flood,order_geom_lyrfile,1)
        arcpy.RefreshActiveView();
        if not psr_utility.if_multipage(order_geometry_pcs_shp):
            mxd_flood.saveACopy(os.path.join(scratchfolder, "mxd_flood.mxd"))       #<-- this line seems to take huge amount of memory, up to 1G. possibly due to df SR change
            arcpy.mapping.ExportToJPEG(mxd_flood, outputjpg_flood, "PAGE_LAYOUT", resolution=150, jpeg_quality=85)
            if not os.path.exists(os.path.join(report_path, 'PSRmaps', order_obj.Number)):
                os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
            shutil.copy(outputjpg_flood, os.path.join(report_path, 'PSRmaps', order_obj.Number))
            del mxd_flood
            del df_flood

    else:
        arcpy.AddWarning('There is no floorplain PSR for this Order!')