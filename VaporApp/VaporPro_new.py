import arcpy,os,math,timeit
import cx_Oracle,itertools


def toCut(tocutt,lines,output):
    polygons=[]
    slices = []
    with arcpy.da.SearchCursor(tocutt, ["SHAPE@", "OID@"]) as pcursor:
        for prow in pcursor:
            polygon = prow[0]
            polyid = prow[1]
            polygons.append((polygon, polyid))
    del pcursor
    while polygons:
        for eachpoly, eachpolyid in polygons:
            iscut = False
            for eachline, eachlineid in lines:
                if eachline.crosses(eachpoly):
                    try:
                        slice1, slice2 = eachpoly.cut(eachline)
                        polygons.insert(0, (slice1, eachlineid))
                        polygons.insert(0, (slice2, eachlineid))
                        iscut = True
                    except RuntimeError:
                        continue
            if iscut == False and eachpoly.partCount==1:# and eachpolyid==1:
                slices.append((eachpoly, eachpolyid))
            polygons.remove((eachpoly, eachpolyid))

    arcpy.CreateFeatureclass_management("in_memory", output, "POLYGON",spatial_reference = srGCS83)
    output = 'in_memory/'+output
    arcpy.AddField_management(output, "SOURCE_OID", "LONG")
    slices1 = {}
    for line in slices:
            if (roundup(line[0].centroid.X,6),roundup(line[0].centroid.Y,6)) not in slices1.keys():
                slices1[(roundup(line[0].centroid.X,6),roundup(line[0].centroid.Y,6))] = line
    with arcpy.da.InsertCursor(output, ["SHAPE@", "SOURCE_OID"]) as icursor:
        for eachslice in slices1.values():
            icursor.insertRow(eachslice)
    del icursor

def FittlingB(Degree,OrderCoord):
    angle = math.radians(Degree)
    pairlist = []
    for feature in OrderCoord:
            for coordPair in feature:
                pairlist.append([coordPair[0],(coordPair[1])])
    blist = {}
    for pair in pairlist:
        if angle != 0.0:
            b = pair[1]-(pair[0]/math.tan(angle))
        else:
            b = pair[1]-(pair[0]/math.tan(angle+0.1))
        blist[b]=pair
    return {'max':blist[max(blist.keys())],'min':blist[min(blist.keys())]}

def createGeometry(coordslist,typeOrder):
    outshpP = str(r'in_memory/outshpP')
    if typeOrder.lower()== 'point':
        arcpy.CreateFeatureclass_management(r'in_memory', "outshpP", "MULTIPOINT", "", "DISABLED", "DISABLED", srGCS83)
        cursor = arcpy.da.InsertCursor(outshpP, ['SHAPE@'])
        cursor.insertRow([arcpy.Multipoint(arcpy.Array([arcpy.Point(*coords) for coords in coordslist[0]]),srGCS83)])
    elif typeOrder.lower() =='polyline':
        arcpy.CreateFeatureclass_management(r'in_memory', "outshpP", "POLYLINE", "", "DISABLED", "DISABLED", srGCS83)
        arcpy.AddField_management(outshpP,"BearingD",'FLOAT',10)
        cursor = arcpy.da.InsertCursor(outshpP, ['SHAPE@','BearingD'])
        cursor.insertRow(((arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in coordslist[0]]),srGCS83)),BearingD))
    else :
        arcpy.CreateFeatureclass_management(r'in_memory', "outshpP", "POLYGON", "", "DISABLED", "DISABLED", srGCS83)
        cursor = arcpy.da.InsertCursor(outshpP, ['SHAPE@'])
        cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in coordslist[0]]),srGCS83)])
    del cursor

    outputShp = os.path.join(scratch,'outshpP.shp')
    if typeOrder.lower() =='polyline':
        arcpy.Buffer_analysis(outshpP,outputShp,u'1 Feet')
    else:
        arcpy.CopyFeatures_management(outshpP,outputShp)
    if typeOrder.lower() != 'point':
        calculateBearDistance(outputShp)
    return outputShp


def calculateBearDistance(geo):
    global BearingD
    arcpy.AddGeometryAttributes_management(geo, "PERIMETER_LENGTH_GEODESIC", "FEET_US")
    rows = arcpy.SearchCursor(geo)
    for row in rows:
        permiter = row.PERIM_GEO
    del row
    del rows
    if int(permiter/2.0) >BearingD:
        BearingD = int(permiter/2.0)

