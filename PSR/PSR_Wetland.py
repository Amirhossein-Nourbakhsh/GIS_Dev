
import arcpy, os, sys
from datetime import datetime
import timeit,time
import shutil
import PSR_config
sys.path.insert(1,os.path.join(os.getcwd(),'DB_Framework'))
import models
reload(sys)

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
def generate_singlepage_report(orderObj,mxd_wetland,outputjpg_wetland,scratchfolder):
    mxd_wetland.saveACopy(os.path.join(scratchfolder, "mxd_wetland.mxd"))
    arcpy.mapping.ExportToJPEG(mxd_wetland, outputjpg_wetland, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
    if not os.path.exists(os.path.join(PSR_config.report_path, 'PSRmaps', str(orderObj.number))):
        os.mkdir(os.path.join(PSR_config.report_path, 'PSRmaps', str(orderObj.number)))
    shutil.copy(outputjpg_wetland, os.path.join(PSR_config.report_path, 'PSRmaps', str(orderObj.number)))
    arcpy.AddMessage('      --> Wetland Output: %s' % os.path.join(PSR_config.report_path, 'PSRmaps', str(orderObj.number)))
    del mxd_wetland
def generate_multipage_report(orderObj,mxd_wetland,outputjpg_wetland,bufferSHP_wetland,df_wetland,orderGeomlyrfile,scratchfolder):
    gridlr = "gridlr_wetland"   # gdb feature class doesn't work, could be a bug. So use .shp
    gridlrshp = os.path.join(scratchfolder, gridlr)
    gridlrshp = arcpy.GridIndexFeatures_cartography(gridlrshp, bufferSHP_wetland, "", "", "", "2 MILES", "2 MILES")  #note the tool takes featureclass name only, not the full path
    spatial_ref = arcpy.Describe(bufferSHP_wetland).spatialReference
    # part 1: the overview map
    # add grid layer
    gridLayer = arcpy.mapping.Layer(PSR_config.gridlyrfile)
    gridLayer.replaceDataSource(scratchfolder,"SHAPEFILE_WORKSPACE",gridlr)
    arcpy.mapping.AddLayer(df_wetland,gridLayer,"Top")
    df_wetland.extent = gridLayer.getExtent()
    df_wetland.scale = df_wetland.scale * 1.1
    mxd_wetland.saveACopy(os.path.join(scratchfolder, "mxd_wetland.mxd"))
    arcpy.mapping.ExportToJPEG(mxd_wetland, outputjpg_wetland, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
    if not os.path.exists(os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number)):
        os.mkdir(os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number))
    shutil.copy(outputjpg_wetland, os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number))
    arcpy.AddMessage('      --> Wetland Output: %s' % os.path.join(PSR_config.report_path, 'PSRmaps', str(orderObj.number)))
    del mxd_wetland
    del df_wetland

    ### part 2: the data driven pages
    page = 1
    page = int(arcpy.GetCount_management(gridlrshp).getOutput(0))  + page
    mxdMM_wetland = arcpy.mapping.MapDocument(PSR_config.mxdMMfile_wetland)
    dfMM_wetland = arcpy.mapping.ListDataFrames(mxdMM_wetland,"big")[0]
    dfMM_wetland.spatialReference = spatial_ref
    addBuffertoMxd("buffer_wetland",dfMM_wetland,scratchfolder)
    addOrdergeomtoMxd("orderGeometry_PCS", dfMM_wetland,orderGeomlyrfile, scratchfolder)
    gridlayerMM = arcpy.mapping.ListLayers(mxdMM_wetland,"Grid" ,dfMM_wetland)[0]
    gridlayerMM.replaceDataSource(scratchfolder, "SHAPEFILE_WORKSPACE","gridlr_wetland")
    arcpy.CalculateAdjacentFields_cartography(gridlrshp, "PageNumber")
    mxdMM_wetland.saveACopy(os.path.join(scratchfolder, "mxdMM_wetland.mxd"))

    for i in range(1,int(arcpy.GetCount_management(gridlrshp).getOutput(0))+1):
        arcpy.SelectLayerByAttribute_management(gridlayerMM, "NEW_SELECTION", ' "PageNumber" =  ' + str(i))
        dfMM_wetland.extent = gridlayerMM.getSelectedExtent(True)
        dfMM_wetland.scale = dfMM_wetland.scale * 1.1
        arcpy.SelectLayerByAttribute_management(gridlayerMM, "CLEAR_SELECTION")

        titleTextE = arcpy.mapping.ListLayoutElements(mxdMM_wetland, "TEXT_ELEMENT", "title")[0]
        titleTextE.text = "Wetland Type - Page " + str(i)
        titleTextE.elementPositionX = 0.468
        arcpy.RefreshTOC()

        arcpy.mapping.ExportToJPEG(mxdMM_wetland, outputjpg_wetland[0:-4]+str(i)+".jpg", "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
        if not os.path.exists(os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number)):
            os.mkdir(os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number))
        shutil.copy(outputjpg_wetland[0:-4]+str(i)+".jpg", os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number))
    del mxdMM_wetland
    del dfMM_wetland
    
