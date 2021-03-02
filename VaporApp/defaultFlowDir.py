import os, arcpy,numpy,math,cx_Oracle,timeit

def get9Cells(x,y):
    masterLayer_dem = arcpy.mapping.Layer(masterlyr_dem)
    a = numpy.zeros((3,3))
    arrays = numpy.array([a,a,a,a,a,a,a,a,a])

    outshpP = r"in_memory\nightSHP"#os.path.join(scratch,'nightSHP.shp')
    arcpy.CreateFeatureclass_management('in_memory', "nightSHP", "MULTIPOINT", "", "DISABLED", "DISABLED", srGCS83)
    cursor = arcpy.da.InsertCursor(outshpP, ['SHAPE@'])
    for i in range(9):
        cursor.insertRow([arcpy.Multipoint(arcpy.Array([arcpy.Point(x+((-3.5+2*(i%3))*cellsize),y+((0.5-2*(i/3))*cellsize))]),srGCS83)])

    arcpy.SelectLayerByLocation_management(masterLayer_dem, 'intersect', outshpP)
    if int((arcpy.GetCount_management(masterLayer_dem).getOutput(0))) != 0:
        columns = arcpy.SearchCursor(masterLayer_dem)
        for column in columns:
            img = column.getValue("image_name")
            if img.strip() !="":
                img = os.path.join(imgdir_dem,img)
                break
        del column
        del columns
        xx = arcpy.RasterToNumPyArray(img,arcpy.Point(x+((-3.5+2*(0%3))*cellsize),y+((0.5-2*(8/3))*cellsize)),9,9)
        (arrays[0],arrays[1],arrays[2],arrays[3],arrays[4],arrays[5],arrays[6],arrays[7],arrays[8])=(xx[:3,[0,1,2]],xx[:3,[3,4,5]],xx[:3,[6,7,8]],xx[3:6,[0,1,2]],xx[3:6,[3,4,5]],xx[3:6,[6,7,8]],xx[6:9,[0,1,2]],xx[6:9,[3,4,5]],xx[6:9,[6,7,8]])
        for i in range(9):
            arrays[i]=(numpy.ma.masked_where(arrays[i] <0, arrays[i]))
    return [[arrays[0].mean(),arrays[1].mean(),arrays[2].mean()],[arrays[3].mean(),arrays[4][2,2],arrays[5].mean()],[arrays[6].mean(),arrays[7].mean(),arrays[8].mean()]]

def flowDirNUm(x,y):
    [[n1,n2,n3],[n4,n5,n6],[n7,n8,n9]] = get9Cells(x,y)
    parameters = {
    1:{'e1': n6, 'e2': n3,'ac':0,'af':1},
    2:{'e1': n2, 'e2': n3,'ac':1,'af':-1},
    3:{'e1': n2, 'e2': n1,'ac':1,'af':1},
    4:{'e1': n4, 'e2': n1,'ac':2,'af':-1},
    6:{'e1': n6, 'e2': n9,'ac':4,'af':-1},
    7:{'e1': n4, 'e2': n4,'ac':2,'af':1},
    8:{'e1': n8, 'e2': n7,'ac':3,'af':-1},
    9:{'e1': n8, 'e2': n9,'ac':3,'af':1}}
    smax = 0
    keymax = 1
    slopeDirections ={}
    for key in parameters.keys():
        e1 = parameters[key]['e1']
        e2 = parameters[key]['e2']
        af = parameters[key]['af']
        ac = parameters[key]['ac']
        s1 = (n5-e1)/cellsize
        s2 = (e1-e2)/cellsize
        s = math.sqrt(math.pow(s1,2)+math.pow(s2,2))
        if s1 ==0:
            s1=s1+0.1
        r = math.atan(s2/s1)
        if r <0:
            r=0
            s=s1
        elif r > math.atan(1):
            r= math.atan(1)
            s= (n5-e2)/math.sqrt(2)
        rg = af*r+ac*math.pi/2
        if s>smax:
            smax=s
            keymax =key
        slopeDirections[key] = {'s':s,'r':r,'rg':rg}
    return (360-(slopeDirections[keymax]['rg']/math.pi*180-90))%360#


arcpy.Delete_management(r"in_memory")
OrderIDText = '427550'#616276'616620'616622'619811'
##scratch = r"E:\GISData_testing\test\temp4"

imgdir_dem = r"\\Cabcvan1gis001\US_DEM\DEM1"
masterlyr_dem =  r"\\cabcvan1gis001\US_DEM\DEM1.shp"
spatialref = arcpy.Describe(masterlyr_dem).spatialReference
cellsize = 2.77777777777997E-04
connectionString = 'ERIS_GIS/gis295@GMTEST.glaciermedia.inc'
srGCS83 = arcpy.SpatialReference(4326)

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

arrOrderCoord =numpy.array(OrderCoord[0])
length = arrOrderCoord.shape[0]
sum_x = numpy.sum([arrOrderCoord[:,0]])
sum_y = numpy.sum(arrOrderCoord[:, 1])
pointX = sum_x/length
pointY =  sum_y/length
flowDir =  flowDirNUm(pointX,pointY)
print flowDir

arcpy.Delete_management(r'in_memory')
arcpy.SetParameterAsText(1, int(0 if numpy.isnan(flowDir) else flowDir))



