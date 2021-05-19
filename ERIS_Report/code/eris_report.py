import os
import traceback
import timeit
import arcpy
import json
import cx_Oracle
import shutil
import urllib
import topo_image_path
import ConfigParser
import csv
import xml.etree.ElementTree as ET
start1 = timeit.default_timer()
arcpy.env.overwriteOutput = True

eris_report_path = r"GISData\ERISReport\ERISReport\PDFToolboxes"
us_topo_path =r"GISData\Topo_USA"
eris_aerial_ca_path = r"GISData\Aerial_CAN"
tifdir_topo = r'\\cabcvan1fpr009\USGS_Topo\USGS_currentTopo_Geotiff'
world_aerial_arcGIS_online_URL = r"https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/0/query?f=json&returnGeometry=false&spatialRel=esriSpatialRelIntersects&maxAllowableOffset=0&geometryType=esriGeometryPoint&inSR=4326&outFields=SRC_DATE"

def server_loc_config(configpath,environment):
    configParser = ConfigParser.RawConfigParser()
    configParser.read(configpath)
    if environment == 'test':
        reportcheck = configParser.get('server-config','reportcheck_test')
        reportviewer = configParser.get('server-config','reportviewer_test')
        reportinstant = configParser.get('server-config','instant_test')
        reportnoninstant = configParser.get('server-config','noninstant_test')
        upload_viewer = configParser.get('url-config','uploadviewer')
        server_config = {'reportcheck':reportcheck,'viewer':reportviewer,'instant':reportinstant,'noninstant':reportnoninstant,'viewer_upload':upload_viewer}
        return server_config
    elif environment == 'prod':
        reportcheck = configParser.get('server-config','reportcheck_prod')
        reportviewer = configParser.get('server-config','reportviewer_prod')
        reportinstant = configParser.get('server-config','instant_prod')
        reportnoninstant = configParser.get('server-config','noninstant_prod')
        upload_viewer = configParser.get('url-config','uploadviewer_prod')
        server_config = {'reportcheck':reportcheck,'viewer':reportviewer,'instant':reportinstant,'noninstant':reportnoninstant,'viewer_upload':upload_viewer}
        return server_config
    else:
        return 'invalid server configuration'

server_environment = 'test' #'test' for both dev and test
server_config_file = r'\\cabcvan1gis006\GISData\ERISServerConfig.ini'
server_config = server_loc_config(server_config_file,server_environment)
#eris_report_path = r"gptools\ERISReport"
#us_topo_path = r"gptools\Topo_USA"
#eris_aerial_ca_path = r"gptools\Aerial_CAN"
#tifdir_topo = r"\\cabcvan1fpr009\USGS_Topo\USGS_currentTopo_Geotiff"
#world_aerial_arcGIS_online_URL = r"https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/0/query?f=json&returnGeometry=false&spatialRel=esriSpatialRelIntersects&maxAllowableOffset=0&geometryType=esriGeometryPoint&inSR=4326&outFields=SRC_DATE"

class Machine:
    machine_dev = r"\\cabcvan1gis005"
    machine_test = r"\\cabcvan1gis006"
    machine_prod = r"\\cabcvan1gis007"

class Credential:
    oracle_dev = r'eris_gis/gis295@GMDEVC.glaciermedia.inc'
    oracle_test = r'eris_gis/gis295@GMTESTC.glaciermedia.inc'
    oracle_production = r'eris_gis/gis295@GMPRODC.glaciermedia.inc'

class ReportPath:
    noninstant_reports_test = server_config['noninstant']
    noninstant_reports_prod = server_config['noninstant']
    instant_report_test = server_config['instant']
    instant_report_prod = server_config['instant']

class DevConfig:
    machine_path=Machine.machine_test
    instant_reports =ReportPath.instant_report_test
    noninstant_reports = ReportPath.noninstant_reports_test

    def __init__(self,code):
        machine_path=self.machine_path
        self.LAYER=LAYER(machine_path)
        self.DATA=DATA(machine_path)
        self.MXD=MXD(machine_path,code)

class TestConfig:
    machine_path=Machine.machine_test
    instant_reports =ReportPath.instant_report_test
    noninstant_reports = ReportPath.noninstant_reports_test

    def __init__(self,code):
        machine_path=self.machine_path
        self.LAYER=LAYER(machine_path)
        self.DATA=DATA(machine_path)
        self.MXD=MXD(machine_path,code)

class ProdConfig:
    machine_path=Machine.machine_prod
    instant_reports =ReportPath.instant_report_prod
    noninstant_reports = ReportPath.noninstant_reports_prod

    def __init__(self,code):
        machine_path=self.machine_path
        self.LAYER=LAYER(machine_path)
        self.DATA=DATA(machine_path)
        self.MXD=MXD(machine_path,code)

class Map(object):
    def __init__(self,mxdPath,dfname=''):
        self.mxd = arcpy.mapping.MapDocument(mxdPath)
        self.df= arcpy.mapping.ListDataFrames(self.mxd,('%s*')%(dfname))[0]

    def addLayer(self,lyr,workspace_path, dataset_name='',workspace_type="SHAPEFILE_WORKSPACE",add_position="TOP"):
        lyr = arcpy.mapping.Layer(lyr)
        if dataset_name !='':
            lyr.replaceDataSource(workspace_path, workspace_type, os.path.splitext(dataset_name)[0])
        arcpy.mapping.AddLayer(self.df, lyr, add_position)

    def replaceLayerSource(self,lyr_name,to_path, dataset_name='',workspace_type="SHAPEFILE_WORKSPACE"):
        for _ in arcpy.mapping.ListLayers(self.mxd):
            if _.name == lyr_name:
                _.replaceDataSource(to_path, workspace_type,dataset_name)
                return

    def toScale(self,value):
        self.df.scale=value
        self.scale =self.df.scale

    def zoomToTopLayer(self,position =0):
        self.df.extent = arcpy.mapping.ListLayers(self.mxd)[0].getExtent()

    def zoomToLayer(self,lyr_name):
        for _ in arcpy.mapping.ListLayers(self.mxd):
            if _.name ==lyr_name:
                self.df.extent = _.getExtent()
                break
            elif lyr_name in _.name:
                self.df.extent = _.getExtent()
                break
        arcpy.RefreshActiveView()

    def turnOnLayer(self):
        layers = arcpy.mapping.ListLayers(self.mxd, "*", self.df)
        for layer in layers:
            layer.visible = True
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

    def turnLabel(self,lyr_name,visibility =True):
        layers = arcpy.mapping.ListLayers(self.mxd, "*", self.df)
        for layer in layers:
            if layer.name ==lyr_name or layer.name ==arcpy.mapping.Layer(lyr_name).name:
                layer.showLabels = visibility
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

    def addTextoMap(self,textName,textValue, x=None,y=None):
        textElements =arcpy.mapping.ListLayoutElements(self.mxd,"TEXT_ELEMENT")
        for element in textElements:
            if textName.lower() in (element.name).lower():
                element.text = textValue
                if x!=None or y!=None:
                    element.elementPositionX=x
                    element.elementPositionY=y

class LAYER():
    def __init__(self,machine_path):
        self.machine_path = machine_path
        self.get()

    def get(self):
        machine_path = self.machine_path
        self.buffer = os.path.join(machine_path,eris_report_path,'layer','buffer.lyr')
        self.point = os.path.join(machine_path,eris_report_path,r"layer","SiteMaker.lyr")
        self.polyline = os.path.join(machine_path,eris_report_path,r"layer","orderLine.lyr")
        self.polygon = os.path.join(machine_path,eris_report_path,r"layer","orderPoly.lyr")
        self.buffer = os.path.join(machine_path,eris_report_path,'layer','buffer.lyr')
        self.grid = os.path.join(machine_path,eris_report_path,r"layer","GridCC.lyr")
        self.erisPoints = os.path.join(machine_path,eris_report_path,r"layer","ErisClipCC.lyr")
        self.topowhite = os.path.join(machine_path,eris_report_path,'layer',"topo_white.lyr")
        self.road = os.path.join(machine_path,eris_report_path,r"layer","Roadadd_notransparency.lyr")
        self.eris_polygon = os.path.join(machine_path,eris_report_path,r"layer","eris_polygon.lyr")

class DATA():
    def __init__(self,machine_path):
        self.machine_path = machine_path
        self.get()

    def get(self):
        machine_path = self.machine_path
        self.data_topo = os.path.join(machine_path,us_topo_path,"masterfile","CellGrid_7_5_Minute.shp")
        self.road = os.path.join(machine_path,eris_report_path,r"layer","US","Roads2.lyr")

class MXD():
    def __init__(self,machine_path,code):
        self.machine_path = machine_path
        self.get(code)

    def get(self,code):
        machine_path = self.machine_path
        if code == 9093:        # USA
            self.mxdtopo = os.path.join(machine_path,eris_report_path,r"mxd","USTopoMapLayoutCC.mxd")
            self.mxdbing = os.path.join(machine_path,eris_report_path,r"mxd","USBingMapLayoutCC.mxd")
            self.mxdMM = os.path.join(machine_path,eris_report_path,'mxd','USLayoutMMCC.mxd')
        elif code == 9036:      # CAN
            self.mxdtopo = os.path.join(machine_path,eris_report_path,r"mxd","TopoMapLayoutCC.mxd")
            self.mxdbing = os.path.join(machine_path,eris_report_path,r"mxd","BingMapLayoutCC.mxd")
            self.mxdMM = os.path.join(machine_path,eris_report_path,'mxd','DMTILayoutMMCC.mxd')
        elif code == 9049:      # MEX
            self.mxdtopo = os.path.join(machine_path,eris_report_path,r"mxd","TopoMapLayoutCC.mxd")
            self.mxdbing = os.path.join(machine_path,eris_report_path,r"mxd","USBingMapLayoutCC.mxd")
            self.mxdMM = os.path.join(machine_path,eris_report_path,'mxd','MXLayoutMMCC.mxd')

