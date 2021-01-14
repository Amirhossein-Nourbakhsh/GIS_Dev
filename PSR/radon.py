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
def generate_radon_report(order_obj):
    arcpy.AddMessage('  -- Start generating PSR Radon report...')
    start = timeit.default_timer()   
    ### set scratch folder
    arcpy.env.workspace = config.scratch_folder
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage('      - scratch folder: %s' % config.scratch_folder)
    
    ### extract buffer size for flood report
    psr_list = order_obj.get_psr()
    if len(psr_list) > 0:
        buffer_radius = next(psr.search_radius for psr in psr_list if psr.type == 'radon')
        order_buffer_dist = str(buffer_radius) + ' MILES'
        ### create buffer map based on order geometry
        arcpy.Buffer_analysis(config.order_geometry_pcs_shp, config.order_buffer_shp, order_buffer_dist) 
        
        arcpy.MakeFeatureLayer_management(config.master_lyr_states, 'states_lyr') 
        arcpy.SelectLayerByLocation_management('states_lyr', 'intersect',  config.order_buffer_shp)
        arcpy.CopyFeatures_management('states_lyr', config.states_selectedby_order)
        
    else:
        arcpy.AddWarning('      - There is no Radon PSR for this Order!')
    
    end = timeit.default_timer()
    arcpy.AddMessage((' -- End generating PSR Radon report. Duration:', round(end -start,4)))