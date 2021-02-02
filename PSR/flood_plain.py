from imp import reload
import arcpy, os, sys
from datetime import datetime
import timeit,time
import shutil
import psr_utility as utility
import psr_config as config
file_path =os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1,os.path.join(os.path.dirname(file_path),'DB_Framework'))
import models
reload(sys)
def generate_flood_report(order_obj):
    arcpy.AddMessage('  -- Start generating PSR flood report...')
    start = timeit.default_timer()   
    ### set scratch folder
    arcpy.env.workspace = config.scratch_folder
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage('      - scratch folder: %s' % config.scratch_folder)
    eris_id = 0
    output_jpg_flood = config.output_jpg(order_obj,config.Report_Type.flood)
    ### extract buffer size for flood report
    psr_list = order_obj.get_psr()
    page = 1
    if len(psr_list) > 0:
        buffer_radius = next(psr.search_radius for psr in psr_list if psr.type.lower() == 'flood')
       
        order_buffer_dist = str(buffer_radius) + ' MILES'
        arcpy.Buffer_analysis(config.order_geometry_pcs_shp, config.order_buffer_shp, order_buffer_dist) ### create buffer map based on order geometry
        
        arcpy.MakeFeatureLayer_management(config.data_flood, 'flood_lyr') 
        arcpy.SelectLayerByLocation_management('flood_lyr', 'intersect',  config.order_buffer_shp)
        arcpy.CopyFeatures_management('flood_lyr', config.flood_selectedby_order_shp)
        
        arcpy.MakeFeatureLayer_management(config.data_flood_panel, 'flood_panel_lyr') 
        arcpy.SelectLayerByLocation_management('flood_panel_lyr', 'intersect',  config.order_buffer_shp)
        arcpy.CopyFeatures_management('flood_panel_lyr', config.flood_panel_selectedby_order_shp)
        
        arcpy.Statistics_analysis(config.flood_selectedby_order_shp, os.path.join(config.scratch_folder,"summary_flood.dbf"), [['FLD_ZONE','FIRST'], ['ZONE_SUBTY','FIRST']],'ERIS_CLASS')
        arcpy.Sort_management(os.path.join(config.scratch_folder,"summary_flood.dbf"), os.path.join(config.scratch_folder,"summary_sorted_flood.dbf"), [["ERIS_CLASS", "ASCENDING"]])
        
        mxd_flood = arcpy.mapping.MapDocument(config.mxd_file_flood)
        df_flood = arcpy.mapping.ListDataFrames(mxd_flood,"Flood*")[0]
        df_flood.spatialReference = config.spatial_ref_pcs
        
        df_floodsmall = arcpy.mapping.ListDataFrames(mxd_flood,"Study*")[0]
        df_floodsmall.spatialReference = config.spatial_ref_pcs
        del df_floodsmall
        
        utility.add_layer_to_mxd("order_buffer",df_flood,config.buffer_lyr_file, 1.1)
        utility.add_layer_to_mxd("order_geometry_pcs", df_flood,config.order_geom_lyr_file,1)
        arcpy.RefreshActiveView();
        arcpy.AddMessage('      - multiple pages: %s' % str(utility.if_multipage(config.order_geometry_pcs_shp)))
        if not utility.if_multipage(config.order_geometry_pcs_shp): # single-page
            mxd_flood.saveACopy(os.path.join(config.scratch_folder, "mxd_flood.mxd"))  
            arcpy.mapping.ExportToJPEG(mxd_flood, output_jpg_flood, "PAGE_LAYOUT", resolution=75, jpeg_quality=40)
            if not os.path.exists(os.path.join(config.report_path, 'PSRmaps', order_obj.number)):
                os.mkdir(os.path.join(config.report_path, 'PSRmaps', order_obj.number))
            arcpy.AddMessage('      - output jpg image path (overview map): %s' % os.path.join(config.report_path, 'PSRmaps', order_obj.number,os.path.basename(output_jpg_flood)))
            shutil.copy(output_jpg_flood, os.path.join(config.report_path, 'PSRmaps', order_obj.number))
            del mxd_flood
            del df_flood
        else: # multi-page
            grid_lyr_shp = os.path.join(config.scratch_folder, 'grid_lyr_flood.shp')
            arcpy.GridIndexFeatures_cartography(grid_lyr_shp, config.order_buffer_shp, "", "", "", config.grid_size, config.grid_size)
            
            # part 1: the overview map
            # add grid layer
            grid_layer = arcpy.mapping.Layer(config.grid_lyr_file)
            grid_layer.replaceDataSource(config.scratch_folder,"SHAPEFILE_WORKSPACE","grid_lyr_flood")
            arcpy.mapping.AddLayer(df_flood,grid_layer,"Top")

            df_flood.extent = grid_layer.getExtent()
            df_flood.scale = df_flood.scale * 1.1

            mxd_flood.saveACopy(os.path.join(config.scratch_folder, "mxd_flood.mxd"))
            arcpy.mapping.ExportToJPEG(mxd_flood, output_jpg_flood, "PAGE_LAYOUT", 480, 640, 75, "False", "24-BIT_TRUE_COLOR", 40)
            if not os.path.exists(os.path.join(config.report_path, 'PSRmaps', order_obj.number)):
                os.mkdir(os.path.join(config.report_path, 'PSRmaps', order_obj.number))
            shutil.copy(output_jpg_flood, os.path.join(config.report_path, 'PSRmaps', order_obj.number))
            arcpy.AddMessage('      - output jpg image page 1: %s' % os.path.join(config.report_path, 'PSRmaps', order_obj.number,os.path.basename(output_jpg_flood)))
            del mxd_flood
            del df_flood
            # part 2: the data driven pages
            
            page = int(arcpy.GetCount_management(grid_lyr_shp).getOutput(0))  + page
            mxd_multi_flood = arcpy.mapping.MapDocument(config.mxd_mm_file_flood)

            df_mm_flood = arcpy.mapping.ListDataFrames(mxd_multi_flood,"Flood*")[0]
            df_mm_flood.spatialReference = config.spatial_ref_pcs
            utility.add_layer_to_mxd("order_buffer",df_mm_flood,config.buffer_lyr_file,1.1)
            utility.add_layer_to_mxd("order_geometry_pcs", df_mm_flood,config.order_geom_lyr_file,1)
            
            grid_layer_mm = arcpy.mapping.ListLayers(mxd_multi_flood,"Grid" ,df_mm_flood)[0]
            grid_layer_mm.replaceDataSource(config.scratch_folder,"SHAPEFILE_WORKSPACE","grid_lyr_flood")
            arcpy.CalculateAdjacentFields_cartography(grid_lyr_shp, "PageNumber")
            mxd_multi_flood.saveACopy(os.path.join(config.scratch_folder, "mxd_mm_flood.mxd"))
            
            for i in range(1,int(arcpy.GetCount_management(grid_lyr_shp).getOutput(0)) + 1):
                arcpy.SelectLayerByAttribute_management(grid_layer_mm, "NEW_SELECTION", ' "PageNumber" =  ' + str(i))
                df_mm_flood.extent = grid_layer_mm.getSelectedExtent(True)
                df_mm_flood.scale = df_mm_flood.scale * 1.1
                arcpy.SelectLayerByAttribute_management(grid_layer_mm, "CLEAR_SELECTION")

                titleTextE = arcpy.mapping.ListLayoutElements(mxd_multi_flood, "TEXT_ELEMENT", "title")[0]
                titleTextE.text = '      - Flood Hazard Zones - Page ' + str(i)
                titleTextE.elementPositionX = 0.5946
                arcpy.RefreshTOC()

                arcpy.mapping.ExportToJPEG(mxd_multi_flood, output_jpg_flood[0:-4]+str(i)+".jpg", "PAGE_LAYOUT", 480, 640, 75, "False", "24-BIT_TRUE_COLOR", 40)
                if not os.path.exists(os.path.join(config.report_path, 'PSRmaps', order_obj.number)):
                    os.mkdir(os.path.join(config.report_path, 'PSRmaps', order_obj.number))
                shutil.copy(output_jpg_flood[0:-4]+str(i)+".jpg", os.path.join(config.report_path, 'PSRmaps', order_obj.number))
                ### update tables in DB
                page = int(arcpy.GetCount_management(grid_lyr_shp).getOutput(0))  + page
                psr_obj = models.PSR()
                for i in range(1,page):
                    psr_obj.insert_map(order_obj.id, 'FLOOD', order_obj.number + '_US_FLOOD' + str(i) + '.jpg', i + 1)
            del mxd_multi_flood
            del df_mm_flood
            
        flood_panels = ''
        psr_obj = models.PSR()
        if (int(arcpy.GetCount_management(os.path.join(config.scratch_folder,"summary_flood.dbf")).getOutput(0))== 0):
            # no floodplain records selected....
            arcpy.AddMessage('      - No floodplain records are selected....')
            if (int(arcpy.GetCount_management(config.flood_panel_selectedby_order_shp).getOutput(0))== 0):
                # no panel available, means no data
                arcpy.AddMessage('      - no panels available in the area')
            else:
                # panel available, just not records in area
                in_rows = arcpy.SearchCursor(config.flood_panel_selectedby_order_shp)
                for in_row in in_rows:
                    arcpy.AddMessage('      - : ' + in_row.FIRM_PAN)    # panel number
                    arcpy.AddMessage('      - %s' % in_row.EFF_DATE)      # effective date
                    flood_panels = flood_panels + in_row.FIRM_PAN+'(effective:' + str(in_row.EFF_DATE)[0:10]+') '
                    del in_row
                del in_rows
            
            if len(flood_panels) > 0:
                eris_id += 1
                arcpy.AddMessage('      - erisid for flood_panels is ' + str(eris_id))
                psr_obj.insert_order_detail(order_obj.id,eris_id, '10683')   
                psr_obj.insert_flex_rep(order_obj, eris_id, '10683', 2, 'N', 1, 'Available FIRM Panels in area: ', flood_panels)
            psr_obj.insert_map(order_obj.id, 'FLOOD', order_obj.number + '_US_FLOOD.jpg', 1)
        else:
            in_rows = arcpy.SearchCursor(config.flood_panel_selectedby_order_shp)
            for in_row in in_rows:
                arcpy.AddMessage('      : ' + in_row.FIRM_PAN)      # panel number
                arcpy.AddMessage('      - %s' %in_row.EFF_DATE)             # effective date
                flood_panels = flood_panels + in_row.FIRM_PAN+'(effective:' + str(in_row.EFF_DATE)[0:10]+') '
                del in_row
            del in_rows

            flood_IDs =[]
            in_rows = arcpy.SearchCursor(os.path.join(config.scratch_folder,"summary_flood.dbf"))
            eris_id += 1
            psr_obj.insert_order_detail(order_obj.id , eris_id, '10683')
            psr_obj.insert_flex_rep(order_obj.id, eris_id, '10683', 2, 'N', 1, 'Available FIRM Panels in area: ', flood_panels)
          
            for in_row in in_rows:
                # note the column changed in summary dbf
                arcpy.AddMessage('      : ' + in_row.ERIS_CLASS)    # eris label
                arcpy.AddMessage('      : ' + (in_row.FIRST_FLD_))           # zone type
                arcpy.AddMessage('      : '+ (in_row.FIRST_ZONE))           # subtype

                eris_id += 1
                flood_IDs.append([in_row.ERIS_CLASS,eris_id])
                
                psr_obj.insert_order_detail(order_obj.id,eris_id, '10683')   
                psr_obj.insert_flex_rep(order_obj.id, eris_id, '10683', 2, 'S1', 1, 'Flood Zone ' + in_row.ERIS_CLASS, '')
                psr_obj.insert_flex_rep(order_obj.id, eris_id, '10683', 2, 'N', 2, 'Zone: ', in_row.FIRST_FLD_)
                psr_obj.insert_flex_rep(order_obj.id, eris_id, '10683', 2, 'N', 3, 'Zone subtype: ', in_row.FIRST_ZONE)
                del in_row
            del in_rows
            psr_obj.insert_map(order_obj.id, 'FLOOD', order_obj.number + '_US_FLOOD.jpg'+'.jpg', 1)
            
    else:
        arcpy.AddWarning('      - There is no floorplain PSR for this Order!')
    end = timeit.default_timer()
    arcpy.AddMessage((' -- End generating PSR flood report. Duration:', round(end -start,4)))