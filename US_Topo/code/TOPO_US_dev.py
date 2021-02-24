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
import time
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
import TOPO_US_func as tf
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
'''
select 
a.order_id, a.order_num, a.site_name,
b.customer_id, 
c.company_id, c.company_desc,
d.radius_type, d.geometry_type, d.geometry
from orders a, customer b, company c, eris_order_geometry d
where 
a.customer_id = b.customer_id and
b.company_id = c.company_id and
a.order_id = d.order_id
and upper(a.site_name) not like '%TEST%'
and upper(c.company_desc) like '%NOVA GROUP%'
and d.geometry_type = 'POLYGON'
order by a.order_num DESC;
'''

if __name__ == '__main__':
    print("...starting..." + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
    start = time.clock()
    arcpy.env.overwriteOutput = True

    order_obj = models.Order().get_order(21013000010)
    print("Order: " + str(order_obj.id) + ", " + str(order_obj.number))

    BufsizeText = "2.4"
    yesBoundary = "yes"
    delyearFlag = 'N'

    pdfreport = order_obj.number + "_US_Topo.pdf"
    viewerdir = os.path.join(cfg.scratch,order_obj.number+'_topo')
        
    tf = tf.topo_us_rpt(order_obj,yesBoundary)
    
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

        # GET CUSTOM REPORT FLAGS
        is_nova, is_aei, is_newLogofile = tf.customrpt(order_obj)
        
        # GET SPATIAL REFERENCES
        srGCS83,srWGS84,srGoogle,srUTM = tf.projlist(order_obj)

        # CREATE ORDER GEOMETRY
        tf.createordergeometry(order_obj,srUTM)

        # GET TOPO RECORDS ---------------------------------------------------------------------------------------------------------------
        logger.debug("#1")
        bufferDistance_e75 = '2 KILOMETERS'                                                                     # has to be not smaller than the search radius to void white page
        
        arcpy.Buffer_analysis(cfg.orderGeometryPR, cfg.extentBuffer75SHP, bufferDistance_e75)

        masterLayer = arcpy.mapping.Layer(cfg.masterlyr)
        arcpy.SelectLayerByLocation_management(masterLayer,'intersect', cfg.orderGeometryPR,'0.25 KILOMETERS')  # it doesn't seem to work without the distance

        logger.debug("#2")
        if(int((arcpy.GetCount_management(masterLayer).getOutput(0))) ==0):
            print ("NO records selected")
            masterLayer = None
        else:
            cellids_selected = []
            # loop through the relevant records, locate the selected cell IDs
            rows = arcpy.SearchCursor(masterLayer)    # loop through the selected records
            for row in rows:
                cellid = str(int(row.getValue("CELL_ID")))
                cellids_selected.append(cellid)
            del row
            del rows

            arcpy.SelectLayerByLocation_management(masterLayer,'intersect', cfg.orderGeometryPR,'7 KILOMETERS','NEW_SELECTION')
            cellids = []
            cellsizes = []
            # loop through the relevant records, locate the selected cell IDs
            rows = arcpy.SearchCursor(masterLayer)    # loop through the selected records

            for row in rows:
                cellid = str(int(row.getValue("CELL_ID")))
                cellsize = str(int(row.getValue("CELL_SIZE")))
                cellids.append(cellid)
                cellsizes.append(cellsize)
            del row
            del rows

            masterLayer = None
            logger.debug(cellids)

            # cellids are found, need to find corresponding map .pdf by reading the .csv file
            # also get the year info from the corresponding .xml
            print("#1 " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
            infomatrix = []
            yearalldict = {}

            with open(cfg.csvfile_h, "rb") as f:
                print("___All USGS HTMC Topo List.")
                reader = csv.reader(f)
                for row in reader:
                    if row[9] in cellids:
                        pdfname = row[15].strip()
                        # read the year from .xml file
                        xmlname = pdfname[0:-3] + "xml"
                        xmlpath = os.path.join(cfg.tifdir_h,xmlname)
                        tree = ET.parse(xmlpath)
                        root = tree.getroot()
                        procsteps = root.findall("./dataqual/lineage/procstep")
                        yeardict = {}
                        for procstep in procsteps:
                            procdate = procstep.find("./procdate")
                            if procdate != None:
                                procdesc = procstep.find("./procdesc")
                                yeardict[procdesc.text.lower()] = procdate.text

                        year2use = yeardict.get("date on map")

                        if year2use == "":
                            print("################### cannot determine year of the map from xml...get from csv instead")
                            year2use = row[11].strip()

                        yearalldict[year2use] = yeardict

                        infomatrix.append([row[9],row[5],row[15],year2use])  # [64818, 15X15 GRID,  LA_Zachary_335142_1963_62500_geo.pdf,  1963]

            with open(cfg.csvfile_c, "rb") as f:
                print("___All USGS Current Topo List.")
                reader = csv.reader(f)
                for row in reader:
                    if row[9] in cellids:
                        pdfname = row[15].strip()

                        # for current topos, read the year from the geopdf file name
                        templist = pdfname.split("_")
                        year2use = templist[len(templist)-3][0:4]

                        if year2use[0:2] != "20" or year2use == "" or year2use == None:
                            print ("################### Error in the year of the map!!!" + year2use)

                        infomatrix.append([row[9],row[5],pdfname,year2use])

            logger.debug("#3")
            print("#3 " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
            # locate the geopdf and find the exact year to report, only use one from the same year per cell
            maps7575 = []
            maps1515 = []
            maps3060 =[]
            maps12 = []
            
            for row in infomatrix:
                if row[3] =="":
                    print("BLANK YEAR VALUE IN ROW EXISTS: " + str(row))
                else:
                    if row[1] == "7.5X7.5 GRID":
                        maps7575.append(row)
                    elif row[1] == "15X15 GRID":
                        maps1515.append(row)
                    elif row[1] == "30X60 GRID":
                        maps3060.append(row)
                    elif row[1] == "1X2 GRID":
                        maps12.append(row)

            # dedup the duplicated years
            maps7575 = tf.dedupMaplist(maps7575)
            maps1515 = tf.dedupMaplist(maps1515)
            maps3060 = tf.dedupMaplist(maps3060)
            maps12 = tf.dedupMaplist(maps12)

            logger.debug("#4")
            print("#4 " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))

            # reorganize data structure
            (dict7575,dict7575_s) = tf.reorgByYear(maps7575, cellids_selected)  # {1975: geopdf.pdf, 1973: ...}
            (dict1515,dict1515_s) = tf.reorgByYear(maps1515, cellids_selected)
            (dict3060,dict3060_s) = tf.reorgByYear(maps3060, cellids_selected)
            (dict12,dict12_s) = tf.reorgByYear(maps12, cellids_selected)

            # remove blank maps
            if delyearFlag == 'Y':
                delyear75 = filter(None, str(raw_input("Years you want to delete in the 7.5min series (comma-delimited no-space):\n>>> ")).replace(" ", "").strip().split(","))
                delyear15 = filter(None, str(raw_input("Years you want to delete in the 15min series (comma-delimited no-space):\n>>> ")).replace(" ", "").strip().split(","))
                tf.delyear(delyear75, delyear15, dict7575, dict7575_s, dict1515, dict1515_s)

            logger.debug("#5")
            copydirs = []    # will keep directories to be zipped
            if is_aei == 'Y':
                comb7515 = {}
                comb7515_s = {}
                comb7515.update(dict1515)
                comb7515.update(dict7575)
                comb7515_s.update(dict1515_s)
                comb7515_s.update(dict7575_s)

                tf.createPDF("15-7.5", comb7515, comb7515_s, "map_" + order_obj.number + "_7515.pdf", yearalldict, copydirs)
            else:
                print("dict7575: " + str(dict7575.keys()))
                print("dict1515: " + str(dict1515.keys()))
                tf.createPDF("7.5", dict7575, dict7575_s, "map_" + order_obj.number + "_75.pdf", yearalldict, copydirs)
                tf.createPDF("15", dict1515, dict1515_s, "map_" + order_obj.number + "_15.pdf", yearalldict, copydirs)

            tabledata = []
            summarydata = []
            topoSource = 'USGS'

            if is_aei == 'Y':
                tempyears = comb7515_s.keys()
                tempyears.sort(reverse = False)
                for year in tempyears:
                    if year != "":
                        if comb7515_s[year][0].split('_')[-2] == '24000':
                            tabledata.append([year,'7.5'])
                            summarydata.append([year,'7.5',topoSource])
                        elif comb7515_s[year][0].split('_')[-2] == '62500':
                            tabledata.append([year,'15'])
                            summarydata.append([year,'15',topoSource])
                        else:
                            tabledata.append([year,'7.5'])
                            summarydata.append([year,'7.5',topoSource])
                tempyears = None

            else:
                tempyears = dict7575.keys()
                tempyears.sort(reverse = True)
                for year in tempyears:
                    if year != "":
                        tabledata.append([year,'7.5'])
                        summarydata.append([year,'7.5',topoSource])
                tempyears = None

                tempyears = dict1515.keys()
                tempyears.sort(reverse = True)
                for year in tempyears:
                    if year != "":
                        tabledata.append([year,'15'])
                        summarydata.append([year,'15',topoSource])
                tempyears = None
            
            # CREATE AND APPEND COVER AND SUMMARY PAGES ---------------------------------------------------------------------------------------------
            tf.goCoverPage(cfg.coverPDF)
            tf.goSummaryPage(cfg.summarypdf, tabledata)

            output = PdfFileWriter()
            coverPages = PdfFileReader(open(cfg.coverPDF,'rb'))
            summaryPages = PdfFileReader(open(cfg.summarypdf,'rb'))
            output.addPage(coverPages.getPage(0))
            output.addPage(summaryPages.getPage(0))
            coverPages= None
            summaryPages=None
            output.addBookmark("Cover Page",0)
            output.addBookmark("Summary",1)
            output.addAttachment("US Topo Map Symbols.pdf", open(cfg.pdfsymbolfile,"rb").read())

            # save summary to Oracle
            summarylist = {"ORDER_ID":order_obj.id,"FILENAME":pdfreport,"SUMMARY":summarydata}
            topassorc = json.dumps(summarylist,ensure_ascii=False)

            try:
                con = cx_Oracle.connect(cfg.connectionString)
                cur = con.cursor()
                orc_return = cur.callfunc('eris_gis.AddTopoSummary', str, (str(topassorc),))

                if orc_return == 'Success':
                    print("Summary successfully populated to Oracle.")
                else:
                    print("Summary failed to populate to Oracle, check DB admin.")
            except Exception as e:
                logger.error("Function error, " + str(e))
                raise
            finally:
                cur.close()
                con.close()

            # CREATE AND APPEND MAP PAGES ----------------------------------------------------------------------------------------------------------
            if is_aei == 'Y':
                j = 0
                if len(comb7515) > 0:
                    map1575Pages = PdfFileReader(open(os.path.join(cfg.scratch,"map_" + order_obj.number+"_7515.pdf"),'rb'))
                    years = comb7515.keys()
                    years.sort(reverse = False)
                    print("==========years 7515")
                    years = filter(None, years)         # removes empty strings
                    print(years)

                    for year in years:
                        page = map1575Pages.getPage(j)
                        output.addPage(page)
                        if comb7515_s[year][0].split('_')[-2] in ['24000','31680'] and year < 2008:
                            seriesbkm = '7.5'
                        elif comb7515_s[year][0].split('_')[-2] == '62500':
                            seriesbkm = '15'
                        else:
                            seriesbkm = '7.5'
                        output.addBookmark(year+"_"+seriesbkm,j+2)
                        j = j + 1
                        page = None

            else:
                i=0
                if len(dict7575) > 0:
                    map7575Pages = PdfFileReader(open(os.path.join(cfg.scratch,"map_" + order_obj.number+"_75.pdf"),'rb'))
                    years = dict7575.keys()
                    years.sort(reverse = True)
                    print("==========years 7575")
                    years = filter(None, years)         # removes empty strings
                    print(years)

                    for year in years:
                        page = map7575Pages.getPage(i)
                        output.addPage(page)
                        output.addBookmark(year+"_7.5",i+2)   #i+1 to accommodate the summary page
                        i = i + 1
                        page = None

                j=0
                if len(dict1515) > 0:
                    map1515Pages = PdfFileReader(open(os.path.join(cfg.scratch,"map_" + order_obj.number+"_15.pdf"),'rb'))
                    years = dict1515.keys()
                    years.sort(reverse = True)
                    print("==========years 1515")
                    years = filter(None, years)         # removes empty strings
                    print(years)

                    for year in years:
                        page = map1515Pages.getPage(j)
                        output.addPage(page)
                        output.addBookmark(year+"_15",i+j+2)  # +1 to accomodate the summary page
                        j = j + 1
                        page = None

            outputStream = open(os.path.join(cfg.scratch,pdfreport),"wb")
            output.setPageMode('/UseOutlines')
            output.write(outputStream)
            outputStream.close()
            output = None
            summaryPages = None
            map7575Pages = None
            map1515Pages = None

            # ZIP REPORT IF NEEDTIF ------------------------------------------------------------------------------------------------------
            print("#5 " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))

            if len(copydirs) > 0:
                shutil.copy(os.path.join(cfg.scratch,pdfreport),os.path.join(cfg.scratch,order_obj.number))
                shutil.copy(cfg.readmefile,os.path.join(cfg.scratch,order_obj.number))
                myZipFile = zipfile.ZipFile(os.path.join(cfg.scratch,order_obj.number+"_US_Topo.zip"),"w")
                tf.zipdir(os.path.join(cfg.scratch,order_obj.number),myZipFile)
                myZipFile.close()

            # VIEWER/XPLORER -------------------------------------------------------------------------------------------------------------
            needViewer = 'N'
            # check if need to copy data for Topo viewer
            try:
                con = cx_Oracle.connect(cfg.connectionString)
                cur = con.cursor()

                cur.execute("select topo_viewer from order_viewer where order_id =" + str(order_obj.id))
                t = cur.fetchone()
                if t != None:
                    needViewer = t[0]
            finally:
                cur.close()
                con.close()

            if needViewer == 'Y':
                metadata = []
                
                arcpy.AddMessage("Viewer is needed.")

                if not os.path.exists(viewerdir):
                    os.mkdir(viewerdir)
                
                if not os.path.exists(cfg.tempdir):
                    os.mkdir(cfg.tempdir)

                # need to reorganize deliver directory
                dirs = filter(os.path.isdir, glob.glob(os.path.join(cfg.scratch,order_obj.number)+'\*_7.5_*'))
                if len(dirs) > 0:
                    if not os.path.exists(os.path.join(viewerdir,"75")):
                        os.mkdir(os.path.join(viewerdir,"75"))
                    # get the extent to use. use one uniform for now
                    year = dirs[0].split('_7.5_')[0][-4:]
                    mxdname = '75_'+year+'.mxd'
                    mxd = arcpy.mapping.MapDocument(os.path.join(cfg.scratch,mxdname))
                    df = arcpy.mapping.ListDataFrames(mxd,"*")[0]    # the spatial reference here is UTM zone #, need to change to WGS84 Web Mercator
                    df.spatialReference = srGoogle
                    extent = df.extent

                    del df, mxd
                    XMAX = extent.XMax
                    XMIN = extent.XMin
                    YMAX = extent.YMax
                    YMIN = extent.YMin
                    pnt1 = arcpy.Point(XMIN, YMIN)
                    pnt2 = arcpy.Point(XMIN, YMAX)
                    pnt3 = arcpy.Point(XMAX, YMAX)
                    pnt4 = arcpy.Point(XMAX, YMIN)
                    array = arcpy.Array()
                    array.add(pnt1)
                    array.add(pnt2)
                    array.add(pnt3)
                    array.add(pnt4)
                    array.add(pnt1)
                    polygon = arcpy.Polygon(array)
                    arcpy.CopyFeatures_management(polygon, os.path.join(cfg.tempdir, "Extent75.shp"))
                    arcpy.DefineProjection_management(os.path.join(cfg.tempdir, "Extent75.shp"), srGoogle)

                    arcpy.Project_management(os.path.join(cfg.tempdir, "Extent75.shp"), os.path.join(cfg.tempdir,"Extent75_WGS84.shp"), srWGS84)
                    desc = arcpy.Describe(os.path.join(cfg.tempdir, "Extent75_WGS84.shp"))
                    lat_sw = desc.extent.YMin
                    long_sw = desc.extent.XMin
                    lat_ne = desc.extent.YMax
                    long_ne = desc.extent.XMax

                arcpy.env.outputCoordinateSystem = srGoogle
                if is_aei == 'Y':
                    for year in comb7515.keys():
                        if os.path.exists(os.path.join(cfg.scratch,'75_'+str(year)+'.mxd')):
                            mxdname = os.path.join(cfg.scratch,'75_'+str(year)+'.mxd')
                            mxd = arcpy.mapping.MapDocument(mxdname)
                            df = arcpy.mapping.ListDataFrames(mxd)[0]               # the spatial reference here is UTM zone #, need to change to WGS84 Web Mercator
                            df.spatialReference = srGoogle

                            imagename = str(year)+".jpg"
                            arcpy.mapping.ExportToJPEG(mxd, os.path.join(cfg.scratch, viewerdir,"75", imagename), df,df_export_width= 3573,df_export_height=4000, color_mode='24-BIT_TRUE_COLOR',world_file = True, jpeg_quality=50)#,df_export_width= 14290,df_export_height=16000, color_mode='8-BIT_GRAYSCALE',world_file = True, jpeg_quality=100)

                            desc = arcpy.Describe(os.path.join(viewerdir,"75",imagename))
                            featbound = arcpy.Polygon(arcpy.Array([desc.extent.lowerLeft, desc.extent.lowerRight, desc.extent.upperRight, desc.extent.upperLeft]),srGoogle)
                                                
                            del desc

                            tempfeat = os.path.join(cfg.tempdir, "tilebnd_"+str(year)+ ".shp")

                            arcpy.Project_management(featbound, tempfeat, srWGS84)  # function requires output not be in_memory
                            del featbound
                            desc = arcpy.Describe(tempfeat)

                            metaitem = {}
                            metaitem['type'] = 'topo75'
                            metaitem['imagename'] = imagename[:-4]+'.jpg'
                            metaitem['lat_sw'] = desc.extent.YMin
                            metaitem['long_sw'] = desc.extent.XMin
                            metaitem['lat_ne'] = desc.extent.YMax
                            metaitem['long_ne'] = desc.extent.XMax

                            metadata.append(metaitem)
                            del mxd, df
                        elif os.path.exists(os.path.join(cfg.scratch,'15_'+str(year)+'.mxd')):
                            if not os.path.exists(os.path.join(viewerdir,"150")):
                                os.mkdir(os.path.join(viewerdir,"150"))

                            mxdname = os.path.join(cfg.scratch,'15_'+str(year)+'.mxd')
                            mxd = arcpy.mapping.MapDocument(mxdname)
                            df = arcpy.mapping.ListDataFrames(mxd)[0]                   # the spatial reference here is UTM zone #, need to change to WGS84 Web Mercator
                            df.spatialReference = srGoogle

                            imagename = str(year)+".jpg"
                            arcpy.mapping.ExportToJPEG(mxd, os.path.join(cfg.scratch, viewerdir,"150", imagename), df,df_export_width= 3573,df_export_height=4000, color_mode='24-BIT_TRUE_COLOR',world_file = True, jpeg_quality=50)#,df_export_width= 14290,df_export_height=16000, color_mode='8-BIT_GRAYSCALE',world_file = True, jpeg_quality=100)

                            desc = arcpy.Describe(os.path.join(viewerdir,"150",imagename))
                            featbound = arcpy.Polygon(arcpy.Array([desc.extent.lowerLeft, desc.extent.lowerRight, desc.extent.upperRight, desc.extent.upperLeft]),srGoogle)
                            del desc

                            tempfeat = os.path.join(cfg.tempdir, "tilebnd_"+str(year)+ ".shp")

                            arcpy.Project_management(featbound, tempfeat, srWGS84)      # function requires output not be in_memory
                            del featbound
                            desc = arcpy.Describe(tempfeat)

                            metaitem = {}
                            metaitem['type'] = 'topo150'
                            metaitem['imagename'] = imagename[:-4]+'.jpg'
                            metaitem['lat_sw'] = desc.extent.YMin
                            metaitem['long_sw'] = desc.extent.XMin
                            metaitem['lat_ne'] = desc.extent.YMax
                            metaitem['long_ne'] = desc.extent.XMax

                            metadata.append(metaitem)
                            del mxd, df
                        arcpy.env.outputCoordinateSystem = None

                else:
                    for year in dict7575.keys():
                        print(year)
                        mxdname = glob.glob(os.path.join(cfg.scratch,'75_'+str(year)+'.mxd'))[0]
                        mxd = arcpy.mapping.MapDocument(mxdname)
                        df = arcpy.mapping.ListDataFrames(mxd)[0]               # the spatial reference here is UTM zone #, need to change to WGS84 Web Mercator
                        df.spatialReference = srGoogle

                        imagename = str(year)+".jpg"
                        arcpy.mapping.ExportToJPEG(mxd, os.path.join(cfg.scratch, viewerdir,"75", imagename), df,df_export_width= 3573,df_export_height=4000, color_mode='24-BIT_TRUE_COLOR',world_file = True, jpeg_quality=50)#,df_export_width= 14290,df_export_height=16000, color_mode='8-BIT_GRAYSCALE',world_file = True, jpeg_quality=100)

                        desc = arcpy.Describe(os.path.join(viewerdir,"75",imagename))
                        featbound = arcpy.Polygon(arcpy.Array([desc.extent.lowerLeft, desc.extent.lowerRight, desc.extent.upperRight, desc.extent.upperLeft]), srGoogle)
                        del desc

                        tempfeat = os.path.join(cfg.tempdir, "tilebnd_"+str(year)+ ".shp")

                        arcpy.Project_management(featbound, tempfeat, srWGS84)  # function requires output not be in_memory
                        del featbound
                        desc = arcpy.Describe(tempfeat)

                        metaitem = {}
                        metaitem['type'] = 'topo75'
                        metaitem['imagename'] = imagename[:-4]+'.jpg'
                        metaitem['lat_sw'] = desc.extent.YMin
                        metaitem['long_sw'] = desc.extent.XMin
                        metaitem['lat_ne'] = desc.extent.YMax
                        metaitem['long_ne'] = desc.extent.XMax

                        metadata.append(metaitem)
                        del mxd, df
                    arcpy.env.outputCoordinateSystem = None

                    for year in dict1515.keys():
                        if not os.path.exists(os.path.join(viewerdir,"150")):
                            os.mkdir(os.path.join(viewerdir,"150"))
                            
                        mxdname = glob.glob(os.path.join(cfg.scratch,'15_'+str(year)+'.mxd'))[0]
                        mxd = arcpy.mapping.MapDocument(mxdname)
                        df = arcpy.mapping.ListDataFrames(mxd)[0]    # the spatial reference here is UTM zone #, need to change to WGS84 Web Mercator
                        df.spatialReference = srGoogle

                        imagename = str(year)+".jpg"
                        arcpy.mapping.ExportToJPEG(mxd, os.path.join(cfg.scratch, viewerdir,"150", imagename), df,df_export_width= 3573,df_export_height=4000, color_mode='24-BIT_TRUE_COLOR',world_file = True, jpeg_quality=50)#,df_export_width= 14290,df_export_height=16000, color_mode='8-BIT_GRAYSCALE',world_file = True, jpeg_quality=100)

                        desc = arcpy.Describe(os.path.join(viewerdir,"150",imagename))
                        featbound = arcpy.Polygon(arcpy.Array([desc.extent.lowerLeft, desc.extent.lowerRight, desc.extent.upperRight, desc.extent.upperLeft]),srGoogle)
                        del desc

                        tempfeat = os.path.join(cfg.tempdir, "tilebnd_"+str(year)+ ".shp")

                        arcpy.Project_management(featbound, tempfeat, srWGS84) #function requires output not be in_memory
                        del featbound
                        desc = arcpy.Describe(tempfeat)

                        metaitem = {}
                        metaitem['type'] = 'topo150'
                        metaitem['imagename'] = imagename[:-4]+'.jpg'
                        metaitem['lat_sw'] = desc.extent.YMin
                        metaitem['long_sw'] = desc.extent.XMin
                        metaitem['lat_ne'] = desc.extent.YMax
                        metaitem['long_ne'] = desc.extent.XMax

                        metadata.append(metaitem)
                        del mxd, df
                    arcpy.env.outputCoordinateSystem = None

                if os.path.exists(os.path.join(cfg.viewerFolder, order_obj.number+"_topo")):
                    shutil.rmtree(os.path.join(cfg.viewerFolder, order_obj.number+"_topo"))
                shutil.copytree(os.path.join(cfg.scratch, order_obj.number+"_topo"), os.path.join(cfg.viewerFolder, order_obj.number+"_topo"))
                url = cfg.topouploadurl + order_obj.number
                urllib.urlopen(url)

            else:
                arcpy.AddMessage("No viewer is needed. Do nothing")

            try:
                con = cx_Oracle.connect(cfg.connectionString)
                cur = con.cursor()

                cur.execute("delete from overlay_image_info where order_id = %s and (type = 'topo75' or type = 'topo150')" % str(order_obj.id))

                if needViewer == 'Y':
                    for item in metadata:
                        cur.execute("insert into overlay_image_info values (%s, %s, %s, %.5f, %.5f, %.5f, %.5f, %s, '', '')" % (str(order_obj.id), str(order_obj.number), "'" + item['type']+"'", item['lat_sw'], item['long_sw'], item['lat_ne'], item['long_ne'],"'"+item['imagename']+"'" ))
                    con.commit()
            finally:
                cur.close()
                con.close()

            # COPY FILES TO REPORT CHECK ---------------------------------------------------------------------------------------------------
            # see if need to provide the tiffs too
            if len(copydirs) > 0:
                if os.path.exists(os.path.join(cfg.reportcheckFolder,"TopographicMaps",order_obj.number+"_US_Topo.zip")):
                    os.remove(os.path.join(cfg.reportcheckFolder,"TopographicMaps",order_obj.number+"_US_Topo.zip"))
                shutil.copyfile(os.path.join(cfg.scratch,order_obj.number+"_US_Topo.zip"),os.path.join(cfg.reportcheckFolder,"TopographicMaps",order_obj.number+"_US_Topo.zip"))
                arcpy.SetParameterAsText(3, os.path.join(cfg.scratch,order_obj.number+"_US_Topo.zip"))
            else:
                if os.path.exists(os.path.join(cfg.reportcheckFolder,"TopographicMaps",pdfreport)):
                    os.remove(os.path.join(cfg.reportcheckFolder,"TopographicMaps",pdfreport))
                shutil.copyfile(os.path.join(cfg.scratch, pdfreport),os.path.join(cfg.reportcheckFolder,"TopographicMaps",pdfreport))
                arcpy.SetParameterAsText(3, os.path.join(cfg.scratch,pdfreport))

            try:
                con = cx_Oracle.connect(cfg.connectionString)
                cur = con.cursor()

                cur.callproc('eris_topo.processTopo', (int(order_obj.id),))
            finally:
                cur.close()
                con.close()

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
            con = cx_Oracle.connect(cfg.connectionString)
            cur = con.cursor()
            cur.callproc('eris_topo.InsertTopoAudit', (order_obj.id, 'python-Error Handling',pymsg))
        finally:
            cur.close()
            con.close()
        raise       # raise the error again

    finish = time.clock()
    print(cfg.reportcheckFolder + "\\TopographicMaps\\" + str(order_obj.number) + "_US_Topo.pdf")
    print("Finished in " + str(round(finish-start, 2)) + " secs")