import arcpy
import os
import sys
import ConfigParser
addpath = os.path.abspath(__file__).replace(os.path.relpath(__file__),"GIS_Dev")
sys.path.insert(1,os.path.join(addpath,'DB_Framework'))
import db_connections as con

def server_loc_config(configpath,environment):
    configParser = ConfigParser.RawConfigParser()
    configParser.read(configpath)
    if environment == 'test':
        dbconnection = configParser.get('server-config','dbconnection_test')
        reportcheck = configParser.get('server-config','reportcheck_test')
        reportviewer = configParser.get('server-config','reportviewer_test')
        reportinstant = configParser.get('server-config','instant_test')
        reportnoninstant = configParser.get('server-config','noninstant_test')
        upload_viewer = configParser.get('url-config','uploadviewer')
        server_config = {'dbconnection':dbconnection,'reportcheck':reportcheck,'viewer':reportviewer,'instant':reportinstant,'noninstant':reportnoninstant,'viewer_upload':upload_viewer}
        return server_config
    # elif environment == 'prod':
    #     dbconnection = configParser.get('server-config','dbconnection_prod')
    #     reportcheck = configParser.get('server-config','reportcheck_prod')
    #     reportviewer = configParser.get('server-config','reportviewer_prod')
    #     reportinstant = configParser.get('server-config','instant_prod')
    #     reportnoninstant = configParser.get('server-config','noninstant_prod')
    #     upload_viewer = configParser.get('url-config','uploadviewer_prod')
    #     server_config = {'dbconnection':dbconnection,'reportcheck':reportcheck,'viewer':reportviewer,'instant':reportinstant,'noninstant':reportnoninstant,'viewer_upload':upload_viewer}
    #     return server_config
    else:
        return 'invalid server configuration'

# OrderIDText = arcpy.GetParameterAsText(0)#'734618'#
# BufsizeText = arcpy.GetParameterAsText(1)#'2.4'
# yesBoundary = arcpy.GetParameterAsText(2)#'no'##
# scratch = arcpy.env.scratchWorkspace#r"

scratch = os.path.join(r"\\cabcvan1gis005\MISC_DataManagement\_AW\TOPO_US_SCRATCHY", "test_test")
if not os.path.exists(scratch):
    os.mkdir(scratch)

# connections/report outputs
server_environment = 'test'
server_config_file = con.server_config_file #r"\\cabcvan1gis006\GISData\ERISServerConfig.ini"
server_config = server_loc_config(server_config_file,server_environment)

reportcheckFolder = server_config["reportcheck"]
viewerFolder = server_config["viewer"]
topouploadurl =  server_config["viewer_upload"] + r"/ErisInt/BIPublisherPortal_prod/Viewer.svc/TopoUpload?ordernumber="
connectionString = server_config["dbconnection"] #con.connection_string #'eris_gis/gis295@cabcvan1ora006.glaciermedia.inc:1521/GMTESTC'

# scratch file/folder outputs
summaryPdf = os.path.join(scratch,'summary.pdf')
coverPdf = os.path.join(scratch,"cover.pdf")
shapePdf = os.path.join(scratch, 'shape.pdf')
annotPdf = os.path.join(scratch, "annot.pdf")
orderGeometry= os.path.join(scratch,"orderGeometry.shp")
orderGeometryPR = os.path.join(scratch, "orderGeometryPR.shp")
orderBuffer = os.path.join(scratch,"buffer.shp")
extent = os.path.join(scratch, "extent.shp")
viewertemp = os.path.join(scratch,'viewertemp')

# folders
testpath = r"\\cabcvan1gis005\GISData\Topo_USA"
mxdpath = os.path.join(testpath, r"mxd")

# master data files\folders
mastergdb = os.path.join(testpath, r"masterfile\MapIndices_National_GDB.gdb")
csvfile_h = os.path.join(testpath, r"masterfile\All_HTMC_all_all_gda_results.csv")
csvfile_c = os.path.join(testpath, r"masterfile\All_USTopo_T_7.5_gda_results.csv")
tifdir_h = r'\\cabcvan1fpr009\USGS_Topo\USGS_HTMC_Geotiff'
tifdir_c = r'\\cabcvan1fpr009\USGS_Topo\USGS_currentTopo_Geotiff'

# mxds
mxdfile = os.path.join(mxdpath,"template.mxd")
mxdfile_nova = os.path.join(mxdpath,'template_nova.mxd')

# layers
topolyrfile_none = os.path.join(mxdpath,"topo.lyr")
topolyrfile_b = os.path.join(mxdpath,"topo_black.lyr")
topolyrfile_w = os.path.join(mxdpath,"topo_white.lyr")
bufferlyrfile = os.path.join(mxdpath,"buffer_extent.lyr")
orderGeomlyrfile_point = os.path.join(mxdpath,"orderPoint.lyr")
orderGeomlyrfile_polyline = os.path.join(mxdpath,"orderLine.lyr")
orderGeomlyrfile_polygon = os.path.join(mxdpath,"orderPoly.lyr")

# pdfs
annot_poly = os.path.join(mxdpath,"annot_poly.pdf")
annot_line = os.path.join(mxdpath,"annot_line.pdf")
annot_poly_c = os.path.join(mxdpath,"annot_poly_red.pdf")
annot_line_c = os.path.join(mxdpath,"annot_line_red.pdf")
pdfsymbolfile = os.path.join(mxdpath, "US Topo Map Symbols v7.4.pdf")

# logos
logopath = os.path.join(mxdpath,"logos")

# covers
coverPic = os.path.join(mxdpath, "coverPic", "ERIS_2018_ReportCover_Topographic Maps_F.jpg")
summarypage = os.path.join(mxdpath, "coverPic", "ERIS_2018_ReportCover_Second Page_F.jpg")

# other
logfile = os.path.join(testpath, r"log\USTopoSearch_Log.txt")
logname = "TOPO_US_dev"
readmefile = os.path.join(mxdpath,"readme.txt")