def roundup(a, digits=0):
    n = 10**-digits
    return round(math.ceil(a / n) * n, digits)

def calculateBearingAngel():
    outPointSHP =os.path.join(scratch,"outPointSHP.shp")#r'in_memory/outPointSHP'
    arcpy.CreateFeatureclass_management(scratch, r"outPointSHP.shp", "POINT", "", "DISABLED", "DISABLED", srGCS83)
    arcpy.AddField_management(outPointSHP,"BearingD",'DOUBLE',10)
    arcpy.AddField_management(outPointSHP,"Angle",'DOUBLE',10)
    arcpy.AddField_management(outPointSHP,"Angle1",'DOUBLE',10)
    fields = ['SHAPE@XY', r'BearingD', r'Angle', r'Angle1']
    cursor = arcpy.da.InsertCursor(outPointSHP,fields)
    result = FittlingB(degree,OrderCoord)

    templist = []
    for key in result.keys():
        if degree<180:
            if key=='max':
                Angle = degree-UpperRange/2
                Angle1 = degree-UpperRange/2-sideRange
            elif key=='min':
                Angle = degree+UpperRange/2
                Angle1 = degree+UpperRange/2+sideRange

        else:
            if key=='max':
                Angle = degree+UpperRange/2
                Angle1 = degree+UpperRange/2+sideRange
            elif key=='min':
                Angle = degree-UpperRange/2
                Angle1 = degree-UpperRange/2-sideRange
        if Angle ==0 or Angle==360:
            Angle+=1
        if Angle1 ==0 or Angle1==360:
            Angle1+=1
        print Angle,Angle1
        templist.append((Angle)%360)
        templist.append((Angle1)%360)
        cursor.insertRow(((result[key][0],result[key][1]),BearingD,Angle%360,Angle1%360))
    del cursor
    arcpy.DefineProjection_management(outPointSHP, srGCS83)
    arcpy.AddXY_management(outPointSHP)
    if len(list(set(templist)))==3:
        global mark
        mark=1
    return outPointSHP

def linetoCut (outPoint):

    bearingFeature = os.path.join(scratch,'bearingFeature.shp')#r"in_memory/bearingFeature"#
    arcpy.BearingDistanceToLine_management(outPoint[:-4]+".dbf", r"in_memory/tB", 'POINT_X',"POINT_Y",'BearingD', 'FEET','Angle', 'DEGREES', 'GEODESIC', "",srGCS83)
    arcpy.BearingDistanceToLine_management(outPoint[:-4]+".dbf", r"in_memory/tBB", 'POINT_X',"POINT_Y",'BearingD', 'FEET','Angle1', 'DEGREES', 'GEODESIC', "",srGCS83)

    arcpy.Merge_management(["in_memory/tB","in_memory/tBB"],bearingFeature)
    rows = arcpy.da.SearchCursor(bearingFeature,['Shape@'])
    for row in rows:
        BearingLine.append([[row[0].firstPoint.X,row[0].firstPoint.Y],[row[0].lastPoint.X,row[0].lastPoint.Y]])
    del rows

    if OrderType.lower() =='point':
        temp1 =r"in_memory/bearingFeature"#os.path.join(scratch,'bearingFeature.shp')#
        arcpy.Dissolve_management(bearingFeature, temp1, dissolve_field="Angle;Angle1")
        bearingFeature = temp1
    arcpy.MakeFeatureLayer_management(bearingFeature, 'bearingFeature')
    com = tuple(itertools.combinations([r[0] for r in arcpy.da.SearchCursor(bearingFeature, ["OID@"])], 2))
    comlist = []
    for i in range(len(com)):
        id1 = com[i][0]
        id2 = com[i][1]
        arcpy.SelectLayerByAttribute_management('bearingFeature',"NEW_SELECTION", '"FID" =%s OR "FID" = %s '%(id1,id2))
        temp = os.path.join("in_memory",'com'+str(i))
        arcpy.Dissolve_management('bearingFeature',temp)
        comlist.append(temp)
    arcpy.Merge_management(comlist,"in_memory/cut")

    lines = {}
    with arcpy.da.SearchCursor("in_memory/cut", ["SHAPE@" ,"OID@"]) as lcursor:
        for line in lcursor:
            if (line[0].firstPoint.X,line[0].firstPoint.Y,line[0].lastPoint.X,line[0].lastPoint.Y) not in lines.keys():
                lines[(line[0].firstPoint.X,line[0].firstPoint.Y,line[0].lastPoint.X,line[0].lastPoint.Y)] = (line[0],line[1])
    del lcursor
    arcpy.CopyFeatures_management("in_memory/cut",os.path.join(scratch,"cutline.shp"))
    return lines.values()

