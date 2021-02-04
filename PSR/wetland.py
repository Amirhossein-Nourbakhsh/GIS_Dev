
from imp import reload
import arcpy, os, sys
from datetime import datetime
import timeit,time
import shutil
import psr_utility as utility
import psr_config as config
sys.path.insert(1,os.path.join(os.getcwd(),'DB_Framework'))
import models
reload(sys)

def addBuffertoMxd(bufferName,thedf,scratch_folder):    # note: buffer is a shapefile, the name doesn't contain .shp
    bufferLayer = arcpy.mapping.Layer(config.buffer_lyr_file)
    bufferLayer.replaceDataSource(scratch_folder,"SHAPEFILE_WORKSPACE",bufferName)
    arcpy.mapping.AddLayer(thedf,bufferLayer,"Top")
    thedf.extent = bufferLayer.getSelectedExtent(False)
    thedf.scale = thedf.scale * 1.1
def addOrdergeomtoMxd(ordergeomName, thedf,orderGeomlyrfile,scratch_folder):
    orderGeomLayer = arcpy.mapping.Layer(orderGeomlyrfile)
    orderGeomLayer.replaceDataSource(scratch_folder,"SHAPEFILE_WORKSPACE",ordergeomName)
    arcpy.mapping.AddLayer(thedf,orderGeomLayer,"Top")
def if_multipage(geometry_PCS_shp):
    geomExtent = arcpy.Describe(geometry_PCS_shp).extent
    if geomExtent.width > 1300 or geomExtent.height > 1300:
        return True
    else:
        return False
