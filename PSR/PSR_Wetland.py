
import arcpy, os, numpy
from datetime import datetime
import traceback
import PSR_config
import shutil

def Generate_WetlandReport(orderObj):
    print('wetland Process....!')    
    if orderObj.geometry.type.lower()== 'point':
        orderGeomlyrfile = PSR_config.orderGeomlyrfile_point
    elif orderObj.geometry.type.lower() =='polyline':
        orderGeomlyrfile = PSR_config.orderGeomlyrfile_polyline
    else: #polygon
        orderGeomlyrfile = PSR_config.orderGeomlyrfile_polygon
    scratchfolder =  arcpy.env.scratchFolder
    arcpy.env.workspace = scratchfolder
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage(scratchfolder)
    gridsize = "2 MILES"
    psr_list = orderObj.getPSR()
    ### set parameters and output paths
    wetland_radius = next(psrObj.search_radius for psrObj in psr_list if psrObj.type == 'wetland')
    bufferDist_wetland = str(wetland_radius) + ' MILES'
    centre_point = orderObj.geometry.trueCentroid
    orderGeo_GCS_shp= os.path.join(scratchfolder,"orderGeo_GCS_shp.shp")
    orderGeo_PCS_shp= os.path.join(scratchfolder,"orderGeometry_PCS.shp")
    bufferSHP_wetland = os.path.join(scratchfolder,"buffer_wetland.shp")
    outputjpg_wetland = os.path.join(scratchfolder, str(orderObj.order_Id) +'_US_WETL.jpg')
    sr = arcpy.GetUTMFromLocation(centre_point.X,centre_point.Y)
    orderGeometry_PCS = orderObj.geometry.projectAs(sr)
    arcpy.CopyFeatures_management(orderGeometry_PCS, orderGeo_PCS_shp)
    ### Wetland Map , no attributes
    arcpy.Buffer_analysis(orderGeo_PCS_shp, bufferSHP_wetland, bufferDist_wetland)
    mxd_wetland = arcpy.mapping.MapDocument(PSR_config.mxdfile_wetland)
    df_wetland = arcpy.mapping.ListDataFrames(mxd_wetland,"big")[0]
    df_wetland.spatialReference = sr
    df_wetlandsmall = arcpy.mapping.ListDataFrames(mxd_wetland,"small")[0]
    df_wetlandsmall.spatialReference = sr
    del df_wetlandsmall

    addBuffertoMxd("buffer_wetland",df_wetland,scratchfolder)
    addOrdergeomtoMxd("orderGeometry_PCS", df_wetland,orderGeomlyrfile,scratchfolder)
    multipage_wetland = if_multipage(orderGeo_PCS_shp)
    print(multipage_wetland)
    # print the maps
    if multipage_wetland == False:
       mxd_wetland.saveACopy(os.path.join(scratchfolder, "mxd_wetland.mxd"))
       arcpy.mapping.ExportToJPEG(mxd_wetland, outputjpg_wetland, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
       print(os.path.join(PSR_config.report_path, 'PSRmaps', str(orderObj.order_num)))
       if not os.path.exists(os.path.join(PSR_config.report_path, 'PSRmaps', str(orderObj.order_num))):
            os.mkdir(os.path.join(PSR_config.report_path, 'PSRmaps', str(orderObj.order_num)))
       shutil.copy(outputjpg_wetland, os.path.join(PSR_config.report_path, 'PSRmaps', str(orderObj.order_num)))
       del mxd_wetland
       del df_wetland
    else:                           # multipage
        print('True')
        gridlr = "gridlr_wetland"   # gdb feature class doesn't work, could be a bug. So use .shp
        gridlrshp = os.path.join(scratchfolder, gridlr)
        arcpy.GridIndexFeatures_cartography(gridlrshp, bufferSHP_wetland, "", "", "", gridsize, gridsize)  #note the tool takes featureclass name only, not the full path
      
       
   
def addBuffertoMxd(bufferName,thedf,scratchfolder):    # note: buffer is a shapefile, the name doesn't contain .shp
    bufferLayer = arcpy.mapping.Layer(PSR_config.bufferlyrfile)
    bufferLayer.replaceDataSource(scratchfolder,"SHAPEFILE_WORKSPACE",bufferName)
    arcpy.mapping.AddLayer(thedf,bufferLayer,"Top")
    thedf.extent = bufferLayer.getSelectedExtent(False)
    thedf.scale = thedf.scale * 1.1
def addOrdergeomtoMxd(ordergeomName, thedf,orderGeomlyrfile,scratchfolder):
    orderGeomLayer = arcpy.mapping.Layer(orderGeomlyrfile)
    orderGeomLayer.replaceDataSource(scratchfolder,"SHAPEFILE_WORKSPACE",ordergeomName)
    arcpy.mapping.AddLayer(thedf,orderGeomLayer,"Top")
def if_multipage(geometry_PCS_shp):
    geomExtent = arcpy.Describe(geometry_PCS_shp).extent
    if geomExtent.width > 1300 or geomExtent.height > 1300:
        return True
    else:
        return False