class Oracle:
    # static variable: oracle_functions
    oracle_functions = {
    'getorderinfo':"eris_gis.getOrderInfo",
    'printtopo':"eris_gis.printTopo",
    'geterispointdetails':"eris_gis.getErisPointDetails"}

    oracle_procedures ={
    'xplorerflag':"eris_gis.getOrderXplorer"}

    def __init__(self,machine_name):
        # initiate connection credential
        if machine_name.lower() =='dev':
            self.oracle_credential = Credential.oracle_dev
        if machine_name.lower() =='test':
            self.oracle_credential = Credential.oracle_test
        elif machine_name.lower()=='prod':
            self.oracle_credential = Credential.oracle_production
        else:
            raise ValueError("Bad machine name")

    def connect_to_oracle(self):
        try:
            self.oracle_connection = cx_Oracle.connect(self.oracle_credential)
            self.cursor = self.oracle_connection.cursor()
        except cx_Oracle.Error as e:
            print(e,'Oracle connection failed, review credentials.')

    def close_connection(self):
        self.cursor.close()
        self.oracle_connection.close()

    def call_function(self,function_name,order_id):
        self.connect_to_oracle()
        cursor = self.cursor
        try:
            outType = cx_Oracle.CLOB
            func = [self.oracle_functions[_] for _ in self.oracle_functions.keys() if function_name.lower() ==_.lower()]
            if func != [] and len(func) == 1:
                try:
                    output=json.loads(cursor.callfunc(func[0],outType,((str(order_id)),)).read())
                except ValueError:
                    output = cursor.callfunc(func[0],outType,((str(order_id)),)).read()
                except AttributeError:
                    output = cursor.callfunc(func[0],outType,((str(order_id)),))
            return output
        except cx_Oracle.Error as e:
            raise Exception(("Oracle Failure",e.message))
        except Exception as e:
            raise Exception(("JSON Failure",e.message))
        except NameError as e:
            raise Exception("Bad Function")
        finally:
            self.close_connection()

    def call_procedure(self,procedure_name,order_id):
        self.connect_to_oracle()
        cursor = self.cursor
        try:
            outValue = 'Y'
            func = [self.oracle_procedures[_] for _ in self.oracle_procedures.keys() if procedure_name.lower() ==_.lower()]
            if func !=[] and len(func)==1:
                try:
                    output = cursor.callproc(func[0],[outValue,str(order_id),])
                except ValueError:
                    output = cursor.callproc(func[0],[outValue,str(order_id),])
                except AttributeError:
                    output = cursor.callproc(func[0],[outValue,str(order_id),])
            return output
        except cx_Oracle.Error as e:
            raise Exception(("Oracle Failure",e.message))
        except Exception as e:
            raise Exception(("JSON Failure",e.message))
        except NameError as e:
            raise Exception("Bad Function")
        finally:
            self.close_connection()

    def insert_overlay(self,delete_query,insert_query):
        self.connect_to_oracle()
        cursor = self.cursor
        try:
            cursor.execute(delete_query)
            cursor.execute("commit")
            cursor.execute(insert_query)
            cursor.execute("commit")
            return "Oracle successfully populated image overlay info"
        except cx_Oracle.Error as e:
            raise Exception(("Oracle Failure",e.message))
        except Exception as e:
            raise Exception(("JSON Failure",e.message))
        except NameError as e:
            raise Exception("Bad Function")
        finally:
            self.close_connection()

def createBuffers(orderBuffers,output_folder,buffer_name=r"buffer_%s.shp"):
    buffer_dict={}
    buffer_sizes_dict ={}
    for i in range(len(orderBuffers)):
        buffer_dict[i]=createGeometry(eval(orderBuffers[i].values()[0])[0],"polygon",output_folder,buffer_name%i)
        buffer_sizes_dict[i] =float(orderBuffers[i].keys()[0])
    print(buffer_dict,buffer_sizes_dict)
    return [buffer_dict,buffer_sizes_dict]

def createGeometry(pntCoords,geometry_type,output_folder,output_name, spatialRef = arcpy.SpatialReference(4269)):
    outputSHP = os.path.join(output_folder,output_name)
    if geometry_type.lower()== 'point':
        arcpy.CreateFeatureclass_management(output_folder, output_name, "MULTIPOINT", "", "DISABLED", "DISABLED", spatialRef)
        cursor = arcpy.da.InsertCursor(outputSHP, ['SHAPE@'])
        cursor.insertRow([arcpy.Multipoint(arcpy.Array([arcpy.Point(*coords) for coords in pntCoords]),spatialRef)])
    elif geometry_type.lower() =='polyline':
        arcpy.CreateFeatureclass_management(output_folder, output_name, "POLYLINE", "", "DISABLED", "DISABLED", spatialRef)
        cursor = arcpy.da.InsertCursor(outputSHP, ['SHAPE@'])
        cursor.insertRow([arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in pntCoords]),spatialRef)])
    elif geometry_type.lower() =='polygon':
        arcpy.CreateFeatureclass_management(output_folder,output_name, "POLYGON", "", "DISABLED", "DISABLED", spatialRef)
        cursor = arcpy.da.InsertCursor(outputSHP, ['SHAPE@'])
        cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in pntCoords]),spatialRef)])
    del cursor
    return outputSHP

def addERISpoint(pointInfo,mxd,output_folder,out_points=r'points.shp'):
    out_pointsSHP = os.path.join(output_folder,out_points)
    erisPointsLayer = config.LAYER.erisPoints
    #erisIDs_4points = dict((_.get('DATASOURCE_POINTS')[0].get('ERIS_DATA_ID'),[('m%sc'%(_.get("MAP_KEY_LOC"))) if _.get("MAP_KEY_NO_TOT")==1 else ('m%sc(%s)'%(_.get("MAP_KEY_LOC"), _.get("MAP_KEY_NO_TOT"))) ,float('%s'%(1 if round(_.get("ELEVATION_DIFF"),2)>0.0 else 0 if round(_.get("ELEVATION_DIFF"),2)==0.0 else -1 if round(_.get("ELEVATION_DIFF"),2)<0.0 else 100))]) for _ in pointInfo)
    erisIDs_4points = dict((_.get('DATASOURCE_POINTS')[0].get('ERIS_DATA_ID'),[('m%sc'%(_.get("MAP_KEY_LOC"))) if _.get("MAP_KEY_NO_TOT")==1 else ('m%sc(%s)'%(_.get("MAP_KEY_LOC"), _.get("MAP_KEY_NO_TOT"))) ,float('%s'%(-2 if _.get("ELEVATION_DIFF")=='-' else 1 if float(_.get("ELEVATION_DIFF"))>0.0 else 0 if float(_.get("ELEVATION_DIFF"))==0.0 else -1 if float(_.get("ELEVATION_DIFF"))<0.0 else 100))]) for _ in pointInfo)
    erispoints = dict((int(_.get('DATASOURCE_POINTS')[0].get('ERIS_DATA_ID')),(_.get("X"),_.get("Y"))) for _ in pointInfo)
    # print(erisIDs_4points)
    if erisIDs_4points != {}:
        arcpy.CreateFeatureclass_management(output_folder, out_points, "MULTIPOINT", "", "DISABLED", "DISABLED", arcpy.SpatialReference(4269))
        check_field = arcpy.ListFields(out_pointsSHP,"ERISID")
        if check_field==[]:
            arcpy.AddField_management(out_pointsSHP, "ERISID", "LONG", field_length='40')
        cursor = arcpy.da.InsertCursor(out_pointsSHP, ['SHAPE@','ERISID'])
        for point in erispoints.keys():
            cursor.insertRow([arcpy.Multipoint(arcpy.Array([arcpy.Point(*erispoints[point])]),arcpy.SpatialReference(4269)),point])
        del cursor
        check_field = arcpy.ListFields(out_pointsSHP,"mapkey")
        if check_field==[]:
            arcpy.AddField_management(out_pointsSHP, "mapkey", "TEXT", "", "", "20", "", "NULLABLE", "NON_REQUIRED", "")
        check_field = arcpy.ListFields(out_pointsSHP,"eleRank")
        if check_field==[]:
            arcpy.AddField_management(out_pointsSHP, "eleRank", "SHORT", "12", "6", "", "", "NULLABLE", "NON_REQUIRED", "")
        rows = arcpy.UpdateCursor(out_pointsSHP)
        for row in rows:
            row.mapkey = erisIDs_4points[int(row.ERISID)][0]
            row.eleRank = erisIDs_4points[int(row.ERISID)][1]
            rows.updateRow(row)
        del rows
        mxd.addLayer(erisPointsLayer,output_folder,out_points)
    return erisPointsLayer

def addRoadLayer(mxd,buffer_name, output_folder):
    road_clip = r"road_clip"
    arcpy.Clip_analysis(config.DATA.road, buffer_name, os.path.join(output_folder,road_clip), "0.3 Meters")
    mxd.addLayer(config.LAYER.road,output_folder,road_clip)

def addorder_geometry(mxd,geometry_type,output_folder,name):
    geometryLayer = eval('config.LAYER.%s'%(geometry_type.lower()))
    if arcpy.mapping.ListLayoutElements(mxd.mxd, "LEGEND_ELEMENT", "Legend") !=[]:
        legend = arcpy.mapping.ListLayoutElements(mxd.mxd, "LEGEND_ELEMENT", "Legend")[0]
        legend.autoAdd = True
        mxd.addLayer(geometryLayer,output_folder,name)
        legend.autoAdd = False
    else:
        mxd.addLayer(geometryLayer,output_folder,name)
    mxd.zoomToTopLayer()

