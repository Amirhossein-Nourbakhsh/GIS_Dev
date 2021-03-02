import os,arcpy,shutil
import VaporPro_module
import cx_Oracle
import glob
########################### Main ##################################################
# arcpy.Delete_management("in_memory")
# arcpy.Delete_management("in_memory")
# arcpy.Delete_management('bearingFeature')
# arcpy.Delete_management('Upper1')
# arcpy.Delete_management('Side2')
# arcpy.Delete_management('Lower3')
# Inputs
OrderIDText = arcpy.GetParameterAsText(0)
scratch = arcpy.env.scratchFolder
arcpy.env.workspace = scratch
arcpy.env.overwriteOutput = True 
OrderIDText = '846388'
arcpy.AddMessage(scratch)
#clean the scratch foler
try:
    files = os.listdir(scratch)
    for f in files:
        os.remove(os.path.join(scratch , f))
except OSError as e:
    print("Error: %s : %s" % (scratch, e.strerror))


# Static Connection Paths
# connectionString = 'ERIS_GIS/gis295@GMTEST.glaciermedia.inc'
connectionString = r'eris_gis/gis295@cabcvan1ora006.glaciermedia.inc:1521/GMTESTC'
# report_path = r"\\cabcvan1obi002\ErisData\Reports\test\noninstant_reports"
report_path = r"\\cancvan1eap006\ErisData\Reports\test\noninstant_reports"


# Layers

erisPoints = r"C:\git\GIS_Dev\VaporApp\VaporPoints.lyr"
quadLyr = r"C:\git\GIS_Dev\VaporApp\Quadrants1.lyr"
mxdVapor = r"C:\git\GIS_Dev\VaporApp\mxdVapor1.mxd"
orderPoly=r"C:\git\GIS_Dev\VaporApp\orderPoly.lyr"
orderPoint =r"C:\git\GIS_Dev\VaporApp\SiteMaker.lyr"
buffer10lyr =r"C:\git\GIS_Dev\VaporApp\buffer10.lyr"
buffer3lyr = r"C:\git\GIS_Dev\VaporApp\buffer3.lyr"
bufferMaxlyr =r"C:\git\GIS_Dev\VaporApp\Buffer.lyr"
ERISvaporLyr = r"C:\git\GIS_Dev\VaporApp\ERIStemp.lyr"
LTANKLyr = r"C:\git\GIS_Dev\VaporApp\LTANK.lyr"
DRYCLyr = r"C:\git\GIS_Dev\VaporApp\DRYC.lyr"
LTDCLyr =  r"C:\git\GIS_Dev\VaporApp\LTDC.lyr"


# erisPoints = r"\\cabcvan1gis005\GISData\VaporApp\VaporPoints.lyr"
# quadLyr = r"\\cabcvan1gis005\GISData\VaporApp\Quadrants1.lyr"
# mxdVapor = r"\\cabcvan1gis005\GISData\VaporApp\mxdVapor1.mxd"
# orderPoly=r"\\cabcvan1gis005\GISData\VaporApp\orderPoly.lyr"
# orderPoint =r"\\cabcvan1gis005\GISData\VaporApp\SiteMaker.lyr"
# buffer10lyr =r"\\cabcvan1gis005\GISData\VaporApp\buffer10.lyr"
# buffer3lyr = r"\\cabcvan1gis005\GISData\VaporApp\buffer3.lyr"
# bufferMaxlyr =r"\\cabcvan1gis005\GISData\VaporApp\Buffer.lyr"
# ERISvaporLyr = r"\\cabcvan1gis005\GISData\VaporApp\ERIStemp.lyr"
# LTANKLyr = r"\\cabcvan1gis005\GISData\VaporApp\LTANK.lyr"
# DRYCLyr = r"\\cabcvan1gis005\GISData\VaporApp\DRYC.lyr"
# LTDCLyr =  r"\\cabcvan1gis005\GISData\VaporApp\LTDC.lyr"
srGCS83 = arcpy.SpatialReference(4269)

