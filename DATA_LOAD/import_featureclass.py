import arcpy, os
class DBConnections():
    def __init__(self):
        self.sde_con_us_work = r'\\cabcvan1gis005\GISData\US_WORK.sde'
        self.sde_con_ca_work = r'\\cabcvan1gis005\GISData\CA_WORK.sde'
        self.sde_con_eris_work = r'\\cabcvan1gis005\GISData\ERIS_WORK.sde'
        self.sde_con_test_ca = r'\\cabcvan1gis005\GISData\TEST_CA.sde'
        self.sde_con_test_us = r'\\cabcvan1gis005\GISData\TEST_US.sde'
        self.sde_con_test_work = r'\\cabcvan1gis005\GISData\TEST_WORK.sde'
def strip_arcenv(infc):
    arcpy.env.outputMFlag = "Disabled"
    arcpy.env.outputZFlag = "Disabled"
    arcpy.CopyFeatures_management(infc,os.path.join(scratchgdb,outfc))
    return os.path.join(scratchgdb,outfc)
def getdb_connection(indbconnection):
    us_load = str(r'\\cabcvan1gis005\GISData\US_LOAD_TEST.sde')
    ca_load = str(r'\\cabcvan1gis005\GISData\CA_LOAD_TEST.sde')
    if indbconnection == 'US_LOAD':
        return us_load
    elif indbconnection == 'CA_LOAD':
        return ca_load
    else:
        arcpy.AddError('Could not connect to %s'%(indbconnection))
def getspatial_ref(infc,outfc):
    infc = strip_arcenv(infc)
    spatial_ref = arcpy.Describe(infc).spatialReference
    if spatial_ref.factoryCode != 4326: #factory code for wgs84
        outload = os.path.join(scratchgdb,outfc+'load')
        arcpy.Project_management(infc,outload,4326)
        return outload
    else:
        return infc
indbconnection = 'US_LOAD'#str(arcpy.GetParameterAsText(0))#r'\\cabcvan1gis005\GISData\Connection to GMTESTC.sde'#arcpy.GetParameterAsText(0) #location of connection file
infc = r'\\cabcvan1gis005\MISC_DataManagement\DATA_TEAM_LOAD\US\SDR_TX\SDRDB_well_locations.shp'#str(arcpy.GetParameterAsText(1))#r'C:\Users\JLoucks\Desktop\HFA_CO.shp'#arcpy.GetParameterAsText(1) This can be a shapefile or .gdb featureclass
outfc = 'SDRDB_well_locations'#str(arcpy.GetParameterAsText(2))#'HFA_CO_test'#arcpy.GetParameterAsText(2) #name of table that will be imported to db
scratch = r'C:\Users\JLoucks\Documents\JL\test1'#arcpy.env.scratchFolder#r'C:\Users\JLoucks\Documents\JL\test1'
scratchgdb = os.path.join(scratch,'scratch.gdb')
arcpy.CreateFileGDB_management(scratch,'scratch.gdb')

indbconnection = str(getdb_connection(indbconnection))
infc = str(getspatial_ref(infc,outfc))
arcpy.FeatureClassToFeatureClass_conversion(infc,indbconnection,outfc)
