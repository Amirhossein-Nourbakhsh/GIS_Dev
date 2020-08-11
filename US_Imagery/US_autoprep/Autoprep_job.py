## Create job folder, pull images from nas, copy images to job folder/clip doqq images for process
## may need to pass back json to FE or DB
import sys
import arcpy
import cx_Oracle
import contextlib
import json
import os
import shutil
import timeit
import urllib
start1 = timeit.default_timer()
arcpy.env.overwriteOutput = True

class Machine:
    machine_test = r"\\cabcvan1gis006"
    machine_prod = r"\\cabcvan1gis007"
class Credential:
    oracle_test = r"ERIS_GIS/gis295@GMTESTC.glaciermedia.inc"
    oracle_production = r"ERIS_GIS/gis295@GMPRODC.glaciermedia.inc"
class ReportPath:
    caaerial_prod= r"\\CABCVAN1OBI007\ErisData\prod\aerial_ca"
    caaerial_test= r"\\CABCVAN1OBI007\ErisData\test\aerial_ca"
class TestConfig:
    machine_path=Machine.machine_test
    caaerial_path = ReportPath.caaerial_test

    def __init__(self):
        machine_path=self.machine_path
        self.LAYER=LAYER(machine_path)
        self.MXD=MXD(machine_path)
class ProdConfig:
    machine_path=Machine.machine_prod
    caaerial_path = ReportPath.caaerial_prod

    def __init__(self):
        machine_path=self.machine_path
        self.LAYER=LAYER(machine_path)
        self.MXD=MXD(machine_path)
class Oracle:
    # static variable: oracle_functions
    oracle_functions = {'getorderinfo':"eris_gis.getOrderInfo"
    }
    erisapi_procedures = {'getaeriallist':'flow_autoprep.getAerialImageJson','passclipextent': 'flow_autoprep.setClipImageDetail'}
    def __init__(self,machine_name):
        # initiate connection credential
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
    def call_function(self,function_name,orderID):
        self.connect_to_oracle()
        cursor = self.cursor
        try:
            outType = cx_Oracle.CLOB
            func = [self.oracle_functions[_] for _ in self.oracle_functions.keys() if function_name.lower() ==_.lower()]
            if func !=[] and len(func)==1:
                try:
                    if type(orderID) !=list:
                        orderID = [orderID]
                    output=json.loads(cursor.callfunc(func[0],outType,orderID).read())
                except ValueError:
                    output = cursor.callfunc(func[0],outType,orderID).read()
                except AttributeError:
                    output = cursor.callfunc(func[0],outType,orderID)
            return output
        except cx_Oracle.Error as e:
            raise Exception(("Oracle Failure",e.message.message))
        except Exception as e:
            raise Exception(("JSON Failure",e.message.message))
        except NameError as e:
            raise Exception("Bad Function")
        finally:
            self.close_connection()
    def call_erisapi(self,erisapi_input):
        self.connect_to_oracle()
        cursor = self.cursor
        arg1 = erisapi_input
        arg2 = cursor.var(cx_Oracle.CLOB)
        arg3 = cursor.var(cx_Oracle.CLOB)
        arg4 = cursor.var(str)
        try:
            func = ['eris_api.callOracle']
            if func !=[] and len(func)==1:
                try:
                    output = cursor.callproc(func[0],[arg1,arg2,arg3,arg4])
                except ValueError:
                    output = cursor.callproc(func[0],[arg1,arg2,arg3,arg4])
                except AttributeError:
                    output = cursor.callproc(func[0],[arg1,arg2,arg3,arg4])
            return [output[0],cx_Oracle.LOB.read(output[1]),cx_Oracle.LOB.read(output[2]),output[3]]
        except cx_Oracle.Error as e:
            raise Exception(("Oracle Failure",e.message))
        except Exception as e:
            raise Exception(("JSON Failure",e.message))
        except NameError as e:
            raise Exception("Bad Function")
        finally:
            self.close_connection()
    def pass_values(self,function_name,value):#(self,function_name,data_type,value):
        self.connect_to_oracle()
        cursor = self.cursor
        try:
            func = [self.oracle_functions[_] for _ in self.oracle_functions.keys() if function_name.lower() ==_.lower()]
            if func !=[] and len(func)==1:
                try:
                    #output= cursor.callfunc(func[0],oralce_object,value)
                    output= cursor.callproc(func[0],value)
                    return 'pass'
                except ValueError:
                    raise
            return 'failed'
        except cx_Oracle.Error as e:
            raise Exception(("Oracle Failure",e.message.message))
        except Exception as e:
            raise Exception(e.message)
        except NameError as e:
            raise Exception("Bad Function")
        finally:
            self.close_connection()
