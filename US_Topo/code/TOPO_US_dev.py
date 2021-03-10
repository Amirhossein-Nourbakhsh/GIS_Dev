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
# import json
import arcpy
import os
import sys
import traceback
import time

import TOPO_US_func as tp
import TOPO_US_config as cfg

from PyPDF2 import PdfFileReader, PdfFileWriter

# ----------------------------------------------------------------------------------------------------------------------------------------
'''for quick grab of order_id(s) for testing:
select 
a.order_id, a.order_num, a.site_name,
b.customer_id, 
c.company_id, c.company_desc,
d.radius_type, d.geometry_type, d.geometry, length(d.geometry),
e.topo_viewer
from orders a, customer b, company c, eris_order_geometry d, order_viewer e
where 
a.customer_id = b.customer_id and
b.company_id = c.company_id and
a.order_id = d.order_id and
a.order_id = e.order_id
and upper(a.site_name) not like '%TEST%'
--and upper(c.company_desc) like '%MID-ATLANTIC%'
and d.geometry_type = 'POLYGON'
and e.topo_viewer = 'Y'
order by length(d.geometry),a.order_num  desc;
'''
cfg
if __name__ == '__main__':
    arcpy.AddMessage("...starting..." + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
    start = time.clock()
    pdfreport = cfg.order_obj.number + "_US_Topo.pdf"    

    oc = tp.oracle(cfg.connectionString)
    tf = tp.topo_us_rpt(cfg.order_obj)

    arcpy.AddMessage("Order: " + str(cfg.order_obj.id) + ", " + str(cfg.order_obj.number))
    arcpy.AddMessage("multipage = " + cfg.multipage)

    try:
        logger,handler = tf.log(cfg.logfile)

        # get custom order flags
        is_nova, is_aei, is_newLogo = tf.customrpt(cfg.order_obj)
        
        # get spatial references
        srGCS83,srWGS84,srGoogle,srUTM = tf.projlist(cfg.order_obj)

        # create order geometry
        tf.createordergeometry(cfg.order_obj, srUTM)
        
        # open mxd and create map extent
        logger.debug("#1")
        mxd, df = tf.mapDocument(is_nova, srUTM)
        needtif = tf.mapExtent(df, mxd, srUTM)

        # set boundary
        mxd, df, yesBoundary = tf.setBoundary(mxd, df, cfg.yesBoundary)                         # need to return variables again or won't update

        # select topo records
        rowsMain, rowsAdj = tf.selectTopo(cfg.orderGeometryPR, cfg.extent, srUTM)
        
        # get topo records
        logger.debug("#2")
        if int(len(rowsMain)) == 0:
            arcpy.AddMessage("...NO records selected.")
        else:
            maps7575, maps1515, yearalldict = tf.getTopoRecords(rowsMain, rowsAdj, cfg.csvfile_h, cfg.csvfile_c)

            # remove duplicated years
            maps7575 = tf.dedupMaplist(maps7575)
            maps1515 = tf.dedupMaplist(maps1515)

            # reorganize data structure by year
            logger.debug("#4")
            dict7575 = tf.reorgByYear(maps7575)  # {1975: geopdf.pdf, 1973: ...}
            dict1515 = tf.reorgByYear(maps1515)
            arcpy.AddMessage("dict7575: " + str(dict7575.keys()))
            arcpy.AddMessage("dict1515: " + str(dict1515.keys()))

            # remove blank maps flag
            if cfg.delyearFlag == 'Y':
                delyear75 = filter(None, str(raw_input("Years you want to delete in the 7.5min series (comma-delimited):\n>>> ")).replace(" ", "").strip().split(","))
                delyear15 = filter(None, str(raw_input("Years you want to delete in the 15min series (comma-delimited):\n>>> ")).replace(" ", "").strip().split(","))
                tf.delyear(delyear75, delyear15, dict7575, dict1515)

            # create map pages
            logger.debug("#5")
            dictlist = []
            if is_aei == 'Y':
                comb7515 = {}
                comb7515.update(dict7575)
                comb7515.update(dict1515)
                tf.createPDF(comb7515, yearalldict, mxd, df, yesBoundary, cfg.multipage, srUTM)
                dictlist.append(comb7515)
            else:
                if dict7575:
                    tf.createPDF(dict7575, yearalldict, mxd, df, yesBoundary, cfg.multipage, srUTM)
                    dictlist.append(dict7575)
                if dict1515:
                    tf.createPDF(dict1515, yearalldict, mxd, df, yesBoundary, cfg.multipage, srUTM)
                    dictlist.append(dict1515)

            # create blank pdf and append cover and summary pages
            output = PdfFileWriter()
            tf.goCoverPage(cfg.coverPdf)
            tf.goSummaryPage(dictlist, cfg.summaryPdf)

            coverPages = PdfFileReader(open(cfg.coverPdf,'rb'))
            summaryPages = PdfFileReader(open(cfg.summaryPdf,'rb'))
            output.addPage(coverPages.getPage(0))
            output.addPage(summaryPages.getPage(0))
            output.addBookmark("Cover Page",0)
            output.addBookmark("Summary",1)
            output.addAttachment("US Topo Map Symbols.pdf", open(cfg.pdfsymbolfile,"rb").read())
            # output.addLink(1,0,[60,197,240,207],None,fit="/Fit")

            # append map pages   
            tf.appendMapPages(dictlist, output, cfg.yesBoundary, cfg.multipage)          # [dict7575, dict1515] or [comb7515]

            outputStream = open(os.path.join(cfg.scratch,pdfreport),"wb")
            output.setPageMode('/UseOutlines')
            output.write(outputStream)
            outputStream.close()

            output = None
            coverPages = None
            summaryPages = None
            summaryPages = None

            # save summary data to oracle
            tf.oracleSummary(dictlist, pdfreport)

            # zip tiffs if needtif  
            copydirs = [os.path.join(os.path.join(cfg.scratch,cfg.order_obj.number), name) for name in os.listdir(os.path.join(cfg.scratch,cfg.order_obj.number))]
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
        pymsg = "Order ID: %s PYTHON ERRORS:\nTraceback info:\n"%cfg.order_obj.id + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
        arcpy.AddError("hit CC's error code in except: ")
        arcpy.AddError(pymsg)

        try:
            procedure = 'eris_topo.InsertTopoAudit'
            oc.proc(procedure, (cfg.order_obj.id, 'python-Error Handling',pymsg))
        finally:
            pass
        raise                   # raise the error again

    finally:
        oc.close()              # close oracle connection

    finish = time.clock()
    arcpy.AddMessage(cfg.reportcheckFolder + "\\TopographicMaps\\" + pdfreport)
    arcpy.AddMessage("Finished in " + str(round(finish-start, 2)) + " secs")