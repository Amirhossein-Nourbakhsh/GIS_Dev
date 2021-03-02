#-------------------------------------------------------------------------------
# Name:        USGS Topo retrieval
# Purpose:
#
# Author:      LiuJ
#
# Created:     14/10/2014
# Copyright:   (c) LiuJ 2014
# Licence:     <your licence>
#-------------------------------------------------------------------------------

# changes 11/13/2016: change all maps to fixed scale 1:24000
import json
import arcpy
import os
import sys
import csv
import operator
import shutil
import zipfile
import logging
import traceback
import cx_Oracle
import glob
import urllib
import re
import time
import xml.etree.ElementTree as ET

addpath = os.path.abspath(__file__).replace(os.path.relpath(__file__),"GIS_Dev")
sys.path.insert(1,os.path.join(addpath,'DB_Framework'))
import TOPO_US_func as tp
import TOPO_US_config as cfg
import models

from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.generic import NameObject, createStringObject, ArrayObject, FloatObject
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Frame,Table
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import portrait, letter
from reportlab.pdfgen import canvas

# ----------------------------------------------------------------------------------------------------------------------------------------
'''for quick grab of order_id(s) for testing:
select 
a.order_id, a.order_num, a.site_name,
b.customer_id, 
c.company_id, c.company_desc,
d.radius_type, d.geometry_type, d.geometry,
e.topo_viewer
from orders a, customer b, company c, eris_order_geometry d, order_viewer e
where 
a.customer_id = b.customer_id and
b.company_id = c.company_id and
a.order_id = d.order_id and
a.order_id = e.order_id
and upper(a.site_name) not like '%TEST%'
and upper(c.company_desc) like '%AEI%'
and d.geometry_type = 'POLYGON'
and e.topo_viewer = 'Y'
order by a.order_num DESC;
'''