## Custom Exceptions ##
class SingleEmptyImage(Exception):
    pass
class DoqqEmptyImage(Exception):
    pass
class OracleBadReturn(Exception):
    pass
class NoAvailableImage(Exception):
    pass
def createGeometry(pntCoords,geometry_type,output_folder,output_name, spatialRef = arcpy.SpatialReference(4326)):
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
def export_reportimage(imagepath,ordergeometry,auid):
    ## In memory
    mxd = arcpy.mapping.MapDocument(mxdexport_template)
    df = arcpy.mapping.ListDataFrames(mxd,'*')[0]
    sr = arcpy.SpatialReference(4326)
    df.SpatialReference = sr
    lyrpath = os.path.join(scratch,str(auid) + '.lyr')
    arcpy.MakeRasterLayer_management(imagepath,lyrpath)
    image_lyr = arcpy.mapping.Layer(lyrpath)
    geo_lyr = arcpy.mapping.Layer(ordergeometry)
    arcpy.mapping.AddLayer(df,image_lyr,'TOP')
    arcpy.mapping.AddLayer(df,geo_lyr,'TOP')
    arcpy.mapping.ListLayers()
    geometry_layer = arcpy.mapping.ListLayers(mxd,'OrderGeometry',df)[0]
    geometry_layer.visible = False
    geo_extent = geometry_layer.getExtent(True)
    df.extent = geo_extent
    if df.scale <= MapScale:
        df.scale = MapScale
        export_width = 5100
        export_height = 6600
    elif df.scale > MapScale:
        df.scale = ((int(df.scale)/100)+1)*100
        export_width = int(5100*1.4)
        export_height = int(6600*1.4)
    arcpy.RefreshActiveView()
    ###############################
    ## NEED TO EXPORT DF EXTENT TO ORACLE HERE
    NW_corner= str(df.extent.XMin) + ',' +str(df.extent.YMax)
    NE_corner= str(df.extent.XMax) + ',' +str(df.extent.YMax)
    SW_corner= str(df.extent.XMin) + ',' +str(df.extent.YMin)
    SE_corner= str(df.extent.XMax) + ',' +str(df.extent.YMin)
    try:
        image_extents = str({"PROCEDURE":Oracle.erisapi_procedures['passclipextent'], "ORDER_NUM" : OrderNumText,"AUI_ID":auid,"SWLAT":str(df.extent.YMin),"SWLONG":str(df.extent.XMin),"NELAT":(df.extent.XMax),"NELONG":str(df.extent.XMax)})
        message_return = Oracle('test').call_erisapi(image_extents)
        if message_return[3] != 'Y':
            raise OracleBadReturn
    except OracleBadReturn:
        arcpy.AddError('status: '+message_return[3]+' - '+message_return[2])
    ##############################
    #arcpy.mapping.ExportToJPEG(mxd,os.path.join(job_folder,'year'+'_source'+auid + '.jpg'),df,df_export_width=5100,df_export_height=6600,world_file=True,color_mode = '24-BIT_TRUE_COLOR', jpeg_quality = 50)
    #arcpy.DefineProjection_management(os.path.join(job_folder,'year'+'_source'+auid + '.jpg'), 3857)
    #shutil.copy(os.path.join(job_folder,'year'+'_source'+auid + '.jpg'),os.path.join(jpg_image_folder,auid + '.jpg'))
    arcpy.mapping.ExportToJPEG(mxd,os.path.join(jpg_image_folder,image_year + '_' + image_source + '_' +auid + '.jpg'),df,df_export_width=export_width,df_export_height=export_height,world_file=False,color_mode = '24-BIT_TRUE_COLOR', jpeg_quality = 50)
    mxd.saveACopy(os.path.join(scratch,auid+'_export.mxd'))
    del mxd