def getMaps(mxd, output_folder,map_name,buffer_dict, buffer_sizes_list,unit_code,buffer_name=r"buffer_%s.shp", multi_page = False):
    temp = []
    if buffer_name.endswith(".shp"):
        buffer_name = buffer_name[:-4]
    bufferLayer = config.LAYER.buffer
    for i in buffer_dict.keys():
        if buffer_sizes_list[i]>=0.04:
            mxd.addLayer(bufferLayer,output_folder,"buffer_%s"%(i))
        if i in buffer_dict.keys()[-3:]:
            mxd.zoomToLayer("Grid") if i == buffer_dict.keys()[-1] and multi_page == True else mxd.zoomToTopLayer()
            mxd.df.scale = ((int(1.1*mxd.df.scale)/100)+1)*100
            unit = 'Kilometer' if unit_code ==9036 else 'Mile'
            mxd.addTextoMap("Map","Map: %s %s Radius"%(buffer_sizes_list[i],unit))
            arcpy.mapping.ExportToPDF(mxd.mxd,os.path.join(output_folder,map_name%(i)))
            temp.append(os.path.join(output_folder,map_name%(i)))
    if temp==[] and buffer_dict=={}:
        arcpy.mapping.ExportToPDF(mxd.mxd,os.path.join(output_folder,map_name%0))
        temp.append(os.path.join(output_folder,map_name%0))
    return temp

def exportMap(mxd,output_folder,map_name,UTMzone,buffer_dict,buffer_sizes_list,unit_code, buffer_name=r"buffer_%s.shp"):
    mxd.df.spatialReference = arcpy.SpatialReference('WGS 1984 UTM Zone %sN'%UTMzone)
    mxd.resolution =250
    temp = getMaps(mxd, output_folder,map_name, buffer_dict, buffer_sizes_list,unit_code, buffer_name=r"buffer_%s.shp", multi_page = False)
    mxd.mxd.saveACopy(os.path.join(output_folder,"mxd.mxd"))
    return temp

def exportmulti_page(mxd,output_folder,map_name,UTMzone,grid_size,erisPointLayer,buffer_dict,buffer_sizes_list,unit_code, buffer_name=r"buffer_%s.shp"):
    bufferLayer = config.LAYER.buffer
    gridlr = "gridlr"
    gridlrSHP = os.path.join(output_folder, gridlr+'.shp')

    arcpy.GridIndexFeatures_cartography(gridlrSHP, buffer_dict[buffer_dict.keys()[-1]], "", "", "", grid_size, grid_size)
    mxd.replaceLayerSource("Grid",output_folder,gridlr)
    arcpy.CalculateAdjacentFields_cartography(gridlrSHP, u'PageNumber')
    mxd.turnLabel(erisPointLayer,False)
    mxd.df.spatialReference = arcpy.SpatialReference('WGS 1984 UTM Zone %sN'%UTMzone)
    mxd.resolution =250
    temp = getMaps(mxd, output_folder,map_name, buffer_dict, buffer_sizes_list, unit_code, buffer_name=r"buffer_%s.shp", multi_page = True)
    mxd.turnLabel(erisPointLayer,True)
    mxd.addTextoMap("Map","Grid: ")
    mxd.addTextoMap("Grid",'<dyn type="page"  property="number"/>')
    ddMMDDP = mxd.mxd.dataDrivenPages
    ddMMDDP.refresh()
    ddMMDDP.exportToPDF(os.path.join(output_folder,map_name%("GRID")), "ALL",resolution=200,layers_attributes='LAYERS_ONLY',georef_info=False)
    mxd.mxd.saveACopy(os.path.join(output_folder,"mxdMM.mxd"))
    return [temp,os.path.join(output_folder,map_name%("GRID"))]

def exportTopo(mxd,output_folder,geometry_name,geometry_type, output_pdf,unit_code,bufferSHP,UTMzone):
    geometryLayer = eval('config.LAYER.%s'%geometry_type.lower())
    addorder_geometry(mxd,geometry_type,output_folder,geometry_name)
    mxd.df.spatialReference = arcpy.SpatialReference('WGS 1984 UTM Zone %sN'%UTMzone)
    topoYear = '2020'
    if unit_code == 9093:
        topoLayer = config.LAYER.topowhite    
        topolist = getCurrentTopo(config.DATA.data_topo,bufferSHP,output_folder)
        topoYear = getTopoQuadnYear(topolist)[1]
        mxd.addTextoMap("Year", "Year: %s"%topoYear)
        mxd.addTextoMap("Quadrangle","Quadrangle(s): %s"%getTopoQuadnYear(topolist)[0])
        for topo in topolist:
            mxd.addLayer(topoLayer,output_folder,topo.split('.')[0],"RASTER_WORKSPACE","BOTTOM")
    elif unit_code == 9049:
        mxd.addTextoMap("Logo", "\xa9 ERIS Information Inc.")
    mxd.toScale(24000) if mxd.df.scale<24000 else mxd.toScale(1.1*mxd.df.scale)
    mxd.resolution=300
    arcpy.mapping.ExportToPDF(mxd.mxd,output_pdf)
    if xplorerflag == 'Y' :
        df = arcpy.mapping.ListDataFrames(mxd.mxd,'')[0]
        mxd.df.spatialReference = arcpy.SpatialReference(3857)
        projectproperty = arcpy.mapping.ListLayers(mxd.mxd,"Project Property",df)[0]
        projectproperty.visible = False
        arcpy.mapping.ExportToJPEG(mxd.mxd,os.path.join(scratchviewer,topoYear+'_topo.jpg'), df, 3825, 4950, world_file = True, jpeg_quality = 85)
        exportViewerTable(os.path.join(scratchviewer,topoYear+'_topo.jpg'),topoYear+'_topo.jpg')
    mxd.mxd.saveACopy(os.path.join(output_folder,"maptopo.mxd"))

def getCurrentTopo(masterfile_topo,inputSHP,output_folder): # copy current topo images that intersect with input shapefile to output folder
    masterLayer_topo = arcpy.mapping.Layer(masterfile_topo)
    arcpy.SelectLayerByLocation_management(masterLayer_topo,'intersect',inputSHP)
    if(int((arcpy.GetCount_management(masterLayer_topo).getOutput(0))) ==0):
        return None
    else:
        cellids_selected = []
        infomatrix = []
        rows = arcpy.SearchCursor(masterLayer_topo) # loop through the relevant records, locate the selected cell IDs
        for row in rows:
            cellid = str(int(row.getValue("CELL_ID")))
            cellids_selected.append(cellid)
        del row
        del rows
        masterLayer_topo = None        
        
        for cellid in cellids_selected:
            try:
                exec("info =  topo_image_path.topo_%s"%(cellid))
                infomatrix.append(info)
                print(infomatrix)
            except  AttributeError as ae:
                print("AttributeError: No current topo available")
                print(ae)

                newmastertopo = r'\\cabcvan1gis006\GISData\Topo_USA\masterfile\Cell_PolygonAll.shp'                
                csvfile_h = r'\\cabcvan1gis006\GISData\Topo_USA\masterfile\All_HTMC_all_all_gda_results.csv'
                global tifdir_topo
                tifdir_topo = r'\\cabcvan1fpr009\USGS_Topo\USGS_HTMC_Geotiff'
                masterLayer = arcpy.mapping.Layer(newmastertopo)
                #arcpy.SelectLayerByLocation_management(masterLayer,'intersect', inputSHP, '0.25 KILOMETERS')  #it doesn't seem to work without the distance
                arcpy.SelectLayerByLocation_management(masterLayer,'INTERSECT', inputSHP)
                cellids_selected = []
                cellids = []
                infomatrix = []

                if(int((arcpy.GetCount_management(masterLayer).getOutput(0))) ==0):
                    print ("NO records selected")
                    masterLayer = None
                else:
                    # loop through the relevant records, locate the selected cell IDs
                    rows = arcpy.SearchCursor(masterLayer)    # loop through the selected records
                    for row in rows:
                        cellid = str(int(row.getValue("CELL_ID")))
                        cellids_selected.append(cellid)
                        cellsize = str(int(row.getValue("CELL_SIZE")))
                        cellids.append(cellid)
                        # cellsizes.append(cellsize)
                    del row
                    del rows
                    masterLayer = None
                    
                    with open(csvfile_h, "rb") as f:
                        reader = csv.reader(f)
                        for row in reader:
                            if row[9] in cellids:
                                # print "#2 " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                                pdfname = row[15].strip()
                                # read the year from .xml file
                                xmlname = pdfname[0:-3] + "xml"
                                xmlpath = os.path.join(tifdir_topo,xmlname)
                                tree = ET.parse(xmlpath)
                                root = tree.getroot()
                                procsteps = root.findall("./dataqual/lineage/procstep")
                                yeardict = {}
                                for procstep in procsteps:
                                    procdate = procstep.find("./procdate")
                                    if procdate != None:
                                        procdesc = procstep.find("./procdesc")
                                        yeardict[procdesc.text.lower()] = procdate.text

                                year2use = ""
                                yearcandidates = []
                                if "edit year" in yeardict.keys():
                                    yearcandidates.append(int(yeardict["edit year"]))

                                if "aerial photo year" in yeardict.keys():
                                    yearcandidates.append(int(yeardict["aerial photo year"]))

                                if "photo revision year" in yeardict.keys():
                                    yearcandidates.append(int(yeardict["photo revision year"]))

                                if "field check year" in yeardict.keys():
                                    yearcandidates.append(int(yeardict["field check year"]))

                                if "photo inspection year" in yeardict.keys():
                                    # print "photo inspection year is " + yeardict["photo inspection year"]
                                    yearcandidates.append(int(yeardict["photo inspection year"]))

                                if "date on map" in yeardict.keys():
                                    # print "date on  map " + yeardict["date on map"]
                                    yearcandidates.append(int(yeardict["date on map"]))

                                if len(yearcandidates) > 0:
                                    # print "***** length of yearcnadidates is " + str(len(yearcandidates))
                                    year2use = str(max(yearcandidates))
                                if year2use == "":
                                    print ("################### cannot determine the year of the map!!")
                                
                                # ONLY GET 7.5 OR 15 MINUTE MAP SERIES
                                if row[5] == "7.5X7.5 GRID" or row[5] == "15X15 GRID":
                                    infomatrix.append([row[15],year2use])  # [64818, 15X15 GRID,  LA_Zachary_335142_1963_62500_geo.pdf,  1963]
                    # print(infomatrix)
                    # GET MAX YEAR ONLY
                    infomatrix = [item for item in infomatrix if item[1] == max(item[1] for item in infomatrix)]             
        _=[]
        for item in infomatrix:
            tifname = item[0][0:-4]   # note without .tif part
            topofile = os.path.join(tifdir_topo,tifname+"_t.tif")
            year = item[1]

            if os.path.exists(topofile):
                if '.' in tifname:
                    tifname = tifname.replace('.','')
                temp = tifname.split('_')
                temp.insert(-2,item[1])
                newtopo = '_'.join(temp)+'.tif'
                shutil.copyfile(topofile,os.path.join(output_folder,newtopo))
                _.append(newtopo)
        return _
        
