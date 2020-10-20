import shutil, csv
import cx_Oracle,urllib, glob
import arcpy, os, numpy
from datetime import datetime
import getDirectionText
import gc, time
import traceback
from numpy import gradient
from numpy import arctan2, arctan, sqrt
import PSR_config
import PSR_Wetland
import json
import os,sys, timeit
sys.path.insert(1,os.path.join(os.getcwd(),'DB_Framework'))
import models
reload(sys)
sys.setdefaultencoding('utf8')
psr_list = []
if __name__ == "__main__":
   order_Id = '932499'
   arcpy.AddMessage('Start PSR report...')
   start = timeit.default_timer() 
   # Fetch data from database using GIS framework
   orderObj = models.Order().getbyId(932499)
   # Generate Wetland report
   PSR_Wetland.Generate_WetlandReport(orderObj)
   end = timeit.default_timer()
   arcpy.AddMessage(('End PSR report process. Duration:', round(end -start,4)))