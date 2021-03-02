import arcpy,os,math
import cx_Oracle

def createGeometry(coordslist,typeOrder, scratch):
    arcpy.env.overwriteOutput = True 
    # outshpP = str(r'in_memory/outshpP')
    outshpP = os.path.join(scratch, 'outshpP.shp')
    if typeOrder.lower()== 'point':
        # arcpy.CreateFeatureclass_management(r'in_memory', "outshpP", "MULTIPOINT", "", "DISABLED", "DISABLED", srGCS83)
        arcpy.CreateFeatureclass_management(scratch, 'outshpP.shp', "MULTIPOINT", "", "DISABLED", "DISABLED", srGCS83)
        cursor = arcpy.da.InsertCursor(outshpP, ['SHAPE@'])
        cursor.insertRow([arcpy.Multipoint(arcpy.Array([arcpy.Point(*coords) for coords in coordslist[0]]),srGCS83)])
    elif typeOrder.lower() =='polyline':
        # arcpy.CreateFeatureclass_management(r'in_memory', "outshpP", "POLYLINE", "", "DISABLED", "DISABLED", srGCS83)
        arcpy.CreateFeatureclass_management(scratch, 'outshpP.shp', "POLYLINE", "", "DISABLED", "DISABLED", srGCS83)
        cursor = arcpy.da.InsertCursor(outshpP, ['SHAPE@'])
        cursor.insertRow([arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in coordslist[0]]),srGCS83)])
    else :
        # arcpy.CreateFeatureclass_management(r'in_memory', "outshpP", "POLYGON", "", "DISABLED", "DISABLED", srGCS83)
        arcpy.CreateFeatureclass_management(scratch, 'outshpP.shp', "POLYGON", "", "DISABLED", "DISABLED", srGCS83)
        cursor = arcpy.da.InsertCursor(outshpP, ['SHAPE@'])
        cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in coordslist[0]]),srGCS83)])
    del cursor

    outshpP1 = os.path.join(scratch,'orderGeometry.shp')
    if typeOrder.lower() !='polygon':
        arcpy.Buffer_analysis(outshpP,outshpP1,"1 Feet")
        if typeOrder.lower()=='point':
            outshpPoint = os.path.join(scratch,'orderGeometryPoint.shp')
            # arcpy.CopyFeatures_management("in_memory/outshpP",outshpPoint)
            arcpy.CopyFeatures_management(outshpP ,outshpPoint)
    else:
        arcpy.CopyFeatures_management(outshpP,outshpP1)
    if arcpy.Exists(outshpP):
        del outshpP
        
    return outshpP1


def GP2vapor(OrderIDText,folder):

    global connectionString
    global srGCS83
    global scratch
    global OrderCoord
    global OrderType
    
    outshpP = None
    Upper1 = None
    Side2 = None
    Lower3 = None
    
    # arcpy.Delete_management('in_memory\outshpP')
    scratch = folder
    # connectionString = 'ERIS_GIS/gis295@GMTEST.glaciermedia.inc'
    connectionString = r'eris_gis/gis295@cabcvan1ora006.glaciermedia.inc:1521/GMTESTC'
    srGCS83 = arcpy.SpatialReference(4269)

    try:
        con = cx_Oracle.connect(connectionString)
        cur = con.cursor()

        cur.execute("select geometry,geometry_type from eris_order_geometry where order_id =" + OrderIDText)
        t = cur.fetchone()
        OrderCoord = eval(str(t[0]))
        OrderType = str(t[1])
        cur.execute("select UPPER_POLYGON_GEOMETRY,LOWER_POLYGON_GEOMETRY,SIDE_POLYGON1_GEOMETRY, SIDE_POLYGON2_GEOMETRY, POLYLINE_GEOMETRY from order_vapor where order_id =" + OrderIDText)
        t = cur.fetchone()
        upCoordinates = eval(str(t[0]))
        downCoordinates = eval(str(t[1]))
        sideCoordinates1 = eval(str(t[2]))
        sideCoordinates2 = eval(str(t[3]))
        lineCoordinates = eval(str(t[4]))
    except Exception,e:
        print e
        raise
    finally:
        cur.close()
        con.close()


    outshpP = createGeometry(OrderCoord,OrderType,scratch)

    if upCoordinates !=[] and len(upCoordinates[0]) >10 :
        Upper1 =os.path.join(scratch,"Upper1.shp")
        arcpy.CreateFeatureclass_management(scratch, "Upper1", "POLYGON", "", "DISABLED", "DISABLED", srGCS83)
        arcpy.AddMessage('Upper1.shp is created')
        cursor = arcpy.da.InsertCursor(Upper1, ['SHAPE@'])
        cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in upCoordinates[0]]),srGCS83)])
        arcpy.AddField_management(Upper1, "Label", "TEXT", "", "", "150", "", "NULLABLE", "NON_REQUIRED", "")
        rows = arcpy.UpdateCursor(Upper1)
        for row in rows:
            row.Label = "Up"
            rows.updateRow(row)
        del rows

    if downCoordinates !=[] and len(downCoordinates[0]) >10 :
        Lower3 =os.path.join(scratch,"Lower3.shp")
        arcpy.CreateFeatureclass_management(scratch, "Lower3", "POLYGON", "", "DISABLED", "DISABLED", srGCS83)
        arcpy.AddMessage('Lower3.shp is created')
        cursor = arcpy.da.InsertCursor(Lower3, ['SHAPE@'])
        cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in downCoordinates[0]]),srGCS83)])
        arcpy.AddField_management(Lower3, "Label", "TEXT", "", "", "150", "", "NULLABLE", "NON_REQUIRED", "")
        rows = arcpy.UpdateCursor(Lower3)
        for row in rows:
            row.Label = "Down"
            rows.updateRow(row)


    if sideCoordinates1 !=[] and len(sideCoordinates2) >10 :
        Side2 =os.path.join(scratch,"Side2.shp")
        arcpy.CreateFeatureclass_management(scratch, "Side2", "POLYGON", "", "DISABLED", "DISABLED", srGCS83)
        arcpy.AddMessage('Side2.shp is created')
        cursor = arcpy.da.InsertCursor(Side2, ['SHAPE@'])
        cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in sideCoordinates1]),srGCS83)])
        cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in sideCoordinates2]),srGCS83)])
        arcpy.AddField_management(Side2, "Label", "TEXT", "", "", "150", "", "NULLABLE", "NON_REQUIRED", "")
        rows = arcpy.UpdateCursor(Side2)
        for row in rows:
            row.Label = "Cross"
            rows.updateRow(row)
        del rows

    return [OrderType,outshpP,Upper1,Side2,Lower3]