try:
    cur = None
    con = cx_Oracle.connect(connectionString)
    cur = con.cursor()

    cur.execute("select eris_data_id from order_detail_vapor where include = 'Include Record' and order_id= " + OrderIDText)
    t = cur.fetchall()
    erisdataIDs = [_[0]for _ in t]

    cur.execute("select order_num, address1, city, provstate from orders where order_id =" + OrderIDText)
    t = cur.fetchone()
    OrderNumText = str(t[0])
    AddressText = str(t[1])+","+str(t[2])+","+str(t[3])

    cur.execute("select max_buffer from order_vapor where order_id= " + OrderIDText)
    t = cur.fetchone()
    maxbuffer = t[0]
except Exception,e:
    print e
    raise
finally:
    if cur is not None:
        cur.close()
        con.close()

[OrderType,outshpP,Upper1,Side2,Lower3] =VaporPro_module.GP2vapor(OrderIDText,scratch)

ERIS_sel= os.path.join(scratch,"ERISPoly"+OrderIDText+".shp")
vaporPolygon= os.path.join(scratch,'mergedSHP.shp')

arcpy.Merge_management([_ for _ in [outshpP,Side2,Lower3,Upper1] if _ !=""],vaporPolygon)
if erisdataIDs !=[]:
    arcpy.Clip_analysis(erisPoints, vaporPolygon, ERIS_sel)
    ERIS_vapor= os.path.join(scratch,"ERISvapor.shp")
    arcpy.Select_analysis(ERIS_sel, ERIS_vapor, "\"ID\" IN ("+ str(erisdataIDs).strip("[]")+")")
    arcpy.AddField_management(ERIS_vapor, "Elevation", "DOUBLE", "12", "6", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(ERIS_vapor, "MapKeyNo", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(ERIS_vapor, "MapKeyLoc", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(ERIS_vapor, "MapKeyTot", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
    arcpy.AddField_management(ERIS_vapor, "Distance", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    keyDict={}
    astmList = {}
    LTANKlist = []
    DRYClist = []
    try:
        con = cx_Oracle.connect(connectionString)
        cur = con.cursor()
        for erisID in erisdataIDs:
            cur.execute("select map_key_loc,distance, elevation_diff,map_key_no,map_key_no_tot from order_detail_vapor where eris_data_id= %s and order_id = %s " % (str(erisID), OrderIDText))
            t = cur.fetchone()
            keyDict[erisID] = t

            cur.execute("select bb.astm_type from order_detail_vapor aa, eris_data_source bb where aa.eris_data_id = %s and bb.ds_oid = aa.ds_oid" % (str(erisID)))
            t = cur.fetchone()
            if 'LTANK' in t:
                LTANKlist.append(erisID)
            elif 'DRYC' in t:
                DRYClist.append(erisID)
        astmList['LTANK'] = LTANKlist
        astmList['DRYC'] = DRYClist
        astmList['LTDC'] = list(set([_ for _ in [keyDict[temp][0] for temp in LTANKlist] if _ in [keyDict[temp][0] for temp in DRYClist]]))
    except Exception,e:
        print e
        raise
    finally:
        cur.close()
        con.close()

if 'ERIS_vapor' in locals():
    rows = arcpy.UpdateCursor(ERIS_vapor)
    for row in rows:
        key = row.ID
        if keyDict[key] !=None:
            row.MapKeyLoc = keyDict[key][0]
            row.Distance = keyDict[key][1]
            row.Elevation = keyDict[key][2]
            row.MapKeyNo  =keyDict[key][3]
            row.MapKeyTot = keyDict[key][4]
            rows.updateRow(row)
    del rows

mxd = arcpy.mapping.MapDocument(mxdVapor)
df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
if OrderType.lower()=='point':
    geom = orderPoint
else:
    geom=orderPoly
legend = arcpy.mapping.ListLayoutElements(mxd, "LEGEND_ELEMENT", "Legend")[0]


buffer10P = os.path.join(scratch,'buffer10P.shp')
buffer10 = os.path.join(scratch,'buffer10.shp')
buffer3P = os.path.join(scratch,'buffer3P.shp')
buffer3 = os.path.join(scratch,'buffer3.shp')
bufferMax = os.path.join(scratch,'bufferMax.shp')
arcpy.Buffer_analysis(outshpP,buffer10P,"528 Feet")
arcpy.Buffer_analysis(outshpP,buffer3P,"1760 Feet")
arcpy.Buffer_analysis(outshpP,bufferMax,str(maxbuffer)+" Mile")

coordslist = []
rows = arcpy.da.SearchCursor(buffer10P,['Shape@'])
for row in rows:
    templist = []
    for array in row[0]:
        for pnt in array:
            templist.append([pnt.X,pnt.Y])
    coordslist.append(templist)
arcpy.CreateFeatureclass_management(scratch, "buffer10", "POLYLINE", "", "DISABLED", "DISABLED", srGCS83)
cursor = arcpy.da.InsertCursor(buffer10, ['SHAPE@'])
cursor.insertRow([arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in coordslist[0]]),srGCS83)])
del cursor
coordslist = []
rows = arcpy.da.SearchCursor(buffer3P,['Shape@'])
for row in rows:
    templist = []
    for array in row[0]:
        for pnt in array:
            templist.append([pnt.X,pnt.Y])
    coordslist.append(templist)
arcpy.CreateFeatureclass_management(scratch, "buffer3", "POLYLINE", "", "DISABLED", "DISABLED", srGCS83)
cursor = arcpy.da.InsertCursor(buffer3, ['SHAPE@'])
cursor.insertRow([arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in coordslist[0]]),srGCS83)])
del cursor
legend.autoAdd = False

