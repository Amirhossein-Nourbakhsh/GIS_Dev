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
import json
import os,sys
sys.path.insert(1,os.path.join(os.getcwd(),'DB_Framework'))
import models
reload(sys)
sys.setdefaultencoding('utf8')
psr_list = []
if __name__ == "__main__":
   scratchfolder = arcpy.env.scratchFolder
   arcpy.env.overWriteOutput = True
   outputjpg_wetland = os.path.join(scratchfolder, OrderNumText+'_US_WETL.jpg')
   # Fetch data from database using GIS framework
   orderObj =models. Order().getbyId(932499)
   order_geo = models.OrderGeometry().getbyId(932499)
   psr_list = orderObj.getPSR()
   
   ### Wetland Map , no attributes