if __name__ == '__main__':
    start = timeit.default_timer()
    orderID = '889844'#arcpy.GetParameterAsText(0)
    scratch = r'C:\Users\JLoucks\Documents\JL\usaerial'#arcpy.env.scratchFolder
    job_directory = r'\\192.168.136.164\v2_usaerial\JobData\test'
    mxdexport_template = r'\\cabcvan1gis006\GISData\Aerial_US\mxd\Aerial_US_Export.mxd'
    conversion_input = r'\\192.168.136.164\v2_usaerial\input'
    conversion_output = r'\\192.168.136.164\v2_usaerial\output'
    Conversion_URL = r'http://erisservice3.ecologeris.com/ErisInt/USAerialAppService_test/USAerial.svc/USAerialImagePromote_temp?inputfile='
    MapScale = 6000

    ##get info for order from oracle
    orderInfo = Oracle('test').call_function('getorderinfo',orderID)
    OrderNumText = str(orderInfo['ORDER_NUM'])

    ## Return aerial list from oracle
    oracle_autoprep = str({"PROCEDURE":Oracle.erisapi_procedures['getaeriallist'],"ORDER_NUM":OrderNumText})
    aerial_list_return = Oracle('test').call_erisapi(oracle_autoprep)
    aerial_list_json = json.loads(aerial_list_return[1])

    ## Get order geometry 
    OrderGeometry = createGeometry(eval(orderInfo[u'ORDER_GEOMETRY'][u'GEOMETRY'])[0],orderInfo['ORDER_GEOMETRY']['GEOMETRY_TYPE'],scratch,'OrderGeometry.shp')

    ## Seperate processes for singleframe and DOQQ
    single_image_candidates = aerial_list_json['INHOUSE_IMAGE']
    doqq_image_candidates = aerial_list_json['DOQQ_IMAGE']

    ##Create job folder and copy images
    try:
        job_folder = os.path.join(job_directory,OrderNumText)
        org_image_folder = os.path.join(job_folder,'org')
        jpg_image_folder = os.path.join(job_folder,'jpg')
        if os.path.exists(job_folder):
            shutil.rmtree(job_folder)
        os.mkdir(job_folder)
        os.mkdir(org_image_folder)
        os.mkdir(jpg_image_folder)

        if len(single_image_candidates) == 0:
            raise SingleEmptyImage

        for inhouse_image in single_image_candidates:
            image_auid = str(inhouse_image['AUI_ID'])
            image_name = inhouse_image['IMAGE_NAME']
            image_year = str(inhouse_image['AERIAL_YEAR'])
            image_source = inhouse_image['IMAGE_SOURCE']
            if image_source == '':
                image_source = 'UNKWN'
            export_reportimage(image_name,OrderGeometry,image_auid)

        if len(doqq_image_candidates) == 0:
            raise DoqqEmptyImage

        for inhouse_image in doqq_image_candidates:
            image_auid = str(inhouse_image['AUI_ID'])
            image_name = inhouse_image['IMAGE_NAME']
            image_year = str(inhouse_image['AERIAL_YEAR'])
            image_source = inhouse_image['IMAGE_SOURCE']
            if image_source == '':
                image_source = 'UNKWN'
            export_reportimage(image_name,OrderGeometry,image_auid)

        if len(doqq_image_candidates) == 0 and len(single_image_candidates) == 0:
            raise NoAvailableImage
    except SingleEmptyImage:
        arcpy.AddWarning('No singleframe image candidates')
    except DoqqEmptyImage:
        arcpy.AddWarning('No DOQQ image candidates')
    except NoAvailableImage:
        arcpy.AddError('No available images for location')
        sys.exit()