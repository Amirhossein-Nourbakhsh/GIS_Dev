from imp import reload
import shutil, csv
import cx_Oracle,urllib, glob
import arcpy, os, numpy
from datetime import datetime
# import getDirectionText
import gc, time
import traceback
from numpy import gradient
from numpy import arctan2, arctan, sqrt
import psr_config
import wetland
import flood_plain
import os,sys, timeit
sys.path.insert(1,os.path.join(os.getcwd(),'DB_Framework'))
import models
reload(sys)
sys.setdefaultencoding('utf8')
psr_list = []


if __name__ == "__main__":
   # orderId = '930894' #single pages: 20292800115 - 20200814009
   order_id = '462873' # no psr ->'354268' ## newyork
   # order_Id = '932499' # multi page
   arcpy.AddMessage('Start PSR report...')
   start = timeit.default_timer() 
 ### set scratch folder  
   scratch_folder =  arcpy.env.scratchFolder
   arcpy.env.workspace = scratch_folder
   arcpy.env.overwriteOutput = True   
   
   ### temp gdb in scratch folder
   temp_gdb =os.path.join(scratch_folder,r"temp.gdb")
   if not os.path.exists(temp_gdb):
      arcpy.CreateFileGDB_management(scratch_folder,r"temp_gdb") 
   
   # Fetch data from database using GIS framework
   # orderObj = models.Order().getbyId(932499)
   # orderObj = models.Order().getbyNumber(20292800115) # single page
   order_obj = models.Order().getbyId(order_id)

   print(order_obj.geometry)
   # Generate Wetland report
   # wetland.Generate_WetlandReport(order_obj)
   # Generate flood report
   flood_plain.Generate_FloodReport(order_obj)
   end = timeit.default_timer()
   arcpy.AddMessage(('End PSR report process. Duration:', round(end -start,4)))