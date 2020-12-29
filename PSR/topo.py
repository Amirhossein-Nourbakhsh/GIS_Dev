
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

def generate_topo_report(order_obj):
    arcpy.AddMessage('  -- Start generating PSR topo report...')
    start = timeit.default_timer()  
    ### set scratch folder
    scratch_folder =  arcpy.env.scratchFolder
    arcpy.env.workspace = scratch_folder
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage('      - scratch folder: %s' %scratch_folder)
    ### set paths
    buffer_topo_shp = os.path.join(scratch_folder,"buffer_topo.shp")
    arcpy.Buffer_analysis(orderGeometryPR, bufferSHP_topo, bufferDist_topo)
    
    
    
    
    end = timeit.default_timer()
    arcpy.AddMessage((' -- End generating PSR topo report. Duration:', round(end -start,4)))