def generate_singlepage_report(order_obj,mxd_wetland,outputjpg_wetland,scratch_folder):
    mxd_wetland.saveACopy(os.path.join(scratch_folder, "mxd_wetland.mxd"))
    arcpy.mapping.ExportToJPEG(mxd_wetland, outputjpg_wetland, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
    if not os.path.exists(os.path.join(config.report_path, 'PSRmaps', str(order_obj.number))):
        os.mkdir(os.path.join(config.report_path, 'PSRmaps', str(order_obj.number)))
    shutil.copy(outputjpg_wetland, os.path.join(config.report_path, 'PSRmaps', str(order_obj.number)))
    arcpy.AddMessage('      - Wetland Output: %s' % os.path.join(config.report_path, 'PSRmaps', str(order_obj.number)))
    del mxd_wetland
def generate_multipage_report(order_obj,mxd_wetland,outputjpg_wetland,buffer_wetland_shp,df_wetland,orderGeomlyrfile,scratchfolder):
    gridlr = "gridlr_wetland"   # gdb feature class doesn't work, could be a bug. So use .shp
    gridlrshp = os.path.join(scratchfolder, gridlr)
    gridlrshp = arcpy.GridIndexFeatures_cartography(gridlrshp, buffer_wetland_shp, "", "", "", "2 MILES", "2 MILES")  #note the tool takes featureclass name only, not the full path
    spatial_ref = arcpy.Describe(buffer_wetland_shp).spatialReference
    # part 1: the overview map
    # add grid layer
    gridLayer = arcpy.mapping.Layer(config.grid_lyr_file)
    gridLayer.replaceDataSource(scratchfolder,"SHAPEFILE_WORKSPACE",gridlr)
    arcpy.mapping.AddLayer(df_wetland,gridLayer,"Top")
    df_wetland.extent = gridLayer.getExtent()
    df_wetland.scale = df_wetland.scale * 1.1
    mxd_wetland.saveACopy(os.path.join(scratchfolder, "mxd_wetland.mxd"))
    arcpy.mapping.ExportToJPEG(mxd_wetland, outputjpg_wetland, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
    if not os.path.exists(os.path.join(config.report_path, 'PSRmaps', order_obj.number)):
        os.mkdir(os.path.join(config.report_path, 'PSRmaps', order_obj.number))
    shutil.copy(outputjpg_wetland, os.path.join(config.report_path, 'PSRmaps', order_obj.number))
    arcpy.AddMessage('      - Wetland Output: %s' % os.path.join(config.report_path, 'PSRmaps', str(order_obj.number)))
    del mxd_wetland
    del df_wetland

    ### part 2: the data driven pages
    page = 1
    page = int(arcpy.GetCount_management(gridlrshp).getOutput(0))  + page
    mxdMM_wetland = arcpy.mapping.MapDocument(config.mxdMMfile_wetland)
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
        if not os.path.exists(os.path.join(config.report_path, 'PSRmaps', order_obj.number)):
            os.mkdir(os.path.join(config.report_path, 'PSRmaps', order_obj.number))
        shutil.copy(outputjpg_wetland[0:-4]+str(i)+".jpg", os.path.join(config.report_path, 'PSRmaps', order_obj.number))
    del mxdMM_wetland
    del dfMM_wetland
    
def generate_wetland_report(order_obj):
    arcpy.AddMessage('  -- Start generating PSR wetland report...')
    start = timeit.default_timer()   
    ### set scratch folder
    arcpy.env.workspace = config.scratch_folder
    arcpy.env.overwriteOutput = True   
    ### set paths
    orderGeo_GCS_shp= os.path.join(config.scratch_folder,"orderGeo_GCS_shp.shp")
    order_geometry_pcs_shp = os.path.join(config.scratch_folder,"orderGeometry_PCS.shp")
    buffer_wetland_shp = os.path.join(config.scratch_folder,"buffer_wetland.shp")
    
    output_jpg_wetland = config.output_jpg(order_obj,config.Report_Type.wetland)
    output_jpg_ny_wetland = os.path.join(config.scratch_folder, str(order_obj.number)+'_NY_WETL.jpg')
    
    centre_point = order_obj.geometry.trueCentroid
    sr = arcpy.GetUTMFromLocation(centre_point.X,centre_point.Y)
    order_geometry_pcs = order_obj.geometry.projectAs(sr)
    arcpy.CopyFeatures_management(order_geometry_pcs, order_geometry_pcs_shp)
    multipage_wetland = utility.if_multipage(order_geometry_pcs_shp)
    psr_list = order_obj.get_psr()
    if len(psr_list) > 0:
        ### Wetland Map
        wetland_radius = next(psr.search_radius for psr in psr_list if psr.type.lower() == 'wetland')
        bufferDist_wetland = str(wetland_radius) + ' MILES'
        arcpy.Buffer_analysis(order_geometry_pcs_shp, buffer_wetland_shp, bufferDist_wetland)
        mxd_wetland = arcpy.mapping.MapDocument(config.mxdfile_wetland)
        df_wetland = arcpy.mapping.ListDataFrames(mxd_wetland,"big")[0]
        df_wetland.spatialReference = sr
        df_wetlandsmall = arcpy.mapping.ListDataFrames(mxd_wetland,"small")[0]
        df_wetlandsmall.spatialReference = sr
        del df_wetlandsmall
        addBuffertoMxd("buffer_wetland",df_wetland,config.scratch_folder)
        addOrdergeomtoMxd("orderGeometry_PCS", df_wetland,config.order_geom_lyr_file,config.scratch_folder)
        arcpy.AddMessage('      - multiple pages: %s' % str(multipage_wetland))
        # print the maps
        if not multipage_wetland :  # sinle page report
           generate_singlepage_report(order_obj,mxd_wetland,output_jpg_wetland,config.scratch_folder)
        else:                           # multipage report
            generate_multipage_report(order_obj,mxd_wetland,output_jpg_wetland,buffer_wetland_shp,df_wetland,config.order_geom_lyr_file,config.scratch_folder)
        end = timeit.default_timer()
        arcpy.AddMessage((' -- End generating PSR Wetland report. Duration:', round(end -start,4)))
    else:
        arcpy.AddWarning('There is no wetland PSR for this Order!')
   
   ### Create wetlan report for Newyork province
    if order_obj.province =='NY':
        arcpy.AddMessage ("      - Starting NY wetland section: " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
        buffer_wetland_shp = os.path.join(config.scratch_folder,"buffer_wetland.shp")
        mxd_wetlandNY = arcpy.mapping.MapDocument(config.mxdfile_wetlandNY)
        df_wetlandNY = arcpy.mapping.ListDataFrames(mxd_wetlandNY,"big")[0]
        df_wetlandNY.spatialReference = sr
        addBuffertoMxd("buffer_wetland",df_wetlandNY, config.scratch_folder)
        addOrdergeomtoMxd("orderGeometry_PCS", df_wetlandNY, config.order_geom_lyr_file,config.scratch_folder)
        page = 1
        ### print the maps
        if multipage_wetland == False:
            mxd_wetlandNY.saveACopy(os.path.join(config.scratch_folder, "mxd_wetlandNY.mxd"))
            arcpy.mapping.ExportToJPEG(mxd_wetlandNY, output_jpg_ny_wetland, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
            shutil.copy(output_jpg_ny_wetland, os.path.join(config.report_path, 'PSRmaps', order_obj.number))
            arcpy.AddMessage('      - Wetland Output for NY state: %s' % os.path.join(config.report_path, 'PSRmaps', order_obj.number))
            del mxd_wetlandNY
            del df_wetlandNY
        else:                           # multipage
            grid_lyr = "gridlr_wetland"
            gridlrshp = os.path.join(config.scratch_folder, grid_lyr)
            arcpy.GridIndexFeatures_cartography(gridlrshp, buffer_wetland_shp, "", "", "", config.grid_size, config.grid_size)  #note the tool takes featureclass name only, not the full path

            # part 1: the overview map
            # add grid layer
            gridLayer = arcpy.mapping.Layer(config.gridlyrfile)
            gridLayer.replaceDataSource(config.scratch_folder,"SHAPEFILE_WORKSPACE","gridlr_wetland")
            arcpy.mapping.AddLayer(df_wetlandNY,gridLayer,"Top")

            df_wetlandNY.extent = gridLayer.getExtent()
            df_wetlandNY.scale = df_wetlandNY.scale * 1.1

            mxd_wetlandNY.saveACopy(os.path.join(config.scratch_folder, "mxd_wetlandNY.mxd"))
            arcpy.mapping.ExportToJPEG(mxd_wetlandNY, output_jpg_ny_wetland, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
            if not os.path.exists(os.path.join(config.report_path, 'PSRmaps', order_obj.number)):
                os.mkdir(os.path.join(config.report_path, 'PSRmaps', order_obj.number))
            shutil.copy(output_jpg_ny_wetland, os.path.join(config.report_path, 'PSRmaps', order_obj.number))

            del mxd_wetlandNY
            del df_wetlandNY

            # part 2: the data driven pages
            
            page = int(arcpy.GetCount_management(gridlrshp).getOutput(0))  + page
            mxdMM_wetlandNY = arcpy.mapping.MapDocument(config.mxdMMfile_wetlandNY)

            dfMM_wetlandNY = arcpy.mapping.ListDataFrames(mxdMM_wetlandNY,"big")[0]
            dfMM_wetlandNY.spatialReference = sr
            addBuffertoMxd("buffer_wetland",dfMM_wetlandNY)
            addOrdergeomtoMxd("ordergeoNamePR", dfMM_wetlandNY)
            gridlayerMM = arcpy.mapping.ListLayers(mxdMM_wetlandNY,"Grid" ,dfMM_wetlandNY)[0]
            gridlayerMM.replaceDataSource(config.scratch_folder, "FILEGDB_WORKSPACE","gridlr_wetland")
            arcpy.CalculateAdjacentFields_cartography(gridlrshp, "PageNumber")
            mxdMM_wetlandNY.saveACopy(os.path.join(config.scratch_folder, "mxdMM_wetlandNY.mxd"))

            for i in range(1,int(arcpy.GetCount_management(gridlrshp).getOutput(0))+1):
                arcpy.SelectLayerByAttribute_management(gridlayerMM, "NEW_SELECTION", ' "PageNumber" =  ' + str(i))
                dfMM_wetlandNY.extent = gridlayerMM.getSelectedExtent(True)
                dfMM_wetlandNY.scale = dfMM_wetlandNY.scale * 1.1
                arcpy.SelectLayerByAttribute_management(gridlayerMM, "CLEAR_SELECTION")
                titleTextE = arcpy.mapping.ListLayoutElements(mxdMM_wetlandNY, "TEXT_ELEMENT", "title")[0]
                titleTextE.text = "NY Wetland Type - Page " + str(i)
                titleTextE.elementPositionX = 0.468
                arcpy.RefreshTOC()
                arcpy.mapping.ExportToJPEG(mxdMM_wetlandNY, output_jpg_ny_wetland[0:-4]+str(i)+".jpg", "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                if not os.path.exists(os.path.join(config.report_path, 'PSRmaps', order_obj.number)):
                    os.mkdir(os.path.join(config.report_path, 'PSRmaps', order_obj.number))
                shutil.copy(output_jpg_ny_wetland[0:-4]+str(i)+".jpg", os.path.join(config.report_path, 'PSRmaps', order_obj.number))
                arcpy.AddMessage('      - Wetland Output for NY state: %s' % os.path.join(config.report_path, 'PSRmaps', order_obj.number))
            del mxdMM_wetlandNY
            del dfMM_wetlandNY
        psr_obj = models.PSR()
        for i in range(1,page): #insert generated .jpg report path into eris_maps_psr table
            psr_obj.insert_map(order_obj.id, 'WETLAND', order_obj.number +'_NY_WETL'+str(i)+'.jpg', int(i)+1)
           
   