bufferLayer10 = arcpy.mapping.Layer(buffer10lyr)
bufferLayer10.replaceDataSource(scratch,"SHAPEFILE_WORKSPACE","buffer10")
arcpy.mapping.AddLayer(df,bufferLayer10,"TOP")

bufferLayer3 = arcpy.mapping.Layer(buffer3lyr)
bufferLayer3.replaceDataSource(scratch,"SHAPEFILE_WORKSPACE","buffer3")
arcpy.mapping.AddLayer(df,bufferLayer3,"TOP")

newLayerordergeo = arcpy.mapping.Layer(geom)
if OrderType.lower()=='point':
    newLayerordergeo.replaceDataSource(scratch, "SHAPEFILE_WORKSPACE", "orderGeometryPoint" )
else:
    newLayerordergeo.replaceDataSource(scratch, "SHAPEFILE_WORKSPACE", "orderGeometry" )
arcpy.mapping.AddLayer(df, newLayerordergeo , "TOP")

legend.autoAdd = False
bufferLayerMax = arcpy.mapping.Layer(bufferMaxlyr)
bufferLayerMax.replaceDataSource(scratch,"SHAPEFILE_WORKSPACE","bufferMax")
arcpy.mapping.AddLayer(df,bufferLayerMax,"TOP")

if 'ERIS_vapor' in locals():
    legend.autoAdd = True
    if astmList['LTANK'] !=[]:
        ERIS_LTANK= os.path.join(scratch,"LTANK.shp")
        if astmList['LTDC'] !=[]:
            arcpy.Select_analysis(ERIS_vapor, ERIS_LTANK,  "\"ID\" IN ("+ str(astmList['LTANK']).strip("[]")+")" + ' AND "MapKeyLoc" NOT IN ('+ str(astmList['LTDC']).strip("[]")+')')
        else:
            arcpy.Select_analysis(ERIS_vapor, ERIS_LTANK,  "\"ID\" IN ("+ str(astmList['LTANK']).strip("[]")+")")
        newLayerLTANK = arcpy.mapping.Layer(LTANKLyr)
        newLayerLTANK.replaceDataSource(scratch, "SHAPEFILE_WORKSPACE", "LTANK")
        arcpy.mapping.AddLayer(df, newLayerLTANK, "TOP")
    if astmList['DRYC'] !=[]:
        ERIS_DRYC= os.path.join(scratch,"DRYC.shp")
        if astmList['LTDC'] !=[]:
            arcpy.Select_analysis(ERIS_vapor, ERIS_DRYC, "\"ID\" IN ("+ str(astmList['DRYC']).strip("[]")+")"+ ' AND "MapKeyLoc" NOT IN ('+ str(astmList['LTDC']).strip("[]")+')')
        else:
            arcpy.Select_analysis(ERIS_vapor, ERIS_DRYC, "\"ID\" IN ("+ str(astmList['DRYC']).strip("[]")+")")
        newLayerDRYC = arcpy.mapping.Layer(DRYCLyr)
        newLayerDRYC.replaceDataSource(scratch, "SHAPEFILE_WORKSPACE", "DRYC")
        arcpy.mapping.AddLayer(df, newLayerDRYC, "TOP")
    if astmList['LTDC'] !=[]:
        ERIS_LTDC= os.path.join(scratch,"LTDC.shp")
        arcpy.Select_analysis(ERIS_vapor, ERIS_LTDC,'"MapKeyLoc" IN ('+ str(astmList['LTDC']).strip("[]")+')')
        newLayerLTDC = arcpy.mapping.Layer(LTDCLyr)
        newLayerLTDC.replaceDataSource(scratch, "SHAPEFILE_WORKSPACE", "LTDC")
        arcpy.mapping.AddLayer(df, newLayerLTDC, "TOP")
    newLayerERIS = arcpy.mapping.Layer(ERISvaporLyr)
    newLayerERIS.replaceDataSource(scratch, "SHAPEFILE_WORKSPACE", "ERISvapor")
    arcpy.mapping.AddLayer(df, newLayerERIS, "TOP")

