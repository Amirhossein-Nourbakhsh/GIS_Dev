import os
import sys
import arcpy
import ConfigParser

addpath = os.path.abspath(__file__).replace(os.path.relpath(__file__),"GIS_Dev")
sys.path.insert(1,os.path.join(addpath,'DB_Framework'))
import models

def server_loc_config(configpath,environment):
    configParser = ConfigParser.RawConfigParser()
    configParser.read(configpath)
    if environment == 'test':
        dbconnection = configParser.get('server-config','dbconnection_test')
        reportcheck = configParser.get('server-config','reportcheck_test')
        reportviewer = configParser.get('server-config','reportviewer_test')
        reportinstant = configParser.get('server-config','instant_test')
        reportnoninstant = configParser.get('server-config','noninstant_test')
        upload_viewer = configParser.get('url-config','uploadviewer_test')
        server_config = {'dbconnection':dbconnection,'reportcheck':reportcheck,'viewer':reportviewer,'instant':reportinstant,'noninstant':reportnoninstant,'viewer_upload':upload_viewer}
        return server_config
    else:
        return 'invalid server configuration'

def createScratch():
    scratch = os.path.join(r"W:\Data Analysts\Alison\_GIS\FIM_US_SCRATCHY", "test123")
    scratchgdb = "scratch.gdb"
    if not os.path.exists(scratch):
        os.mkdir(scratch)
    if not os.path.exists(os.path.join(scratch, scratchgdb)):
        arcpy.CreateFileGDB_management(scratch, "scratch.gdb")
    return scratch, scratchgdb

# arcpy parameter
# OrderIDText = arcpy.GetParameterAsText(0) 
# BufsizeText = arcpy.GetParameterAsText(1)
# yesBoundary = arcpy.GetParameterAsText(2)
# multipage = arcpy.GetParameterAsText(3)
# gridsize = arcpy.GetParameterAsText(4)
# scratchgdb = arcpy.env.scratchGDB

# order info
order_obj = models.Order().get_order(21013100011)

# parameters
BufsizeText ='0.17'
yesBoundary = "yes"
gridsize = "0.3 KiloMeters"
resolution = "600"

# flags
multipage = True
delyearFlag = "N"
NRF = 'N'

# scratch file
scratch, scratchgdb = createScratch()
orderGeometry= os.path.join(scratch, "orderGeometry.shp")
orderGeometryPR = os.path.join(scratch, "orderGeometryPR.shp")
outBufferSHP = os.path.join(scratch, "buffer.shp")
selectedmain = os.path.join(scratch, "selectedmain.shp")
selectedadj = os.path.join(scratch, "selectedadj.shp")
extent = os.path.join(scratch, "extent.shp")
summaryfile = os.path.join(scratch, "summary.pdf")
coverfile = os.path.join(scratch, "cover.pdf")
shapePdf = os.path.join(scratch, "shape.pdf")
annotPdf = os.path.join(scratch, "annot.pdf")

# connection/report output
server_environment = 'test'
server_config_file = r'\\cabcvan1gis005\GISData\ERISServerConfig.ini'
server_config = server_loc_config(server_config_file,server_environment)

connectionString = server_config["dbconnection"]
reportcheckFolder = server_config["reportcheck"]
viewerFolder = server_config["viewer"]
uploadlink =  server_config["viewer_upload"] + r"/FIMUpload?ordernumber="

# folder
connectionPath = r"\\cabcvan1gis005\GISData\FIMS_USA"
logopath = os.path.join(connectionPath, "logos")

# master file/folder
mastergdb = r"\\CABCVAN1FPR009\USA_FIPs\US FIM Footprints\_master\FIM_US_STATES.gdb"
excelfile = os.path.join(connectionPath,"master\MASTER_ALL_STATES.xlsx")

# layer
imagelyr = os.path.join(connectionPath,r"layer\mosaic_jpg_255.lyr")
bndylyrfile = os.path.join(connectionPath,r"layer\boundary.lyr")
orderGeomlyrfile_point = os.path.join(connectionPath,r"layer\SiteMaker.lyr")
orderGeomlyrfile_polyline = os.path.join(connectionPath,r"layer\orderLine.lyr")
orderGeomlyrfile_polygon = os.path.join(connectionPath,r"layer\orderPoly.lyr")
sheetLayer = os.path.join(connectionPath, r"layer\hallowsheet.lyr")

# mxd
FIMmxdfile = os.path.join(connectionPath, r"mxd\FIMLayout.mxd")

# pdf
annot_poly = os.path.join(connectionPath,r"mxd\annot_poly.pdf")
annot_line = os.path.join(connectionPath,r"mxd\annot_line.pdf")

# coverPic
coverPic = os.path.join(connectionPath, r"coverPic\ERIS_2018_ReportCover_Fire Insurance Maps_F.jpg")
secondPic = os.path.join(connectionPath, r"coverPic\ERIS_2018_ReportCover_Second Page_F.jpg")

# log
logfile = os.path.join(connectionPath, r"log\USFIM_Log.txt")
logname = "FIM_US_dev"