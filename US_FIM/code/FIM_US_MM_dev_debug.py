#-------------------------------------------------------------------------------
# Name:        USFIM rework
# Purpose:
#
# Author:      cchen
#
# Created:     01/12/2019
# Copyright:   (c) cchen 2019
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import arcpy, os, sys
import cx_Oracle
import traceback
import time
import FIM_US_config as cfg
import FIM_US_utility as fp

from PyPDF2 import PdfFileReader,PdfFileWriter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import portrait, letter

if __name__ == '__main__':
    start = time.clock()
    
    order_obj = cfg.order_obj
    ff = fp.fim_us_rpt(cfg.order_obj)
    oc = fp.oracle(cfg.connectionString)

    # get custom order flags
    is_newLogo, is_aei, is_emg = ff.customrpt(order_obj)
    
    # get spatial references
    srGCS83,srWGS84,srGoogle,srUTM = ff.projlist(order_obj)

    # create order geometry
    ff.createOrderGeometry(order_obj, srGCS83)

    # open mxd and create map extent
    mxd, dfmain, dfinset = ff.mapDocument(srUTM)
    ff.mapExtent(mxd, dfmain, dfinset)

    # set boundary
    mxd, df, yesBoundary = ff.setBoundary(mxd, dfmain, cfg.yesBoundary)                         # if multipage, set to 'fixed' if want to show boundary; need to return variables again or won't update

    try:
        # select FIM
        presentedlist = ff.selectFim(cfg.mastergdb)



        if len(presentedlist) == 0 :
            print("...NO records selected, will print out NRF letter.")
            cfg.NRF = 'Y'
            ff.goCoverPage(cfg.coverfile, cfg.NRF)
            os.rename(cfg.coverfile, os.path.join(cfg.scratch, pdfreport_name))
        else:
            # get FIM records
            summaryList = ff.getFimRecords(cfg.presentedFIPs)

            # remove blank maps flag
            if cfg.delyearFlag == 'Y':
                delyear = filter(None, str(raw_input("Years you want to delete (comma-delimited):\n>>> ")).replace(" ", "").strip().split(","))        # No quotes
                ff.delyear(delyear, summaryList)

            pdfreport_name = cfg.order_obj.number+"_US_FIM.pdf"
            # if coverInfotext["COUNTRY"]=='MEX':
            #     pdfreport_name =  cfg.order_obj.number+"_MEX_FIM.pdf"
            
            # create map page
            ff.createPDF(summaryList, is_aei, mxd, dfmain, dfinset, cfg.Multipage, cfg.gridsize, cfg.presentedFIPs)

            pagesize = portrait(letter)
            [PAGE_WIDTH,PAGE_HEIGHT]=pagesize[:2]
            PAGE_WIDTH = int(PAGE_WIDTH)
            PAGE_HEIGHT = int(PAGE_HEIGHT)
            styles = getSampleStyleSheet()

            ff.goSummaryPage(cfg.summaryfile,summaryList)
            ff.goCoverPage(cfg.coverfile, cfg.NRF)

            output = PdfFileWriter()

            output.addPage(PdfFileReader(open(cfg.coverfile,'rb')).getPage(0))
            output.addBookmark("Cover Page",0)

            for j in range(PdfFileReader(open(cfg.summaryfile,'rb')).getNumPages()):
                output.addPage(PdfFileReader(open(cfg.summaryfile,'rb')).getPage(j))
                output.addBookmark("Summary Page",j+1)

            ff.appendMapPages(output,summaryList, cfg.Multipage, cfg.yesBoundary)

            outputStream = open(os.path.join(cfg.scratch, pdfreport_name),"wb")
            output.setPageMode('/UseOutlines')
            output.write(outputStream)
            outputStream.close()

            ff.toXplorer(summaryList, srGoogle, srWGS84)

            ff.toReportCheck(pdfreport_name)

            try:
                procedure = 'eris_fim.processFim'
                oc.proc(procedure, (order_obj.id))
            except Exception as e:
                arcpy.AddError(e)
                arcpy.AddError("### eris_fim.processFim failed...")

    except:
        # Get the traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "Order ID: %s PYTHON ERRORS:\nTraceback info:\n"%order_obj.id + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
        traceback.print_exc()

        try:
            con = cx_Oracle.connect(cfg.connectionString)
            cur = con.cursor()
            cur.callproc('eris_fim.InsertFIMAudit', (order_obj.id, 'python-Error Handling',pymsg))
        finally:
            cur.close()
            con.close()
        raise       # raise the error again

    finally:
        oc.close()
        # logger.removeHandler(handler)
        # handler.close()

    finish = time.clock()
    print("Final FIM report directory: " + (str(os.path.join(cfg.reportcheckFolder,"FIM", pdfreport_name))))
    arcpy.AddMessage("Finished in " + str(round(finish-start, 2)) + " secs")