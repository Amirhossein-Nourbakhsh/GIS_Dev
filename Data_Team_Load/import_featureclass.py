import arcpy, os
class DBConnections():
    sde_con_us_work = r'\\cabcvan1gis005\GISData\US_WORK.sde'
    sde_con_ca_work = r'\\cabcvan1gis005\GISData\CA_WORK.sde'
    sde_con_eris_work = r'\\cabcvan1gis005\GISData\ERIS_WORK.sde'
    sde_con_test_ca = r'\\cabcvan1gis005\GISData\TEST_CA.sde'
    sde_con_test_us = r'\\cabcvan1gis005\GISData\TEST_US.sde'
    sde_con_test_work = r'\\cabcvan1gis005\GISData\TEST_WORK.sde'

class OracleCredential():
    def __init__(self,db_connection_name):
        # initiate connection credential
        if db_connection_name.upper() =='TEST_CA':
            self.oracle_credential = DBConnections.sde_con_test_ca
        elif db_connection_name.upper() =='TEST_US':
            self.oracle_credential = DBConnections.sde_con_test_us
        elif db_connection_name.upper()=='TEST_WORK':
            self.oracle_credential = DBConnections.sde_con_test_work
        elif db_connection_name.upper() =='CA_WORK':
            self.oracle_credential = DBConnections.sde_con_ca_work
        elif db_connection_name.upper()=='US_WORK':
            self.oracle_credential = DBConnections.sde_con_us_work
        elif db_connection_name.upper() =='ERIS_WORK':
            self.oracle_credential = DBConnections.sde_con_eris_work
        else:
            raise ValueError("Bad connection name")
    def get_sde_con_file(self):
        return self.oracle_credential

def strip_arcenv(infc):
    arcpy.env.outputMFlag = "Disabled"
    arcpy.env.outputZFlag = "Disabled"
    arcpy.CopyFeatures_management(infc,os.path.join(scratchgdb,outfc))
    return os.path.join(scratchgdb,outfc)
def getspatial_ref(infc,outfc):
    infc = strip_arcenv(infc)
    spatial_ref = arcpy.Describe(infc).spatialReference
    if spatial_ref.factoryCode != 4326: #factory code for wgs84
        outload = os.path.join(scratchgdb,outfc+'load')
        arcpy.Project_management(infc,outload,4326)
        return outload
    else:
        return infc
indbconnection = 'TEST_US'#arcpy.GetParameterAsText(0)#r'\\cabcvan1gis005\GISData\Connection to GMTESTC.sde'#arcpy.GetParameterAsText(0) #location of connection file
infc = r'\\Cabcvan1fpr001\data\12CTESTING\US\_Federal\NPL\2021_05_20\PYLOADER\NationalPrioritiesList.gdb\Region9_boundaries'#arcpy.GetParameterAsText(1)#r'C:\Users\JLoucks\Desktop\HFA_CO.shp'#arcpy.GetParameterAsText(1) This can be a shapefile or .gdb featureclass
outfc = 'candelete4'#arcpy.GetParameterAsText(2)#'HFA_CO_test'#arcpy.GetParameterAsText(2) #name of table that will be imported to db
scratch = r'C:\Users\JLoucks\Documents\JL\test9'#arcpy.env.scratchFolder#r'C:\Users\JLoucks\Documents\JL\test1'
scratchgdb = os.path.join(scratch,'scratch.gdb')
arcpy.CreateFileGDB_management(scratch,'scratch.gdb')

try:
    arcpy.AddMessage('Stripping M Z values and projecting to WGS84')
    infc = str(getspatial_ref(infc,outfc))
    arcpy.AddMessage('Grabbing connection file')
    indbconnection = OracleCredential(indbconnection).get_sde_con_file()
    arcpy.AddMessage(indbconnection)
    arcpy.AddMessage('Copying Feature Class to DB')
    arcpy.FeatureClassToFeatureClass_conversion(infc,indbconnection,outfc,config_keyword='SDO_GEOMETRY')
except Exception as e:
    arcpy.AddError(e)
    arcpy.ClearWorkspaceCache_management()
finally:
    arcpy.ClearWorkspaceCache_management()
