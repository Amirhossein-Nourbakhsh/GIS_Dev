#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:     Georeferecing the input images
# Author:      hkiavarz
# Created:     19/08/2020
#-------------------------------------------------------------------------------
import arcpy, os ,timeit
import cx_Oracle
import json
from difflib import SequenceMatcher


class Machine:
    machine_test = r"\\cabcvan1gis006"
    machine_prod = r"\\cabcvan1gis007"
class Credential:
    oracle_test = r"ERIS_GIS/gis295@GMTESTC.glaciermedia.inc"
    oracle_production = r"ERIS_GIS/gis295@GMPRODC.glaciermedia.inc"
class ImageBasePath:
    caaerial_test= r"\\CABCVAN1OBI007\ErisData\test\aerial_ca"
    caaerial_prod= r"\\CABCVAN1OBI007\ErisData\prod\aerial_ca"
class TransformationType():
    POLYORDER0 = "POLYORDER0"
    POLYORDER1 = "POLYORDER1"
    POLYORDER2 = "POLYORDER2"
    POLYORDER3 = "POLYORDER3"
    SPLINE = "ADJUST SPLINE"
    PROJECTIVE = "PROJECTIVE "
class ResamplingType():
    NEAREST  = "NEAREST"
    BILINEAR = "BILINEAR"
    CUBIC = "CUBIC"
    MAJORITY = "MAJORITY"
class Oracle:
    # static variable: oracle_functions
    # oracle_functions = {'getorderinfo':"eris_gis.getOrderInfo"}
    erisapi_procedures = {'getGeoreferencingInfo':'flow_gis.getGeoreferencingInfo'}
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
    def call_erisapi(self,erisapi_input):
        self.connect_to_oracle()
        cursor = self.cursor
        
        self.connect_to_oracle()
        cursor = self.cursor
        arg1 = erisapi_input
        arg2 = cursor.var(cx_Oracle.CLOB)
        arg3 = cursor.var(cx_Oracle.CLOB) ## Message
        arg4 = cursor.var(str)  ## Status
        try:
            func = ['eris_api.callOracle']
            if func !=[] and len(func)==1:
                try:
                    output = cursor.callproc(func[0],[arg1,arg2,arg3,arg4])
                except ValueError:
                    output = cursor.callproc(func[0],[arg1,arg2,arg3,arg4])
                except AttributeError:
                    output = cursor.callproc(func[0],[arg1,arg2,arg3,arg4])
            return output[0],cx_Oracle.LOB.read(output[1]),cx_Oracle.LOB.read(output[2]),output[3]
        except cx_Oracle.Error as e:
            raise Exception(("Oracle Failure",e.message))
        except Exception as e:
            raise Exception(("JSON Failure",e.message))
        except NameError as e:
            raise Exception("Bad Function")
        finally:
            self.close_connection()
def CoordToString(inputObj):
    coordPts_string = ""
    for i in range(len(inputObj)-1):
            coordPts_string +=  "'" + " ".join(str(i) for i in  inputObj[i]) + "';"
    result =  coordPts_string[:-1]
    return result
def ApplyGeoref(scratchFolder,inputRaster,srcPoints,gcpPoints,transType, resType):
    arcpy.AddMessage('Start Georeferencing...')
    out_coor_system = arcpy.SpatialReference(4326)

    # georeference to WGS84
    gcsImage_wgs84 = arcpy.Warp_management(inputRaster, srcPoints,gcpPoints,os.path.join(scratchFolder,'image_gc.tif'), transType, resType)

    # Define projection system for output image after warpping the raw image
    arcpy.DefineProjection_management(gcsImage_wgs84, out_coor_system)
    arcpy.AddMessage('--Georeferencing Done.')
    return gcsImage_wgs84
def ClipbyGeometry(scratchFolder,tempGDB, inputImg, coordinates):
    arcpy.AddMessage('Start Clipping...')
    spatialRef = arcpy.SpatialReference(4326)

    # Create temp polygon(clipper) featureclass -- > Envelope
    clp_FC = arcpy.CreateFeatureclass_management(tempGDB,"clipper", "POLYGON", "", "DISABLED", "DISABLED", spatialRef)
    cursor = arcpy.da.InsertCursor(clp_FC, ['SHAPE@'])
    cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in coordinates]),spatialRef)])
    del cursor
    # Clip the georeferenced image
    outpuImg = arcpy.Clip_management(inputImg,"",os.path.join(scratchFolder,'image_clp.tif'),clp_FC,"256","ClippingGeometry", "NO_MAINTAIN_EXTENT")
    arcpy.AddMessage('-- Clipping Done.')
    return outpuImg

