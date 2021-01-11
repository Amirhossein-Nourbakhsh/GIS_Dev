import arcpy, os,sys, timeit
from imp import reload
file_path =os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1,os.path.join(os.path.dirname(file_path),'DB_Framework'))
import models
import psr_utility as utility
import psr_config as config
import flood_plain
import topo
import relief
import wetland
import geology
import soil

reload(sys)
sys.setdefaultencoding('utf8')
psr_list = []

if __name__ == "__main__":
   # order_id = '930894' #single pages: 20292800115 - 20200814009
   # order_id = '462873' # no psr ->'354268' ## newyork
   order_id = '932499' # multi page
   arcpy.AddMessage('Start PSR report...')
   start = timeit.default_timer() 
   ### set workspace
   arcpy.env.workspace = config.scratch_folder
   arcpy.env.overwriteOutput = True   
   # temp gdb in scratch folder
   temp_gdb = os.path.join(config.scratch_folder,r"temp.gdb")
   
   if not os.path.exists(temp_gdb):
      arcpy.CreateFileGDB_management(config.scratch_folder,r"temp") 
   ### isntantiate of order class and set order geometry and buffering
   order_obj = models.Order().get_by_Id(order_id)
   utility.set_order_geometry(order_obj)
   
   # shaded releif map report
   # relief.generate_relief_report(order_obj)
   
   # topo map report
   # topo.generate_topo_report(order_obj)

   # # Wetland report
   # wetland.generate_wetland_report(order_obj)
   
   # # flood report
   # flood_plain.generate_flood_report(order_obj)
   
   # # geology report
   # geology.generate_geology_report(order_obj)
   
   # soil report
   soil.generate_soil_report(order_obj)
   
   end = timeit.default_timer()
   arcpy.AddMessage(('End PSR report process. Duration:', round(end -start,4)))