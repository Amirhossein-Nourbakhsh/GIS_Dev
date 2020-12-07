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
   orderId = '462873' # no psr ->'354268' ## newyork
   # order_Id = '932499' # multi page
   arcpy.AddMessage('Start PSR report...')
   start = timeit.default_timer() 
   
   scratchfolder =  arcpy.env.scratchFolder
   arcpy.CreateFileGDB_management(scratchfolder,r"temp.gdb") 
   tempGDB = os.path.join(scratchfolder,r"temp.gdb")
   # Fetch data from database using GIS framework
   # orderObj = models.Order().getbyId(932499)
   # orderObj = models.Order().getbyNumber(20292800115) # single page
   orderObj = models.Order().getbyId(orderId)
   # Generate Wetland report
   wetland.Generate_WetlandReport(orderObj)
   # Generate flood report
   # flood_plain.Generate_FloodReport(orderObj)
   end = timeit.default_timer()
   arcpy.AddMessage(('End PSR report process. Duration:', round(end -start,4)))