df.scale = 2500
df.extent = bufferLayerMax.getSelectedExtent(False)
df.scale = df.scale*1.1

OrderIDBing = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "OrderIDText")[0]
AddressBing = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "AddressText")[0]
OrderIDBing.text = "Order No: "+ OrderNumText + "v"
AddressBing.text = "Address: " + AddressText + ""

outputPDFName = os.path.join(scratch, "map_" + OrderNumText + "_vapor.pdf")
arcpy.AddMessage(outputPDFName)
outputPDF = arcpy.mapping.PDFDocumentCreate(outputPDFName)
outputLayoutPDF1 = os.path.join(scratch, "map1.pdf")
arcpy.mapping.ExportToPDF(mxd, outputLayoutPDF1, "PAGE_LAYOUT", 640, 480, 250, "BEST", "RGB", True, "ADAPTIVE", "VECTORIZE_BITMAP", False, True, "LAYERS_AND_ATTRIBUTES", True, 90)

for lyr in arcpy.mapping.ListLayers(mxd, "", df):
        if lyr.dataSource == bufferMax:
            arcpy.mapping.RemoveLayer(df, lyr)
            break
arcpy.mapping.RemoveLayer(df,bufferLayerMax)

legend.autoAdd = True
if 'ERIS_DRYC' in locals():
    for lyr in arcpy.mapping.ListLayers(mxd, "", df):
        if lyr.dataSource == ERIS_DRYC:
            arcpy.mapping.RemoveLayer(df, lyr)
            arcpy.mapping.AddLayer(df,newLayerDRYC,"TOP")
            break
if 'ERIS_LTANK' in locals():
    for lyr in arcpy.mapping.ListLayers(mxd, "", df):
        if lyr.dataSource == ERIS_LTANK:
            arcpy.mapping.RemoveLayer(df, lyr)
            arcpy.mapping.AddLayer(df,newLayerLTANK,"TOP")
            break

quadrantLayer = arcpy.mapping.Layer(quadLyr)
quadrantLayer.replaceDataSource(scratch,"SHAPEFILE_WORKSPACE","mergedSHP")
arcpy.mapping.AddLayer(df,quadrantLayer,"TOP")

if 'ERIS_vapor' in locals():
    for lyr in arcpy.mapping.ListLayers(mxd, "", df):
        if lyr.dataSource == ERIS_vapor:
            arcpy.mapping.RemoveLayer(df, lyr)
            arcpy.mapping.AddLayer(df,newLayerERIS,"TOP")
            break

df.scale = 2500
df.extent = bufferLayer3.getSelectedExtent(False)
df.scale = df.scale*1.1

outputLayoutPDF2 = os.path.join(scratch, "map2.pdf")
arcpy.mapping.ExportToPDF(mxd, outputLayoutPDF2, "PAGE_LAYOUT", 640, 480, 250, "BEST", "RGB", True, "ADAPTIVE", "VECTORIZE_BITMAP", False, True, "LAYERS_AND_ATTRIBUTES", True, 90)
outputPDF.appendPages(outputLayoutPDF2)
outputPDF.appendPages(outputLayoutPDF1)
outputPDF.saveAndClose()
mxd.saveACopy(os.path.join(scratch, "mxd.mxd"))
shutil.copy(outputPDFName, report_path)

del outshpP,
del Upper1
del Side2
del Lower3
del df
del bufferLayerMax
del bufferLayer3
del bufferLayer10
del newLayerordergeo
del mxd
arcpy.SetParameterAsText(1, outputPDFName)
