def getTopoYear(name):
    for year in range(1900,2030):
        if str(year) in name:
            return str(year)
    return None

def getTopoQuadnYear(topo_filelist):
    quadrangles=set()
    year=set()
    for topo in topo_filelist:
        name = topo.split("_")
        z = 0
        for i in range(len(name)):
            year_value = getTopoYear(name[i])
            if year_value:
                if z == 0:
                    quadrangles.add('%s, %s'%(' '.join([name[j] for j in range(1,i)]), name[0]))
                year.add(year_value)
                z = z + 1
    # GET MAX YEAR FROM FILE NAME
    year = [y for y in year if y == max(y for y in year)]
    return ('; '.join(quadrangles),'; '.join(year))

def exportAerial(mxd,output_folder,geometry_name,geometry_type,centroid,scale,output_pdf,UTMzone):
    geometryLayer = eval('config.LAYER.%s'%geometry_type.lower())
    addorder_geometry(mxd,geometry_type,output_folder,geometry_name)
    aerialYear = getWorldAerialYear(centroid)
    mxd.addTextoMap("Year","Year: %s"%aerialYear)
    mxd.df.spatialReference = arcpy.SpatialReference('WGS 1984 UTM Zone %sN'%UTMzone)
    mxd.toScale(10000) if mxd.df.scale<10000 else mxd.toScale(1.1*mxd.df.scale)
    mxd.resolution=200
    arcpy.mapping.ExportToPDF(mxd.mxd,output_pdf)

    if xplorerflag == 'Y' :
        df = arcpy.mapping.ListDataFrames(mxd.mxd,'')[0]
        mxd.df.spatialReference = arcpy.SpatialReference(3857)
        projectproperty = arcpy.mapping.ListLayers(mxd.mxd,"Project Property",df)[0]
        projectproperty.visible = False
        arcpy.mapping.ExportToJPEG(mxd.mxd,os.path.join(scratchviewer,aerialYear+'_aerial.jpg'), df, 3825, 4950, world_file = True, jpeg_quality = 85)
        exportViewerTable(os.path.join(scratchviewer,aerialYear+'_aerial.jpg'),aerialYear+'_aerial.jpg')
    mxd.mxd.saveACopy(os.path.join(output_folder,"mapbing.mxd"))

def getWorldAerialYear((centroid_X,centroid_Y)):
    fsURL = r"https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/0/query?f=json&returnGeometry=false&spatialRel=esriSpatialRelIntersects&maxAllowableOffset=0&geometryType=esriGeometryPoint&inSR=4326&outFields=SRC_DATE"
    params = urllib.urlencode({'geometry':{'x':float(centroid_X),'y':float(centroid_Y)}})
    resultBing = urllib.urlopen(fsURL,params).read()

    if "error" not in resultBing:
        for year in list(reversed(range(1900,2020))):
            if str(year) in resultBing :
                return str(year)
    else:
        tries = 5
        key = False
        while tries >= 0:
            if "error" not in resultBing:
                for year in list(reversed(range(1900,2020))):
                    if str(year) in resultBing:
                        return str(year)
            elif tries == 0:
                    return ""
            else:
                time.sleep(5)
                tries -= 1

def exportViewerTable(ImagePath,FileName):
    srGoogle = arcpy.SpatialReference(3857)
    srWGS84 = arcpy.SpatialReference(4326)
    metaitem = {}
    arcpy.DefineProjection_management(ImagePath,srGoogle)
    desc = arcpy.Describe(ImagePath)
    featbound = arcpy.Polygon(arcpy.Array([desc.extent.lowerLeft, desc.extent.lowerRight, desc.extent.upperRight, desc.extent.upperLeft]),srGoogle)
    del desc

    tempfeat = os.path.join(scratch, "imgbnd_"+FileName[:-4]+ ".shp")
    arcpy.Project_management(featbound, tempfeat, srWGS84)
    desc = arcpy.Describe(tempfeat)
    metaitem['type'] = 'cur'+ str(FileName.split('_')[1]).split('.')[0]
    metaitem['imagename'] = FileName
    metaitem['lat_sw'] = desc.extent.YMin
    metaitem['long_sw'] = desc.extent.XMin
    metaitem['lat_ne'] = desc.extent.YMax
    metaitem['long_ne'] = desc.extent.XMax

    delete_query = "delete from overlay_image_info where order_id = '%s' and type = '%s' and filename = '%s'"%(order_id,metaitem['type'],FileName)
    insert_query = "insert into overlay_image_info values (%s, %s, %s, %.5f, %.5f, %.5f, %.5f, %s, '', '')" % (str(order_id), orderInfo['ORDER_NUM'], "'" + metaitem['type']+"'", metaitem['lat_sw'], metaitem['long_sw'], metaitem['lat_ne'], metaitem['long_ne'],"'"+metaitem['imagename']+"'" )
    image_info = Oracle('test').insert_overlay(delete_query,insert_query)
    
def export_to_kml(order_number,mxd_doc):
    viewer_kml_path = os.path.join(scratch,order_number +'_eris_kml')
    if not os.path.exists(viewer_kml_path):
        os.mkdir(viewer_kml_path)
    eris_polygon_clip = os.path.join(scratch, "eris_polygon_clip.shp")
    df = arcpy.mapping.ListDataFrames(mxd_doc.mxd,'')[0]    # the spatial reference here is UTM zone #, need to change to WGS84 Web Mercator
    df.spatialReference = srWGS84
    #re-focus using Buffer layer for multipage
    if multi_page:
        buffer_layer = arcpy.mapping.ListLayers(mxd_doc.mxd, "Buffer", df)[0]
        df.extent = buffer_layer.getSelectedExtent(False)
        df.scale = df.scale * 1.1
    df_as_feature = arcpy.Polygon(arcpy.Array([df.extent.lowerLeft, df.extent.lowerRight, df.extent.upperRight, df.extent.upperLeft]), df.spatialReference)
    del df, mxd_doc
    eris_kml_extend = os.path.join(scratch,"eris_kml_extend.shp")
    arcpy.Project_management(df_as_feature, eris_kml_extend, srWGS84)
    arcpy.Clip_analysis(config.LAYER.eris_polygon, eris_kml_extend, eris_polygon_clip)
    del df_as_feature
    
    if int(arcpy.GetCount_management(eris_polygon_clip).getOutput(0)) > 0:
        keep_field_list = ("source")
        field_info = ""
        field_list = arcpy.ListFields(eris_polygon_clip)
        for field in field_list:
            if field.name.lower() in keep_field_list:
                if field.name.lower() == 'source':
                    field_info = field_info + field.name + " " + "Wetland CLASS" + " VISIBLE;"
                else:
                    pass
            else:
                field_info = field_info + field.name + " " + field.name + " HIDDEN;"
        arcpy.MakeFeatureLayer_management(eris_polygon_clip, 'eris_polygon_clip_lyr',"", "", field_info[:-1])
        arcpy.ApplySymbologyFromLayer_management('eris_polygon_clip_lyr', config.LAYER.eris_polygon)
        arcpy.LayerToKML_conversion('eris_polygon_clip_lyr', os.path.join(viewer_kml_path,"eris_polygon.kmz"))
        arcpy.AddMessage('      -- Create ERIS polygon kmz map: %s' % os.path.join(viewer_kml_path,"eris_polygon.kmz"))
        
        ### copy kml to 006
        if os.path.exists(os.path.join(viewer_path, order_number + '_eris_kml')):
                shutil.rmtree(os.path.join(viewer_path, order_number + '_eris_kml'))
        shutil.copytree(viewer_kml_path, os.path.join(viewer_path, order_number + '_eris_kml'))
        arcpy.Delete_management('eris_polygon_clip_lyr')
    
