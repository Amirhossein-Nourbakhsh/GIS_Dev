import arcpy, os
def getspatial_ref(infc):
    spatial_ref = arcpy.Describe(infc).spatialReference
    if spatial_ref.factoryCode != 4326: #factory code for wgs84
        arcpy.Project_management(infc,os.path.join(scratch,infc),4326)
        infc = os.path.join(scratch,infc)
        return infc
    else:
        return infc
indbconnection = r'\\cabcvan1gis005\GISData\Connection to GMTESTC.sde'#arcpy.GetParameterAsText(0) #location of connection file
infc = r'C:\Users\JLoucks\Desktop\HFA_CO.shp'#arcpy.GetParameterAsText(1) This can be a shapefile or .gdb featureclass
outfc = 'HFA_CO_test'#arcpy.GetParameterAsText(2) #name of table that will be imported to db
scratch = r'C:\Users\JLoucks\Documents\JL\test1'
arcpy.env.outputMFlag = "Disabled"
arcpy.env.outputZFlag = "Disabled"
infc = getspatial_ref(infc)
arcpy.FeatureClassToFeatureClass_conversion(infc,indbconnection,outfc)
