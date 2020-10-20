
import arcpy, os, numpy
from datetime import datetime
import traceback
import PSR_config

def Generate_WetlandReport(orderObj):
    print('wetland Process....!')    
    
    scratchfolder =  arcpy.env.scratchFolder
    arcpy.env.workspace = scratchfolder
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage(scratchfolder)
    psr_list = orderObj.getPSR()
    # ### set buffering parameters
    wetland_radius = next(psrObj.search_radius for psrObj in psr_list if psrObj.type == 'wetland')
    bufferDist_wetland = str(wetland_radius) + ' MILES'
    centre_point = orderObj.geometry.trueCentroid
    orderGeo_GCS_shp= os.path.join(scratchfolder,"orderGeo_GCS_shp.shp")
    orderGeo_PCS_shp= os.path.join(scratchfolder,"orderGeometry_PCS.shp")
    sr = arcpy.GetUTMFromLocation(centre_point.X,centre_point.Y)
    orderGeometry_PCS = orderObj.geometry.projectAs(sr)
    arcpy.CopyFeatures_management(orderGeometry_PCS, orderGeo_PCS_shp)
    # print(sr)
    # arcpy.CopyFeatures_management(orderObj.geometry, orderGeo_shp)
    # arcpy.AddField_management(orderGeo_shp, "UTM", "TEXT", "", "", "1500", "", "NULLABLE", "NON_REQUIRED", "")
    # arcpy.CalculateUTMZone_cartography(orderGeo_shp, "UTM")
    # ### Wetland Map , no attributes
    # bufferSHP_wetland = os.path.join(scratchfolder,"buffer_wetland.shp")
    # arcpy.Buffer_analysis(orderGeometryPR, bufferSHP_wetland, bufferDist_wetland)

    # mxd_wetland = arcpy.mapping.MapDocument(mxdfile_wetland)
    # df_wetland = arcpy.mapping.ListDataFrames(mxd_wetland,"big")[0]
    # df_wetland.spatialReference = spatialRef
    # df_wetlandsmall = arcpy.mapping.ListDataFrames(mxd_wetland,"small")[0]
    # df_wetlandsmall.spatialReference = spatialRef
    # del df_wetlandsmall

    # addBuffertoMxd("buffer_wetland",df_wetland)
    # addOrdergeomtoMxd("ordergeoNamePR", df_wetland)

    # # print the maps
    # if multipage_wetland == False:
    #    mxd_wetland.saveACopy(os.path.join(scratchfolder, "mxd_wetland.mxd"))
    #    arcpy.mapping.ExportToJPEG(mxd_wetland, outputjpg_wetland, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
    # outputjpg_wetland = os.path.join(scratchfolder, str(order_Id) +'_US_WETL.jpg')