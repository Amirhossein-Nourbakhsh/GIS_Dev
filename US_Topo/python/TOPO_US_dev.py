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
import time,json
import arcpy, os, sys
import csv
import operator
import shutil, zipfile
import logging
import traceback
import cx_Oracle, glob, urllib
import re
import xml.etree.ElementTree as ET

addpath = os.path.abspath(__file__).replace(os.path.relpath(__file__),"GIS-Dev")
sys.path.insert(1,os.path.join(addpath,'DB_Framework'))
import TOPO_US_func as tf
import TOPO_US_config as cfg
import models

from time import strftime
from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.generic import NameObject, createStringObject, ArrayObject, FloatObject
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Frame,Table
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import portrait, letter
from reportlab.pdfgen import canvas


# -----------------------------------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    print ("...starting..." + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
    arcpy.env.overwriteOutput = True

    # BufsizeText = "2.4"
    yesBoundary = "yes"

    # id = input("Input order_id or order_num: ").strip()
    order_obj = models.Order().get_order(1014804)
    print("Order: " + str(order_obj.id) + ", " + str(order_obj.number))
        
    tf = tf.topo_us_rpt(order_obj,yesBoundary)
    logger,handler = tf.log(cfg.logfile)
    
    try:
        # GET ORDER_ID AND BOUNDARY FROM ORDER_NUM
        if yesBoundary == "":
            con = cx_Oracle.connect(cfg.connectionString)
            cur = con.cursor()

            cur.execute("SELECT * FROM ERIS.TOPO_AUDIT WHERE ORDER_ID IN (select order_id from orders where order_num = '" + str(order_obj.number) + "')")
            result = cur.fetchall()
            yesBoundaryqry = str([row[3] for row in result if row[2]== "URL"][0])
            yesBoundary = re.search('(yesBoundary=)(\w+)(&)', yesBoundaryqry).group(2).strip()            
            print("Yes Boundary: " + yesBoundary)


        if len(order_obj.site_name) > 40:
                order_obj.site_name = order_obj.site_name[0: order_obj.site_name[0:40].rfind(' ')] + '\n' + order_obj.site_name[order_obj.site_name[0:40].rfind(' ')+1:]
        
        OrderCoord = json.loads(order_obj.geometry.JSON).values()[0]

#-------------------------
        is_nova, is_aei, is_newLogofile = tf.custom_rpt()
