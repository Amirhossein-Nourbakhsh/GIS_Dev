
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

def generate_topo_report(order_obj):
    arcpy.AddMessage('  -- Start generating PSR topo report...')
    start = timeit.default_timer()  
    ### set scratch folder
    scratch_folder =  arcpy.env.scratchFolder
    arcpy.env.workspace = scratch_folder
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage('      - scratch folder: %s' %scratch_folder)
    ### set paths
    output_jpg_topo = config.output_jpg(order_obj,config.Report_Type.topo)
    ### extract buffer size for topo report
    psr_list = order_obj.get_psr()
    
    if len(psr_list) > 0:
        buffer_radius = next(psr.search_radius for psr in psr_list if psr.type == 'topo')
        order_buffer_dist = str(buffer_radius) + ' MILES'
        ### create buffer map based on order geometry
        arcpy.Buffer_analysis(config.order_geometry_pcs_shp, config.order_buffer_shp, order_buffer_dist) 
    else:
        arcpy.AddWarning('      - There is no topo PSR for this Order!')
    end = timeit.default_timer()
    arcpy.AddMessage(('-- End generating PSR topo report. Duration:', round(end -start,4)))