def selectUpper(upper1):
    upperS = []
    if UpperRange ==360:
        rows = arcpy.da.SearchCursor(r"in_memory/orderGeoNameBuffer1",['Shape@'])
        for row in rows:
            templist = []
            for array in row[0]:
                for pnt in array:
                    if pnt:
                        templist.append([pnt.X,pnt.Y])
                    else:
                        break
            upperS.append(templist)
        del rows
        arcpy.CopyFeatures_management(r"in_memory/orderGeoNameBuffer1",os.path.join(scratch,"tempUp.shp"))
        return upperS
    elif UpperRange ==0:
        return []
    elif UpperRange+DownRange==360:
        if UpperRange >= DownRange:
            maxArea = max([row[1] for row in arcpy.da.SearchCursor(upper1,['OID@','Shape@AREA'])])
            oid = [row[0] for row in arcpy.da.SearchCursor(upper1,['OID@','Shape@AREA']) if row[1] == maxArea][0]
            rows = arcpy.da.SearchCursor(upper1,['OID@','Shape@AREA'])
            arcpy.SelectLayerByAttribute_management(upper1,"NEW_SELECTION", '"OID" =%s'%(oid))
        else:
            minArea = min([row[1] for row in arcpy.da.SearchCursor(upper1,['OID@','Shape@AREA'])])
            oid = [row[0] for row in arcpy.da.SearchCursor(upper1,['OID@','Shape@AREA']) if row[1] == minArea][0]
            arcpy.SelectLayerByAttribute_management(upper1,"NEW_SELECTION", '"OID" =%s'%(oid))
        rows = arcpy.da.SearchCursor(upper1,['Shape@'])
        for row in rows:
            templist = []
            for array in row[0]:
                for pnt in array:
                    if pnt:
                        templist.append([pnt.X,pnt.Y])
                    else:
                        break
            upperS.append(templist)
        del rows
        arcpy.CopyFeatures_management(upper1,os.path.join(scratch,"tempUp.shp"))
        return upperS
    elif  UpperRange+2*sideRange==360 and OrderType.lower() !='polygon':#OrderType.lower() =='point':
        arcpy.SelectLayerByAttribute_management("bearingFeature", "NEW_SELECTION", '"Angle" <>0 ')
        if int(arcpy.GetCount_management('bearingFeature')[0]) ==2:
            arcpy.SelectLayerByAttribute_management("bearingFeature", "NEW_SELECTION", '"Angle" =0 ')
        arcpy.SelectLayerByLocation_management(upper1,"SHARE_A_LINE_SEGMENT_WITH",'bearingFeature',"", "NEW_SELECTION",str("INVERT"))
        rows = arcpy.da.SearchCursor(upper1,['Shape@'])
        for row in rows:
            templist = []
            for array in row[0]:
                for pnt in array:
                    if pnt:
                        templist.append([pnt.X,pnt.Y])
                    else:
                        break
            upperS.append(templist)
        del rows
        return upperS
    else:
        arcpy.SelectLayerByAttribute_management('bearingFeature',"NEW_SELECTION", '"Angle" <> 0')
        arcpy.SelectLayerByLocation_management(upper1,"SHARE_A_LINE_SEGMENT_WITH",'bearingFeature',"", "NEW_SELECTION")
        arcpy.SelectLayerByAttribute_management("bearingFeature", "NEW_SELECTION", '"Angle1"<>0')
        arcpy.SelectLayerByLocation_management(upper1, "SHARE_A_LINE_SEGMENT_WITH", 'bearingFeature', "", "SUBSET_SELECTION", str("INVERT"))
        rows = arcpy.da.SearchCursor(upper1,['Shape@'])
        for row in rows:
            templist = []
            for array in row[0]:
                for pnt in array:
                    if pnt:
                        templist.append([pnt.X,pnt.Y])
                    else:
                        break
            upperS.append(templist)
        del rows
        return upperS

