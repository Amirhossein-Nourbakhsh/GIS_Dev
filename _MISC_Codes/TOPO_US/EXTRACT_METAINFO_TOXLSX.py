#-------------------------------------------------------------------------------
# Name:        TOPO_US-all
# Purpose:     As we did not have a compiled list of all our topo inventory combined, this script will
#              extract info from the csvs and xmls from our current topo inventory, and compile it into one list.
# Date:        20200126
#-------------------------------------------------------------------------------

import xml.etree.ElementTree as ET
import os
import re
import time
import csv
import openpyxl
import datetime

class TOPO_Process():
    def getmetadata(self, pdfname, tifpath_t, tifpath_o, xmlpath, xmldict):
       
        # GET BOUNDING COORDINATES/NEATLINE FROM XML FILE
        westbc = None
        eastbc = None
        northbc = None
        southbc = None
    
        yeardateonmap = None
        yearimprint = None
        yearphotoinsp = None
        yearphotorevis = None
        yearfieldcheck = None
        yearsurvey = None
        yearedit = None
        yearaerial = None
        neatline_wkt = None
    
        if os.path.exists(xmlpath):
            tree = ET.parse(xmlpath)
            root = tree.getroot()
        
            # procsteps = root.findall("./dataqual/lineage/procstep")
            # yeardict = {}
            # for procstep in procsteps:
            #     procdate = procstep.find("./procdate")
            #     if procdate != None:
            #         procdesc = procstep.find("./procdesc")
            #         yeardict[procdesc.text.upper()] = procdate.text

            for child in root.iter():
                if child.tag == 'westbc':
                    westbc = float(child.text)
                elif child.tag == 'eastbc':
                    eastbc = float(child.text)
                elif child.tag == 'northbc':
                    northbc = float(child.text)
                elif child.tag == 'southbc':
                    southbc = float(child.text)
                elif child.tag == 'procstep':
                    if child[0].text.upper().strip() == 'DATE ON MAP':
                        yeardateonmap = child[1].text.strip()
                    elif child[0].text.upper().strip() == 'IMPRINT YEAR':
                        yearimprint = child[1].text.strip()
                    elif child[0].text.upper().strip() == 'PHOTO INSPECTION YEAR':
                        yearphotoinsp = child[1].text.strip()
                    elif child[0].text.upper().strip() == 'PHOTO REVISION YEAR':
                        yearphotorevis = child[1].text.strip()
                    elif child[0].text.upper().strip() == 'FIELD CHECK YEAR':
                        yearfieldcheck = child[1].text.strip()                                                                                      
                    elif child[0].text.upper().strip() == 'SURVEY YEAR':
                        yearsurvey = child[1].text.strip()
                    elif child[0].text.upper().strip() == 'EDIT YEAR':
                        yearedit = child[1].text.strip()
                    elif child[0].text.upper().strip() == 'AERIAL PHOTO YEAR':
                        yearaerial = child[1].text.strip()     
        
            neatline_wkt = '"' + f"POLYGON (({eastbc} {southbc}, {eastbc} {northbc}, {westbc} {northbc}, {westbc} {southbc}, {eastbc} {southbc}))" + '"'
    
        # CREATE DICT FOR USE IN METAXLSX FILE
        if os.path.exists(xmlpath):
            xmlFLAG = "Y"
        else:
            xmlFLAG = ""            
        if os.path.exists(tifpath_t):
            topoFLAG = "Y"
        else:
            topoFLAG = ""
        if os.path.exists(tifpath_t[0:-4]+".tfw"):
            t_tfwFLAG = "Y"
        else:
            t_tfwFLAG = ""
        if os.path.exists(tifpath_o):
            orthoFLAG = "Y"
        else:
            orthoFLAG = ""
        if os.path.exists(tifpath_o[0:-4]+".tfw"):
            o_tfwFLAG = "Y"
        else:
            o_tfwFLAG = ""
        
        tgtepsg = ""
        wkt = ""
        if pdfname == "" or pdfname == None or pdfname == " ":
            print("there's a blank!!!")
        xmldict[pdfname] = ["", topoFLAG, t_tfwFLAG, orthoFLAG, o_tfwFLAG, xmlFLAG, tgtepsg, wkt, neatline_wkt, yeardateonmap, yearimprint, yearphotoinsp, yearphotorevis, yearfieldcheck, yearsurvey, yearedit, yearaerial]

    def mergemetadata(self,metadict,csvpath):
        print("--------------------")
        print("...merge xml to xlsx...")

        # MERGE XML AND CSV TO DICT
        n = 0
        with open(csvpath, "r") as f:
            reader = csv.reader(f)
            next(f)                                                                                     # skip header
            for row in reader:
                key = row[15]
                if key == "" or key == None or key == " ":
                    print(row)

                try:
                    csvdate = datetime.datetime.strptime(row[10], "%d-%b-%y")
                except:
                    print(row)
                if key in metadict:
                    if key == "" or key == None:
                        print(metadict[key])

                    elif len(metadict[key]) == 17:
                        row.reverse()
                        for item in row:
                            metadict[key].insert(0, item)
                    elif len(metadict[key]) == 33:
                        metadate = datetime.datetime.strptime(metadict[key][10], "%d-%b-%y")
                        if metadate < csvdate:
                            print(metadate)
                            print(csvdate)
                            input(">>>")
                            # print(csvdate)
                            del metadict[key][0:16]
                            row.reverse()
                            for item in row:
                                metadict[key].insert(0, item)


                    elif len(metadict[key]) == 16:
                        print(row)
                        print(metadict[key])
                        print(len(row),len(metadict[key]))
                        input(">>>")

                else:
                    metadict[key] = [row]
                    # metadict[key].append("")
                    n += 1
        print(f"\t{n} csv records not in metadict..." )

    def createxlsx(self, metadict, xlsxpath, csvpath):
        # WRITE TO XLSX
        if os.path.exists(xlsxpath):
            wb = openpyxl.load_workbook(xlsxpath)
            ws = wb["TOPO"]
            
            r = ws.max_row + 1
            for k, v in metadict.items():
                for i in range(0, 33):
                    ws.cell(row=r, column=(i+1), value=v[i]).number_format = "@"
                ws.cell(row=r, column=34, value=record_date).number_format = "@"
                r += 1
        else:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "TOPO"
            
            # ADD XLSX HEADERS  *openpyxl starts at 1
            ws.cell(row=1, column=1).value = "Item ID"
            ws.cell(row=1, column=2).value = "Download(MB unzipped)"
            ws.cell(row=1, column=3).value = "BA"
            ws.cell(row=1, column=4).value = "Sa"
            ws.cell(row=1, column=5).value = "Se"
            ws.cell(row=1, column=6).value = "Grid Size"
            ws.cell(row=1, column=7).value = "Short Name"
            ws.cell(row=1, column=8).value = "Full Name"
            ws.cell(row=1, column=9).value = "MassLoad ID"
            ws.cell(row=1, column=10).value = "Cell ID"
            ws.cell(row=1, column=11).value = "Create Date"
            ws.cell(row=1, column=12).value = "SourceYear"
            ws.cell(row=1, column=13).value = "HTMCImprintYear"
            ws.cell(row=1, column=14).value = "HTMCScan ID"
            ws.cell(row=1, column=15).value = "Download URL"
            ws.cell(row=1, column=16).value = "Filename"
            ws.cell(row=1, column=17).value = "Cloud URL"

            ws.cell(row=1, column=18).value = "TOPO_FLAG"
            ws.cell(row=1, column=19).value = "T_TFW_FLAG"
            ws.cell(row=1, column=20).value = "ORTHO_FLAG"
            ws.cell(row=1, column=21).value = "O_TFW_FLAG"
            ws.cell(row=1, column=22).value = "XML_FLAG"
            ws.cell(row=1, column=23).value = "EPSG"
            ws.cell(row=1, column=24).value = "WKT"
            ws.cell(row=1, column=25).value = "NEATLINE"

            ws.cell(row=1, column=26).value = "XML_DATE_ON_MAP"
            ws.cell(row=1, column=27).value = "XML_IMPRINT_YEAR"
            ws.cell(row=1, column=28).value = "XML_PHOTO_INSPECTION_YEAR"
            ws.cell(row=1, column=29).value = "XML_PHOTO_REVISION_YEAR"
            ws.cell(row=1, column=30).value = "XML_FIELD_CHECK_YEAR"
            ws.cell(row=1, column=31).value = "XML_SURVEY_YEAR"
            ws.cell(row=1, column=32).value = "XML_EDIT_YEAR"
            ws.cell(row=1, column=33).value = "XML_AERIAL_PHOTO_YEAR"

            ws.cell(row=1, column=34).value = "ERIS_RECORD_DATE"

            # WRITE DICT TO XLSX
            r = 2
            for k, v in metadict.items():
                if v[15] == "" or v[15] == None or v[15] == " ":
                    print("there's a blank!")
                    print(k,v)
                try:
                    if len(v) == 17:
                        for i in range(0,17):
                            ws.cell(row=r, column=(i+17), value=v[i]).number_format = "@"
                    elif len(v) == 33:
                        for i in range(0, 33):
                            ws.cell(row=r, column=(i+1), value=v[i]).number_format = "@"
                    ws.cell(row=r, column=34, value=record_date).number_format = "@"
                    r += 1
                except Exception as e:
                    print(f"...failed...{k,v}")
                    print(e)
                    raise
        wb.save(xlsxpath)
        wb.close

