from imp import reload
import arcpy, os, sys
import timeit
import shutil
import psr_utility as utility
import psr_config as config
sys.path.insert(1,os.path.join(os.getcwd(),'DB_Framework'))
reload(sys)
import models

def generate_soil_report(order_obj):
    arcpy.AddMessage('  -- Start generating PSR soil report...')
    start = timeit.default_timer() 
    ### set scratch folder
    arcpy.env.workspace = config.scratch_folder
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage('      - scratch folder: %s' % config.scratch_folder)
    output_jpg_soil = config.output_jpg(order_obj,config.Report_Type.soil)
    
    ### extract buffer size for soil report
    psr_list = order_obj.get_psr()
    page = 1
    eris_id = 0
    if len(psr_list) > 0:
        
        buffer_radius = next(psr.search_radius for psr in psr_list if psr.type == 'soil')
        order_buffer_dist = str(buffer_radius) + ' MILES'
        ### create buffer map based on order geometry
        arcpy.Buffer_analysis(config.order_geometry_pcs_shp, config.order_buffer_shp, order_buffer_dist) 
        
        if order_obj.province == 'HI':
            data_path_soil = config.data_path_soil_HI
        elif order_obj.province == 'AK':
            data_path_soil = config.data_path_soil_AK
        else:
            data_path_soil = config.data_path_soil_CONUS
            
        data_soil = os.path.join(data_path_soil,'MUPOLYGON')
        # select soil data by using spatial query of order buffere layer
        arcpy.MakeFeatureLayer_management(data_soil,'soil_lyr') 
        arcpy.SelectLayerByLocation_management('soil_lyr', 'intersect',  config.order_buffer_shp)
        arcpy.CopyFeatures_management('soil_lyr', config.soil_selectedby_order_shp)
        
        table_muaggatt = os.path.join(data_path_soil,'muaggatt')
        table_component = os.path.join(data_path_soil,'component')
        table_chorizon = os.path.join(data_path_soil,'chorizon')
        table_chtexturegrp = os.path.join(data_path_soil,'chtexturegrp')
        
        
        stable_muaggatt = os.path.join(config.scratch_folder,"muaggatt")
        stable_component = os.path.join(config.scratch_folder,"component")
        stable_chorizon = os.path.join(config.scratch_folder,"chorizon")
        stable_chtexture_grp = os.path.join(config.scratch_folder,"chtexture_grp")
        
        if (int(arcpy.GetCount_management('soil_lyr').getOutput(0)) == 0):   # no soil polygons selected
            arcpy.AddMessage('no soil data in order geometry buffer')
            psr_obj = models.PCR()
            eris_id = eris_id + 1
            psr_obj.insert_flex_rep(order_obj.id, eris_id, '9334', 2, 'N', 1, 'No soil data available in the project area.', '')
        else:
            soil_selectedby_order_pcs_shp = arcpy.Project_management(config.soil_selectedby_order_shp, config.soil_selectedby_order_pcs_shp, config.spatial_ref_pcs)
            # create map keys
            arcpy.Statistics_analysis(soil_selectedby_order_pcs_shp, os.path.join(config.scratch_folder,"summary_soil.dbf"), [['mukey','FIRST'],["Shape_Area","SUM"]],'musym')
            arcpy.Sort_management(os.path.join(config.scratch_folder,"summary_soil.dbf"), os.path.join(config.scratch_folder,"summary_sorted_soil.dbf"), [["musym", "ASCENDING"]])
            seq_array = arcpy.da.TableToNumPyArray(os.path.join(config.scratch_folder,'summary_sorted_soil.dbf'), '*')    #note: it could contain 'NOTCOM' record
            # retrieve attributes
            unique_MuKeys = utility.return_unique_setstring_musym(soil_selectedby_order_pcs_shp)
            
            if len(unique_MuKeys) > 0:    # special case: order only returns one "NOTCOM" category, filter out
                where_clause_select_table = "muaggatt.mukey in " + unique_MuKeys
                arcpy.TableSelect_analysis(table_muaggatt, stable_muaggatt, where_clause_select_table)

                where_clause_select_table = "component.mukey in " + unique_MuKeys
                arcpy.TableSelect_analysis(table_component, stable_component, where_clause_select_table)

                unique_CoKeys = utility.return_unique_setString(stable_component, 'cokey')
                where_clause_select_table = "chorizon.cokey in " + unique_CoKeys
                arcpy.TableSelect_analysis(table_chorizon, stable_chorizon, where_clause_select_table)

                unique_achkeys = utility.return_unique_setString(stable_chorizon,'chkey')
                if len(unique_achkeys) > 0:       # special case: e.g. there is only one Urban Land polygon
                    where_clause_select_table = "chorizon.chkey in " + unique_achkeys
                    arcpy.TableSelect_analysis(table_chtexturegrp, stable_chtexture_grp, where_clause_select_table)

                    table_list = [stable_muaggatt, stable_component,stable_chorizon, stable_chtexture_grp]
                    field_list  = config.fc_soils_fieldlist #[['muaggatt.mukey','mukey'], ['muaggatt.musym','musym'], ['muaggatt.muname','muname'],['muaggatt.drclassdcd','drclassdcd'],['muaggatt.hydgrpdcd','hydgrpdcd'],['muaggatt.hydclprs','hydclprs'], ['muaggatt.brockdepmin','brockdepmin'], ['muaggatt.wtdepannmin','wtdepannmin'], ['component.cokey','cokey'],['component.compname','compname'], ['component.comppct_r','comppct_r'], ['component.majcompflag','majcompflag'],['chorizon.chkey','chkey'],['chorizon.hzname','hzname'],['chorizon.hzdept_r','hzdept_r'],['chorizon.hzdepb_r','hzdepb_r'], ['chtexturegrp.chtgkey','chtgkey'], ['chtexturegrp.texdesc1','texdesc'], ['chtexturegrp.rvindicator','rv']]
                    keylist = config.fc_soils_keylis #['muaggatt.mukey', 'component.cokey','chorizon.chkey','chtexturegrp.chtgkey']
                
                    where_clause_query_table = config.fc_soils_whereClause_queryTable#"muaggatt.mukey = component.mukey and component.cokey = chorizon.cokey and chorizon.chkey = chtexturegrp.chkey"
                    #Query tables may only be created using data from a geodatabase or an OLE DB connection
                    query_table_result = arcpy.MakeQueryTable_management(table_list,'queryTable','USE_KEY_FIELDS', keylist, field_list, where_clause_query_table)  #note: outTable is a table view and won't persist

                    arcpy.TableToTable_conversion('query_table',config.scratch_folder, 'soil_table')  #note: 1. <null> values will be retained using .gdb, will be converted to 0 using .dbf; 2. domain values, if there are any, will be retained by using .gdb

                    data_array = arcpy.da.TableToNumPyArray(os.path.join(config.scratch_folder,'soil_table'), '*', null_value = -99)
    else:
        arcpy.AddWarning('      - There is no soil PSR for this Order!')  
        
    
    end = timeit.default_timer()
    arcpy.AddMessage((' -- End generating PSR soil report. Duration:', round(end -start,4)))