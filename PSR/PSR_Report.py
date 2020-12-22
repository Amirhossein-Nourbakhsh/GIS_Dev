import gc, time
import os,sys, timeit
from imp import reload
import shutil, csv
import cx_Oracle,urllib, glob
import arcpy, os, numpy
from datetime import datetime
# import getDirectionText
import traceback
from numpy import gradient
from numpy import arctan2, arctan, sqrt
file_path =os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1,os.path.join(os.path.dirname(file_path),'DB_Framework'))
import models
import wetland
import flood_plain
import psr_config


reload(sys)
sys.setdefaultencoding('utf8')
psr_list = []

if __name__ == "__main__":

   # order_id = '930894' #single pages: 20292800115 - 20200814009
   # order_id = '462873' # no psr ->'354268' ## newyork
   order_id = '932499' # multi page
   arcpy.AddMessage('Start PSR report...')
   start = timeit.default_timer() 
 ### set scratch folder  
   scratch_folder =  arcpy.env.scratchFolder
   arcpy.env.workspace = scratch_folder
   arcpy.env.overwriteOutput = True   
   
   ### temp gdb in scratch folder
   temp_gdb =os.path.join(scratch_folder,r"temp.gdb")
   if not os.path.exists(temp_gdb):
      arcpy.CreateFileGDB_management(scratch_folder,r"temp") 
   
   order_obj = models.Order().get_by_Id(order_id)

   # Wetland report
   # wetland.Generate_WetlandReport(order_obj)
   
   # flood report
   flood_plain.generate_flood_report(order_obj)
   
   
   
   end = timeit.default_timer()
   arcpy.AddMessage(('End PSR report process. Duration:', round(end -start,4)))