# ===============================================================================================================
if __name__ == '__main__':
    s = time.perf_counter()
    tifdir = r"\\CABCVAN1FPR009\USGS_Topo\USGS_currentTopo_Geotiff"
    mscpath = r"\\cabcvan1fpr001\data_us\_GIS_Layers\_FEDERAL\TOPO\2020_09_18"
    csvfile = r"\\cabcvan1fpr001\data_us\_GIS_Layers\_FEDERAL\TOPO\2020_09_18\_oldcsv\TOPO_US_merged.csv"
    record_date = ""

    xlsxpath = os.path.join(mscpath, "TOPO_US_xmlcsv.xlsx")
    xmldict = {}
    tp = TOPO_Process()

    print(f"...starting {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    for file in os.listdir(tifdir):
        if file.endswith("_t.tif"):
            pdfname = file[0:-6]+".pdf"
            tifpath_t = os.path.join(tifdir, pdfname[0:-4]+"_t.tif")
            tifpath_o = os.path.join(tifdir, pdfname[0:-4]+"_o.tif")
            xmlpath = os.path.join(tifdir,pdfname[0:-4]+".xml")

            tp.getmetadata(pdfname, tifpath_t, tifpath_o, xmlpath, xmldict)
    
    print(len(xmldict))
    tp.mergemetadata(xmldict,csvfile)
    tp.createxlsx(xmldict,xlsxpath,csvfile)

    f = time.perf_counter()
    print(f"finished in {round(f-s, 2)} secs  --  {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")