def selectLower(lower2):
    temp = lower2
    lowerS = []
    if DownRange ==360:
        rows = arcpy.da.SearchCursor(r"in_memory/orderGeoNameBuffer3",['Shape@'])
        for row in rows:
            templist = []
            for array in row[0]:
                for pnt in array:
                    if pnt:
                        templist.append([pnt.X,pnt.Y])
                    else:
                        break
            lowerS.append(templist)
        del rows
        arcpy.CopyFeatures_management(r"in_memory/orderGeoNameBuffer3",os.path.join(scratch,"tempDown.shp"))
        return lowerS
    elif DownRange ==0:
        return []
    elif (DownRange+UpperRange==360):
        if DownRange >= UpperRange + sideRange and UpperRange!=180 :
            maxArea = max([row[1] for row in arcpy.da.SearchCursor(lower2,['OID@','Shape@AREA'])])
            oid = [row[0] for row in arcpy.da.SearchCursor(lower2,['OID@','Shape@AREA']) if row[1] == maxArea][0]
            rows = arcpy.da.SearchCursor(lower2,['OID@','Shape@AREA'])
            arcpy.SelectLayerByAttribute_management(lower2,"NEW_SELECTION", '"OID" =%s'%(oid))
        else:
            minArea = min([row[1] for row in arcpy.da.SearchCursor(lower2,['OID@','Shape@AREA'])])
            oid = [row[0] for row in arcpy.da.SearchCursor(lower2,['OID@','Shape@AREA']) if row[1] == minArea][0]
            arcpy.SelectLayerByAttribute_management(lower2,"NEW_SELECTION", '"OID" =%s'%(oid))
        rows = arcpy.da.SearchCursor(lower2,['Shape@'])
        for row in rows:
            templist = []
            for array in row[0]:
                for pnt in array:
                    if pnt:
                        templist.append([pnt.X,pnt.Y])
                    else:
                        break
            lowerS.append(templist)
        del rows
        arcpy.CopyFeatures_management(lower2,os.path.join(scratch,"tempDown.shp"))
        return lowerS
    elif DownRange+2*sideRange==360 and OrderType.lower() !='polygon':#and OrderType.lower() =='point':
        arcpy.SelectLayerByAttribute_management("bearingFeature", "NEW_SELECTION", '"Angle" <>0 ')
        if int(arcpy.GetCount_management('bearingFeature')[0]) ==2:
            arcpy.SelectLayerByAttribute_management("bearingFeature", "NEW_SELECTION", '"Angle" =0 ')
        arcpy.SelectLayerByLocation_management(lower2,"SHARE_A_LINE_SEGMENT_WITH",'bearingFeature',"", "NEW_SELECTION",str("INVERT"))
        rows = arcpy.da.SearchCursor(lower2,['Shape@'])
        for row in rows:
            templist = []
            for array in row[0]:
                for pnt in array:
                    if pnt:
                        templist.append([pnt.X,pnt.Y])
                    else:
                        break
            lowerS.append(templist)
        del rows
        return lowerS
    else:
        arcpy.SelectLayerByAttribute_management("bearingFeature", "NEW_SELECTION", '"Angle1"<>0')
        arcpy.SelectLayerByLocation_management(lower2,"SHARE_A_LINE_SEGMENT_WITH",'bearingFeature',"", "NEW_SELECTION")
        arcpy.SelectLayerByAttribute_management("bearingFeature", "NEW_SELECTION", '"Angle" <>0 ')
        arcpy.SelectLayerByLocation_management(lower2, "SHARE_A_LINE_SEGMENT_WITH", 'bearingFeature', "", "SUBSET_SELECTION", str("INVERT"))
        rows = arcpy.da.SearchCursor(lower2,['Shape@'])
        arcpy.CopyFeatures_management(lower2,os.path.join(scratch,"tempDown.shp"))
        for row in rows:
            templist = []
            for array in row[0]:
                for pnt in array:
                    if pnt:
                        templist.append([pnt.X,pnt.Y])
                    else:
                        break

            lowerS.append(templist)
        del rows
        return lowerS

