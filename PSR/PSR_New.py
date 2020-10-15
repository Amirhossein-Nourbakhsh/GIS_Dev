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

if __name__ == "__main__":
   order = models.order().getbyId(932499)
#    order2 = models.order().getbyNumber(20293000254)
   print(order.order_num) 
  
   