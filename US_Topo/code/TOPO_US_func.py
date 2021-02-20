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
import TOPO_US_config as cfg

from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.generic import NameObject, createStringObject, ArrayObject, FloatObject
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Frame,Table
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import portrait, letter
from reportlab.pdfgen import canvas
from time import strftime

class topo_us_rpt():
    def __init__(self,order_obj,yesBoundary):
        self.order_obj = order_obj
        self.yesBoundary = yesBoundary

    def createAnnotPdf(self, myShapePdf):
        # input variables
        # part 1: read geometry pdf to get the vertices and rectangle to use
        source  = PdfFileReader(open(myShapePdf,'rb'))
        geomPage = source.getPage(0)
        mystr = geomPage.getObject()['/Contents'].getData()
        # to pinpoint the string part: 1.19997 791.75999 m 1.19997 0.19466 l 611.98627 0.19466 l 611.98627 791.75999 l 1.19997 791.75999 l
        # the format seems to follow x1 y1 m x2 y2 l x3 y3 l x4 y4 l x5 y5 l
        geomString = mystr.split('S\r\n')[0].split('M\r\n')[1]
        coordsString = [value for value in geomString.split(' ') if value not in ['m','l','']]

        # part 2: update geometry in the map
        if self.order_obj.geometry.type.upper() == 'POLYGON':
            pdf_geom = PdfFileReader(open(cfg.annot_poly,'rb'))
        elif self.order_obj.geometry.type.upper() == 'POLYLINE':
            pdf_geom = PdfFileReader(open(cfg.annot_line,'rb'))
        
        page_geom = pdf_geom.getPage(0)
        annot = page_geom['/Annots'][0]
        updateVertices = "annot.getObject().update({NameObject('/Vertices'):ArrayObject([FloatObject("+coordsString[0]+")"

        for item in coordsString[1:]:
            updateVertices = updateVertices + ',FloatObject('+item+')'
        updateVertices = updateVertices + "])})"
        exec(updateVertices)

        xcoords = []
        ycoords = []
        for i in range(0,len(coordsString)-1):
            if i%2 == 0:
                xcoords.append(float(coordsString[i]))
            else:
                ycoords.append(float(coordsString[i]))

        # below rect seems to be geom bounding box coordinates: xmin, ymin, xmax,ymax
        annot.getObject().update({NameObject('/Rect'):ArrayObject([FloatObject(min(xcoords)), FloatObject(min(ycoords)), FloatObject(max(xcoords)), FloatObject(max(ycoords))])})
        annot.getObject().pop('/AP')  # this is to get rid of the ghost shape
        annot.getObject().update({NameObject('/T'):createStringObject(u'ERIS')})

        output = PdfFileWriter()
        output.addPage(page_geom)
        annotPdf = os.path.join(cfg.scratch, "annot.pdf")
        outputStream = open(annotPdf,"wb")
        output.write(outputStream)
        outputStream.close()
        output = None
        return annotPdf

    def annotatePdf(self, mapPdf, myAnnotPdf):
        pdf_intermediate = PdfFileReader(open(mapPdf,'rb'))
        page= pdf_intermediate.getPage(0)

        pdf = PdfFileReader(open(myAnnotPdf,'rb'))
        FIMpage = pdf.getPage(0)
        page.mergePage(FIMpage)

        output = PdfFileWriter()
        output.addPage(page)

        annotatedPdf = mapPdf[:-4]+'_a.pdf'
        outputStream = open(annotatedPdf,"wb")
        output.write(outputStream)
        outputStream.close()
        output = None
        return annotatedPdf

    def myFirstPage(self, canvas, doc):
        canvas.saveState()
        canvas.drawImage(cfg.summarypage,0,0, int(self.PAGE_WIDTH),int(self.PAGE_HEIGHT))
        canvas.setStrokeColorRGB(0.67,0.8,0.4)
        canvas.line(50,100,int(self.PAGE_WIDTH-30),100)
        styles = getSampleStyleSheet()
        style = styles["Normal"]

        # SET HYPERLINKS        https://www.usgs.gov/faqs/where-can-i-find-a-topographic-map-symbol-sheet?qt-news_science_products=0#qt-news_science_products
        canvas.linkURL(r"https://pubs.usgs.gov/unnumbered/70039569/report.pdf", (60,247,220,257), thickness=0, relative=1)
        canvas.linkURL(r"https://pubs.usgs.gov/bul/0788e/report.pdf", (60,237,220,247), thickness=0, relative=1)
        canvas.linkURL(r"https://pubs.usgs.gov/gip/TopographicMapSymbols/topomapsymbols.pdf", (60,217,220,227), thickness=0, relative=1)

        canvas.setFont('Helvetica-Bold', 8)
        canvas.drawString(54, 270, "Topographic Map Symbology for the maps may be available in the following documents:")

        canvas.setFont('Helvetica-Oblique', 8)
        canvas.drawString(54, 260, "Pre-1947")
        canvas.drawString(54, 230, "1947-2009")
        canvas.drawString(54, 210, "2009-present")

        canvas.setFont('Helvetica', 8)
        canvas.drawString(54, 180, "Topographic Maps included in this report are produced by the USGS and are to be used for research purposes including a phase I report.")
        canvas.drawString(54, 170, "Maps are not to be resold as commercial property.")
        canvas.drawString(54, 160, "No warranty of Accuracy or Liability for ERIS: The information contained in this report has been produced by ERIS Information Inc.(in the US)")
        canvas.drawString(54, 150, "and ERIS Information Limited Partnership (in Canada), both doing business as 'ERIS', using Topographic Maps produced by the USGS.")
        canvas.drawString(54, 140, "This maps contained herein does not purport to be and does not constitute a guarantee of the accuracy of the information contained herein.")
        canvas.drawString(54, 130, "Although ERIS has endeavored to present you with information that is accurate, ERIS disclaims, any and all liability for any errors, omissions, ")
        canvas.drawString(54, 120, "or inaccuracies in such information and data, whether attributable to inadvertence, negligence or otherwise, and for any consequences")
        canvas.drawString(54, 110, "arising therefrom. Liability on the part of ERIS is limited to the monetary value paid for this report.")
        
        canvas.setFillColorRGB(0,0,255)
        canvas.drawString(54, 250, "    Page 223 of 1918 Topographic Instructions")
        canvas.drawString(54, 240, "    Page 130 of 1928 Topographic Instructions")
        canvas.drawString(54, 220, "    Topographic Map Symbols")
        canvas.drawString(54, 200, "    US Topo Map Symbols (see attached document in this report)")
        
        canvas.restoreState()
        style = None
        del canvas

    def goSummaryPage(self, summaryPdf, data):
        doc = SimpleDocTemplate(summaryPdf, pagesize = letter)

        Story = [Spacer(1,0.5*inch)]
        styles = getSampleStyleSheet()
        style = styles["Normal"]

        p = None

        try:
            p = Paragraph('<para alignment="justify"><font name=Helvetica size = 11>We have searched USGS collections of current topographic maps and historical topographic maps for the project property. Below is a list of maps found for the project property and adjacent area. Maps are from 7.5 and 15 minute topographic map series, if available.</font></para>',style)
        except Exception as e:
            raise

        Story.append(p)
        Story.append(Spacer(1,0.28*inch))

        if len(data) < 31:
            data.insert(0,["  "])
            data.insert(0,['Year','Map Series'])
            table = Table(data, colWidths = 35,rowHeights=14)
            table.setStyle([('FONT',(0,0),(1,0),'Helvetica-Bold'),
                            ('ALIGN',(0,1),(-1,-1),'CENTER'),
                            ('ALIGN',(0,0),(1,0),'LEFT'),])   #note the last comma
            Story.append(table)
        elif len(data) > 30 and len(data) < 61: #break into 2 columns
            newdata = []
            newdata.append(['Year','Map Series','   ','Year','Map Series'])
            newdata.append([' ','   ',' '])
            i = 0
            while i < 30:
                row= data[i]
                row.append('    ')
                if (i+30) < len(data):
                    row.extend(data[i+30])
                else:
                    row.extend(['    ','  '])
                newdata.append(row)
                i = i + 1
            table = Table(newdata, colWidths = 35,rowHeights=12)
            table.setStyle([('ALIGN',(0,0),(4,0),'LEFT'),
                    ('FONT',(0,0),(4,0),'Helvetica-Bold'),
                    ('ALIGN',(0,1),(-1,-1),'CENTER'),])
            Story.append(table)
        elif len(data) > 60 and len(data) < 91:   #break into 3 columns
            newdata = []
            newdata.append(['Year','Map Series','   ','Year','Map Series','   ','Year','Map Series'])
            newdata.append([' ',' ','   ',' ',' ','   ',' ',' '])
            i = 0
            while i < 30:
                row= data[i]
                row.append('    ')
                row.extend(data[i+30])
                row.append('    ')
                if(i+60) < len(data):
                    row.extend(data[i+60])
                else:
                    row.append('    ')
                    row.append('  ')

                newdata.append(row)
                i = i + 1
            table = Table(newdata, colWidths = 35,rowHeights=12)
            table.setStyle([('FONT',(0,0),(7,0),'Helvetica-Bold'),
                    ('ALIGN',(0,1),(-1,-1),'CENTER'),
                    ('ALIGN',(0,0),(7,0),'LEFT'),])
            Story.append(table)

        doc.build(Story, onFirstPage=self.myFirstPage, onLaterPages=self.myFirstPage)
        doc = None

    def myCoverPage(self, canvas, doc):
        pagesize = portrait(letter)
        [self.PAGE_WIDTH,self.PAGE_HEIGHT]=pagesize[:2]
        self.PAGE_WIDTH=int(self.PAGE_WIDTH)
        self.PAGE_HEIGHT=int(self.PAGE_HEIGHT)

        AddressText = '%s\n%s %s %s'%(self.order_obj.addr, self.order_obj.city, self.order_obj.provstate, self.order_obj.postal_code)

        canvas.drawImage(cfg.coverPic,0,0, self.PAGE_WIDTH,self.PAGE_HEIGHT)
        leftsw= 54
        heights = 400
        rightsw = 200
        space = 20

        canvas.setFont('Helvetica-Bold', 13)
        canvas.drawString(leftsw, heights, "Project Property:")
        canvas.drawString(leftsw, heights-3*space,"Project No.:")
        canvas.drawString(leftsw, heights-4*space,"Requested By:")
        canvas.drawString(leftsw, heights-5*space,"Order No.:")
        canvas.drawString(leftsw, heights-6*space,"Date Completed:")
        canvas.setFont('Helvetica', 13)
        canvas.drawString(rightsw,heights-0*space, self.order_obj.site_name)
        canvas.drawString(rightsw, heights-1*space,AddressText.split("\n")[0])
        canvas.drawString(rightsw, heights-2*space,AddressText.split("\n")[1])
        canvas.drawString(rightsw, heights-3*space,self.order_obj.project_num)
        canvas.drawString(rightsw, heights-4*space,self.order_obj.company_desc)
        canvas.drawString(rightsw, heights-5*space,self.order_obj.number)
        canvas.drawString(rightsw, heights-6*space,time.strftime('%B %d, %Y', time.localtime()))
        canvas.saveState()

        del canvas

    def goCoverPage(self,coverPdf):
        doc = SimpleDocTemplate(coverPdf, pagesize = letter)
        doc.build([Spacer(0,4*inch)], onFirstPage=self.myCoverPage, onLaterPages=self.myCoverPage)
        doc = None

    def dedupMaplist(self, mapslist):
        if mapslist != []:
        # remove duplicates (same cell and same year)
            if len(mapslist) > 1:   # if just 1, no need to do anything
                mapslist = sorted(mapslist,key=operator.itemgetter(3,0), reverse = True)  # sorted based on year then cell
                i=1
                remlist = []
                while i<len(mapslist):
                    row = mapslist[i]
                    if row[3] == mapslist[i-1][3] and row[0] == mapslist[i-1][0]:
                        remlist.append(i)
                    i = i+1

                for index in sorted(remlist,reverse = True):
                    del mapslist[index]
        return mapslist

    def countSheets(self, mapslist):
        if len(mapslist) == 0:
            count = []
        elif len(mapslist) == 1:
            count = [1]
        else:
            count = [1]
            i = 1
            while i < len(mapslist):
                if mapslist[i][3] == mapslist[i-1][3]:
                    count.append(count[i-1]+1)
                else:
                    count.append(1)
                i = i + 1
        return count

    # reorganize the pdf dictionary based on years
    # filter out irrelevant background years (which doesn't have a centre selected map)
    def reorgByYear(self, mapslist, cellids_selected):      # [64818, 15X15 GRID,  LA_Zachary_335142_1963_62500_geo.pdf,  1963]
        diction_pdf_inPresentationBuffer = {}               # {1975: [geopdf1.pdf, geopdf2.pdf...], 1968: [geopdf11.pdf, ...]}
        diction_pdf_inSearchBuffer = {}
        diction_cellids = {}                                # {1975:[cellid1,cellid2...], 1968:[cellid11,cellid12,...]}

        for row in mapslist:
            if row[3] in diction_pdf_inPresentationBuffer.keys():  #{1963:LA_Zachary_335142_1963_62500_geo.pdf, 1975:....}
                diction_pdf_inPresentationBuffer[row[3]].append(row[2])
                diction_cellids[row[3]].append(row[0])
            else:
                diction_pdf_inPresentationBuffer[row[3]] = [row[2]]
                diction_cellids[row[3]] = [row[0]]

        for key in diction_cellids:    # key is the year
            hasSelectedMap = False
            for (cellid,pdfname) in zip(diction_cellids[key],diction_pdf_inPresentationBuffer[key]):
                if cellid in cellids_selected:
                    if key in diction_pdf_inSearchBuffer.keys():
                        diction_pdf_inSearchBuffer[key].append(pdfname)
                    else:
                        diction_pdf_inSearchBuffer[key] = [pdfname]
                    hasSelectedMap = True
                    # break;
            if not hasSelectedMap:
                diction_pdf_inPresentationBuffer.pop(key,None)
        return (diction_pdf_inPresentationBuffer,diction_pdf_inSearchBuffer)

    # create PDF and also make a copy of the geotiff files if the scale is too small
    def createPDF(self,seriesText,diction,diction_s,outpdfname,yearalldict,copydirs):
        
        if self.order_obj.geometry.type.lower() == 'point':
            orderGeomlyrfile = cfg.orderGeomlyrfile_point
        elif self.order_obj.geometry.type.lower() =='polyline':
            orderGeomlyrfile = cfg.orderGeomlyrfile_polyline
        else:
            orderGeomlyrfile = cfg.orderGeomlyrfile_polygon

        orderGeomLayer = arcpy.mapping.Layer(orderGeomlyrfile)
        orderGeomLayer.replaceDataSource(cfg.scratch,"SHAPEFILE_WORKSPACE","orderGeometry")

        extentBufferLayer = arcpy.mapping.Layer(cfg.bufferlyrfile)
        extentBufferLayer.replaceDataSource(cfg.scratch,"SHAPEFILE_WORKSPACE","buffer_extent75")   #change on 11/3/2016, fix all maps to the same scale

        outputPDF = arcpy.mapping.PDFDocumentCreate(os.path.join(cfg.scratch, outpdfname))
        years = diction.keys()

        if self.is_aei == 'Y':
            years.sort(reverse = False)
        else:
            years.sort(reverse = True)

        for year in years:
            if year == "":
                years.remove("")
        print(years)

        for year in years:
            if int(year) < 2008:
                tifdir = cfg.tifdir_h

                if len(years) > 1:
                    topofile = cfg.topolyrfile_b
                else:
                    topofile = cfg.topolyrfile_none

                mscale = int(diction[year][0].split('_')[-2])   #assumption: WI_Ashland East_500066_1964_24000_geo.pdf, and all pdfs from the same year are of the same scale
                print("########" + str(mscale))

                if self.is_aei == 'Y' and mscale in [24000,31680]:
                    seriesText = '7.5'
                elif self.is_aei == 'Y' and mscale == 62500:
                    seriesText = '15'
                elif self.is_aei == 'Y':
                    seriesText = '7.5'
                else:
                    pass
            else:
                tifdir = cfg.tifdir_c

                if len(years) > 1:
                    topofile = cfg.topolyrfile_w
                else:
                    topofile = cfg.topolyrfile_none

                mscale = 24000
            mscale = 24000      # change on 11/3/2016, to fix all maps to the same scale
            # add to map template, clip (but need to keep both metadata: year, grid size, quadrangle name(s) and present in order

            if self.is_nova == 'Y':
                mxd = arcpy.mapping.MapDocument(cfg.mxdfile_nova)
            else:
                mxd = arcpy.mapping.MapDocument(cfg.mxdfile)

            df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
            df.spatialReference = self.out_coordinate_system

            arcpy.mapping.AddLayer(df,extentBufferLayer,"Top")

            if self.yesBoundary.lower() == 'fixed':
                arcpy.mapping.AddLayer(df,orderGeomLayer,"Top")

            # change scale, modify map elements, export
            needtif = False
            df.extent = extentBufferLayer.getSelectedExtent(False)

            if df.scale < mscale:
                scale = mscale
                needtif = False
            else:
                # if df.scale > 2 * mscale:  # 2 is an empirical number
                if df.scale > 1.5 * mscale:
                    print("***** need to provide geotiffs")
                    scale = df.scale
                    needtif = True
                else:
                    print("scale is slightly bigger than the original map scale, use the standard topo map scale.")
                    scale = df.scale
                    needtif = False

            copydir = os.path.join(cfg.scratch,self.order_obj.number,str(year)+"_"+seriesText+"_"+str(mscale))
            os.makedirs(copydir)   # WI_Marengo_503367_1984_24000_geo.pdf -> 1984_7.5_24000

            if needtif == True:
                copydirs.append(copydir)

            pdfnames = diction[year]
            pdfnames.sort()

            quadrangles = ""
            seq = 0
            firstTime = True

            for pdfname in pdfnames:
                tifname = pdfname[0:-4]   # note without .tif part
                tifname_bk = tifname

                if os.path.exists(os.path.join(tifdir,tifname+ "_t.tif")):
                    if '.' in tifname:
                        tifname = tifname.replace('.','')

                    # need to make a local copy of the tif file for fast data source replacement
                    namecomps = tifname.split('_')
                    namecomps.insert(-2,year)
                    newtifname = '_'.join(namecomps)

                    shutil.copyfile(os.path.join(tifdir,tifname_bk+"_t.tif"),os.path.join(copydir,newtifname+'.tif'))
                    topoLayer = arcpy.mapping.Layer(topofile)
                    topoLayer.replaceDataSource(copydir, "RASTER_WORKSPACE", newtifname)
                    topoLayer.name = newtifname
                    arcpy.mapping.AddLayer(df, topoLayer, "BOTTOM")

                    if pdfname in diction_s[year]:
                        comps = diction[year][seq].split('_')
                        if int(year)<2008:
                            quadname = comps[1] +", "+comps[0]
                        else:
                            quadname = " ".join(comps[1:len(comps)-3])+", "+comps[0]

                        if quadrangles =="":
                            quadrangles = quadname
                        else:
                            quadrangles = quadrangles + "; " + quadname
                else:
                    print("tif file doesn't exist " + tifname)
                    if not os.path.exists(tifdir):
                        print("tif dir doesn't exist " + tifdir)
                    else:
                        print("tif dir does exist " + tifdir)
                seq = seq + 1

            df.extent = extentBufferLayer.getSelectedExtent(False) # this helps centre the map
            df.scale = scale

            for lyr in arcpy.mapping.ListLayers(mxd, "", df):
                if lyr.name == "Buffer Outline":
                    arcpy.mapping.RemoveLayer(df, lyr)

            if self.is_nova == 'Y':
                yearTextE = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "year")[0]
                yearTextE.text = year

                quadrangleTextE = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "quadrangle")[0]
                quadrangleTextE.text = "Quadrangle(s): " + quadrangles

                sourceTextE = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "source")[0]
                sourceTextE.text = "Source: USGS " + seriesText + " Minute Topographic Map"

                projNoTextE = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "projno")[0]
                projNoTextE.text = "Project No. " + self.order_obj.project_num

                siteNameTextE = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "sitename")[0]
                siteNameTextE.text = "Site Name: " + self.order_obj.site_name + ', ' + self.order_obj.addr

                ordernoTextE = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "orderno")[0]
                ordernoTextE.text = "Order No. " + self.order_obj.number
            else:
                yearTextE = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "year")[0]
                yearTextE.text = year

                # write photo and photo revision year
                yearlist = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "yearlist")[0]
                y = yearalldict.get(year)
                if y != None:
                    yearlisttext = " "                  # must include blank space if blank to write text element
                    for k,v in y.items():               # for now we only want to include "aerial photo year","photo revision year" out of 8 years
                        if k in ["aerial photo year","photo revision year"]:
                            x = "".join((str(k).title() + ": " + v + "\r\n"))
                            yearlisttext += x
                    yearlist.text = yearlisttext
                else:
                    yearlist.text = " "                 # must include blank space if blank to write text element

                quadrangleTextE = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "quadrangle")[0]
                quadrangleTextE.text = "Quadrangle(s): " + quadrangles

                sourceTextE = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "source")[0]
                sourceTextE.text = "Source: USGS " + seriesText + " Minute Topographic Map"

                ordernoTextE = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "orderno")[0]
                ordernoTextE.text = "Order No.: " + self.order_obj.number

            if self.is_newLogofile == 'Y':     # need to change logo for emg
                logoE = arcpy.mapping.ListLayoutElements(mxd, "PICTURE_ELEMENT", "logo")[0]
                logoE.sourceImage = os.path.join(cfg.logopath, self.newlogofile)

            arcpy.RefreshTOC()
            outputpdf = os.path.join(cfg.scratch, "map_"+seriesText+"_"+year+".pdf")

            if int(year)<2008:
                arcpy.mapping.ExportToPDF(mxd, outputpdf, "PAGE_LAYOUT", 640, 480, 250, "BEST", "RGB", True, "ADAPTIVE", "RASTERIZE_BITMAP", False, True, "LAYERS_AND_ATTRIBUTES", True, 90)
            else:
                arcpy.mapping.ExportToPDF(mxd, outputpdf, "PAGE_LAYOUT", 640, 480, 350, "BEST", "RGB", True, "ADAPTIVE", "RASTERIZE_BITMAP", False, True, "LAYERS_AND_ATTRIBUTES", True, 90)

            if seriesText == "7.5":
                mxd.saveACopy(os.path.join(cfg.scratch,"75_"+year+".mxd"))
            else:
                mxd.saveACopy(os.path.join(cfg.scratch,"15_"+year+".mxd"))

            if (self.yesBoundary.lower() == 'yes' and (self.order_obj.geometry.type.lower() == "polyline" or self.order_obj.geometry.type.lower() == "polygon")):

                if firstTime:
                    # remove all other layers
                    scale2use = df.scale
                    for lyr in arcpy.mapping.ListLayers(mxd, "", df):
                        arcpy.mapping.RemoveLayer(df, lyr)
                    arcpy.mapping.AddLayer(df,orderGeomLayer,"Top") #the layer is visible
                    df.scale = scale2use
                    shapePdf = os.path.join(cfg.scratch, 'shape.pdf')
                    arcpy.mapping.ExportToPDF(mxd, shapePdf, "PAGE_LAYOUT", 640, 480, 250, "BEST", "RGB", True, "ADAPTIVE", "RASTERIZE_BITMAP", False, True, "LAYERS_AND_ATTRIBUTES", True, 90)
                    # create the a pdf with annotation just once
                    myAnnotPdf = self.createAnnotPdf(shapePdf)
                    firstTime = False

                # merge annotation pdf to the map
                Topopdf = self.annotatePdf(outputpdf, myAnnotPdf)
                outputpdf = Topopdf

            outputPDF.appendPages(outputpdf)

        outputPDF.saveAndClose()
        return copydirs

    def zipdir(self, path, zip):
        for root, dirs, files in os.walk(path):
            for file in files:
                arcname = os.path.relpath(os.path.join(root, file), os.path.join(path, '..'))
                zip.write(os.path.join(root, file), arcname)

    def log(self, logfile):
        logger = logging.getLogger("TOPO_US_dev")
        handler = logging.FileHandler(logfile)
        handler.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)    
        logger.addHandler(handler)
        return logger,handler

    def custom_rpt(self):
        # Get company flag for custom colour border
        if self.order_obj.company_id == '109085': # Mid-Atlantic Associates, Inc.
            cfg.annot_poly = cfg.annot_poly_c
            cfg.annot_line = cfg.annot_line_c
            print('custom colour boundary set')
        else:
            print('no custom colour boundary set')

        self.is_nova = 'N'
        try:
            con = cx_Oracle.connect(cfg.connectionString)
            cur = con.cursor()

            cur.execute("select decode(c.company_id, 40385, 'Y', 'N') is_nova from orders o, customer c where o.customer_id = c.customer_id and o.order_id=" + str(self.order_obj.id))
            t = cur.fetchone()
            self.is_nova = t[0]
        finally:
            cur.close()
            con.close()

        self.is_aei = 'N'
        try:
            con = cx_Oracle.connect(cfg.connectionString)
            cur = con.cursor()
            self.is_aei = cur.callfunc('ERIS_CUSTOMER.IsProductChron', str, (str(self.order_obj.id),))
        finally:
            cur.close()
            con.close()

        self.is_newLogofile = 'N'
        try:
            con = cx_Oracle.connect(cfg.connectionString)
            cur = con.cursor()
            self.newlogofile = cur.callfunc('ERIS_CUSTOMER.IsCustomLogo', str, (str(self.order_obj.id),))

            if self.newlogofile != None:
                self.is_newLogofile = 'Y'
                if self.newlogofile =='RPS_RGB.gif':
                    self.newlogofile='RPS.png'
        finally:
            cur.close()
            con.close()

        return self.is_nova, self.is_aei, self.is_newLogofile

    def proj_list(self, orderGeometry):
        self.srGCS83 = arcpy.SpatialReference(os.path.join(cfg.prjpath, "GCSNorthAmerican1983.prj"))
        self.srWGS84 = arcpy.SpatialReference(os.path.join(cfg.prjpath, "WGS1984.prj"))
        self.srGoogle = arcpy.SpatialReference(3857)   # web mercator

        for row in arcpy.SearchCursor(orderGeometry):
            print(row)
            UTMvalue = str(row.getValue('UTM'))[41:43]
        if UTMvalue[0] == '0':
            UTMvalue=' '+UTMvalue[1:]
        self.out_coordinate_system = arcpy.SpatialReference('WGS 1984 UTM Zone %sN'%UTMvalue)

        return self.srGCS83, self.srWGS84, self.srGoogle, self.out_coordinate_system