def selectSide(side3):
    temp = side3
    SideS = []
    if 2*sideRange ==360:
        rows = arcpy.da.SearchCursor(r"in_memory/orderGeoNameBuffer2",['Shape@'])
        for row in rows:
            templist = []
            for array in row[0]:
                for pnt in array:
                    if pnt:
                        templist.append([pnt.X,pnt.Y])
                    else:
                        break
            SideS.append(templist)
        del rows
        return SideS
    elif 2*sideRange ==0:
        return []
    elif (2*sideRange+UpperRange==360 or 2*sideRange+DownRange==360) and OrderType.lower() !='polygon':#and OrderType.lower() =='point':
        arcpy.SelectLayerByAttribute_management("bearingFeature", "NEW_SELECTION", '"Angle" <>0 ')
        if int(arcpy.GetCount_management('bearingFeature')[0]) ==2:
            arcpy.SelectLayerByAttribute_management("bearingFeature", "NEW_SELECTION", '"Angle" =0 ')
        arcpy.SelectLayerByLocation_management(side3,"SHARE_A_LINE_SEGMENT_WITH",'bearingFeature',"", "NEW_SELECTION")
        rows = arcpy.da.SearchCursor(side3,['Shape@'])
        for row in rows:
            templist = []
            for array in row[0]:
                for pnt in array:
                    if pnt:
                        templist.append([pnt.X,pnt.Y])
                    else:
                        break
            SideS.append(templist)
        del rows
        return SideS
    else:
        arcpy.SelectLayerByAttribute_management("bearingFeature", "NEW_SELECTION", '"Angle" <>0 ')
        arcpy.SelectLayerByLocation_management(side3,"SHARE_A_LINE_SEGMENT_WITH",'bearingFeature',"", "NEW_SELECTION")
        if UpperRange !=0:
            if int(float(bufferSize_U))<=int(float(bufferSize_S)):
                arcpy.SelectLayerByLocation_management(side3, "CONTAINS", upperClip, "", "SUBSET_SELECTION", str("INVERT"))
            else:
                arcpy.SelectLayerByLocation_management(side3, "WITHIN", upperClip, "", "SUBSET_SELECTION", str("INVERT"))
        else:
            arcpy.SelectLayerByLocation_management(side3,"SHARE_A_LINE_SEGMENT_WITH",lowerClip,"", "SUBSET_SELECTION")
        rows = arcpy.da.SearchCursor(side3,['Shape@'])
        for row in rows:
            templist = []
            for array in row[0]:
                for pnt in array:
                    if pnt:
                        templist.append([pnt.X,pnt.Y])
                    else:
                        break
            SideS.append(templist)
        del rows
        return SideS

def toLayer(outshp,line):
    global OrderType
    outshp_Buffer1 =  r"in_memory/orderGeoNameBuffer1"
    outshp_Buffer2 =  r"in_memory/orderGeoNameBuffer2"
    outshp_Buffer3 =  r"in_memory/orderGeoNameBuffer3"
    if OrderType.lower() == 'point':
        arcpy.Buffer_analysis(outshp,outshp_Buffer1,bufferSize_U+" Feet")
        arcpy.Buffer_analysis(outshp,outshp_Buffer2,bufferSize_S+" Feet")
        arcpy.Buffer_analysis(outshp,outshp_Buffer3,bufferSize_D+" Feet")
    else:
        arcpy.Buffer_analysis(outshp,outshp_Buffer1,bufferSize_U+" Feet","OUTSIDE_ONLY")
        arcpy.Buffer_analysis(outshp,outshp_Buffer2,bufferSize_S+" Feet","OUTSIDE_ONLY")
        arcpy.Buffer_analysis(outshp,outshp_Buffer3,bufferSize_D+" Feet","OUTSIDE_ONLY")

    Upper1 = str(r"in_memory/Upper1")
    Side2 = str(r"in_memory/Side2")
    Lower3 = str(r"in_memory/Lower3")
    toCut(outshp_Buffer1,line,"Upper1")
    toCut(outshp_Buffer2,line,'Side2')
    toCut(outshp_Buffer3,line,'Lower3')
    arcpy.MakeFeatureLayer_management(Upper1, 'Upper1')
    arcpy.MakeFeatureLayer_management(Side2, 'Side2')
    arcpy.MakeFeatureLayer_management(Lower3, 'Lower3')
    return ['Upper1','Side2','Lower3']

arcpy.Delete_management("in_memory")
arcpy.Delete_management('bearingFeature')
arcpy.Delete_management('Upper1')
arcpy.Delete_management('Side2')
arcpy.Delete_management('Lower3')
timein = timeit.default_timer()

