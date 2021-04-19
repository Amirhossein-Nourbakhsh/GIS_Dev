import arcpy

indbconnection = r'\\cabcvan1gis005\GISData\Connection to GMTESTC.sde'#arcpy.GetParameterAsText(0) #location of connection file
infc = r'C:\Users\JLoucks\Desktop\HFA_CO.shp'#arcpy.GetParameterAsText(1) This can be a shapefile or .gdb featureclass
outfc = 'HFA_CO_test'#arcpy.GetParameterAsText(2) #name of table that will be imported to db
arcpy.env.outputMFlag = "Disabled"
arcpy.env.outputZFlag = "Disabled"
arcpy.FeatureClassToFeatureClass_conversion(infc,indbconnection,outfc)