if __name__ == '__main__':
    print("...starting..." + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
    start = time.clock()

    order_obj = models.Order().get_order(21020700002)
    print("Order: " + str(order_obj.id) + ", " + str(order_obj.number))

    yesBoundary = "yes"
    delyearFlag = 'N'       # for internal use

    pdfreport = order_obj.number + "_US_Topo.pdf"    
    oc = tp.oracle(cfg.connectionString)
    tf = tp.topo_us_rpt(order_obj, yesBoundary)

    try:
        logger,handler = tf.log(cfg.logfile)

        # # GET ORDER_ID AND BOUNDARY FROM ORDER_NUM
        # if yesBoundary == "":
        #     con = cx_Oracle.connect(cfg.connectionString)
        #     cur = con.cursor()

        #     cur.execute("SELECT * FROM ERIS.TOPO_AUDIT WHERE ORDER_ID IN (select order_id from orders where order_num = '" + str(order_obj.number) + "')")
        #     result = cur.fetchall()
        #     yesBoundaryqry = str([row[3] for row in result if row[2]== "URL"][0])
        #     yesBoundary = re.search('(yesBoundary=)(\w+)(&)', yesBoundaryqry).group(2).strip()            
        #     print("Yes Boundary: " + yesBoundary)

        # get custom order flags
        is_nova, is_aei, is_newLogo = tf.customrpt(order_obj)
        
        # get spatial references
        srGCS83,srWGS84,srGoogle,srUTM = tf.projlist(order_obj)

        # create order geometry
        tf.createordergeometry(order_obj,srUTM)
        
        # open mxd and create map extent
        logger.debug("#1")
        mxd, df, orderGeomLayer, bufferLayer = tf.mapDocument(srUTM, is_nova)
        needtif = tf.mapExtent(df, srUTM, bufferLayer)

        # select topo records
        rowsMain, rowsAdj = tf.selectTopo(cfg.orderGeometryPR, cfg.extent, srUTM)
        
        # get topo records
        logger.debug("#2")
        if int(len(rowsMain)) == 0:
            print("...NO records selected.")
        else:
            maps7575, maps1515, yearalldict = tf.getTopoRecords(rowsMain, rowsAdj, cfg.csvfile_h, cfg.csvfile_c)

            # remove duplicated years
            maps7575 = tf.dedupMaplist(maps7575)
            maps1515 = tf.dedupMaplist(maps1515)

            # reorganize data structure
            logger.debug("#4")
            dict7575 = tf.reorgByYear(maps7575, "75")  # {1975: geopdf.pdf, 1973: ...}
            dict1515 = tf.reorgByYear(maps1515, "15")

            # remove blank maps flag
            if delyearFlag == 'Y':
                delyear75 = filter(None, str(raw_input("Years you want to delete in the 7.5min series (comma-delimited no-space):\n>>> ")).replace(" ", "").strip().split(","))
                delyear15 = filter(None, str(raw_input("Years you want to delete in the 15min series (comma-delimited no-space):\n>>> ")).replace(" ", "").strip().split(","))
                tf.delyear(delyear75, delyear15, dict7575, dict1515)

            # create map pdf
            logger.debug("#5")
            if is_aei == 'Y':
                comb7515 = {}
                comb7515.update(dict7575)
                comb7515.update(dict1515)
                tf.createPDF(comb7515, "map_" + order_obj.number + "_7515.pdf", yearalldict, mxd, df)
                dictlist = [comb7515]
            else:
                print("dict7575: " + str(dict7575.keys()))
                print("dict1515: " + str(dict1515.keys()))
                tf.createPDF(dict7575, "map_" + order_obj.number + "_75.pdf", yearalldict, mxd, df)
                tf.createPDF(dict1515, "map_" + order_obj.number + "_15.pdf", yearalldict, mxd, df)
                dictlist = [dict7575, dict1515]

            # create blank pdf and append cover and summary pages
            output = PdfFileWriter()
            tf.goCoverPage(cfg.coverPdF)
            tf.goSummaryPage(dictlist, cfg.summaryPdf)

            coverPages = PdfFileReader(open(cfg.coverPdF,'rb'))
            summaryPages = PdfFileReader(open(cfg.summaryPdf,'rb'))
            output.addPage(coverPages.getPage(0))
            output.addPage(summaryPages.getPage(0))
            output.addBookmark("Cover Page",0)
            output.addBookmark("Summary",1)
            output.addAttachment("US Topo Map Symbols.pdf", open(cfg.pdfsymbolfile,"rb").read())

            # append map pages
            for d in dictlist:      # [dict7575, dict1515] or [comb7515]
                tf.appendMapPages(d, output)

            outputStream = open(os.path.join(cfg.scratch,pdfreport),"wb")
            output.setPageMode('/UseOutlines')
            output.write(outputStream)
            outputStream.close()

            output = None
            coverPages= None
            summaryPages=None
            summaryPages = None

            # save summary data to oracle
            tf.oracleSummary(dictlist, pdfreport)

            # zip tiffs if needtif  
            copydirs = [os.path.join(os.path.join(cfg.scratch,order_obj.number), name) for name in os.listdir(os.path.join(cfg.scratch,order_obj.number))]
            if len(copydirs) > 0 and needtif == True:
                tf.zipDir(pdfreport)

            # export to xplorer
            tf.toXplorer(needtif, dictlist, srGoogle, srWGS84)

            # copy files to report check
            tf.toReportCheck(needtif, pdfreport)

        logger.removeHandler(handler)
        handler.close()

    except:
        # Get the traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "Order ID: %s PYTHON ERRORS:\nTraceback info:\n"%order_obj.id + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
        arcpy.AddError("hit CC's error code in except: ")
        arcpy.AddError(pymsg)

        try:
            procedure = 'eris_topo.InsertTopoAudit'
            oc.proc(procedure, (order_obj.id, 'python-Error Handling',pymsg))
        finally:
            pass
        raise       # raise the error again

    finish = time.clock()
    print(cfg.reportcheckFolder + "\\TopographicMaps\\" + str(order_obj.number) + "_US_Topo.pdf")
    print("Finished in " + str(round(finish-start, 2)) + " secs")