def Generate_WetlandReport(orderObj):
    arcpy.AddMessage('  -- Start generating PSR wetland report...')
    start = timeit.default_timer()   
    if orderObj.geometry.type.lower()== 'point':
        orderGeomlyrfile = PSR_config.orderGeomlyrfile_point
    elif orderObj.geometry.type.lower() =='polyline':
        orderGeomlyrfile = PSR_config.orderGeomlyrfile_polyline
    else: #polygon
        orderGeomlyrfile = PSR_config.orderGeomlyrfile_polygon
    scratchfolder =  arcpy.env.scratchFolder
    arcpy.env.workspace = scratchfolder
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage('      --> scratch folder: %s' %scratchfolder)
    ### set paths
    orderGeo_GCS_shp= os.path.join(scratchfolder,"orderGeo_GCS_shp.shp")
    orderGeo_PCS_shp= os.path.join(scratchfolder,"orderGeometry_PCS.shp")
    bufferSHP_wetland = os.path.join(scratchfolder,"buffer_wetland.shp")
    outputjpg_wetland = os.path.join(scratchfolder, str(orderObj.Id) +'_US_WETL.jpg')
    outputjpg_wetlandNY = os.path.join(scratchfolder, str(orderObj.number)+'_NY_WETL.jpg')
    gridsize = "2 MILES"
    centre_point = orderObj.geometry.trueCentroid
    sr = arcpy.GetUTMFromLocation(centre_point.X,centre_point.Y)
    orderGeometry_PCS = orderObj.geometry.projectAs(sr)
    arcpy.CopyFeatures_management(orderGeometry_PCS, orderGeo_PCS_shp)
    multipage_wetland = if_multipage(orderGeo_PCS_shp)
    psr_list = orderObj.getPSR()
    if len(psr_list) > 0:
        ### Wetland Map
        wetland_radius = next(psrObj.search_radius for psrObj in psr_list if psrObj.type == 'wetland')
        bufferDist_wetland = str(wetland_radius) + ' MILES'
        arcpy.Buffer_analysis(orderGeo_PCS_shp, bufferSHP_wetland, bufferDist_wetland)
        mxd_wetland = arcpy.mapping.MapDocument(PSR_config.mxdfile_wetland)
        df_wetland = arcpy.mapping.ListDataFrames(mxd_wetland,"big")[0]
        df_wetland.spatialReference = sr
        df_wetlandsmall = arcpy.mapping.ListDataFrames(mxd_wetland,"small")[0]
        df_wetlandsmall.spatialReference = sr
        del df_wetlandsmall
        addBuffertoMxd("buffer_wetland",df_wetland,scratchfolder)
        addOrdergeomtoMxd("orderGeometry_PCS", df_wetland,orderGeomlyrfile,scratchfolder)
        arcpy.AddMessage('      --> multiple pages: %s' % str(multipage_wetland))
        # print the maps
        if multipage_wetland == False:  # sinle page report
           generate_singlepage_report(orderObj,mxd_wetland,outputjpg_wetland,scratchfolder)
        else:                           # multipage report
            generate_multipage_report(orderObj,mxd_wetland,outputjpg_wetland,bufferSHP_wetland,df_wetland,orderGeomlyrfile,scratchfolder)
        end = timeit.default_timer()
        arcpy.AddMessage((' -- End generating PSR Wetland report. Duration:', round(end -start,4)))
    else:
        arcpy.AddWarning('There is no wetland PSR for this Order!')
   
   ### Create wetlan report for Newyork province
    if orderObj.province =='NY':
        arcpy.AddMessage ("      --> Starting NY wetland section: " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
        bufferSHP_wetland = os.path.join(scratchfolder,"buffer_wetland.shp")
        mxd_wetlandNY = arcpy.mapping.MapDocument(PSR_config.mxdfile_wetlandNY)
        df_wetlandNY = arcpy.mapping.ListDataFrames(mxd_wetlandNY,"big")[0]
        df_wetlandNY.spatialReference = sr
        addBuffertoMxd("buffer_wetland",df_wetlandNY, scratchfolder)
        addOrdergeomtoMxd("orderGeometry_PCS", df_wetlandNY, orderGeomlyrfile,scratchfolder)
        page = 1
        ### print the maps
        if multipage_wetland == False:
            mxd_wetlandNY.saveACopy(os.path.join(scratchfolder, "mxd_wetlandNY.mxd"))
            arcpy.mapping.ExportToJPEG(mxd_wetlandNY, outputjpg_wetlandNY, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
            shutil.copy(outputjpg_wetlandNY, os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number))
            arcpy.AddMessage('      --> Wetland Output for NY state: %s' % os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number))
            del mxd_wetlandNY
            del df_wetlandNY
        else:                           # multipage
            gridlr = "gridlr_wetland"
            gridlrshp = os.path.join(scratchfolder, gridlr)
            arcpy.GridIndexFeatures_cartography(gridlrshp, bufferSHP_wetland, "", "", "", gridsize, gridsize)  #note the tool takes featureclass name only, not the full path

            # part 1: the overview map
            # add grid layer
            gridLayer = arcpy.mapping.Layer(PSR_config.gridlyrfile)
            gridLayer.replaceDataSource(scratchfolder,"SHAPEFILE_WORKSPACE","gridlr_wetland")
            arcpy.mapping.AddLayer(df_wetlandNY,gridLayer,"Top")

            df_wetlandNY.extent = gridLayer.getExtent()
            df_wetlandNY.scale = df_wetlandNY.scale * 1.1

            mxd_wetlandNY.saveACopy(os.path.join(scratchfolder, "mxd_wetlandNY.mxd"))
            arcpy.mapping.ExportToJPEG(mxd_wetlandNY, outputjpg_wetlandNY, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
            if not os.path.exists(os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number)):
                os.mkdir(os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number))
            shutil.copy(outputjpg_wetlandNY, os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number))

            del mxd_wetlandNY
            del df_wetlandNY

            # part 2: the data driven pages
            

            page = int(arcpy.GetCount_management(gridlrshp).getOutput(0))  + page
            mxdMM_wetlandNY = arcpy.mapping.MapDocument(PSR_config.mxdMMfile_wetlandNY)

            dfMM_wetlandNY = arcpy.mapping.ListDataFrames(mxdMM_wetlandNY,"big")[0]
            dfMM_wetlandNY.spatialReference = sr
            addBuffertoMxd("buffer_wetland",dfMM_wetlandNY)
            addOrdergeomtoMxd("ordergeoNamePR", dfMM_wetlandNY)
            gridlayerMM = arcpy.mapping.ListLayers(mxdMM_wetlandNY,"Grid" ,dfMM_wetlandNY)[0]
            gridlayerMM.replaceDataSource(scratchfolder, "FILEGDB_WORKSPACE","gridlr_wetland")
            arcpy.CalculateAdjacentFields_cartography(gridlrshp, "PageNumber")
            mxdMM_wetlandNY.saveACopy(os.path.join(scratchfolder, "mxdMM_wetlandNY.mxd"))

            for i in range(1,int(arcpy.GetCount_management(gridlrshp).getOutput(0))+1):
                arcpy.SelectLayerByAttribute_management(gridlayerMM, "NEW_SELECTION", ' "PageNumber" =  ' + str(i))
                dfMM_wetlandNY.extent = gridlayerMM.getSelectedExtent(True)
                dfMM_wetlandNY.scale = dfMM_wetlandNY.scale * 1.1
                arcpy.SelectLayerByAttribute_management(gridlayerMM, "CLEAR_SELECTION")
                titleTextE = arcpy.mapping.ListLayoutElements(mxdMM_wetlandNY, "TEXT_ELEMENT", "title")[0]
                titleTextE.text = "NY Wetland Type - Page " + str(i)
                titleTextE.elementPositionX = 0.468
                arcpy.RefreshTOC()
                arcpy.mapping.ExportToJPEG(mxdMM_wetlandNY, outputjpg_wetlandNY[0:-4]+str(i)+".jpg", "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                if not os.path.exists(os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number)):
                    os.mkdir(os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number))
                shutil.copy(outputjpg_wetlandNY[0:-4]+str(i)+".jpg", os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number))
                arcpy.AddMessage('      --> Wetland Output for NY state: %s' % os.path.join(PSR_config.report_path, 'PSRmaps', orderObj.number))
            del mxdMM_wetlandNY
            del dfMM_wetlandNY
        psrObj = models.PSR()
        for i in range(1,page): ##insert generated .jpg report path into eris_maps_psr table
            psrObj.insert_report(orderObj,i)
   