#-------------------------

        pdfreport = order_obj.number+"_US_Topo.pdf"

        point = arcpy.Point()
        array = arcpy.Array()

        sr = arcpy.SpatialReference()
        sr.factoryCode = 4269   # requires input geometry is in 4269
        sr.XYTolerance = .00000001
        sr.scaleFactor = 2000
        sr.create()

        featureList = []

        for feature in OrderCoord:
            # For each coordinate pair, set the x,y properties and add to the Array object.
            for coordPair in feature:
                point.X = coordPair[0]
                point.Y = coordPair[1]
                sr.setDomain (point.X, point.X, point.Y, point.Y)
                array.add(point)
            if order_obj.geometry.type.lower()== 'point':
                feat = arcpy.Multipoint(array, sr)
            elif order_obj.geometry.type.lower() =='polyline':
                feat  = arcpy.Polyline(array, sr)
            else:
                feat = arcpy.Polygon(array,sr)
            array.removeAll()

            # Append to the list of Polygon objects
            featureList.append(feat)

        orderGeometry= os.path.join(cfg.scratch,"orderGeometry.shp")
        arcpy.CopyFeatures_management(featureList, orderGeometry)
        # arcpy.DefineProjection_management(orderGeometry, srGCS83)
        arcpy.AddField_management(orderGeometry, "UTM", "TEXT", "", "", "1500", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.CalculateUTMZone_cartography(orderGeometry, 'UTM')

#------------------------------------------------------
        srGCS83,srWGS84,srGoogle,out_coordinate_system = tf.proj_list(orderGeometry)

        orderGeometryPR = os.path.join(cfg.scratch, "ordergeoNamePR.shp")
        arcpy.Project_management(orderGeometry, orderGeometryPR, out_coordinate_system)
#------------------------------------------------------
        del point
        del array

        logger.debug("#1")
        bufferDistance_e75 = '2 KILOMETERS'                                                                 # has to be not smaller than the search radius to void white page
        extentBuffer75SHP = os.path.join(cfg.scratch,"buffer_extent75.shp")
        arcpy.Buffer_analysis(orderGeometryPR, extentBuffer75SHP, bufferDistance_e75)

        masterLayer = arcpy.mapping.Layer(cfg.masterlyr)
        arcpy.SelectLayerByLocation_management(masterLayer,'intersect', orderGeometryPR,'0.25 KILOMETERS')  # it doesn't seem to work without the distance

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

            arcpy.SelectLayerByLocation_management(masterLayer,'intersect', orderGeometryPR,'7 KILOMETERS','NEW_SELECTION')
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
            print ("#1 " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
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
                            print ("################### cannot determine year of the map from xml...get from csv instead")
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
            print ("#3 " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
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
            print ("#4 " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))

            # reorganize data structure
            (dict7575,dict7575_s) = tf.reorgByYear(maps7575, cellids_selected)  # {1975: geopdf.pdf, 1973: ...}
            (dict1515,dict1515_s) = tf.reorgByYear(maps1515, cellids_selected)
            (dict3060,dict3060_s) = tf.reorgByYear(maps3060, cellids_selected)
            (dict12,dict12_s) = tf.reorgByYear(maps12, cellids_selected)

            # -----------------------------------------------------------------------------------------------------------
            # REMOVE BLANK MAPS
            yeardel7575 = []    # include quotes
            yeardel1515 = []    # include quotes
            if yeardel7575:
                for y in yeardel7575:
                    del dict7575[y]
                    del dict7575_s[y]
            if yeardel1515:
                for y in yeardel1515:
                    del dict1515[y]
                    del dict1515_s[y]
            # -----------------------------------------------------------------------------------------------------------

            logger.debug("#5")
            copydirs = []    # will keep directories to be zipped
            if is_aei == 'Y':
                comb7515 = {}
                comb7515_s = {}
                comb7515.update(dict1515)
                comb7515.update(dict7575)
                comb7515_s.update(dict1515_s)
                comb7515_s.update(dict7575_s)

                tf.createPDF("15-7.5", comb7515, comb7515_s, "map_" + order_obj.number + "_7515.pdf")
            else:
                print("dict7575: " + str(dict7575.keys()))
                print("dict7575_s: " + str(dict7575_s.keys()))
                tf.createPDF("7.5", dict7575, dict7575_s, "map_" + order_obj.number + "_75.pdf", yearalldict, copydirs)
                tf.createPDF("15", dict1515, dict1515_s, "map_" + order_obj.number + "_15.pdf", yearalldict, copydirs)

            summarypdf = os.path.join(cfg.scratch,'summary.pdf')
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

            coverPDF = os.path.join(cfg.scratch,"cover.pdf")
            tf.goCoverPage(coverPDF)
            tf.goSummaryPage(summarypdf, tabledata)

            output = PdfFileWriter()
            coverPages = PdfFileReader(open(coverPDF,'rb'))
            summaryPages = PdfFileReader(open(os.path.join(cfg.scratch,summarypdf),'rb'))
            output.addPage(coverPages.getPage(0))
            coverPages= None
            output.addPage(summaryPages.getPage(0))
            summaryPages=None
            output.addBookmark("Cover Page",0)
            output.addBookmark("Summary",1)
            output.addAttachment("US Topo Map Symbols.pdf", open(cfg.pdfsymbolfile,"rb").read())

    # Save Summary #######################################################################################################
            summarylist = {"ORDER_ID":order_obj.id,"FILENAME":pdfreport,"SUMMARY":summarydata}
            topassorc = json.dumps(summarylist,ensure_ascii=False)

            try:
                con = cx_Oracle.connect(cfg.connectionString)
                cur = con.cursor()

                orc_return = cur.callfunc('eris_gis.AddTopoSummary', str, (str(topassorc),))
                if orc_return == 'Success':
                    print ("Summary successfully populated to Oracle")
                else:
                    print ("Summary failed to populate to Oracle, check DB admin")
            except Exception as e:
                logger.error("Function error, " + str(e))
                raise
            finally:
                cur.close()
                con.close()

            if is_aei == 'Y':
                j = 0

                if len(comb7515) > 0:
                    map1575Pages = PdfFileReader(open(os.path.join(cfg.scratch,"map_" + order_obj.number+"_7515.pdf"),'rb'))
                    years = comb7515.keys()
                    years.sort(reverse = False)
                    print("==========years 7515")
                    for year in years:
                        if year == "":
                            years.remove("")
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
                        j=j+1
                        page = None

            else:
                i=0
                if len(dict7575) > 0:
                    map7575Pages = PdfFileReader(open(os.path.join(cfg.scratch,"map_" + order_obj.number+"_75.pdf"),'rb'))
                    years = dict7575.keys()
                    years.sort(reverse = True)
                    print("==========years 7575")
                    for year in years:
                        if year == "":
                            years.remove("")
                    print(years)

                    for year in years:
                        page = map7575Pages.getPage(i)
                        output.addPage(page)
                        output.addBookmark(year+"_7.5",i+2)   #i+1 to accomodate the summary page
                        i = i + 1
                        page = None

                j=0
                if len(dict1515) > 0:
                    map1515Pages = PdfFileReader(open(os.path.join(cfg.scratch,"map_" + order_obj.number+"_15.pdf"),'rb'))
                    years = dict1515.keys()
                    years.sort(reverse = True)
                    print("==========years 1515")
                    for year in years:
                        if year == "":
                            years.remove("")
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

            print ("#5 " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))

            if len(copydirs) > 0:
                shutil.copy(os.path.join(cfg.scratch,pdfreport),os.path.join(cfg.scratch,order_obj.number))
                shutil.copy(cfg.readmefile,os.path.join(cfg.scratch,order_obj.number))
                myZipFile = zipfile.ZipFile(os.path.join(cfg.scratch,order_obj.number+"_US_Topo.zip"),"w")
                zipdir(os.path.join(cfg.scratch,order_obj.number),myZipFile)
                myZipFile.close()

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
                
                arcpy.AddMessage("Viewer is needed. Need to copy data to obi002")
                viewerdir = os.path.join(cfg.scratch,order_obj.number+'_topo')

                if not os.path.exists(viewerdir):
                    os.mkdir(viewerdir)
                tempdir = os.path.join(cfg.scratch,'viewertemp')

                if not os.path.exists(tempdir):
                    os.mkdir(tempdir)
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
                    arcpy.CopyFeatures_management(polygon, os.path.join(tempdir, "Extent75.shp"))
                    arcpy.DefineProjection_management(os.path.join(tempdir, "Extent75.shp"), srGoogle)

                    arcpy.Project_management(os.path.join(tempdir, "Extent75.shp"), os.path.join(tempdir,"Extent75_WGS84.shp"), srWGS84)
                    desc = arcpy.Describe(os.path.join(tempdir, "Extent75_WGS84.shp"))
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

                            tempfeat = os.path.join(tempdir, "tilebnd_"+str(year)+ ".shp")

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

                            tempfeat = os.path.join(tempdir, "tilebnd_"+str(year)+ ".shp")

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

                        tempfeat = os.path.join(tempdir, "tilebnd_"+str(year)+ ".shp")

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

                        tempfeat = os.path.join(tempdir, "tilebnd_"+str(year)+ ".shp")

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
                        cur.execute("insert into overlay_image_info values (%s, %s, %s, %.5f, %.5f, %.5f, %.5f, %s, '', '')" % (str(order_obj.id), str(order_obj.number), "'" + item['type']+"'", item['lat_sw'], item['long_sw'], item['lat_ne'], item['long_ne'],"'"+item['imagename']+"'" ) )
                    con.commit()
            finally:
                cur.close()
                con.close()

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

    print(cfg.reportcheckFolder + "\\TopographicMaps\\" + str(order_obj.number) + "_US_Topo.pdf")
    print("DONE!")