if __name__ == '__main__':
    try:
        # INPUT #####################################
        order_id = '1079998'#arcpy.GetParameterAsText(0).strip()#'736799'#
        
        multi_page = False#True if (arcpy.GetParameterAsText(1).lower()=='yes' or arcpy.GetParameterAsText(1).lower()=='y') else False
        grid_size = '0'#arcpy.GetParameterAsText(2).strip()#0#
        code = 'usa'#arcpy.GetParameterAsText(3).strip()#'usa'#
        is_instant = False#True if arcpy.GetParameterAsText(4).strip().lower()=='yes'else False
        scratch = arcpy.env.scratchFolder
        env = 'test'
        ##get info for order from oracle
        order_info = Oracle(env).call_function('getorderinfo',str(order_id))
        order_num = str(order_info['ORDER_NUM'])
        srGoogle = arcpy.SpatialReference(3857)
        srWGS84 = arcpy.SpatialReference(4326)
        # Server Setting ############################
        code = 9093 if code.strip().lower()=='usa' else 9036 if code.strip().lower()=='can' else 9049 if code.strip().lower()=='mex' else ValueError
        config = DevConfig(code)

        # PARAMETERS ################################
        order_geometry = r'order_geometry.shp'
        order_geometry_shp = os.path.join(scratch,order_geometry)
        map_name = 'map_%s.pdf'
        map_mm_name = 'map_mm_%s.pdf'
        buffer_max = ''
        buffer_name = "buffer_%s.shp"
        map_mm = os.path.join(scratch,map_mm_name)
        aerial_pdf = os.path.join(scratch,'mapbing.pdf')
        topo_pdf = os.path.join(scratch,"maptopo.pdf")
        pdf_report = os.path.join(scratch,map_name)
        grid_unit = 'Kilometers' if code == 9036 and float(grid_size.strip())<100 else 'Meters' if code ==9036 else 'Miles'
        grid_size = '%s %s'%(grid_size,grid_unit)
        viewer_path = server_config['viewer']
        currentuploadurl = server_config['viewer_upload']+r"/ErisInt/BIPublisherPortal_test/Viewer.svc/CurImageUpload?ordernumber="
        
        # STEPS ####################################
        # 1  get order info by Oracle call
        orderInfo= Oracle(env).call_function('getorderinfo',order_id)
        needTopo= Oracle(env).call_function('printTopo',order_id)
        xplorerflag= Oracle(env).call_procedure('xplorerflag',order_id)[0]
        end = timeit.default_timer()
        arcpy.AddMessage(('call oracle', round(end -start1,4)))
        start=end
        
        # 2 create xplorer directory
        if xplorerflag == 'Y':
            scratchviewer = os.path.join(scratch,orderInfo['ORDER_NUM']+'_current')
            os.mkdir(scratchviewer)

        # 2 create order geometry
        order_geometry_shp = createGeometry(eval(orderInfo[u'ORDER_GEOMETRY'][u'GEOMETRY'])[0],orderInfo[u'ORDER_GEOMETRY'][u'GEOMETRY_TYPE'],scratch,order_geometry)
        end = timeit.default_timer()
        arcpy.AddMessage(('create geometry shp', round(end -start,4)))
        start=end

        # 3 create buffers
        [buffers, buffer_sizes] = createBuffers(orderInfo['BUFFER_GEOMETRY'],scratch,buffer_name)
        end = timeit.default_timer()
        arcpy.AddMessage(('create buffer shps', round(end -start,4)))
        start=end

        # 4 Maps
        # 4-0 initial Map
        map1 = Map(config.MXD.mxdMM)
        end = timeit.default_timer()
        arcpy.AddMessage(('4-0 initiate object Map', round(end -start,4)))
        start=end

        if code == 9093:
            # 3.1 MAx Buffer
            buffer_max = os.path.join(scratch,buffer_name%(len(orderInfo['BUFFER_GEOMETRY'])+1))
            max_buffer = max([float(_.keys()[0]) for _ in orderInfo['BUFFER_GEOMETRY']]) if orderInfo['BUFFER_GEOMETRY'] !=[] else 0#
            max_buffer ="%s MILE"%(2*max_buffer if max_buffer>0.2 else 2)
            # print(orderInfo['BUFFER_GEOMETRY'])
            arcpy.Buffer_analysis(order_geometry_shp,buffer_max,max_buffer)
            end = timeit.default_timer()
            arcpy.AddMessage(('create max buffer', round(end -start,4)))
            start=end
            # 4-1 add Road US
            addRoadLayer(map1, buffer_max,scratch)
            end = timeit.default_timer()
            arcpy.AddMessage(('4-1 clip and add road', round(end -start,4)))
            start=end

        # 4-2 add ERIS points
        #erisPointsInfo = Oracle(env).call_function('geterispointdetails',order_id)
        erisPointsInfo = [{
	"ORDER_ID": 1048712,
	"X": -104.95032994,
	"Y": 39.79467523,
	"GEOMETRY_TYPE": "POLYGON",
	"GEOMETRY": "[[[-104.949125378433,39.7954268940368],[-104.949196745033,39.7954283482406],[-104.949217963638,39.7954342846654],[-104.949267919179,39.7954353008993],[-104.949324821982,39.7954419666743],[-104.949360313727,39.7954481935802],[-104.949395614815,39.7954599225383],[-104.94943110656,39.7954661494442],[-104.949473351313,39.7954835243461],[-104.949522924643,39.7954955428859],[-104.949579443436,39.7955132082689],[-104.949635963129,39.7955308736518],[-104.949685344902,39.7955483951432],[-104.949727972767,39.7955547677392],[-104.949770409976,39.7955666414882],[-104.94981265473,39.7955840154908],[-104.949869173523,39.7956016817731],[-104.949918556196,39.7956192032645],[-104.94997507409,39.7956368677482],[-104.950031594682,39.7956545340304],[-104.950081167112,39.7956665534696],[-104.95014463047,39.7956898647963],[-104.950222559423,39.7957079672498],[-104.950299911911,39.7957425722628],[-104.950363567724,39.7957603824366],[-104.950405812478,39.7957777573386],[-104.950462139715,39.7958009238744],[-104.950518466953,39.7958240904103],[-104.950567849626,39.7958416110025],[-104.950610287734,39.7958534847514],[-104.950645585225,39.7958652137095],[-104.950680885414,39.7958769417684],[-104.950715994947,39.7958941718794],[-104.950758432155,39.7959060456284],[-104.950800676909,39.7959234214297],[-104.950864142066,39.7959467327564],[-104.950927605424,39.7959700440832],[-104.950969658622,39.7959929210374],[-104.951026178315,39.7960105864203],[-104.951047203565,39.7960220239981],[-104.951082505553,39.7960337538556],[-104.951117806641,39.7960454801157],[-104.951173941424,39.7960741487039],[-104.951230075307,39.7961028163928],[-104.95127945798,39.7961203369849],[-104.951342922237,39.7961436492109],[-104.951392113355,39.796166670956],[-104.951441494229,39.7961841906488],[-104.951504957587,39.7962075028748],[-104.951547011685,39.7962303789297],[-104.951596202802,39.7962534006748],[-104.951659283049,39.7962877143075],[-104.951708282611,39.7963162372055],[-104.951764225838,39.7963504042486],[-104.9518132245,39.796378928046],[-104.951876113191,39.7964187419323],[-104.951939002782,39.7964585576173],[-104.952001892373,39.7964983724029],[-104.952043370904,39.7965377510173],[-104.952078287982,39.7965604822813],[-104.952106068939,39.7965830687545],[-104.952140793562,39.7966112984735],[-104.952182465448,39.7966451768343],[-104.952217190071,39.7966734074527],[-104.952251532482,39.7967126421756],[-104.952286065549,39.7967463748462],[-104.952299571567,39.7967686699391],[-104.952326969414,39.7968022560202],[-104.952354174805,39.7968413450529],[-104.952374627187,39.7968692851903],[-104.952394887114,39.7969027264805],[-104.952408394032,39.7969250215734],[-104.952422093404,39.7969418155133],[-104.952435600322,39.7969641097068],[-104.95244197022,39.7969862591095],[-104.952470708955,39.7969813398179],[-104.952500022358,39.7969599170674],[-104.952529143305,39.7969439954699],[-104.952565400372,39.7969282186633],[-104.952601658339,39.7969124418566],[-104.952637918105,39.7968966659492],[-104.952673984516,39.7968863902956],[-104.952710243382,39.7968706143882],[-104.952746309794,39.7968603396339],[-104.95278256866,39.7968445637266],[-104.952818826627,39.7968287869199],[-104.952862411371,39.7968076546504],[-104.952898669338,39.7967918778438],[-104.952927792083,39.7967759562463],[-104.95296405005,39.7967601812383],[-104.952993170997,39.7967442587415],[-104.953036758439,39.7967231273713],[-104.953066262497,39.7966962025686],[-104.953102521364,39.7966804266613],[-104.953138970886,39.7966591487017],[-104.95316828249,39.7966377268505],[-104.953197405235,39.7966218043537],[-104.953226527082,39.7966058836555],[-104.953248511909,39.7965898163678],[-104.953270304281,39.7965792511324],[-104.953292290007,39.7965631829454],[-104.953314274833,39.7965471174564],[-104.95334378069,39.796520193553],[-104.953365764618,39.7965041262653],[-104.953387941899,39.7964825569254],[-104.953410116483,39.7964609893841],[-104.953439620541,39.7964340654806],[-104.953454470147,39.7964178543014],[-104.953469317954,39.7964016404243],[-104.953491495236,39.796380072883],[-104.95352119085,39.7963476487259],[-104.953557831928,39.7963208696133],[-104.953572681533,39.7963046584342],[-104.953587528441,39.7962884454563],[-104.953602377147,39.7962722333777],[-104.953632073661,39.7962398083214],[-104.953654249144,39.7962182407801],[-104.953669096951,39.7962020278022],[-104.953683945657,39.7961858157237],[-104.953705930484,39.7961697475367],[-104.953728297522,39.7961426788424],[-104.953750857016,39.7961101098946],[-104.953772841843,39.7960940417075],[-104.9538023468,39.7960671187035],[-104.953824524082,39.7960455502628],[-104.953861355816,39.7960132726953],[-104.95389857336,39.7959699901239],[-104.953935406893,39.7959377098583],[-104.953980333425,39.7958780713168],[-104.95401754917,39.7958347896447],[-104.954061711278,39.7957971548157],[-104.954105489376,39.7957705213934],[-104.954149267474,39.7957438897696],[-104.954192853117,39.7957227575002],[-104.954244150447,39.795685267462],[-104.95429564113,39.7956422762709],[-104.95434693756,39.7956047862328],[-104.954383770194,39.7955725068666],[-104.954427739848,39.7955403722913],[-104.954471519744,39.7955137397682],[-104.954515679155,39.7954761040399],[-104.954574305959,39.7954332603376],[-104.954611138593,39.7954009800721],[-104.954662435922,39.7953634900339],[-104.954691367112,39.7953530686901],[-104.954727816635,39.7953317916298],[-104.954764073702,39.7953160157224],[-104.95479357866,39.795289091819],[-104.954830220638,39.7952623136058],[-104.95485953314,39.7952408908553],[-104.954895983562,39.7952196155937],[-104.954925105409,39.7952036930969],[-104.954954417911,39.7951822703464],[-104.955005141474,39.7951612828678],[-104.955041398541,39.7951455069605],[-104.955078040519,39.7951187278479],[-104.955114298485,39.7951029528399],[-104.955143421231,39.7950870303431],[-104.955165213603,39.7950764651077],[-104.955194527005,39.7950550414579],[-104.955216511832,39.7950389750695],[-104.955217660266,39.7950059690511],[-104.955218427388,39.7949839644393],[-104.955205112026,39.7949561681935],[-104.955198741228,39.7949340205895],[-104.955185042755,39.7949172266496],[-104.955164591272,39.794889285613],[-104.955143948234,39.7948668448299],[-104.955116357933,39.7948387590024],[-104.955088577875,39.7948161734286],[-104.955053659898,39.7947934430638],[-104.955018553063,39.7947762129527],[-104.95499058145,39.7947591285318],[-104.954962417381,39.7947475461633],[-104.954941197877,39.7947416079398],[-104.954905897688,39.7947298798809],[-104.954870405944,39.7947236520758],[-104.95482777718,39.7947172785804],[-104.954785148415,39.7947109068837],[-104.954749658469,39.7947046781792],[-104.95472111129,39.7947040963179],[-104.95469256411,39.7947035153559],[-104.954628142075,39.7947077088946],[-104.954585130199,39.7947123377051],[-104.954549255343,39.7947171113066],[-104.954520709063,39.7947165312438],[-104.954492160085,39.7947159493825],[-104.954470944178,39.7947100129576],[-104.950329944771,39.7946752316775],[-104.950293685904,39.7946910084842],[-104.950278837198,39.7947072205627],[-104.95024971715,39.7947231430595],[-104.950220786859,39.7947335626047],[-104.950198993588,39.7947441287395],[-104.950141133906,39.7947649705279],[-104.950061482751,39.7947963775517],[-104.949982020453,39.7948222852212],[-104.949945760688,39.7948380611285],[-104.949902175045,39.7948591933979],[-104.949851259927,39.7948856811302],[-104.949771224762,39.7949280913592],[-104.949705653393,39.794965290017],[-104.94964027268,39.7949969866226],[-104.949581838331,39.7950343318698],[-104.949523595537,39.7950661759642],[-104.949464969632,39.7951090214651],[-104.949421192433,39.7951356539882],[-104.94936970085,39.7951786451792],[-104.949332869116,39.7952109236461],[-104.949303363259,39.7952378466502],[-104.949266722181,39.7952646248634],[-104.949244355142,39.7952916935577],[-104.949214850185,39.7953186165618],[-104.949200002378,39.7953348295396],[-104.94917763444,39.7953618991332],[-104.949162595077,39.7953836123647],[-104.949132897664,39.7954160383204],[-104.949125378433,39.7954268940368]]]",
	"BUFFER_RADIUS": 0.125,
	"MAP_KEY_LOC": "1",
	"MAP_KEY_NO_TOT": 1,
	"DISTANCE": 89.289253737034,
	"DIRECTION": "NNW",
	"ELEVATION": "-",
	"ELEVATION_DIFF": "-",
	"DATASOURCE_POINTS": [{
		"MAP_KEY_NO": 1,
		"ERIS_DATA_ID": 879394862
	}]
}, {
	"ORDER_ID": 1048712,
	"X": -104.94987526,
	"Y": 39.79310878,
	"GEOMETRY_TYPE": "POINT",
	"GEOMETRY": "[[[-104.94987526,39.79310878]]]",
	"BUFFER_RADIUS": 0.125,
	"MAP_KEY_LOC": "2",
	"MAP_KEY_NO_TOT": 2,
	"DISTANCE": 93.820981529248,
	"DIRECTION": "S",
	"ELEVATION": 1575.7784,
	"ELEVATION_DIFF": 0.4684,
	"DATASOURCE_POINTS": [{
		"MAP_KEY_NO": 1,
		"ERIS_DATA_ID": 816559164
	}, {
		"MAP_KEY_NO": 2,
		"ERIS_DATA_ID": 828449552
	}]
}, {
	"ORDER_ID": 1048712,
	"X": -104.94905962,
	"Y": 39.79464936,
	"GEOMETRY_TYPE": "POLYGON",
	"GEOMETRY": "[[[-104.945044778393,39.7946832104627],[-104.945030311899,39.7946884211347],[-104.945008136416,39.7947099895753],[-104.944993287709,39.7947262016538],[-104.944963782752,39.7947531255572],[-104.944948359379,39.7947858410946],[-104.944918280653,39.7948292684569],[-104.944888201029,39.7948726949198],[-104.944864683758,39.7949327696325],[-104.944841549597,39.7949818429386],[-104.944826318679,39.7950090564237],[-104.944810511295,39.7950527751664],[-104.944801459619,39.7951076392071],[-104.944792982609,39.7951460015876],[-104.944784503801,39.7951843621695],[-104.944775642781,39.7952337241579],[-104.944766399549,39.7952940911503],[-104.944757729185,39.7953379537844],[-104.944749059721,39.7953818164186],[-104.94473981469,39.795442183411],[-104.944737132912,39.795519195955],[-104.944727314114,39.7955960646076],[-104.944718069982,39.7956564307006],[-104.944723482102,39.7957060849687],[-104.944729278233,39.7957447387296],[-104.944741634918,39.7958000380422],[-104.944754568068,39.7958388356946],[-104.944767307864,39.7958831336006],[-104.944772720884,39.7959327887681],[-104.944778133004,39.7959824439355],[-104.94477698457,39.7960154490546],[-104.944782588245,39.7960596021698],[-104.944781054901,39.7961036104941],[-104.944786275466,39.7961587659152],[-104.944784742122,39.7962027742395],[-104.944789580474,39.7962689310672],[-104.944794801039,39.7963240864883],[-104.944800405614,39.7963682396035],[-104.944806199946,39.7964068915657],[-104.944811230753,39.7964675490391],[-104.944809697409,39.7965115573634],[-104.944814535762,39.7965777141911],[-104.944812427751,39.7966382250749],[-104.944811277518,39.7966712310933],[-104.944809361962,39.7967262408243],[-104.944807829517,39.7967702482492],[-104.944806296173,39.7968142565736],[-104.944797819163,39.7968526180548],[-104.944788766588,39.7969074829949],[-104.944780670891,39.7969348430694],[-104.944758302953,39.7969619117637],[-104.944721661875,39.796988689977],[-104.944692540028,39.7970046115745],[-104.944670746757,39.7970151777092],[-104.94462735267,39.7970308079263],[-104.944598613934,39.7970357281172],[-104.944548465938,39.797040212137],[-104.944505454063,39.7970448409475],[-104.944462633743,39.7970439695045],[-104.944426949543,39.797043241953],[-104.944391267143,39.7970425162001],[-104.944355391388,39.7970472898015],[-104.944326844208,39.7970467088394],[-104.944305244291,39.7970517738212],[-104.944283833232,39.7970513385494],[-104.944240629801,39.7970614685129],[-104.944190290249,39.7970714527862],[-104.944132813678,39.7970812922687],[-104.944068201885,39.7970909860611],[-104.944003397638,39.7971061810064],[-104.943924318452,39.7971210863699],[-104.94385218473,39.7971416376773],[-104.943758642647,39.7971617501155],[-104.943686699581,39.79717680027],[-104.943629032353,39.7971921409055],[-104.943578499448,39.7972076263318],[-104.943521022876,39.7972174658143],[-104.943492093485,39.7972278871582],[-104.943448699397,39.7972435182746],[-104.943419769106,39.7972539387192],[-104.943398167391,39.797259003701],[-104.94336210098,39.797269280254],[-104.943325842113,39.797285055262],[-104.943303857287,39.797301123449],[-104.94328187246,39.797317188938],[-104.943266833097,39.7973389030688],[-104.94325160128,39.7973661183526],[-104.943235794795,39.7974098352965],[-104.943226358209,39.7974757007439],[-104.943231197461,39.7975418593702],[-104.943236991793,39.7975805113325],[-104.943243362591,39.7976026607351],[-104.943263622518,39.7976361020254],[-104.943290445697,39.797686193364],[-104.943317268876,39.7977362829041],[-104.943351035721,39.7977920201865],[-104.943384995021,39.7978422554166],[-104.943419528987,39.7978759880873],[-104.943446925934,39.7979095750678],[-104.943474515336,39.7979376626939],[-104.943502103838,39.7979657485214],[-104.943536828461,39.7979939791397],[-104.943571553983,39.7980222106574],[-104.943599334941,39.7980447971306],[-104.943634252019,39.798067526596],[-104.943676306116,39.7980904035502],[-104.943711607204,39.798102131609],[-104.943760988079,39.7981196531004],[-104.943789151248,39.7981312363684],[-104.943824643892,39.7981374632742],[-104.9438670811,39.7981493379225],[-104.94390951741,39.7981612125708],[-104.943959091638,39.7981732311106],[-104.944015417977,39.7981963976466],[-104.94407193677,39.7982140630295],[-104.944149865723,39.7982321645836],[-104.944220848313,39.7982446201939],[-104.944277750217,39.798251283271],[-104.944320378982,39.798257655867],[-104.944370143866,39.7982641741532],[-104.944412771731,39.7982705467492],[-104.94445520894,39.7982824213975],[-104.944497836805,39.7982887939935],[-104.944533329449,39.7982950217987],[-104.944583287688,39.7982960389319],[-104.94465465249,39.7982974931357],[-104.944704418274,39.7983040096232],[-104.944740293129,39.7982992360218],[-104.944783114349,39.7983001074649],[-104.944847344828,39.7983014159785],[-104.94491157351,39.7983027235927],[-104.94497580399,39.7983040321063],[-104.945032898349,39.7983051940304],[-104.945082663234,39.7983117114172],[-104.945125483554,39.7983125837596],[-104.94516849363,39.7983079549491],[-104.945232915666,39.7983037614104],[-104.945297530156,39.7982940685174],[-104.945340541132,39.7982894397068],[-104.945390690028,39.7982849565864],[-104.94543389256,39.7982748266228],[-104.945476903536,39.7982701969129],[-104.945505834726,39.7982597764684],[-104.945548846601,39.7982551467585],[-104.945577775993,39.7982447272133],[-104.945613843304,39.7982344524589],[-104.94567151233,39.7982191118235],[-104.945700440822,39.7982086913789],[-104.945736315678,39.7982039159788],[-104.945757916494,39.7981988509971],[-104.945793793148,39.7981940764963],[-104.945843942044,39.7981895933759],[-104.94589408914,39.7981851093562],[-104.945937102814,39.7981804805456],[-104.945980112891,39.7981758508358],[-104.946016179303,39.7981655751821],[-104.946073464318,39.7981612368525],[-104.946109531629,39.7981509620981],[-104.946152543504,39.7981463332875],[-104.946188609916,39.7981360585332],[-104.946231812448,39.7981259276704],[-104.946260550284,39.7981210083788],[-104.946289289019,39.7981160881878],[-104.946318601522,39.7980946663367],[-104.946347722469,39.7980787438399],[-104.946383981335,39.7980629670332],[-104.946434513342,39.7980474816069],[-104.946470771308,39.7980317048002],[-104.946499701599,39.7980212843557],[-104.946535768011,39.798011008702],[-104.946557560382,39.7980004425673],[-104.94660095447,39.7979848123501],[-104.946665952071,39.7979641162519],[-104.946724004209,39.7979377742098],[-104.946760454631,39.7979164971495],[-104.946811559505,39.7978845082644],[-104.946862667078,39.7978525193791],[-104.946906828287,39.7978148836509],[-104.946950797041,39.7977827499748],[-104.94700923229,39.7977454056269],[-104.947053584155,39.7977022687456],[-104.947104882384,39.7976647796068],[-104.947149235148,39.7976216436248],[-104.947186450893,39.7975783619527],[-104.947223859093,39.797529580027],[-104.947261268192,39.7974807963026],[-104.94730638628,39.7974156575075],[-104.94733665746,39.7973667289922],[-104.94736654463,39.7973288045816],[-104.947381968003,39.7972960890442],[-104.947404719052,39.7972580171447],[-104.947427470101,39.7972199461445],[-104.947450029595,39.797187375398],[-104.947473164654,39.7971383038905],[-104.947503434935,39.7970893753753],[-104.947519049864,39.7970511595843],[-104.947526953106,39.7970293006626],[-104.94753562257,39.7969854380285],[-104.947544100479,39.7969470756479],[-104.947552578388,39.796908715066],[-104.947575713448,39.7968596426593],[-104.947598847608,39.7968105693532],[-104.947636445565,39.7967562853752],[-104.947666332734,39.7967183600651],[-104.947704124945,39.7966585749342],[-104.947748860821,39.7966044366464],[-104.947801116827,39.7965394435414],[-104.947838525027,39.796490659817],[-104.947883069348,39.7964420235814],[-104.947905436386,39.7964149539878],[-104.947934749788,39.796393530338],[-104.947956926171,39.7963719636961],[-104.947971774877,39.7963557507182],[-104.948001088279,39.7963343288671],[-104.948015935187,39.7963181167885],[-104.948038304024,39.796291047195],[-104.948060480406,39.7962694796537],[-104.948075519769,39.7962477655229],[-104.948090751586,39.7962205511384],[-104.948105790949,39.796198837907],[-104.948135870573,39.7961554123433],[-104.948203549054,39.7960577001037],[-104.948271610646,39.7959489900547],[-104.948345851479,39.7958679278635],[-104.948397915031,39.7958084323142],[-104.948435132575,39.79576515334],[-104.948472154965,39.7957273719216],[-104.948516508629,39.7956842359396],[-104.94855391593,39.7956354531146],[-104.948598270493,39.7955923171326],[-104.948628539875,39.7955433895167],[-104.948650716257,39.7955218219754],[-104.948665564963,39.7955056080982],[-104.948680796781,39.7954783955124],[-104.94870354783,39.7954403236129],[-104.948718586293,39.7954186103815],[-104.948733434999,39.7954023983029],[-104.948748283706,39.7953861862244],[-104.948763323068,39.7953644720936],[-104.948785691006,39.7953374025],[-104.948822906751,39.7952941217272],[-104.948852987275,39.7952506943649],[-104.948890012364,39.7952129156445],[-104.948934172673,39.7951752817148],[-104.948971388418,39.7951319991433],[-104.948993756356,39.7951049304491],[-104.949008987274,39.7950777160647],[-104.949039641566,39.7950177861428],[-104.949055255595,39.7949795685532],[-104.949063734403,39.7949412088706],[-104.949064883737,39.7949082019529],[-104.949072978535,39.7948808436769],[-104.949074127868,39.7948478358599],[-104.949075085646,39.7948203318937],[-104.949076235879,39.794787324976],[-104.949077002101,39.7947653212635],[-104.94907082286,39.7947376707078],[-104.949064836073,39.7947045198986],[-104.949065985406,39.7946715120815],[-104.949059615508,39.7946493644775],[-104.945044778393,39.7946832104627]]]",
	"BUFFER_RADIUS": 0.125,
	"MAP_KEY_LOC": "3",
	"MAP_KEY_NO_TOT": 1,
	"DISTANCE": 103.632374135351,
	"DIRECTION": "NE",
	"ELEVATION": "-",
	"ELEVATION_DIFF": "-",
	"DATASOURCE_POINTS": [{
		"MAP_KEY_NO": 1,
		"ERIS_DATA_ID": 879395032
	}]
}, {
	"ORDER_ID": 1048712,
	"X": -104.94971782,
	"Y": 39.7928803,
	"GEOMETRY_TYPE": "POINT",
	"GEOMETRY": "[[[-104.94971782,39.7928803]]]",
	"BUFFER_RADIUS": 0.125,
	"MAP_KEY_LOC": "4",
	"MAP_KEY_NO_TOT": 2,
	"DISTANCE": 119.864702348497,
	"DIRECTION": "S",
	"ELEVATION": 1576.1248,
	"ELEVATION_DIFF": 0.8148,
	"DATASOURCE_POINTS": [{
		"MAP_KEY_NO": 1,
		"ERIS_DATA_ID": 825951091
	}, {
		"MAP_KEY_NO": 2,
		"ERIS_DATA_ID": 828471926
	}]
}, {
	"ORDER_ID": 1048712,
	"X": -104.94875856,
	"Y": 39.79322072,
	"GEOMETRY_TYPE": "POINT",
	"GEOMETRY": "[[[-104.94875856,39.79322072]]]",
	"BUFFER_RADIUS": 0.125,
	"MAP_KEY_LOC": "5",
	"MAP_KEY_NO_TOT": 2,
	"DISTANCE": 125.063689338846,
	"DIRECTION": "ESE",
	"ELEVATION": 1576.4824,
	"ELEVATION_DIFF": 1.1724,
	"DATASOURCE_POINTS": [{
		"MAP_KEY_NO": 1,
		"ERIS_DATA_ID": 807057641
	}, {
		"MAP_KEY_NO": 2,
		"ERIS_DATA_ID": 820843825
	}]
}, {
	"ORDER_ID": 1048712,
	"X": -104.949751,
	"Y": 39.792829,
	"GEOMETRY_TYPE": "POINT",
	"GEOMETRY": "[[[-104.949751,39.792829]]]",
	"BUFFER_RADIUS": 0.125,
	"MAP_KEY_LOC": "6",
	"MAP_KEY_NO_TOT": 1,
	"DISTANCE": 125.268758287778,
	"DIRECTION": "S",
	"ELEVATION": 1576.0924,
	"ELEVATION_DIFF": 0.7824,
	"DATASOURCE_POINTS": [{
		"MAP_KEY_NO": 1,
		"ERIS_DATA_ID": 877441181
	}]
}, {
	"ORDER_ID": 1048712,
	"X": -104.95057174,
	"Y": 39.7928327,
	"GEOMETRY_TYPE": "POINT",
	"GEOMETRY": "[[[-104.95057174,39.7928327]]]",
	"BUFFER_RADIUS": 0.125,
	"MAP_KEY_LOC": "7",
	"MAP_KEY_NO_TOT": 1,
	"DISTANCE": 138.291701868518,
	"DIRECTION": "SSW",
	"ELEVATION": 1575.7443,
	"ELEVATION_DIFF": 0.4343,
	"DATASOURCE_POINTS": [{
		"MAP_KEY_NO": 1,
		"ERIS_DATA_ID": 820831341
	}]
}, {
	"ORDER_ID": 1048712,
	"X": -104.9486862,
	"Y": 39.79309504,
	"GEOMETRY_TYPE": "POINT",
	"GEOMETRY": "[[[-104.9486862,39.79309504]]]",
	"BUFFER_RADIUS": 0.125,
	"MAP_KEY_LOC": "8",
	"MAP_KEY_NO_TOT": 2,
	"DISTANCE": 139.000301811885,
	"DIRECTION": "SE",
	"ELEVATION": 1576.7065,
	"ELEVATION_DIFF": 1.3965,
	"DATASOURCE_POINTS": [{
		"MAP_KEY_NO": 1,
		"ERIS_DATA_ID": 816484425
	}, {
		"MAP_KEY_NO": 2,
		"ERIS_DATA_ID": 820834214
	}]
}, {
	"ORDER_ID": 1048712,
	"X": -104.948663,
	"Y": 39.792892,
	"GEOMETRY_TYPE": "POINT",
	"GEOMETRY": "[[[-104.948663,39.792892]]]",
	"BUFFER_RADIUS": 0.125,
	"MAP_KEY_LOC": "9",
	"MAP_KEY_NO_TOT": 1,
	"DISTANCE": 156.626126681592,
	"DIRECTION": "SE",
	"ELEVATION": 1576.9355,
	"ELEVATION_DIFF": 1.6255,
	"DATASOURCE_POINTS": [{
		"MAP_KEY_NO": 1,
		"ERIS_DATA_ID": 828493348
	}]
}, {
	"ORDER_ID": 1048712,
	"X": -104.94880276,
	"Y": 39.79530407,
	"GEOMETRY_TYPE": "POINT",
	"GEOMETRY": "[[[-104.94880276,39.79530407]]]",
	"BUFFER_RADIUS": 0.125,
	"MAP_KEY_LOC": "10",
	"MAP_KEY_NO_TOT": 1,
	"DISTANCE": 175.384146180231,
	"DIRECTION": "NE",
	"ELEVATION": 1569.9835,
	"ELEVATION_DIFF": -5.3265,
	"DATASOURCE_POINTS": [{
		"MAP_KEY_NO": 1,
		"ERIS_DATA_ID": 807276962
	}]
}, {
	"ORDER_ID": 1048712,
	"X": -104.94760838,
	"Y": 39.79411954,
	"GEOMETRY_TYPE": "POINT",
	"GEOMETRY": "[[[-104.94760838,39.79411954]]]",
	"BUFFER_RADIUS": 0.125,
	"MAP_KEY_LOC": "11",
	"MAP_KEY_NO_TOT": 1,
	"DISTANCE": 194.293616387036,
	"DIRECTION": "E",
	"ELEVATION": 1576.3379,
	"ELEVATION_DIFF": 1.0279,
	"DATASOURCE_POINTS": [{
		"MAP_KEY_NO": 1,
		"ERIS_DATA_ID": 820828534
	}]
}]
        for i in erisPointsInfo:
            print(i)
        erisPointsLayer=addERISpoint(erisPointsInfo,map1,scratch)
        end = timeit.default_timer()
        arcpy.AddMessage(('4-3 add ERIS points to Map object', round(end -start,4)))
        start=end

        # 4-2 add Order Geometry
        addorder_geometry(map1,orderInfo['ORDER_GEOMETRY']['GEOMETRY_TYPE'],scratch,order_geometry)
        end = timeit.default_timer()
        arcpy.AddMessage(('4-2 add Geometry layer to Map object', round(end -start,4)))
        start=end

        # 4-3 Add Address n Order Number Turn on Layers
        map1.addTextoMap('Address',"Address: %s, %s, %s"%(orderInfo['ADDRESS'],orderInfo["CITY"],orderInfo['PROVSTATE']))
        map1.addTextoMap("OrderNum","Order Number: %s"%orderInfo['ORDER_NUM'])
        map1.turnOnLayer()
        end = timeit.default_timer()
        arcpy.AddMessage(('4-3 Add Address n turn on source layers', round(end -start,4)))
        start=end

        # 4-4 Optional multi_page add Buffer Export Map
        zoneUTM = orderInfo['ORDER_GEOMETRY']['UTM_ZONE']
        if zoneUTM<10:
            zoneUTM =' %s'%zoneUTM

        if multi_page==True:
            [maplist,map_mm] = exportmulti_page(map1,scratch,map_mm_name,zoneUTM,grid_size,erisPointsLayer,buffers,buffer_sizes,code,buffer_name)
            end = timeit.default_timer()
            arcpy.AddMessage(('4-4 MM map to pdf', round(end -start,4)))
            start=end
        else:
            # 4-4 add Buffer Export Map
            maplist = exportMap(map1,scratch,map_name,zoneUTM,buffers,buffer_sizes,code,buffer_name)
            end = timeit.default_timer()
            arcpy.AddMessage(('4-4 maps to 3 pdfs', round(end -start,4)))
            start=end
        scale = map1.df.scale
        del erisPointsLayer

        # 5 Aerial
        mapbing = Map(config.MXD.mxdbing)
        end = timeit.default_timer()
        arcpy.AddMessage(('5-1 inital aerial', round(end -start,4)))
        start=end
        mapbing.addTextoMap('Address',"Address: %s, %s, %s"%(orderInfo['ADDRESS'],orderInfo["CITY"],orderInfo['PROVSTATE']))
        mapbing.addTextoMap("OrderNum","Order Number: %s"%orderInfo['ORDER_NUM'])
        exportAerial(mapbing,scratch,order_geometry,orderInfo['ORDER_GEOMETRY']['GEOMETRY_TYPE'],eval(orderInfo['ORDER_GEOMETRY']['CENTROID'].strip('[]')),scale, aerial_pdf,zoneUTM)
        del mapbing
        end = timeit.default_timer()
        arcpy.AddMessage(('5-2 aerial', round(end -start,4)))
        start=end

        # 6 Topo
        if needTopo =='Y':
            maptopo = Map(config.MXD.mxdtopo)
            end = timeit.default_timer()
            arcpy.AddMessage(('6-1 topo', round(end -start,4)))
            start=end
            maptopo.addTextoMap('Address',"Address: %s, %s"%(orderInfo['ADDRESS'],orderInfo['PROVSTATE']))
            maptopo.addTextoMap("OrderNum","Order Number: %s"%orderInfo['ORDER_NUM'])
            
            exportTopo(maptopo,scratch,order_geometry,orderInfo['ORDER_GEOMETRY']['GEOMETRY_TYPE'],topo_pdf,code,buffer_max,zoneUTM)
            del maptopo,order_geometry
            end = timeit.default_timer()
            arcpy.AddMessage(('6 Topo', round(end -start,4)))
            start=end

        # 7 Report
        maplist.sort(reverse=True)
        if multi_page ==True:
            maplist.append(map_mm)
        maplist.append(aerial_pdf)
        maplist.append(topo_pdf) if needTopo =='Y' else None
        end = timeit.default_timer()
        arcpy.AddMessage(('7 maplist', round(end -start,4)))
        start=end

        pdf_report =pdf_report%(orderInfo['ORDER_NUM'])
        outputPDF = arcpy.mapping.PDFDocumentCreate(pdf_report)
        for page in maplist:
            outputPDF.appendPages(str(page))
        outputPDF.saveAndClose()

        if is_instant:
            shutil.copy(pdf_report,config.instant_reports)
        else:
            shutil.copy(pdf_report,config.noninstant_reports)
        end = timeit.default_timer()
        arcpy.AddMessage(('7 Bundle', round(end -start,4)))
        start=end
        arcpy.SetParameterAsText(5,pdf_report)

        # Xplorer
        if xplorerflag == 'Y':
            # os.path.join(scratch,'mxd.mxd')
            export_to_kml(order_num,map1)
            
            if os.path.exists(os.path.join(viewer_path,orderInfo['ORDER_NUM']+'_current')):
                shutil.rmtree(os.path.join(viewer_path,orderInfo['ORDER_NUM']+'_current'))
            shutil.copytree(scratchviewer, os.path.join(viewer_path, orderInfo['ORDER_NUM']+'_current'))
            url = currentuploadurl + orderInfo['ORDER_NUM']
            urllib.urlopen(url)
        del map1
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "PYTHON ERRORS:\nTraceback info:\n %s \nError Info:\n %s"%(tbinfo,str(sys.exc_info()[1]))
        msgs = "ArcPy ERRORS:\n %s\n"%arcpy.GetMessages(2)
        arcpy.AddError("hit CC's error code in except: Order ID %s"%order_id)
        arcpy.AddError(pymsg)
        arcpy.AddError(msgs)
        raise