connectionString = 'ERIS_GIS/gis295@GMTEST.glaciermedia.inc'

OrderIDText = '631617'#616090'#509635'#'568318'
scratch =r"E:\GISData_testing\test\temp1"
degree = float(9)
UpperRange = float(90)
DownRange = float(90)
bufferSize_U = '1750'
bufferSize_D ='100'
bufferSize_S = '365'

if degree >= 180.0:
    degree = degree-180.0
else:
    degree = degree+180.0
if degree == 0.0 or degree == 180.0:
    degree = degree+0.1
BearingD = 1.3*int(max([float(bufferSize_U),float(bufferSize_D),float(bufferSize_S)]))
print BearingD

if UpperRange+DownRange>=360:
    DownRange=360-UpperRange
    sideRange =0
else:
    sideRange = (360-UpperRange-DownRange)/2

srGCS83 = arcpy.SpatialReference(4269)
try:
    con = cx_Oracle.connect(connectionString)
    cur = con.cursor()

    cur.execute("select geometry,geometry_type from eris_order_geometry where order_id =" + OrderIDText)
    t = cur.fetchone()
    OrderCoord = eval(str(t[0]))
    OrderType = str(t[1])
except Exception,e:
    print e
    raise
finally:
    cur.close()
    con.close()

BearingLine = []
outshpP = createGeometry(OrderCoord,OrderType)
outPointSHP =calculateBearingAngel()
lines = linetoCut(outPointSHP)
[upperClip,sideClip,lowerClip]  = toLayer(outshpP,lines)

# ##########Upper Stream ######################
arcpy.CopyFeatures_management(upperClip,os.path.join(scratch,upperClip+".shp"))
### ########### Lower Stream ############################
arcpy.CopyFeatures_management(lowerClip,os.path.join(scratch,lowerClip+".shp"))
### ########### Side Stream ############################
arcpy.CopyFeatures_management(sideClip,os.path.join(scratch,"Side2.shp"))

resultS ={}
resultS['Upper1'] = selectUpper(upperClip)
resultS['Lower3'] = selectLower(lowerClip)
resultS['Side2'] =  selectSide(sideClip)
resultS['Line4'] = BearingLine
timeout = timeit.default_timer()
print timeout-timein
arcpy.CopyFeatures_management(upperClip,os.path.join(scratch,upperClip+"1.shp"))
### ########### Lower Stream ############################
arcpy.CopyFeatures_management(lowerClip,os.path.join(scratch,lowerClip+"1.shp"))
### ########### Side Stream ############################
arcpy.CopyFeatures_management(sideClip,os.path.join(scratch,"Side21.shp"))


for key in resultS.keys():
    print key
    print len(resultS[key])
try:
    con = cx_Oracle.connect(connectionString)
    cur = con.cursor()
    cvUp = cur.var(cx_Oracle.CLOB)
    cvUp.setvalue(0,str(resultS['Upper1']))
    cvDown = cur.var(cx_Oracle.CLOB)
    cvDown.setvalue(0,str(resultS['Lower3']))
    cvSide1 = cur.var(cx_Oracle.CLOB)
    cvSide2 = cur.var(cx_Oracle.CLOB)
    if len(resultS['Side2'])==1:
        cvSide1.setvalue(0,str(resultS['Side2'][0]))
        cvSide2.setvalue(0,str([]))
    elif len(resultS['Side2'])==3:
        cvSide1.setvalue(0,str(resultS['Side2'][1]))
        cvSide2.setvalue(0,str(resultS['Side2'][2]))
    elif resultS['Side2'] ==[]:
        cvSide1.setvalue(0,str([]))
        cvSide2.setvalue(0,str([]))
    else:
        cvSide1.setvalue(0,str(resultS['Side2'][0]))
        cvSide2.setvalue(0,str(resultS['Side2'][1]))
    cvLine = cur.var(cx_Oracle.CLOB)
    cvLine.setvalue(0,str(resultS['Line4']))
    query = cur.callproc('eris_vapor.setOrderVaporGeometry', (int(OrderIDText),cvUp, cvDown,cvSide1,cvSide2,cvLine,))
finally:
    cur.close()
    con.close()
if len(resultS.values())==4:
    arcpy.SetParameterAsText(7, 'OK')
else:
    raise
    'len(resultS)'