if __name__ == '__main__':
    ### set input parameters
    # orderID = arcpy.GetParameterAsText(0)
    # orderNum = arcpy.GetParameterAsText(1)
    # imgName = arcpy.GetParameterAsText(2)
    # env = arcpy.GetParameterAsText(3)
    orderID = '902921'#arcpy.GetParameterAsText(0)
    order_Num = '20200806227'
    AUI_ID = '29683567'
    env = 'test'
    start1 = timeit.default_timer()
    
    scratchFolder = arcpy.env.scratchFolder
    ## georef information from oracle
    oracle_georef = str({"PROCEDURE":Oracle.erisapi_procedures["getGeoreferencingInfo"],"ORDER_NUM": '20282100006',"AUI_ID":AUI_ID})
    aerial_us_georef = Oracle(env).call_erisapi(oracle_georef)
    aerial_georefjson = json.loads(aerial_us_georef[1])
    img_Name = os.path.basename( aerial_georefjson['imgname'])
    img_baseName = (os.path.splitext(img_Name)[0]).replace('_g','') ## get image name without extention and remove _g from image name if availabe
    gcpPoints = CoordToString(aerial_georefjson['envelope'])
    ## Setup input and output paths
    if env == 'test':
        inputImagePath = os.path.join('r',ImageBasePath.caaerial_test,str(order_Num),'gc',aerial_georefjson['imgname'])
        ouputImage_jpg =  os.path.join('r',ImageBasePath.caaerial_test,str(order_Num),'jpg',img_baseName +'_gc.jpg')
        ouputImage_org =  os.path.join('r',ImageBasePath.caaerial_test,str(order_Num),'org',img_baseName +'_gc.tif')
        ouputImage_inv =  os.path.join('r',ImageBasePath.caaerial_test,str(order_Num),img_baseName +'_gc.tif')
        # scratchFolder = os.path.join('r',ImageBasePath.caaerial_test,str(order_Num))
    elif env == 'prod':
        inputImagePath = os.path.join('r',ImageBasePath.caaerial_prod,str(order_Num),'gc',aerial_georefjson['imgname'])
        ouputImage_jpg =  os.path.join('r',ImageBasePath.caaerial_prod,str(order_Num),'jpg',img_baseName +'_gc.jpg') ### year_DOQQ_AUID.jpg
        ouputImage_org =  os.path.join('r',ImageBasePath.caaerial_prod,str(order_Num),'org',img_baseName +'_gc.tif') ### year_DOQQ_AUID.tif (ask Brian or Sabrina)
        ouputImage_inv =  os.path.join('r',ImageBasePath.caaerial_prod,str(order_Num),img_baseName +'_gc.tif')
        # scratchFolder = os.path.join('r',ImageBasePath.caaerial_prod,str(order_Num))
    ### Create temp gdb CreatePersonalGDB
    tempGDB =os.path.join(scratchFolder,r"temp.gdb")
    if not os.path.exists(tempGDB):
        arcpy.CreateFileGDB_management(scratchFolder,r"temp.gdb")
    arcpy.env.workspace = tempGDB
    arcpy.env.overwriteOutput = True  
    
    ### Source point from input extent

    TOP = str(arcpy.GetRasterProperties_management(inputImagePath,"TOP").getOutput(0))
    LEFT = str(arcpy.GetRasterProperties_management(inputImagePath,"LEFT").getOutput(0))
    RIGHT = str(arcpy.GetRasterProperties_management(inputImagePath,"RIGHT").getOutput(0))
    BOTTOM = str(arcpy.GetRasterProperties_management(inputImagePath,"BOTTOM").getOutput(0))
    srcPoints = "'" + LEFT + " " + BOTTOM + "';" + "'" + RIGHT + " " + BOTTOM + "';" + "'" + RIGHT + " " + TOP + "';" + "'" + LEFT + " " + TOP + "'"
    
    ### Apply Georefrencing upon gcp points on input raw image
    img_Georeferenced = ApplyGeoref(scratchFolder,inputImagePath, srcPoints, gcpPoints, TransformationType.POLYORDER1, ResamplingType.BILINEAR)
    print(scratchFolder)
    
