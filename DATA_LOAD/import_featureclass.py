import arcpy, os
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
    spatial_ref = arcpy.Describe(infc).spatialReference
    if spatial_ref.factoryCode != 4326: #factory code for wgs84
        arcpy.Project_management(infc,os.path.join(scratch,outfc+'.shp'),4326)
        infc = os.path.join(scratch,outfc+'.shp')
        return infc
    else:
        return infc
indbconnection = str(arcpy.GetParameterAsText(0))#r'\\cabcvan1gis005\GISData\Connection to GMTESTC.sde'#arcpy.GetParameterAsText(0) #location of connection file
infc = str(arcpy.GetParameterAsText(1))#r'C:\Users\JLoucks\Desktop\HFA_CO.shp'#arcpy.GetParameterAsText(1) This can be a shapefile or .gdb featureclass
outfc = str(arcpy.GetParameterAsText(2))#'HFA_CO_test'#arcpy.GetParameterAsText(2) #name of table that will be imported to db
scratch = arcpy.env.scratchFolder#r'C:\Users\JLoucks\Documents\JL\test1'
arcpy.env.outputMFlag = "Disabled"
arcpy.env.outputZFlag = "Disabled"
indbconnection = str(getdb_connection(indbconnection))
infc = str(getspatial_ref(infc,outfc))
arcpy.FeatureClassToFeatureClass_conversion(infc,indbconnection,outfc)
