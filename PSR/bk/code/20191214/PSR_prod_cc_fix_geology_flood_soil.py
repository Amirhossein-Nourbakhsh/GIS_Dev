#-------------------------------------------------------------------------------
# Name:        Physical Setting Report
# Purpose:
#
# Author:      jliu
#
# Created:     06/10/2015
# Copyright:   (c) jliu 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import sys
sys.path = [u'C:\\Windows\\system32\\python27.zip',
 u'C:\\Python27\\ArcGIS10.3\\DLLs',
 u'C:\\Python27\\ArcGIS10.3\\lib',
 u'C:\\Python27\\ArcGIS10.3\\lib\\site-packages',
 u'C:\\Python27\\ArcGIS10.3\\lib\\plat-win',
 u'C:\\Python27\\ArcGIS10.3\\lib\\lib-tk',
 u'C:\\Users\\cchen\\AppData\\Roaming\\Python\\Python27\\site-packages',
 u'C:\\Program Files (x86)\\ArcGIS\\Desktop10.3\\site-packages',
 u'C:\\Program Files (x86)\\ArcGIS\\Desktop10.3\\bin',
 u'C:\\Program Files (x86)\\ArcGIS\\Desktop10.3\\ArcPy',
 u'C:\\Program Files (x86)\\ArcGIS\\Desktop10.3\\ArcToolBox\\Scripts',
 u'K:\\ERISReport\\ERISReport_prod\\ERISReport\\PDFToolboxes',
 r"C:\Program Files (x86)\Python2.7.7\Lib\site-packages",r"K:\PSR\python"]
import shutil, csv
import cx_Oracle,urllib, glob
import arcpy, os, numpy
from datetime import datetime
import getDirectionText
import gc, time
import traceback
from numpy import gradient
from numpy import arctan2, arctan, sqrt
import PSR_config
import json


def returnUniqueSetString_musym(tableName):
    data = arcpy.da.TableToNumPyArray(tableName, ['mukey', 'musym'])
    uniques = numpy.unique(data[data['musym']!='NOTCOM']['mukey'])
    if len(uniques) == 0:
        return ''
    else:
        myString = '('
        for item in uniques:
            myString = myString + "'" + str(item) + "', "
        myString = myString[0:-2] + ")"
        return myString

def returnUniqueSetString(tableName, fieldName):
    data = arcpy.da.TableToNumPyArray(tableName, [fieldName])
    uniques = numpy.unique(data[fieldName])
    if len(uniques) == 0:
        return ''
    else:
        myString = '('
        for item in uniques:
            myString = myString + "'" + str(item) + "', "
        myString = myString[0:-2] + ")"
        return myString


#check if an array contain the same values
def checkIfUniqueValue(myArray):
    value = myArray[0]
    for i in range(0,len(myArray)):
        if(myArray[i] != value):
            return False
    return True


def returnMapUnitAttribute(dataarray, mukey, attributeName):   #water, urban land is not in dataarray, so will return '?'
    #data = dataarray[dataarray['mukey'] == mukey][attributeName[0:10]]   #0:10 is to account for truncating of the field names in .dbf
    data = dataarray[dataarray['mukey'] == mukey][attributeName]
    if (len(data) == 0):
        return "?"
    else:
        if(checkIfUniqueValue):
            if (attributeName == 'brockdepmin' or attributeName == 'wtdepannmin'):
                if data[0] == -99:
                    return 'null'
                else:
                    return str(data[0]) + 'cm'
            return str(data[0])  #will convert to str no matter what type
        else:
            return "****ERROR****"

def returnComponentAttribute_rvindicatorY(dataarray,mukey):
    resultarray = []
    dataarray1 = dataarray[dataarray['mukey'] == mukey]
    data = dataarray1[dataarray1['majcompflag'] =='Yes']      # 'majcompfla' needs to be used for .dbf table
    comps = data[['cokey','compname','comppct_r']]
    comps_sorted = numpy.sort(numpy.unique(comps), order = 'comppct_r')[::-1]     #[::-1] gives descending order
    for comp in comps_sorted:
        horizonarray = []
        keyname = comp[1] + '('+str(comp[2])+'%)'
        horizonarray.append([keyname])

        selection = data[data['cokey']==comp[0]][['mukey','cokey','compname','comppct_r','hzname','hzdept_r','hzdepb_r','texdesc']]
        selection_sorted = numpy.sort(selection, order = 'hzdept_r')
        for item in selection_sorted:
            horizonlabel = 'horizon ' + item['hzname'] + '(' + str(item['hzdept_r']) + 'cm to '+ str(item['hzdepb_r']) + 'cm)'
            horizonTexture = item['texdesc']
            horizonarray.append([horizonlabel,horizonTexture])
        resultarray.append(horizonarray)

    return resultarray

def returnComponentAttribute(dataarray,mukey):
    resultarray = []
    dataarray1 = dataarray[dataarray['mukey'] == mukey]
    data = dataarray1[dataarray1['majcompflag'] =='Yes']      # 'majcompfla' needs to be used for .dbf table
    comps = data[['cokey','compname','comppct_r', 'rv']]
    comps_sorted = numpy.sort(numpy.unique(comps), order = 'comppct_r')[::-1]     #[::-1] gives descending order
    comps_sorted_rvYes = comps_sorted[comps_sorted['rv'] == 'Yes']     # there are only two values in 'rv' field: Yes and No
    for comp in comps_sorted_rvYes:
        horizonarray = []
        keyname = comp[1] + '('+str(comp[2])+'%)'
        horizonarray.append([keyname])

        data_rvYes = data[data['rv']== 'Yes']
        selection = data_rvYes[data_rvYes['cokey']==comp[0]][['mukey','cokey','compname','comppct_r','hzname','hzdept_r','hzdepb_r','texdesc']]
        selection_sorted = numpy.sort(selection, order = 'hzdept_r')
        for item in selection_sorted:
            horizonlabel = 'horizon ' + item['hzname'] + '(' + str(item['hzdept_r']) + 'cm to '+ str(item['hzdepb_r']) + 'cm)'
            horizonTexture = item['texdesc']
            horizonarray.append([horizonlabel,horizonTexture])
        if len(selection_sorted)> 0:
            resultarray.append(horizonarray)
        else:
            horizonarray.append(['No representative horizons available.',''])
            resultarray.append(horizonarray)

    return resultarray

def addBuffertoMxd(bufferName,thedf):    # note: buffer is a shapefile, the name doesn't contain .shp

    bufferLayer = arcpy.mapping.Layer(bufferlyrfile)
    bufferLayer.replaceDataSource(scratchfolder,"SHAPEFILE_WORKSPACE",bufferName)
    arcpy.mapping.AddLayer(thedf,bufferLayer,"Top")
    thedf.extent = bufferLayer.getSelectedExtent(False)
    thedf.scale = thedf.scale * 1.1


def addOrdergeomtoMxd(ordergeomName, thedf):
    orderGeomLayer = arcpy.mapping.Layer(orderGeomlyrfile)
    orderGeomLayer.replaceDataSource(scratchfolder,"SHAPEFILE_WORKSPACE",ordergeomName)
    arcpy.mapping.AddLayer(thedf,orderGeomLayer,"Top")

def getElevation(dataset,fields):
    pntlist={}
    with arcpy.da.SearchCursor(dataset,fields) as uc:
        for row in uc:
            pntlist[row[2]]=(row[0],row[1])
    del uc

    params={}
    params['XYs']=pntlist
    params = urllib.urlencode(params)
    inhouse_esri_geocoder = r"https://gisserverprod.glaciermedia.ca/arcgis/rest/services/GPTools_temp/pntElevation2/GPServer/pntElevation2/execute?env%3AoutSR=&env%3AprocessSR=&returnZ=false&returnM=false&f=pjson"
    f = urllib.urlopen(inhouse_esri_geocoder,params)
    results =  json.loads(f.read())
    result = eval( results['results'][0]['value'])

    check_field = arcpy.ListFields(dataset,"Elevation")
    if len(check_field)==0:
        arcpy.AddField_management(dataset, "Elevation", "DOUBLE", "12", "6", "", "", "NULLABLE", "NON_REQUIRED", "")
    with arcpy.da.UpdateCursor(dataset,["Elevation"]) as uc:
        for row in uc:
            row[0]=-999
            uc.updateRow(row)
    del uc

    with arcpy.da.UpdateCursor(dataset,['Elevation',fields[-1]]) as uc:
        for row in uc:
            if result[row[1]] !='':
                row[0]= result[row[1]]
                uc.updateRow(row)
    del row
    return dataset


templist = [427550]
for OrderIDText in templist:
    OrderIDText = str(OrderIDText)
    scratchfolder =os.path.join(r"E:\CC\luan\test1",OrderIDText)
    if not os.path.exists(scratchfolder):
        os.mkdir(scratchfolder)   # for regular .shp etc.
    scratch = arcpy.CreateFileGDB_management(scratchfolder,r"scratch.gdb")   # for tables to make Querytable
    scratch = os.path.join(scratchfolder,r"scratch.gdb")
    try:
        ################
        #parameters to change for deployment
        connectionString = PSR_config.connectionString#'ERIS_GIS/gis295@GMTEST.glaciermedia.inc'
        report_path = PSR_config.report_path#"\\cabcvan1obi002\ErisData\Reports\test\noninstant_reports"
        viewer_path = PSR_config.viewer_path#"\\CABCVAN1OBI002\ErisData\Reports\test\viewer"
        upload_link = PSR_config.upload_link#"http://CABCVAN1OBI002/ErisInt/BIPublisherPortal/Viewer.svc/"
        #production: upload_link = r"http://CABCVAN1OBI002/ErisInt/BIPublisherPortal_prod/Viewer.svc/"
        reportcheck_path = PSR_config.reportcheck_path#'\\cabcvan1obi002\ErisData\Reports\test\reportcheck'
        ##############################

##        OrderIDText = arcpy.GetParameterAsText(0)
##        scratch = arcpy.env.scratchGDB
##        scratchfolder = arcpy.env.scratchFolder
##
##    ##    gc.collect()

    ########################### LOCAL ##################################
##        OrderIDText = '790657'
##        scratchfolder =r"E:\GISData_testing\test1"   # for regular .shp etc.
##        scratch = arcpy.CreateFileGDB_management(scratchfolder,r"scratch.gdb")   # for tables to make Querytable
##        scratch = os.path.join(scratchfolder,r"scratch.gdb")
    ######################################################################
        try:
            con = cx_Oracle.connect(connectionString)
            cur = con.cursor()

            cur.execute("select order_num, address1, city, provstate from orders where order_id =" + OrderIDText)
            t = cur.fetchone()

            OrderNumText = str(t[0])
            AddressText = str(t[1])+","+str(t[2])+","+str(t[3])
            ProvStateText = str(t[3])

            cur.execute("select geometry_type, geometry, radius_type  from eris_order_geometry where order_id =" + OrderIDText)
            t = cur.fetchone()

            cur.callproc('eris_psr.ClearOrder', (OrderIDText,))

            OrderType = str(t[0])
            OrderCoord = eval(str(t[1]))
            RadiusType = str(t[2])
        finally:
            cur.close()
            con.close()


        print "--- starting " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        ##bufferDist_topo = "2 MILES"
        ##bufferDist_flood = "1 MILES"
        ##bufferDist_wetland = "1 MILES"
        ##bufferDist_geol = "1 MILES"
        ##bufferDist_soil = "0.25 MILES"
        ##bufferDist_wwells = "0.5 MILES"
        ##bufferDist_ogw = "0.5 MILES"
        ##bufferDist_Radon = "1 MILES"

        searchRadius = {}
        try:
            con = cx_Oracle.connect(connectionString)
            cur = con.cursor()

            ###cur.callproc('eris_psr.ClearOrder', (OrderIDText,))   # note: this line should be removed!

            cur.execute("select DS_OID, SEARCH_RADIUS, REPORT_SOURCE from order_radius_psr where order_id =" + str(OrderIDText))
            items = cur.fetchall()

            for t in items:
                dsoid = t[0]
                radius = t[1]
                reportsource = t[2]

                searchRadius[str(dsoid)] = float(radius)

        finally:
            cur.close()
            con.close()


        # 9334 SSURGO
        # 10683 FEMA FLOOD
        # 10684 US WETLAND
        # 10685 US GEOLOGY
        # 10688 RADON ZONE
        # 10689 INDOOR RADON
        # others:
        # 5937 PCWS
        # 8710 PWS
        # 10093 PWSV
        # 10209 WATER WELL
        # 9144 OGW  (one state source..)
        # 10061 OGW (another state source..)
        bufferDist_topo = "1 MILES"
        bufferDist_flood = str(searchRadius['10683']) + ' MILES'
        bufferDist_wetland = str(searchRadius['10684']) + ' MILES'
        bufferDist_geol = str(searchRadius['10685']) + ' MILES'
        bufferDist_soil = str(searchRadius['9334']) + ' MILES'
        #bufferDist_wwells = "0.5 MILES"
        #bufferDist_ogw = "0.5 MILES"
        bufferDist_radon = str(searchRadius['10689']) + ' MILES'    # use teh indoor radon one

        dsoid_wells = []
        dsoid_wells_maxradius = '10093'     # 10093 is a federal source, PWSV
        for key in searchRadius:
            if key not in ['9334', '10683', '10684', '10685', '10688','10689', '10695', '10696']:       #10695 is US topo, 10696 is HTMC, 10688 and 10689 are radons
                dsoid_wells.append(key)
                if (searchRadius[key] > searchRadius[dsoid_wells_maxradius]):
                    dsoid_wells_maxradius = key
                #radii_wells.append(searchRadius[key])


        connectionPath = PSR_config.connectionPath#r"E:\GISData\PSR\python"

        orderGeomlyrfile_point = PSR_config.orderGeomlyrfile_point#"E:\GISData\PSR\python\mxd\SiteMaker.lyr"
        orderGeomlyrfile_polyline = PSR_config.orderGeomlyrfile_polyline#"E:\GISData\PSR\python\mxd\orderLine.lyr"
        orderGeomlyrfile_polygon = PSR_config.orderGeomlyrfile_polygon#"E:\GISData\PSR\python\mxd\orderPoly.lyr"
        bufferlyrfile = PSR_config.bufferlyrfile#"E:\GISData\PSR\python\mxd\buffer.lyr"
        topowhitelyrfile =PSR_config.topowhitelyrfile# r"E:\GISData\PSR\python\mxd\topo_white.lyr"
        gridlyrfile = PSR_config.gridlyrfile#"E:\GISData\PSR\python\mxd\Grid_hollow.lyr"
        relieflyrfile = PSR_config.relieflyrfile#"E:\GISData\PSR\python\mxd\relief.lyr"


        masterlyr_topo = PSR_config.masterlyr_topo#"E:\GISData\Topo_USA\masterfile\CellGrid_7_5_Minute.shp"
    ##    data_topo = PSR_config.data_topo#"E:\GISData\Topo_USA\masterfile\Cell_PolygonAll.shp"
        csvfile_topo = PSR_config.csvfile_topo#"E:\GISData\Topo_USA\masterfile\All_USTopo_T_7.5_gda_results.csv"
        tifdir_topo = PSR_config.tifdir_topo#"\\cabcvan1gis001\DATA_GIS\USGS_currentTopo_Geotiff"
        data_shadedrelief = PSR_config.data_shadedrelief#"\\cabcvan1gis001\DATA_GIS\US_DEM\CellGrid_1X1Degree_NW.shp"

        data_geol = PSR_config.data_geol#'E:\GISData\Data\PSR\PSR.gdb\GEOL_DD_MERGE'
        data_flood = PSR_config.data_flood#'E:\GISData\Data\PSR\PSR.gdb\S_Fld_haz_Ar_merged'
        data_floodpanel = PSR_config.data_floodpanel#'E:\GISData\Data\PSR\PSR.gdb\S_FIRM_PAN_MERGED'
        data_wetland = PSR_config.data_wetland#'E:\GISData\Data\PSR\PSR.gdb\Merged_wetland_Final'
        eris_wells = PSR_config.eris_wells#"E:\GISData\PSR\python\mxd\ErisWellSites.lyr"   #which contains water, oil/gas wells etc.

        path_shadedrelief = PSR_config.path_shadedrelief#"\\cabcvan1gis001\DATA_GIS\US_DEM\hillshade13"
        datalyr_wetland = PSR_config.datalyr_wetland#"E:\GISData\PSR\python\mxd\wetland.lyr"
    ##    datalyr_wetlandNY = PSR_config.datalyr_wetlandNY
        datalyr_wetlandNYkml = PSR_config.datalyr_wetlandNYkml#u'E:\\GISData\\PSR\\python\\mxd\\wetlandNY_kml.lyr'
        datalyr_wetlandNYAPAkml = PSR_config.datalyr_wetlandNYAPAkml#r"E:\GISData\PSR\python\mxd\wetlandNYAPA_kml.lyr"
        datalyr_plumetacoma = PSR_config.datalyr_plumetacoma#r"E:\GISData\PSR\python\mxd\Plume.lyr"
        datalyr_flood = PSR_config.datalyr_flood#"E:\GISData\PSR\python\mxd\flood.lyr"
        datalyr_geology = PSR_config.datalyr_geology#"E:\GISData\PSR\python\mxd\geology.lyr"
        datalyr_contour = PSR_config.datalyr_contour#"E:\GISData\PSR\python\mxd\contours_largescale.lyr"

        imgdir_dem = PSR_config.imgdir_dem#"\\Cabcvan1gis001\DATA_GIS\US_DEM\DEM13"
        imgdir_demCA = PSR_config.imgdir_demCA#r"\\Cabcvan1gis001\US_DEM\DEM1"
        masterlyr_dem = PSR_config.masterlyr_dem#"\\Cabcvan1gis001\DATA_GIS\US_DEM\CellGrid_1X1Degree_NW_imagename_update.shp"
        masterlyr_demCA =PSR_config.masterlyr_demCA #r"\\Cabcvan1gis001\US_DEM\Canada_DEM_edited.shp"
        masterlyr_states = PSR_config.masterlyr_states#"E:\GISData\PSR\python\mxd\USStates.lyr"
        masterlyr_counties = PSR_config.masterlyr_counties#"E:\GISData\PSR\python\mxd\USCounties.lyr"
        masterlyr_cities = PSR_config.masterlyr_cities#"E:\GISData\PSR\python\mxd\USCities.lyr"
        masterlyr_NHTowns = PSR_config.masterlyr_NHTowns#"E:\GISData\PSR\python\mxd\NHTowns.lyr"
        masterlyr_zipcodes = PSR_config.masterlyr_zipcodes#"E:\GISData\PSR\python\mxd\USZipcodes.lyr"

        mxdfile_topo = PSR_config.mxdfile_topo#"E:\GISData\PSR\python\mxd\topo.mxd"
        mxdfile_topo_Tacoma = PSR_config.mxdfile_topo_Tacoma#"E:\GISData\PSR\python\mxd\topo.mxd"
        mxdMMfile_topo = PSR_config.mxdMMfile_topo#"E:\GISData\PSR\python\mxd\topoMM.mxd"
        mxdMMfile_topo_Tacoma = PSR_config.mxdMMfile_topo_Tacoma #r"E:\GISData\PSR\python\mxd\topoMM_tacoma.mxd"
        mxdfile_relief =  PSR_config.mxdfile_relief#"E:\GISData\PSR\python\mxd\shadedrelief.mxd"
        mxdMMfile_relief =  PSR_config.mxdMMfile_relief#"E:\GISData\PSR\python\mxd\shadedreliefMM.mxd"
        mxdfile_wetland = PSR_config.mxdfile_wetland#"E:\GISData\PSR\python\mxd\wetland.mxd"
        mxdfile_wetlandNY = PSR_config.mxdfile_wetlandNY#"E:\GISData\PSR\python\mxd\wetland.mxd"
        mxdMMfile_wetland = PSR_config.mxdMMfile_wetland#"E:\GISData\PSR\python\mxd\wetlandMM.mxd"
        mxdMMfile_wetlandNY = PSR_config.mxdMMfile_wetlandNY
        mxdfile_flood = PSR_config.mxdfile_flood#"E:\GISData\PSR\python\mxd\flood.mxd"
        mxdMMfile_flood = PSR_config.mxdMMfile_flood#"E:\GISData\PSR\python\mxd\floodMM.mxd"
        mxdfile_geol = PSR_config.mxdfile_geol#"E:\GISData\PSR\python\mxd\geology.mxd"
        mxdMMfile_geol = PSR_config.mxdMMfile_geol#"E:\GISData\PSR\python\mxd\geologyMM.mxd"
        mxdfile_soil = PSR_config.mxdfile_soil#"E:\GISData\PSR\python\mxd\soil.mxd"
        mxdMMfile_soil = PSR_config.mxdMMfile_soil#"E:\GISData\PSR\python\mxd\soilMM.mxd"
        mxdfile_wells = PSR_config.mxdfile_wells#"E:\GISData\PSR\python\mxd\wells.mxd"
        mxdMMfile_wells = PSR_config.mxdMMfile_wells#"E:\GISData\PSR\python\mxd\wellsMM.mxd"

        outputjpg_topo = os.path.join(scratchfolder, OrderNumText+'_US_TOPO.jpg')
        outputjpg_relief = os.path.join(scratchfolder, OrderNumText+'_US_RELIEF.jpg')
        outputjpg_wetland = os.path.join(scratchfolder, OrderNumText+'_US_WETL.jpg')
        outputjpg_wetlandNY = os.path.join(scratchfolder, OrderNumText+'_NY_WETL.jpg')
        outputjpg_flood = os.path.join(scratchfolder, OrderNumText+'_US_FLOOD.jpg')
        outputjpg_soil = os.path.join(scratchfolder, OrderNumText+'_US_SOIL.jpg')
        outputjpg_geol = os.path.join(scratchfolder, OrderNumText+'_US_GEOL.jpg')
        outputjpg_wells = os.path.join(scratchfolder, OrderNumText+'_US_WELLS.jpg')


        srGCS83 = PSR_config.srGCS83#arcpy.SpatialReference(os.path.join(connectionPath, r"projections\GCSNorthAmerican1983.prj"))

        arcpy.env.overwriteOutput = True
        arcpy.env.OverWriteOutput = True

        erisid = 0

        point = arcpy.Point()
        array = arcpy.Array()
        sr = arcpy.SpatialReference()
        sr.factoryCode = 4269  # requires input geometry is in 4269
        sr.XYTolerance = .00000001
        sr.scaleFactor = 2000
        sr.create()
        featureList = []
        for feature in OrderCoord:
            # For each coordinate pair, set the x,y properties and add to the Array object.
            for coordPair in feature:
                point.X = coordPair[0]
                point.Y = coordPair[1]
                sr.setDomain (point.X, point.X, point.Y, point.Y)
                array.add(point)
            if OrderType.lower()== 'point':
                feat = arcpy.Multipoint(array, sr)
            elif OrderType.lower() =='polyline':
                feat  = arcpy.Polyline(array, sr)
            else :
                feat = arcpy.Polygon(array,sr)
            array.removeAll()

            # Append to the list of Polygon objects
            featureList.append(feat)

        orderGeometry= os.path.join(scratchfolder,"orderGeometry.shp")
        arcpy.CopyFeatures_management(featureList, orderGeometry)
        del featureList
        arcpy.DefineProjection_management(orderGeometry, srGCS83)

        arcpy.AddField_management(orderGeometry, "xCentroid", "DOUBLE", 18, 11)
        arcpy.AddField_management(orderGeometry, "yCentroid", "DOUBLE", 18, 11)

        xExpression = "!SHAPE.CENTROID.X!"
        yExpression = "!SHAPE.CENTROID.Y!"

        arcpy.CalculateField_management(orderGeometry, "xCentroid", xExpression, "PYTHON_9.3")
        arcpy.CalculateField_management(orderGeometry, "yCentroid", yExpression, "PYTHON_9.3")

        arcpy.AddField_management(orderGeometry, "UTM", "TEXT", "", "", "1500", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.CalculateUTMZone_cartography(orderGeometry, "UTM")
        UT= arcpy.SearchCursor(orderGeometry)
        UTMvalue = ''
        Lat_Y = 0
        Lon_X = 0
        for row in UT:
            UTMvalue = str(row.getValue('UTM'))[41:43]
            Lat_Y = row.getValue('yCentroid')
            Lon_X = row.getValue('xCentroid')
        del UT
        if UTMvalue[0]=='0':
            UTMvalue=' '+UTMvalue[1:]
        out_coordinate_system = arcpy.SpatialReference('NAD 1983 UTM Zone %sN'%UTMvalue)#os.path.join(connectionPath+'/', r"projections/NAD1983/NAD1983UTMZone"+UTMvalue+"N.prj")


        orderGeometryPR = os.path.join(scratchfolder, "ordergeoNamePR.shp")
        arcpy.Project_management(orderGeometry, orderGeometryPR, out_coordinate_system)
        arcpy.AddField_management(orderGeometryPR, "xCenUTM", "DOUBLE", 18, 11)
        arcpy.AddField_management(orderGeometryPR, "yCenUTM", "DOUBLE", 18, 11)

        xExpression = "!SHAPE.CENTROID.X!"
        yExpression = "!SHAPE.CENTROID.Y!"

        arcpy.CalculateField_management(orderGeometryPR, "xCenUTM", xExpression, "PYTHON_9.3")
        arcpy.CalculateField_management(orderGeometryPR, "yCenUTM", yExpression, "PYTHON_9.3")


        del point
        del array



        ##in_rows = arcpy.SearchCursor(orderGeometryPR)
        ##for in_row in in_rows:
        ##    xCentroid = in_row.xCentroid
        ##    yCentroid = in_row.yCentroid
        ##del in_row
        ##del in_rows

        if OrderType.lower()== 'point':
            orderGeomlyrfile = orderGeomlyrfile_point
        elif OrderType.lower() =='polyline':
            orderGeomlyrfile = orderGeomlyrfile_polyline
        else:
            orderGeomlyrfile = orderGeomlyrfile_polygon

        spatialRef = out_coordinate_system


        # determine if needs to be multipage
        # according to Raf: will be multipage if line is over 1/4 mile, or polygon is over 1 sq miles
        # need to check the extent of the geometry
        geomExtent = arcpy.Describe(orderGeometryPR).extent
        multipage_topo = False
        multipage_relief = False
        multipage_wetland = False
        multipage_flood = False
        multipage_geology = False
        multipage_soil = False
        multipage_wells = False


        gridsize = "2 MILES"
        if geomExtent.width > 1300 or geomExtent.height > 1300:
            multipage_wetland = True
            multipage_flood = True
            multipage_geology = True
            multipage_soil = True
            multipage_topo = True
            multipage_relief = True
            multipage_topo = True
            multipage_wells = True
        if geomExtent.width > 500 or geomExtent.height > 500:
            multipage_topo = True
            multipage_relief = True
            multipage_topo = True
            multipage_wells = True

        multipage_topo = False
        multipage_relief = False
        multipage_wetland = False
        multipage_flood = False
        multipage_geology = False
        multipage_soil = False
        multipage_wells = False
        ## current Topo map, no attributes ----------------------------------------------------------------------------------
        print "--- starting Topo section " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        bufferSHP_topo = os.path.join(scratchfolder,"buffer_topo.shp")
        arcpy.Buffer_analysis(orderGeometryPR, bufferSHP_topo, bufferDist_topo)

        point = arcpy.Point()
        array = arcpy.Array()
        featureList = []

        width = arcpy.Describe(bufferSHP_topo).extent.width/2
        height = arcpy.Describe(bufferSHP_topo).extent.height/2

        if (width/height > 7/7):    #7/7 now since adjusted the frame to square
            # wider shape
            height = width/7*7
        else:
            # longer shape
            width = height/7*7
        xCentroid = (arcpy.Describe(bufferSHP_topo).extent.XMax + arcpy.Describe(bufferSHP_topo).extent.XMin)/2
        yCentroid = (arcpy.Describe(bufferSHP_topo).extent.YMax + arcpy.Describe(bufferSHP_topo).extent.YMin)/2

        if multipage_topo == True:
            width = width + 6400     #add 2 miles to each side, for multipage
            height = height + 6400   #add 2 miles to each side, for multipage

        point.X = xCentroid-width
        point.Y = yCentroid+height
        array.add(point)
        point.X = xCentroid+width
        point.Y = yCentroid+height
        array.add(point)
        point.X = xCentroid+width
        point.Y = yCentroid-height
        array.add(point)
        point.X = xCentroid-width
        point.Y = yCentroid-height
        array.add(point)
        point.X = xCentroid-width
        point.Y = yCentroid+height
        array.add(point)
        feat = arcpy.Polygon(array,spatialRef)
        array.removeAll()
        featureList.append(feat)
        clipFrame_topo = os.path.join(scratchfolder, "clipFrame_topo.shp")
        arcpy.CopyFeatures_management(featureList, clipFrame_topo)

        masterLayer_topo = arcpy.mapping.Layer(masterlyr_topo)
        arcpy.SelectLayerByLocation_management(masterLayer_topo,'intersect',clipFrame_topo)


        if(int((arcpy.GetCount_management(masterLayer_topo).getOutput(0))) ==0):

            print "NO records selected"
            masterLayer_topo = None

        else:
            cellids_selected = []
            cellsizes = []
            # loop through the relevant records, locate the selected cell IDs
            rows = arcpy.SearchCursor(masterLayer_topo)    # loop through the selected records
            for row in rows:
                cellid = str(int(row.getValue("CELL_ID")))
                cellids_selected.append(cellid)
            del row
            del rows
            masterLayer_topo = None


            infomatrix = []
            with open(csvfile_topo, "rb") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row[9] in cellids_selected:
                        pdfname = row[15].strip()

                        #for current topos, read the year from the geopdf file name
                        templist = pdfname.split("_")
                        year2use = templist[len(templist)-3][0:4]

                        if year2use[0:2] != "20":
                            print "################### Error in the year of the map!!"

                        print row[9] + " " + row[5] + "  " + row[15] + "  " + year2use
                        infomatrix.append([row[9],row[5],row[15],year2use])

            mxd_topo = arcpy.mapping.MapDocument(mxdfile_topo) if ProvStateText !='WA' else arcpy.mapping.MapDocument(mxdfile_topo_Tacoma)#mxdfile_topo_Tacoma
            df_topo = arcpy.mapping.ListDataFrames(mxd_topo,"*")[0]
            df_topo.spatialReference = spatialRef

            if multipage_topo == True:
                mxdMM_topo = arcpy.mapping.MapDocument(mxdMMfile_topo) if ProvStateText !='WA' else arcpy.mapping.MapDocument(mxdMMfile_topo_Tacoma)
                dfMM_topo = arcpy.mapping.ListDataFrames(mxdMM_topo,"*")[0]
                dfMM_topo.spatialReference = spatialRef


            topofile = topowhitelyrfile
            quadrangles =""
            for item in infomatrix:
                pdfname = item[2]
                tifname = pdfname[0:-4]   # note without .tif part
                tifname_bk = tifname
                year = item[3]
                if os.path.exists(os.path.join(tifdir_topo,tifname+ "_t.tif")):
                    if '.' in tifname:
                        tifname = tifname.replace('.','')

                    #need to make a local copy of the tif file for fast data source replacement
                    namecomps = tifname.split('_')
                    namecomps.insert(-2,year)
                    newtifname = '_'.join(namecomps)

                    shutil.copyfile(os.path.join(tifdir_topo,tifname_bk+"_t.tif"),os.path.join(scratchfolder,newtifname+'.tif'))

                    topoLayer = arcpy.mapping.Layer(topofile)
                    topoLayer.replaceDataSource(scratchfolder, "RASTER_WORKSPACE", newtifname)
                    topoLayer.name = newtifname
                    arcpy.mapping.AddLayer(df_topo, topoLayer, "BOTTOM")
                    if multipage_topo == True:
                        arcpy.mapping.AddLayer(dfMM_topo, topoLayer, "BOTTOM")

                    comps = pdfname.split('_')
                    quadname = " ".join(comps[1:len(comps)-3])+","+comps[0]

                    if quadrangles =="":
                        quadrangles = quadname
                    else:
                        quadrangles = quadrangles + "; " + quadname
                    topoLayer = None

                else:
                    print "tif file doesn't exist " + tifname
                    if not os.path.exists(tifdir_topo):
                        print "tif dir doesn't exist " + tifdir_topo
                    else:
                        print "tif dir does exist " + tifdir_topo
            if 'topoLayer' in locals():                 # possibly no topo returned. Seen one for EDR Alaska order. = True even for topoLayer = None
                del topoLayer
                addBuffertoMxd("buffer_topo",df_topo)
                addOrdergeomtoMxd("ordergeoNamePR", df_topo)

                yearTextE = arcpy.mapping.ListLayoutElements(mxd_topo, "TEXT_ELEMENT", "year")[0]
                #yearTextE.text = "Current USGS Topo (" + year+ ")"
                yearTextE.text = "Current USGS Topo"
                yearTextE.elementPositionX = 0.4959

                quadrangleTextE = arcpy.mapping.ListLayoutElements(mxd_topo, "TEXT_ELEMENT", "quadrangle")[0]
                quadrangleTextE.text = "Quadrangle(s): " + quadrangles


                sourceTextE = arcpy.mapping.ListLayoutElements(mxd_topo, "TEXT_ELEMENT", "source")[0]
                sourceTextE.text = "Source: USGS 7.5 Minute Topographic Map"

                arcpy.RefreshTOC()


                if multipage_topo == False:
                    arcpy.mapping.ExportToJPEG(mxd_topo, outputjpg_topo, "PAGE_LAYOUT")#, resolution=200, jpeg_quality=90)
                    if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                        os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                    shutil.copy(outputjpg_topo, os.path.join(report_path, 'PSRmaps', OrderNumText))

                    mxd_topo.saveACopy(os.path.join(scratchfolder,"mxd_topo.mxd"))
                    del mxd_topo
                    del df_topo

                else:     #multipage
                    gridlr = "gridlr_topo"   #gdb feature class doesn't work, could be a bug. So use .shp
                    gridlrshp = os.path.join(scratch, gridlr)
                    arcpy.GridIndexFeatures_cartography(gridlrshp, bufferSHP_topo, "", "", "", gridsize, gridsize)  #note the tool takes featureclass name only, not the full path


                    # part 1: the overview map
                    #add grid layer
                    gridLayer = arcpy.mapping.Layer(gridlyrfile)
                    gridLayer.replaceDataSource(scratch,"FILEGDB_WORKSPACE","gridlr_topo")
                    arcpy.mapping.AddLayer(df_topo,gridLayer,"Top")

                    df_topo.extent = gridLayer.getExtent()
                    df_topo.scale = df_topo.scale * 1.1

                    mxd_topo.saveACopy(os.path.join(scratchfolder, "mxd_topo.mxd"))
                    arcpy.mapping.ExportToJPEG(mxd_topo, outputjpg_topo, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                    if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                        os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                    shutil.copy(outputjpg_topo, os.path.join(report_path, 'PSRmaps', OrderNumText))
                    del mxd_topo
                    del df_topo


                    # part 2: the data driven pages
                    page = 1

                    page = int(arcpy.GetCount_management(gridlrshp).getOutput(0))  + page

                    addBuffertoMxd("buffer_topo",dfMM_topo)
                    addOrdergeomtoMxd("ordergeoNamePR", dfMM_topo)


                    gridlayerMM = arcpy.mapping.ListLayers(mxdMM_topo,"Grid" ,dfMM_topo)[0]
                    gridlayerMM.replaceDataSource(scratch, "FILEGDB_WORKSPACE","gridlr_topo")
                    arcpy.CalculateAdjacentFields_cartography(gridlrshp, "PageNumber")
                    mxdMM_topo.saveACopy(os.path.join(scratchfolder, "mxdMM_topo.mxd"))


                    for i in range(1,int(arcpy.GetCount_management(gridlrshp).getOutput(0))+1):
                        arcpy.SelectLayerByAttribute_management(gridlayerMM, "NEW_SELECTION", ' "PageNumber" =  ' + str(i))
                        dfMM_topo.extent = gridlayerMM.getSelectedExtent(True)
                        dfMM_topo.scale = dfMM_topo.scale * 1.1

                        #might want to select the quad name again
                        quadrangles_mm = ""
                        images = arcpy.mapping.ListLayers(mxdMM_topo, "*TM_geo", dfMM_topo)
                        for image in images:
                            if image.getExtent().overlaps(gridlayerMM.getSelectedExtent(True)) or image.getExtent().contains(gridlayerMM.getSelectedExtent(True)):
                                temp = image.name.split('_20')[0]    #e.g. VA_Port_Royal
                                comps = temp.split('_')
                                quadname = " ".join(comps[1:len(comps)])+","+comps[0]

                                if quadrangles_mm =="":
                                    quadrangles_mm = quadname
                                else:
                                    quadrangles_mm = quadrangles_mm + "; " + quadname

                        arcpy.SelectLayerByAttribute_management(gridlayerMM, "CLEAR_SELECTION")

                        yearTextE = arcpy.mapping.ListLayoutElements(mxdMM_topo, "TEXT_ELEMENT", "year")[0]
                        yearTextE.text = "Current USGS Topo - Page " + str(i)
                        yearTextE.elementPositionX = 0.4959


                        quadrangleTextE = arcpy.mapping.ListLayoutElements(mxdMM_topo, "TEXT_ELEMENT", "quadrangle")[0]
                        quadrangleTextE.text = "Quadrangle(s): " + quadrangles_mm


                        sourceTextE = arcpy.mapping.ListLayoutElements(mxdMM_topo, "TEXT_ELEMENT", "source")[0]
                        sourceTextE.text = "Source: USGS 7.5 Minute Topographic Map"

                        arcpy.RefreshTOC()



                        arcpy.mapping.ExportToJPEG(mxdMM_topo, outputjpg_topo[0:-4]+str(i)+".jpg", "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                        if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                            os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                        shutil.copy(outputjpg_topo[0:-4]+str(i)+".jpg", os.path.join(report_path, 'PSRmaps', OrderNumText))

                    del mxdMM_topo
                    del dfMM_topo



        # shaded relief map
        print "--- starting relief " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        mxd_relief = arcpy.mapping.MapDocument(mxdfile_relief)
        df_relief = arcpy.mapping.ListDataFrames(mxd_relief,"*")[0]
        df_relief.spatialReference = spatialRef

        point = arcpy.Point()
        array = arcpy.Array()
        featureList = []

        addBuffertoMxd("buffer_topo",df_relief)
        addOrdergeomtoMxd("ordergeoNamePR", df_relief)
        # locate and add relevant shadedrelief tiles
        width = arcpy.Describe(bufferSHP_topo).extent.width/2
        height = arcpy.Describe(bufferSHP_topo).extent.height/2

        if (width/height > 5/4.4):
            # wider shape
            height = width/5*4.4
        else:
            # longer shape
            width = height/4.4*5

        xCentroid = (arcpy.Describe(bufferSHP_topo).extent.XMax + arcpy.Describe(bufferSHP_topo).extent.XMin)/2
        yCentroid = (arcpy.Describe(bufferSHP_topo).extent.YMax + arcpy.Describe(bufferSHP_topo).extent.YMin)/2

        width = width + 6400     #add 2 miles to each side, for multipage
        height = height + 6400   #add 2 miles to each side, for multipage

        point.X = xCentroid-width
        point.Y = yCentroid+height
        array.add(point)
        point.X = xCentroid+width
        point.Y = yCentroid+height
        array.add(point)
        point.X = xCentroid+width
        point.Y = yCentroid-height
        array.add(point)
        point.X = xCentroid-width
        point.Y = yCentroid-height
        array.add(point)
        point.X = xCentroid-width
        point.Y = yCentroid+height
        array.add(point)
        feat = arcpy.Polygon(array,spatialRef)
        array.removeAll()
        featureList.append(feat)
        clipFrame_relief = os.path.join(scratchfolder, "clipFrame_relief.shp")
        arcpy.CopyFeatures_management(featureList, clipFrame_relief)


        masterLayer_relief = arcpy.mapping.Layer(masterlyr_dem)
        arcpy.SelectLayerByLocation_management(masterLayer_relief,'intersect',clipFrame_relief)
        print "after selectLayerByLocation "+time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())


        cellids_selected = []
        if(int((arcpy.GetCount_management(masterLayer_relief).getOutput(0))) ==0):

            print "NO records selected"
            masterLayer_relief = None

        else:

            cellid = ''
            # loop through the relevant records, locate the selected cell IDs
            rows = arcpy.SearchCursor(masterLayer_relief)    # loop through the selected records
            for row in rows:
                cellid = str(row.getValue("image_name")).strip()
                if cellid !='':
                    cellids_selected.append(cellid)
            del row
            del rows
            masterLayer_relief = None
            print "Before adding data sources" + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            for item in cellids_selected:
                item =item[:-4]
                reliefLayer = arcpy.mapping.Layer(relieflyrfile)
                shutil.copyfile(os.path.join(path_shadedrelief,item+'_hs.img'),os.path.join(scratchfolder,item+'_hs.img'))
                reliefLayer.replaceDataSource(scratchfolder,"RASTER_WORKSPACE",item+'_hs.img')
                reliefLayer.name = item
                arcpy.mapping.AddLayer(df_relief, reliefLayer, "BOTTOM")
                reliefLayer = None

        arcpy.RefreshActiveView()

        if multipage_relief == False:
            mxd_relief.saveACopy(os.path.join(scratchfolder,"mxd_relief.mxd"))
            arcpy.mapping.ExportToJPEG(mxd_relief, outputjpg_relief, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
            if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
            shutil.copy(outputjpg_relief, os.path.join(report_path, 'PSRmaps', OrderNumText))

            del mxd_relief
            del df_relief
        else:     #multipage
            gridlr = "gridlr_relief"   #gdb feature class doesn't work, could be a bug. So use .shp
            gridlrshp = os.path.join(scratch, gridlr)
            arcpy.GridIndexFeatures_cartography(gridlrshp, bufferSHP_topo, "", "", "", gridsize, gridsize)  #note the tool takes featureclass name only, not the full path


            # part 1: the overview map
            #add grid layer
            gridLayer = arcpy.mapping.Layer(gridlyrfile)
            gridLayer.replaceDataSource(scratch,"FILEGDB_WORKSPACE","gridlr_relief")
            arcpy.mapping.AddLayer(df_relief,gridLayer,"Top")

            df_relief.extent = gridLayer.getExtent()
            df_relief.scale = df_relief.scale * 1.1

            mxd_relief.saveACopy(os.path.join(scratchfolder, "mxd_relief.mxd"))
            arcpy.mapping.ExportToJPEG(mxd_relief, outputjpg_relief, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
            if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
            shutil.copy(outputjpg_relief, os.path.join(report_path, 'PSRmaps', OrderNumText))
            del mxd_relief
            del df_relief


            # part 2: the data driven pages
            page = 1

            page = int(arcpy.GetCount_management(gridlrshp).getOutput(0))  + page
            mxdMM_relief = arcpy.mapping.MapDocument(mxdMMfile_relief)

            dfMM_relief = arcpy.mapping.ListDataFrames(mxdMM_relief,"*")[0]
            dfMM_relief.spatialReference = spatialRef
            addBuffertoMxd("buffer_topo",dfMM_relief)
            addOrdergeomtoMxd("ordergeoNamePR", dfMM_relief)

            gridlayerMM = arcpy.mapping.ListLayers(mxdMM_relief,"Grid" ,dfMM_relief)[0]
            gridlayerMM.replaceDataSource(scratch, "FILEGDB_WORKSPACE","gridlr_relief")
            arcpy.CalculateAdjacentFields_cartography(gridlrshp, "PageNumber")
            mxdMM_relief.saveACopy(os.path.join(scratchfolder, "mxdMM_relief.mxd"))

            for item in cellids_selected:
                item =item[:-4]
                reliefLayer = arcpy.mapping.Layer(relieflyrfile)
                shutil.copyfile(os.path.join(path_shadedrelief,item+'_hs.img'),os.path.join(scratchfolder,item+'_hs.img'))   #make a local copy, will make it run faster
                reliefLayer.replaceDataSource(scratchfolder,"RASTER_WORKSPACE",item+'_hs.img')
                reliefLayer.name = item
                arcpy.mapping.AddLayer(dfMM_relief, reliefLayer, "BOTTOM")


            for i in range(1,int(arcpy.GetCount_management(gridlrshp).getOutput(0))+1):
                arcpy.SelectLayerByAttribute_management(gridlayerMM, "NEW_SELECTION", ' "PageNumber" =  ' + str(i))
                dfMM_relief.extent = gridlayerMM.getSelectedExtent(True)
                dfMM_relief.scale = dfMM_relief.scale * 1.1
                arcpy.SelectLayerByAttribute_management(gridlayerMM, "CLEAR_SELECTION")

                arcpy.mapping.ExportToJPEG(mxdMM_relief, outputjpg_relief[0:-4]+str(i)+".jpg", "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                    os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                shutil.copy(outputjpg_relief[0:-4]+str(i)+".jpg", os.path.join(report_path, 'PSRmaps', OrderNumText))
            del mxdMM_relief
            del dfMM_relief

        try:
            con = cx_Oracle.connect(connectionString)
            cur = con.cursor()
            if os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText, OrderNumText+'_US_TOPO.jpg')):
                query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'TOPO', OrderNumText+'_US_TOPO.jpg', 1))
                if multipage_topo == True:
                    for i in range(1,page):
                        query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'TOPO', OrderNumText+'_US_TOPO'+str(i)+'.jpg', i+1))

            else:
                print "No Topo map is available"

            if os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText, OrderNumText+'_US_RELIEF.jpg')):
                query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'RELIEF', OrderNumText+'_US_RELIEF.jpg', 1))
                if multipage_relief == True:
                    for i in range(1,page):
                        query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'RELIEF', OrderNumText+'_US_RELIEF'+str(i)+'.jpg', i+1))

            else:
                print "No Relief map is available"

        finally:
            cur.close()
            con.close()



        ### Wetland Map only, no attributes ---------------------------------------------------------------------------------
        print "--- starting Wetland section " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        bufferSHP_wetland = os.path.join(scratchfolder,"buffer_wetland.shp")
        arcpy.Buffer_analysis(orderGeometryPR, bufferSHP_wetland, bufferDist_wetland)

        mxd_wetland = arcpy.mapping.MapDocument(mxdfile_wetland)
        df_wetland = arcpy.mapping.ListDataFrames(mxd_wetland,"big")[0]
        df_wetland.spatialReference = spatialRef
        df_wetlandsmall = arcpy.mapping.ListDataFrames(mxd_wetland,"small")[0]
        df_wetlandsmall.spatialReference = spatialRef
        del df_wetlandsmall

        addBuffertoMxd("buffer_wetland",df_wetland)
        addOrdergeomtoMxd("ordergeoNamePR", df_wetland)


        # print the maps

        if multipage_wetland == False:
            mxd_wetland.saveACopy(os.path.join(scratchfolder, "mxd_wetland.mxd"))
            arcpy.mapping.ExportToJPEG(mxd_wetland, outputjpg_wetland, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
            if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
            shutil.copy(outputjpg_wetland, os.path.join(report_path, 'PSRmaps', OrderNumText))
            del mxd_wetland
            del df_wetland



        else:    # multipage

            gridlr = "gridlr_wetland"   #gdb feature class doesn't work, could be a bug. So use .shp
            gridlrshp = os.path.join(scratch, gridlr)
            arcpy.GridIndexFeatures_cartography(gridlrshp, bufferSHP_wetland, "", "", "", gridsize, gridsize)  #note the tool takes featureclass name only, not the full path


            # part 1: the overview map
            #add grid layer
            gridLayer = arcpy.mapping.Layer(gridlyrfile)
            gridLayer.replaceDataSource(scratch,"FILEGDB_WORKSPACE","gridlr_wetland")
            arcpy.mapping.AddLayer(df_wetland,gridLayer,"Top")

            df_wetland.extent = gridLayer.getExtent()
            df_wetland.scale = df_wetland.scale * 1.1

            mxd_wetland.saveACopy(os.path.join(scratchfolder, "mxd_wetland.mxd"))
            arcpy.mapping.ExportToJPEG(mxd_wetland, outputjpg_wetland, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
            if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
            shutil.copy(outputjpg_wetland, os.path.join(report_path, 'PSRmaps', OrderNumText))

            del mxd_wetland
            del df_wetland

            # part 2: the data driven pages
            page = 1

            page = int(arcpy.GetCount_management(gridlrshp).getOutput(0))  + page
            mxdMM_wetland = arcpy.mapping.MapDocument(mxdMMfile_wetland)

            dfMM_wetland = arcpy.mapping.ListDataFrames(mxdMM_wetland,"big")[0]
            dfMM_wetland.spatialReference = spatialRef
            addBuffertoMxd("buffer_wetland",dfMM_wetland)
            addOrdergeomtoMxd("ordergeoNamePR", dfMM_wetland)
            gridlayerMM = arcpy.mapping.ListLayers(mxdMM_wetland,"Grid" ,dfMM_wetland)[0]
            gridlayerMM.replaceDataSource(scratch, "FILEGDB_WORKSPACE","gridlr_wetland")
            arcpy.CalculateAdjacentFields_cartography(gridlrshp, "PageNumber")
            mxdMM_wetland.saveACopy(os.path.join(scratchfolder, "mxdMM_wetland.mxd"))


            for i in range(1,int(arcpy.GetCount_management(gridlrshp).getOutput(0))+1):
                arcpy.SelectLayerByAttribute_management(gridlayerMM, "NEW_SELECTION", ' "PageNumber" =  ' + str(i))
                dfMM_wetland.extent = gridlayerMM.getSelectedExtent(True)
                dfMM_wetland.scale = dfMM_wetland.scale * 1.1
                arcpy.SelectLayerByAttribute_management(gridlayerMM, "CLEAR_SELECTION")

                titleTextE = arcpy.mapping.ListLayoutElements(mxdMM_wetland, "TEXT_ELEMENT", "title")[0]
                titleTextE.text = "Wetland Type - Page " + str(i)
                titleTextE.elementPositionX = 0.468
                arcpy.RefreshTOC()

                arcpy.mapping.ExportToJPEG(mxdMM_wetland, outputjpg_wetland[0:-4]+str(i)+".jpg", "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                    os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                shutil.copy(outputjpg_wetland[0:-4]+str(i)+".jpg", os.path.join(report_path, 'PSRmaps', OrderNumText))
            del mxdMM_wetland
            del dfMM_wetland


        try:
            con = cx_Oracle.connect(connectionString)
            cur = con.cursor()

            ###cur.callproc('eris_psr.ClearOrder', (OrderIDText,))
            query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'WETLAND', OrderNumText+'_US_WETL.jpg', 1))
            if multipage_wetland == True:
                for i in range(1,page):
                    query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'WETLAND', OrderNumText+'_US_WETL'+str(i)+'.jpg', i+1))

        finally:
            cur.close()
            con.close()

    # #######################################################
        if ProvStateText =='NY':
    # ##  NY Wetland Map only, no attributes ---------------------------------------------------------------------------------
            print "--- starting NY Wetland section " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            bufferSHP_wetland = os.path.join(scratchfolder,"buffer_wetland.shp")
            #arcpy.Buffer_analysis(orderGeometryPR, bufferSHP_wetland, bufferDist_wetland)

            mxd_wetlandNY = arcpy.mapping.MapDocument(mxdfile_wetlandNY)
            df_wetlandNY = arcpy.mapping.ListDataFrames(mxd_wetlandNY,"big")[0]
            df_wetlandNY.spatialReference = spatialRef

            addBuffertoMxd("buffer_wetland",df_wetlandNY)
            addOrdergeomtoMxd("ordergeoNamePR", df_wetlandNY)


            # print the maps

            if multipage_wetland == False:
                mxd_wetlandNY.saveACopy(os.path.join(scratchfolder, "mxd_wetlandNY.mxd"))
                arcpy.mapping.ExportToJPEG(mxd_wetlandNY, outputjpg_wetlandNY, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                shutil.copy(outputjpg_wetlandNY, os.path.join(report_path, 'PSRmaps', OrderNumText))
                del mxd_wetlandNY
                del df_wetlandNY



            else:    # multipage

                gridlr = "gridlr_wetland"   #gdb feature class doesn't work, could be a bug. So use .shp
                gridlrshp = os.path.join(scratch, gridlr)
                #arcpy.GridIndexFeatures_cartography(gridlrshp, bufferSHP_wetland, "", "", "", gridsize, gridsize)  #note the tool takes featureclass name only, not the full path


                # part 1: the overview map
                #add grid layer
                gridLayer = arcpy.mapping.Layer(gridlyrfile)
                gridLayer.replaceDataSource(scratch,"FILEGDB_WORKSPACE","gridlr_wetland")
                arcpy.mapping.AddLayer(df_wetlandNY,gridLayer,"Top")

                df_wetlandNY.extent = gridLayer.getExtent()
                df_wetlandNY.scale = df_wetlandNY.scale * 1.1

                mxd_wetlandNY.saveACopy(os.path.join(scratchfolder, "mxd_wetlandNY.mxd"))
                arcpy.mapping.ExportToJPEG(mxd_wetlandNY, outputjpg_wetlandNY, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                    os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                shutil.copy(outputjpg_wetlandNY, os.path.join(report_path, 'PSRmaps', OrderNumText))

                del mxd_wetlandNY
                del df_wetlandNY

                # part 2: the data driven pages
                page = 1

                page = int(arcpy.GetCount_management(gridlrshp).getOutput(0))  + page
                mxdMM_wetlandNY = arcpy.mapping.MapDocument(mxdMMfile_wetlandNY)

                dfMM_wetlandNY = arcpy.mapping.ListDataFrames(mxdMM_wetlandNY,"big")[0]
                dfMM_wetlandNY.spatialReference = spatialRef
                addBuffertoMxd("buffer_wetland",dfMM_wetlandNY)
                addOrdergeomtoMxd("ordergeoNamePR", dfMM_wetlandNY)
                gridlayerMM = arcpy.mapping.ListLayers(mxdMM_wetlandNY,"Grid" ,dfMM_wetlandNY)[0]
                gridlayerMM.replaceDataSource(scratch, "FILEGDB_WORKSPACE","gridlr_wetland")
                arcpy.CalculateAdjacentFields_cartography(gridlrshp, "PageNumber")
                mxdMM_wetlandNY.saveACopy(os.path.join(scratchfolder, "mxdMM_wetlandNY.mxd"))


                for i in range(1,int(arcpy.GetCount_management(gridlrshp).getOutput(0))+1):
                    arcpy.SelectLayerByAttribute_management(gridlayerMM, "NEW_SELECTION", ' "PageNumber" =  ' + str(i))
                    dfMM_wetlandNY.extent = gridlayerMM.getSelectedExtent(True)
                    dfMM_wetlandNY.scale = dfMM_wetlandNY.scale * 1.1
                    arcpy.SelectLayerByAttribute_management(gridlayerMM, "CLEAR_SELECTION")

                    titleTextE = arcpy.mapping.ListLayoutElements(mxdMM_wetlandNY, "TEXT_ELEMENT", "title")[0]
                    titleTextE.text = "NY Wetland Type - Page " + str(i)
                    titleTextE.elementPositionX = 0.468
                    arcpy.RefreshTOC()

                    arcpy.mapping.ExportToJPEG(mxdMM_wetlandNY, outputjpg_wetlandNY[0:-4]+str(i)+".jpg", "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                    if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                        os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                    shutil.copy(outputjpg_wetlandNY[0:-4]+str(i)+".jpg", os.path.join(report_path, 'PSRmaps', OrderNumText))
                del mxdMM_wetlandNY
                del dfMM_wetlandNY


            try:
                con = cx_Oracle.connect(connectionString)
                cur = con.cursor()

                ###cur.callproc('eris_psr.ClearOrder', (OrderIDText,))
                query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'WETLAND', OrderNumText+'_NY_WETL.jpg', 1))
                if multipage_wetland == True:
                    for i in range(1,page):
                        query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'WETLAND', OrderNumText+'_NY_WETL'+str(i)+'.jpg', i+1))

            finally:
                cur.close()
                con.close()
    # ##############################################################################


        ### Floodplain ------------------------------------------------------------------------------------------
        print "--- starting floodplain " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

        bufferSHP_flood = os.path.join(scratchfolder,"buffer_flood.shp")
        arcpy.Buffer_analysis(orderGeometryPR, bufferSHP_flood, bufferDist_flood)
        noFlood = False
        arcpy.CheckExtension("Spatial")
        # clip a layer for attribute retrieval, and zoom to the right area on geology mxd.
        flood_clip_temp =os.path.join(scratch,'flood_temp')
        flood_clip =os.path.join(scratch,'flood')   #better keep in file geodatabase due to content length in certain columns
        arcpy.Clip_analysis(data_flood, bufferSHP_flood, flood_clip)
    ##    masterLayer_flood = arcpy.mapping.Layer(data_flood)
    ##    arcpy.SelectLayerByLocation_management(masterLayer_flood, 'intersect', bufferSHP_flood)
    ##    if int((arcpy.GetCount_management(masterLayer_flood).getOutput(0))) != 0:
    ##        arcpy.CopyFeatures_management(masterLayer_flood,flood_clip_temp)
    ##        arcpy.Generalize_edit(flood_clip_temp,"5 FEET")
    ##        arcpy.Clip_analysis(flood_clip_temp, bufferSHP_flood, flood_clip)
    ##    else:
    ##        noFlood = True
        del data_flood

        if not noFlood:
            floodpanel_clip =os.path.join(scratch,'floodpanel')   #better keep in file geodatabase due to content length in certain columns
            arcpy.Clip_analysis(data_floodpanel, bufferSHP_flood, floodpanel_clip)
            del data_floodpanel

            arcpy.Statistics_analysis(flood_clip, os.path.join(scratchfolder,"summary_flood.dbf"), [['FLD_ZONE','FIRST'], ['ZONE_SUBTY','FIRST']],'ERIS_CLASS')
            arcpy.Sort_management(os.path.join(scratchfolder,"summary_flood.dbf"), os.path.join(scratchfolder,"summary1_flood.dbf"), [["ERIS_CLASS", "ASCENDING"]])

            print "right before reading mxdfile_flood " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            mxd_flood = arcpy.mapping.MapDocument(mxdfile_flood)

            print "right before reading df_flood " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            df_flood = arcpy.mapping.ListDataFrames(mxd_flood,"Flood*")[0]
            df_flood.spatialReference = spatialRef

            print "right before reading df_floodsmall " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            df_floodsmall = arcpy.mapping.ListDataFrames(mxd_flood,"Study*")[0]
            df_floodsmall.spatialReference = spatialRef
            del df_floodsmall

            addBuffertoMxd("buffer_flood",df_flood)
            addOrdergeomtoMxd("ordergeoNamePR", df_flood)
            arcpy.RefreshActiveView();


            if multipage_flood == False:
                mxd_flood.saveACopy(os.path.join(scratchfolder, "mxd_flood.mxd"))       #<-- this line seems to take huge amount of memory, up to 1G. possibly due to df SR change
                arcpy.mapping.ExportToJPEG(mxd_flood, outputjpg_flood, "PAGE_LAYOUT", resolution=150, jpeg_quality=85)
                if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                    os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                shutil.copy(r"E:\GISData_testing\test1\20191104048_US_FLOOD.jpg", os.path.join(report_path, 'PSRmaps', OrderNumText))
                del mxd_flood
                del df_flood


            else:    # multipage

                gridlr = "gridlr_flood"   #gdb feature class doesn't work, could be a bug. So use .shp
                gridlrshp = os.path.join(scratch, gridlr)
                arcpy.GridIndexFeatures_cartography(gridlrshp, bufferSHP_flood, "", "", "", gridsize, gridsize)  #note the tool takes featureclass name only, not the full path


                # part 1: the overview map
                #add grid layer
                gridLayer = arcpy.mapping.Layer(gridlyrfile)
                gridLayer.replaceDataSource(scratch,"FILEGDB_WORKSPACE","gridlr_flood")
                arcpy.mapping.AddLayer(df_flood,gridLayer,"Top")

                df_flood.extent = gridLayer.getExtent()
                df_flood.scale = df_flood.scale * 1.1

                mxd_flood.saveACopy(os.path.join(scratchfolder, "mxd_flood.mxd"))
                arcpy.mapping.ExportToJPEG(mxd_flood, outputjpg_flood, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                    os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                shutil.copy(outputjpg_flood, os.path.join(report_path, 'PSRmaps', OrderNumText))

                del mxd_flood
                del df_flood

                # part 2: the data driven pages
                page = 1

                page = int(arcpy.GetCount_management(gridlrshp).getOutput(0))  + page
                mxdMM_flood = arcpy.mapping.MapDocument(mxdMMfile_flood)

                dfMM_flood = arcpy.mapping.ListDataFrames(mxdMM_flood,"Flood*")[0]
                dfMM_flood.spatialReference = spatialRef
                addBuffertoMxd("buffer_flood",dfMM_flood)
                addOrdergeomtoMxd("ordergeoNamePR", dfMM_flood)
                gridlayerMM = arcpy.mapping.ListLayers(mxdMM_flood,"Grid" ,dfMM_flood)[0]
                gridlayerMM.replaceDataSource(scratch, "FILEGDB_WORKSPACE","gridlr_flood")
                arcpy.CalculateAdjacentFields_cartography(gridlrshp, "PageNumber")
                mxdMM_flood.saveACopy(os.path.join(scratchfolder, "mxdMM_flood.mxd"))


                for i in range(1,int(arcpy.GetCount_management(gridlrshp).getOutput(0))+1):
                    arcpy.SelectLayerByAttribute_management(gridlayerMM, "NEW_SELECTION", ' "PageNumber" =  ' + str(i))
                    dfMM_flood.extent = gridlayerMM.getSelectedExtent(True)
                    dfMM_flood.scale = dfMM_flood.scale * 1.1
                    arcpy.SelectLayerByAttribute_management(gridlayerMM, "CLEAR_SELECTION")

                    titleTextE = arcpy.mapping.ListLayoutElements(mxdMM_flood, "TEXT_ELEMENT", "title")[0]
                    titleTextE.text = "Flood Hazard Zones - Page " + str(i)
                    titleTextE.elementPositionX = 0.5946
                    arcpy.RefreshTOC()

                    arcpy.mapping.ExportToJPEG(mxdMM_flood, outputjpg_flood[0:-4]+str(i)+".jpg", "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                    if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                        os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                    shutil.copy(outputjpg_flood[0:-4]+str(i)+".jpg", os.path.join(report_path, 'PSRmaps', OrderNumText))
                del mxdMM_flood
                del dfMM_flood


            flood_IDs=[]
            availPanels = ''
            if (int(arcpy.GetCount_management(os.path.join(scratchfolder,"summary1_flood.dbf")).getOutput(0))== 0):
                # no floodplain records selected....
                print 'No floodplain records are selected....'
                if (int(arcpy.GetCount_management(floodpanel_clip).getOutput(0))== 0):
                    # no panel available, means no data
                    print 'no panels available in the area'

                else:
                    # panel available, just not records in area
                    in_rows = arcpy.SearchCursor(floodpanel_clip)
                    for in_row in in_rows:
                        print ": " + in_row.FIRM_PAN    #panel number
                        print in_row.EFF_DATE      #effective date

                        availPanels = availPanels + in_row.FIRM_PAN+'(effective:' + str(in_row.EFF_DATE)[0:10]+') '
                    del in_row
                    del in_rows

                try:
                    con = cx_Oracle.connect(connectionString)
                    cur = con.cursor()


                    if len(availPanels) > 0:
                        erisid = erisid+1
                        print 'erisid for availPanels is ' + str(erisid)
                        cur.callproc('eris_psr.InsertOrderDetail', (OrderIDText, erisid,'10683'))
                        query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10683', 2, 'N', 1, 'Available FIRM Panels in area: ', availPanels))
                    query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'FLOOD', OrderNumText+'_US_FLOOD.jpg', 1))

                finally:
                    cur.close()
                    con.close()
            else:
                in_rows = arcpy.SearchCursor(floodpanel_clip)
                for in_row in in_rows:
                    print ": " + in_row.FIRM_PAN    #panel number
                    print in_row.EFF_DATE      #effective date
                    if in_row.FIRM_PAN ==r"48113C0155K":
                        availPanels = availPanels + in_row.FIRM_PAN+'(effective:' + str(in_row.EFF_DATE)[0:10]+') '
        #        del in_row
                del in_rows

                try:
                    con = cx_Oracle.connect(connectionString)
                    cur = con.cursor()
                    flood_IDs =[]
                    ###cur.callproc('eris_psr.ClearOrder', (OrderIDText,))
                    in_rows = arcpy.SearchCursor(os.path.join(scratchfolder,"summary1_flood.dbf"))
                    erisid = erisid + 1
                    cur.callproc('eris_psr.InsertOrderDetail', (OrderIDText, erisid,'10683'))
                    query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10683', 2, 'N', 1, 'Available FIRM Panels in area: ', availPanels))
                    for in_row in in_rows:
                        # note the column changed in summary dbf
                        print ": " + in_row.ERIS_CLASS    #eris label
                        print in_row.FIRST_FLD_      #zone type
                        print in_row.FIRST_ZONE   #subtype

                        erisid = erisid + 1
                        flood_IDs.append([in_row.ERIS_CLASS,erisid])
                        ###cur.callproc('eris_psr.ClearOrder', (OrderIDText,))
                        cur.callproc('eris_psr.InsertOrderDetail', (OrderIDText, erisid,'10683'))
                        query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10683', 2, 'S1', 1, "Flood Zone " + in_row.ERIS_CLASS, ''))
                        query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10683', 2, 'N', 2, 'Zone: ', in_row.FIRST_FLD_))
                        query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10683', 2, 'N', 3, 'Zone subtype: ', in_row.FIRST_ZONE))

                        #query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10683', 2, 'N', 2, 'Zone tye: ', in_row.FIRST_FLD_))
                        #query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10683', 2, 'N', 3, 'Zone Subtype: ', in_row.FIRST_ZONE))

                    del in_row
                    del in_rows

                    query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'FLOOD', OrderNumText+'_US_FLOOD.jpg', 1))
                    if multipage_flood == True:
                        for i in range(1,page):
                            query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'FLOOD', OrderNumText+'_US_FLOOD'+str(i)+'.jpg', i+1))

                    #result = cur.callfunc('eris_psr.CreateReport', str, (OrderIDText,))

                finally:
                    cur.close()
                    con.close()


        ### GEOLOGY REPORT ------------------------------------------------------------------------------
        print "--- starting geology " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        bufferSHP_geol = os.path.join(scratchfolder,"buffer_geol.shp")
        arcpy.Buffer_analysis(orderGeometryPR, bufferSHP_geol, bufferDist_geol)


        # clip a layer for attribute retrieval, and zoom to the right area on geology mxd.
        geol_clip_temp =os.path.join(scratch,'geology_temp')   #better keep in file geodatabase due to content length in certain columns
        geol_clip =os.path.join(scratch,'geology')
        #arcpy.Clip_analysis(data_geol, bufferSHP_geol, geol_clip)

        masterLayer_geol = arcpy.mapping.Layer(data_geol)
        arcpy.SelectLayerByLocation_management(masterLayer_geol, 'intersect', bufferSHP_geol)
        if int((arcpy.GetCount_management(masterLayer_geol).getOutput(0))) != 0:
            arcpy.CopyFeatures_management(masterLayer_geol,geol_clip_temp)
            arcpy.Generalize_edit(geol_clip_temp,"40 FEET")
        arcpy.Clip_analysis(geol_clip_temp, bufferSHP_geol, geol_clip)
        arcpy.Statistics_analysis(geol_clip, os.path.join(scratch,"summary_geol"), [['UNIT_NAME','FIRST'], ['UNIT_AGE','FIRST'], ['ROCKTYPE1','FIRST'], ['ROCKTYPE2','FIRST'], ['UNITDESC','FIRST'], ['ERIS_KEY_1','FIRST']],'ORIG_LABEL')
        arcpy.Sort_management(os.path.join(scratch,"summary_geol"), os.path.join(scratch,"summary1_geol"), [["ORIG_LABEL", "ASCENDING"]])


        mxd_geol = arcpy.mapping.MapDocument(mxdfile_geol)
        df_geol = arcpy.mapping.ListDataFrames(mxd_geol,"*")[0]
        df_geol.spatialReference = spatialRef


        addBuffertoMxd("buffer_geol",df_geol)
        addOrdergeomtoMxd("ordergeoNamePR", df_geol)


        # print the maps

        if multipage_geology == False:
            #df.scale = 5000
            mxd_geol.saveACopy(os.path.join(scratchfolder, "mxd_geol.mxd"))
            arcpy.mapping.ExportToJPEG(mxd_geol, outputjpg_geol, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
            if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
            shutil.copy(outputjpg_geol, os.path.join(report_path, 'PSRmaps', OrderNumText))
            del mxd_geol
            del df_geol

        else:    # multipage

            gridlr = "gridlr_geol"   #gdb feature class doesn't work, could be a bug. So use .shp
            gridlrshp = os.path.join(scratch, gridlr)
            arcpy.GridIndexFeatures_cartography(gridlrshp, bufferSHP_geol, "", "", "", gridsize, gridsize)  #note the tool takes featureclass name only, not the full path


            # part 1: the overview map
            #add grid layer
            gridLayer = arcpy.mapping.Layer(gridlyrfile)
            gridLayer.replaceDataSource(scratch,"FILEGDB_WORKSPACE","gridlr_geol")
            arcpy.mapping.AddLayer(df_geol,gridLayer,"Top")

            df_geol.extent = gridLayer.getExtent()
            df_geol.scale = df_geol.scale * 1.1

            mxd_geol.saveACopy(os.path.join(scratchfolder, "mxd_geol.mxd"))
            arcpy.mapping.ExportToJPEG(mxd_geol, outputjpg_geol, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
            if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
            shutil.copy(outputjpg_geol, os.path.join(report_path, 'PSRmaps', OrderNumText))

            del mxd_geol
            del df_geol

            # part 2: the data driven pages
            page = 1

            page = int(arcpy.GetCount_management(gridlrshp).getOutput(0))  + page
            mxdMM_geol = arcpy.mapping.MapDocument(mxdMMfile_geol)

            dfMM_geol = arcpy.mapping.ListDataFrames(mxdMM_geol,"*")[0]
            dfMM_geol.spatialReference = spatialRef
            addBuffertoMxd("buffer_geol",dfMM_geol)
            addOrdergeomtoMxd("ordergeoNamePR", dfMM_geol)

            gridlayerMM = arcpy.mapping.ListLayers(mxdMM_geol,"Grid" ,dfMM_geol)[0]
            gridlayerMM.replaceDataSource(scratch, "FILEGDB_WORKSPACE","gridlr_geol")
            arcpy.CalculateAdjacentFields_cartography(gridlrshp, "PageNumber")
            mxdMM_geol.saveACopy(os.path.join(scratchfolder, "mxdMM_geol.mxd"))

            for i in range(1,int(arcpy.GetCount_management(gridlrshp).getOutput(0))+1):
                arcpy.SelectLayerByAttribute_management(gridlayerMM, "NEW_SELECTION", ' "PageNumber" =  ' + str(i))
                dfMM_geol.extent = gridlayerMM.getSelectedExtent(True)
                dfMM_geol.scale = dfMM_geol.scale * 1.1
                arcpy.SelectLayerByAttribute_management(gridlayerMM, "CLEAR_SELECTION")

                titleTextE = arcpy.mapping.ListLayoutElements(mxdMM_geol, "TEXT_ELEMENT", "title")[0]
                titleTextE.text = "Geologic Units - Page " + str(i)
                titleTextE.elementPositionX = 0.6303
                arcpy.RefreshTOC()


                arcpy.mapping.ExportToJPEG(mxdMM_geol, outputjpg_geol[0:-4]+str(i)+".jpg", "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                    os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                shutil.copy(outputjpg_geol[0:-4]+str(i)+".jpg", os.path.join(report_path, 'PSRmaps', OrderNumText))
            del mxdMM_geol
            del dfMM_geol




        if (int(arcpy.GetCount_management(os.path.join(scratch,"summary1_geol")).getOutput(0))== 0):
            # no geology polygon selected...., need to send in map only
            print 'No geology polygon is selected....'
            try:
                con = cx_Oracle.connect(connectionString)
                cur = con.cursor()

                query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'GEOL', OrderNumText+'_US_GEOL.jpg', 1))          #note type 'SOIL' or 'GEOL' is used internally

            finally:
                cur.close()
                con.close()
        else:
            try:
                con = cx_Oracle.connect(connectionString)
                cur = con.cursor()
                geology_IDs = []
                ###cur.callproc('eris_psr.ClearOrder', (OrderIDText,))
                in_rows = arcpy.SearchCursor(os.path.join(scratch,"summary1_geol"))
                for in_row in in_rows:
                    # note the column changed in summary dbf
    ##                print "Unit label is: " + in_row.ORIG_LABEL
    ##                print in_row.FIRST_UNIT     # unit name
    ##                print in_row.FIRST_UN_1     # unit age
    ##                print in_row.FIRST_ROCK     # rocktype 1
    ##                print in_row.FIRST_RO_1     # rocktype2
    ##                print in_row.FIRST_UN_2     # unit description
    ##                print in_row.FIRST_ERIS     # eris key created from upper(unit_link)
                    erisid = erisid + 1
                    geology_IDs.append([in_row.FIRST_ERIS_KEY_1,erisid])
                    cur.callproc('eris_psr.InsertOrderDetail', (OrderIDText, erisid,'10685'))
                    query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'S1', 1, 'Geologic Unit ' + in_row.ORIG_LABEL, ''))
                    query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 2, 'Unit Name: ', in_row.FIRST_UNIT_NAME))
                    query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 3, 'Unit Age: ', in_row.FIRST_UNIT_AGE))
                    query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 4, 'Primary Rock Type: ', in_row.FIRST_ROCKTYPE1))
                    query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 5, 'Secondary Rock Type: ', in_row.FIRST_ROCKTYPE2))
                    try:
                        print in_row.FIRST_UNITDESC
                        query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', in_row.FIRST_UNITDESC))
                    except UnicodeEncodeError:
                        if in_row.ORIG_LABEL =='Kml':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Sand, quartz, massive to crudely bedded, typically coarsens upward, interbedded with thin clay beds. Glauconite and feldspar are minor sand constituents. Muscovite and biotite are abundant near the base. Lower part of formation is a fine- to medium-grained, clayey, dark-gray, glauconitic (maximum 25 percent) quartz sand. Typically weathers to white or light yellow and locally stained orange brown by iron oxides. Small pebbles scattered throughout, especially in the west-central area. Locally, has small, rounded siderite concretions in the interbedded clay-sand sequence. Granules and gravel are abundant in the upper 1.5 m (5 ft). Upper beds are light gray and weather light brown to reddish brown. The Mount Laurel is 10 m (33 ft) thick from the Roosevelt quadrangle to the Runnemede quadrangle in the central sheet. Thickness varies in the northern part of the map area due, in part, to extensive interfingering of this formation with the underlying Wenonah Formation. Weller (1907) and Kmmel (1940) recognized only about 1.5 m (5 ft) of the Mount Laurel in the north. In this report those beds are assigned to the overlying Navesink Formation. The interbedded sequence, the major facies in the north, ranges to about 4.5 m (15 ft) thick. These interbeds have well-developed large burrows (Martino and Curran, 1990), mainly Ophiomorpha nodosa, and less commonly Rosselia socialis. The Mount Laurel is gradational into the underlying Wenonah Formation. A transition zone of 1.5 m (5 ft) is marked by an increase in clay, silt, and mica into the Wenonah, especially in the west-central area of the central sheet. The oyster Agerostrea falcata occurs in the lower part of the formation. Exogyra cancellata and Belemnitella americana are abundant in upper beds in the west-central area of the central sheet (New Egypt quadrangle). The Mount Laurel Formation is of late Campanian age based on the assignment of Zone CC 22b to the formation by Sugarman and others (1995) and the occurrence of Exogyra cancellata near Mullica Hill, Gloucester County.'))
                        elif in_row.ORIG_LABEL =='Tht':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Sand, glauconite, fine- to medium-grained, locally clayey, massive, dark-gray to dusky-green; weathers dusky yellow or red brown, extensively bioturbated, locally has a small amount of quartz at base. Glauconite grains are typically dark green and have botryoidal shapes. The Hornerstown weathers readily to iron oxide because of its high glauconite content. The Hornerstown in most areas is nearly pure glauconite greensand. The Hornerstown crops out in a narrow belt throughout most of the western outcrop area. In the northern part of the central sheet, it is extensively dissected and occurs as several outliers. Throughout its outcrop belt in the central sheet, the Hornerstown unconformably overlies several formations: the Tinton Formation in the extreme northern area; the Red Bank Formation in the northwestern and west-central areas; and the Navesink Formation in the west-central and southern areas. In the southern sheet, it unconformably overlies the Mount Laurel Formation. The unconformable basal contact locally contains a bed of reworked phosphatic vertebrate and invertebrate fossils. For the most part, however, the basal contact is characterized by an intensely bioturbated zone in which many burrows filled with bright green glauconite sand from the Hornerstown Formation project down into the dark-gray matrix of the underlying Navesink Formation. In a few exposures, a thin layer of medium- to coarse-grained quartz sand separates the Hornerstown from the underlying unit. The Hornerstown is 1.5 to 7 m (5-23 ft) thick. A Cretaceous age was assigned to this unit by Koch and Olsson (1977) based, in part, on a vertebrate fauna found at Sewell, Gloucester County. However, early Paleocene calcareous nannofossil Zones NP 2-4 were found in a core at Allaire State Park, Monmouth County. This is the only locality in New Jersey where Zone NP 2 was observed; otherwise, the Hornerstown is confined to Zones NP 3 and NP 4. Lowermost Paleocene Zone NP 1 was not identified, and it is thought that the Cretaceous-Tertiary boundary in New Jersey may be unconformable. A complete Cretaceous-Tertiary boundary section was recovered at the Bass River borehole (ODP Leg 174AX). It contained the uppermost Maastrichtian calcareous nannofossil Micula prinsii Zone below a spherule layer and the basal Danian planktonic foraminiferal Guembeletria cretacea P0 Zone just above the layer (Olsson and others, 1997).'))
                        elif in_row.ORIG_LABEL =='Tkl':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Sand and clay. Upper sand facies: sand, typically fine- to medium-grained, massive to thick-bedded, locally crossbedded, light-yellow to white, locally very micaceous and extensively stained by iron oxides in near-surface beds. The thick-bedded strata commonly consist of interbedded fine-grained, micaceous sand and gravelly, coarse- to fine-grained sand. Some beds are intensely burrowed. Trough crossbedded strata with high concentrations of ilmenite and a few burrows are most commonly seen in the Lakewood quadrangle. Lower clay facies: clay and clay-silt, massive to thin-bedded, dark-gray, micaceous, contains wood fragments, flattened lignitized twigs, and other plant debris. Locally, the clay has irregularly shaped sand pockets, which may represent some type of burrow. In the least weathered beds, the sand of the upper sand facies is principally quartz and muscovite with lesser amounts of feldspar. The light-mineral fraction of the dark-colored clay has significantly more feldspar (10-15 percent) and rock fragments (10-15 percent) than the upper sand facies, where the feldspar was probably leached during weathering. The basal beds have a reworked zone 0.3 to 1.2 m (1-4 ft) thick that contains fine- to very coarse grained sand and, locally, gravel. These beds are very glauconitic and less commonly contain wood fragments. Reworked zones are present throughout the lower member. The lower member consists of a lower finegrained, clayey, dark-colored, micaceous sand (transgressive) and an upper massive or thick-bedded to crossbedded, light-colored sand (regressive). The lower, dark clayey unit was formerly called the Asbury Park Member. The clay-silt was previously called the Asbury Clay by K?mmel and Knapp (1904). The upper sand facies has been observed only in pits and roadcuts. It is poorly exposed because of its sandy nature. In the central sheet, the lower clay facies is exposed in pits north of Farmingdale, Monmouth County; in a few cuts along the Manasquan River, north of Farmingdale; and along the Shark River, northeast of Farmingdale. In the southern sheet, the lower clay facies is exposed only where the Coastal Plain was deeply entrenched and stripped away. In the southwesternmost part of the southern sheet, for example, the Cohansey Formation and much of the upper sand facies were stripped away by successive entrenchments of the Delaware River. On the central sheet, the lower member ranges in thickness from 20 to 30 m (66-98 ft) along strike, but thickens to over 60 m (197 ft) to the southeast. On the southern sheet, the unit ranges in thickness from 15 to 25 m (49-82 ft). The age of the lower member is based on the presence of the diatom Actinoptychus heliopelta, which was recovered from an exposure southwest of Farmingdale near Oak Glen, Monmouth County (Goldstein, 1974). This diatom places the lower member in the lower part of the ECDZ 1 of Andrews (1987), indicative of an early Miocene (Burdigalian) age (Andrews, 1988). Sugarman and others (1993) report strontium-isotope ages of 22.6 to 20.8 Ma, thereby extending the age of the unit to Aquitanian.'))
                        elif in_row.ORIG_LABEL =='Obl':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Beekmantown Group, Lower Part(Clarke and Schuchert, 1899) - Very thin to thick-bedded, interbedded dolomite and minor limestone. Upper beds are light-olive-gray to dark-gray, fine- to medium-grained, thin- to thick-bedded dolomite. Middle part is olivegray-, light-brown-, or dark-yellowish-orange- weathering, dark-gray, aphanitic to fine-grained, laminated to medium-bedded dolomite and light-gray to light-bluish-gray-weathering, medium-dark- to dark-gray, fine-grained, thin- to medium-bedded limestone, that is characterized by mottling with reticulate dolomite and light-olive-gray to grayish-orange, dolomitic shale laminae surrounding limestone lenses. Limestone grades laterally and down section into medium- gray, fine-grained dolomite. Lower beds consist of medium-light- to dark-gray, aphanitic to coarse-grained, laminated to medium-bedded, locally slightly fetid dolomite having thin black chert beds, quartz-sand laminae, and oolites. Lenses of light-gray, very coarse to coarse-grained dolomite and floating quartz sand grains and quartz-sand stringers at base of sequence. Lower contact placed at top of distinctive medium-gray quartzite. Contains conodonts of Cordylodus proavus to Rossodus manitouensis zones of North American Midcontinent province as used by Sweet and Bergstrom (1986). Unit Obl forms Stonehenge Formation of Drake and Lyttle (1985) and Drake and others (1985), upper and middle beds are included in Epler Formation, and lower beds are in Rickenbach Dolomite of Markewicz and Dalton (1977). Unit is about 183 m (600 ft) thick.'))
                        elif in_row.ORIG_LABEL =='OCa':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Not available'))
                        elif in_row.ORIG_LABEL =='Obu':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Beekmantown Group, Upper Part(Clarke and Schuchert, 1899) - Locally preserved upper beds are light- to medium-gray- to yellowish-gray-weathering, medium-light- to medium-gray, aphanitic to medium-grained, thin- to thick-bedded, locally laminated, slightly fetid dolomite. Medium-dark to dark-gray, fine-grained, medium-bedded, sparsely fossiliferous limestone lenses occur locally. Lower beds are medium-dark- to dark-gray, medium- to coarse-grained, mottled surface weathering, medium- to thick-bedded, strongly fetid dolomite that contains pods and lenses of dark-gray to black chert. Cauliflower-textured black chert beds of variable thickness occur locally. Gradational lower contact is placed at top of laminated to thin-bedded dolomite of the lower part (Obl) of the Beekmantown Group. Contains conodonts high in the Rossodus manitouensis zone to low zone D of the North American midcontinent province as used by Sweet and Bergstrom (1986). Upper beds are included in Epler Formation; lower beds are included in Rickenbach Dolomite of Drake and Lyttle (1985) and Drake and others (1985); entire upper part (Obu) is Ontelaunee Formation of Markewicz and Dalton (1977). Thickness ranges from 0 to 244 m (0-800 ft).'))
                        elif in_row.ORIG_LABEL =='Oj':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Jacksonburg Limestone(Kummel, 1908; Miller, 1937) - Upper part is medium- to dark-gray, laminated to thin-bedded shaly limestone and less abundant medium-gray arenaceous limestone containing quartz-sand lenses. Upper part thin to absent to northeast. Lower part is interbedded medium- to dark-gray, fine- to medium-grained, very thin to medium-bedded fossiliferous limestone and minor medium- to thick-bedded dolomite-cobble conglomerate having a limestone matrix. Unconformable on Beekmantown Group and conformable on the discontinuous sequence at Wantage in the Paulins Kill area. Contains conodonts of North American midcontinent province from Phragmodus undatus to Aphelognathus shatzeri zones of Sweet and Bergstrom (1986). Thickness ranges from 41 to 244m (135-800 ft). Jacksonburg Limestone (K?mmel, 1908; Miller, 1937) - Upper part is medium- to dark-gray, laminated to thin-bedded shaly limestone and less abundant medium-gray arenaceous limestone containing quartz-sand lenses. Upper part thin to absent to northeast. Lower part is interbedded medium- to dark-gray, fine- to medium-grained, very thin to medium-bedded fossiliferous limestone and minor medium- to thick-bedded dolomite-cobble conglomerate having a limestone matrix. Unconformable on Beekmantown Group and conformable on the discontinuous sequence at Wantage in the Paulins Kill area. Contains conodonts of North American midcontinent province from Phragmodus undatus to Aphelognathus shatzeri zones of Sweet and Bergstrom (1986). Thickness ranges from 41 to 244m (135-800 ft).'))
                        elif in_row.ORIG_LABEL =='Omb':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Bushkill Member(Drake and Epstein, 1967) - Interbedded medium- to dark gray, thinly laminated to thick-bedded shale and slate and less abundant medium-gray to brownish-gray, laminated to thin-bedded siltstone. To the southwest, fine-grained, thin dolomite lenses occur near base. Complete turbidite sequences (Bouma, 1962) occur locally, but basal cutout sequences (Tbcde, Tcde or Tde) dominate. Conformable lower contact is placed at top of highest shaly limestone; elsewhere, lower contact is commonly strain slipped. Correlates with graptolite Climacograptus bicornis to Corynoides americanus zones of Riva (1969, 1974) (Parris and Cruikshank, 1992). Thickness ranges from 1,250 m (4,100 ft) in Delaware River Valley to 457 m (1,500 ft) at New York State line.'))
                        elif in_row.ORIG_LABEL =='Kmt':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Sand, quartz and glauconite, fine- to medium-grained, silty and clayey, massive, dark-gray; weathers light brown or pale red, extensively bioturbated. Very glauconitic in basal few meters; glauconite concentration decreases upward so that in upper part of unit, quartz and glauconite are nearly equal. Feldspar, mica, pyrite, and phosphatic fragments are minor sand constituents. Locally, very micaceous (mostly green chlorite) with sparse carbonized wood fragments. Fine-grained pyrite abundant throughout formation. Local thin, pebbly zones with large fossil impressions occur in the middle of the formation. In the upper part of the formation, quartz increases to about 40 percent. Unit crops out in a narrow belt throughout the map area and forms isolated outliers in the central sheet. Best exposures are along Crosswicks Creek in the Allentown quadrangle. In the southern sheet, the Marshalltown underlies a narrow belt in the uplands and broadens to the southwest. Many Marshalltown exposures occur along Oldmans Creek and its tributaries near Auburn, Gloucester County. The contact with the underlying Englishtown Formation is sharp and unconformable. The basal few centimeters of the Marshalltown contain siderite concentrations, clay balls, and wood fragments reworked from the underlying Englishtown. Many burrows, some filled with glauconite, project downward into the Englishtown for about one meter (3 ft) giving a spotted appearance to the upper part of the Englishtown (Owens and others, 1970). The Marshalltown is the basal transgressive unit of a sedimentation cycle that includes the regressive deposits of the overlying Wenonah and Mount Laurel Formations resembling the overlying Red Bank Formation to Navesink Formation cycle in its asymmetry. Within the map area, only a few long-ranging megafossils occur in the Moorestown quadrangle (Richards, 1967). To the south, in the type area, Weller (1907) reported diverse molluskan assemblages indicating a Campanian age. More importantly, Olsson (1964) reported the late Campanian foraminifera Globotruncana calcarata Cushman from the upper part of the formation. No G. calcarata were found during our investigations. Wolfe (1976) assigned the pollen assemblage of the Marshalltown to the CA5A Zone considered to be Campanian. The Marshalltown has most recently been assigned to Zone CC 20-21 (Sugarman and others, 1995) of middle and late Campanian age (Perch-Nielsen, 1985).'))
                        elif in_row.ORIG_LABEL =='Kw':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Sand, quartz and mica, fine-grained, silty and clayey, massive to thick-bedded, dark-gray to medium-gray; weathers light brown to white, extensively bioturbated, very micaceous, locally contains high concentrations of sand-sized lignitized wood and has large burrows of Ophiomorpha nodosa. Feldspar (5-10 percent) is a minor sand constituent. Unit crops out in a narrow belt from Sandy Hook Bay on the central sheet and pinches out southwest of Oldmans Creek, Salem County, on the southern sheet. Isolated outliers of the Wenonah are detached from the main belt in the central sheet area. Thickness is about 10 m (33 ft) in the northern part of the central sheet, 20 m (66 ft) in the southwestern part of the central sheet, and 7.5 m (25 ft) in the southern sheet. The Wenonah is gradational into the underlying Marshalltown Formation. A transition zone of several meters is marked by a decrease in mica and an increase in glauconite sand into the Marshalltown. Fossil casts are abundant in the Wenonah. Weller (1907) reported Flemingostrea subpatulata Hop Brook in the Marlboro quadrangle indicating a late Campanian age. Wolfe (1976) placed the Wenonah microflora in his CA5A assemblage, considered to be of late Campanian age. Kennedy and Cobban (1994) identified ammonites including Baculites cf. B. scotti, Didymoceras n. sp., Menuites portlocki, Nostoceras (Nostoceras) puzosiforme n. sp., Nostoceras (Nostoceras) aff. N. colubriformus, Parasolenoceras sp., Placenticeras placenta, P. minor n. sp., and Trachyscaphites pulcherrimus. The presence of M. portlocki and T. pulcherrimus indicates late, but not latest, Campanian.'))
                        elif in_row.ORIG_LABEL =='Kns':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Sand, quartz, massive to crudely bedded, typically coarsens upward, interbedded with thin clay beds. Glauconite and feldspar are minor sand constituents. Muscovite and biotite are abundant near the base. Lower part of formation is a fine- to medium-grained, clayey, dark-gray, glauconitic (maximum 25 percent) quartz sand. Typically weathers to white or light yellow and locally stained orange brown by iron oxides. Small pebbles scattered throughout, especially in the west-central area. Locally, has small, rounded siderite concretions in the interbedded clay-sand sequence. Granules and gravel are abundant in the upper 1.5 m (5 ft). Upper beds are light gray and weather light brown to reddish brown. The Mount Laurel is 10 m (33 ft) thick from the Roosevelt quadrangle to the Runnemede quadrangle in the central sheet. Thickness varies in the northern part of the map area due, in part, to extensive interfingering of this formation with the underlying Wenonah Formation. Weller (1907) and K?mmel (1940) recognized only about 1.5 m (5 ft) of the Mount Laurel in the north. In this report those beds are assigned to the overlying Navesink Formation. The interbedded sequence, the major facies in the north, ranges to about 4.5 m (15 ft) thick. These interbeds have well-developed large burrows (Martino and Curran, 1990), mainly Ophiomorpha nodosa, and less commonly Rosselia socialis. The Mount Laurel is gradational into the underlying Wenonah Formation. A transition zone of 1.5 m (5 ft) is marked by an increase in clay, silt, and mica into the Wenonah, especially in the west-central area of the central sheet. The oyster Agerostrea falcata occurs in the lower part of the formation. Exogyra cancellata and Belemnitella americana are abundant in upper beds in the west-central area of the central sheet (New Egypt quadrangle). The Mount Laurel Formation is of late Campanian age based on the assignment of Zone CC 22b to the formation by Sugarman and others (1995) and the occurrence of Exogyra cancellata near Mullica Hill, Gloucester County.'))
                        elif in_row.ORIG_LABEL =='Ket':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Sand, quartz, fine- to coarsegrained, gravelly, massive, bioturbated, medium- to dark-gray; weathers light brown, yellow, or reddish brown, locally interbedded with thin to thick beds of dark clay. Abundant carbonaceous matter, with large lignitized logs occur locally, especially in clay strata. Feldspar, glauconite, and muscovite are minor sand constituents. Sand is extensively trough crossbedded particularly west of Mount Holly, Burlington County. In a few places in the western outcrop belt, trace fossils are abundant, typically the burrow Ophiomorpha nodosa. Unit is pyritic, especially in the carbonaceous-rich beds where pyrite is finely disseminated grains or pyritic masses as much as 0.6 m (2 ft) in diameter. Lowest part of unit is a massive sand that contains small to large, soft, light-gray siderite concretions. The Englishtown underlies a broad belt throughout the map area and ranges from about 45 m (148 ft) thick in the northern part of the central sheet to 30 m (98 ft) thick in the western part of the central sheet to 15 m (49 ft) in the southern sheet. Best exposures occur along Crosswicks Creek in the Allentown quadrangle and along Oldmans Creek. The basal contact with the underlying Woodbury Formation or Merchantville Formation is transitional over several meters. The age of the Englishtown in outcrop could not be determined directly but was inferred from stratigraphic position and pollen content. Wolfe (1976) designated the microflora of the unit as Zone CA4 and assigned it to the lower Campanian.'))
                        elif in_row.ORIG_LABEL =='Dkec':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"Kanouse Sandstone (Kummel, 1908) - Medium-gray, light-brown, and grayish-red, fine- to coarse-grained, thin- to thick-bedded sparsely fossiliferous sandstone and pebble conglomerate. Basal conglomerate beds are interbedded with siltstone similar to the upper part of the Esopus Formation and contain well-sorted, subangular to subrounded, gray and white quartz pebbles less than 1 cm (0.4 in.) long. Lower contact gradational. About 14 m (46 ft) thick. Esopus Formation - (Vanuxem, 1842; Boucot, 1959) - Light- to dark-gray, laminated to thin-bedded siltstone interbedded with dark-gray to black mudstone, dusky-blue sandstone and siltstone, and yellowish-gray fossiliferous siltstone and sandstone. Lower contact probably conformable with the Connelly Conglomerate. The formation is about 100 m (330 ft) thick at Greenwood Lake and estimated at 55 m (180 ft) thick in Longwood Valley. Connelly Conglomerate (Chadwick, 1908) - Grayish-orange weathering, very light gray to yellowish-gray, thin-bedded quartz-pebble conglomerate. Quartz pebbles average 1 to 2 cm (0.4-0.8 in.), are subrounded to well rounded, and well sorted. The unit unconformably overlies the Berkshire Valley Formation. About 11 m (36 ft) thick."))
                        elif in_row.ORIG_LABEL =='Sg':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"(Rogers, 1836) - Medium- to coarse-grained quartz-pebble conglomerate, quartzitic arkose and orthoquartzite, and thin- to thick-bedded reddish-brown siltstone. Grades downward into gray, very dark-red, or grayish-purple, medium- to coarse-grained, thin- to very thick bedded pebble to cobble conglomerate containing clasts of red shale, siltstone, and chert; yellowish-gray sandstone and chert; dark-gray shale and chert; and white-gray and pink milky quartz. Quartz cobbles are as long as 10 cm (4 in.), and rare red shale clasts as much as 46 cm (18 in.) across. Milky quartz pebbles average 2.5 cm (1 in.) in length. Red arkosic quartz-pebble conglomerate and quartzite are more abundant than gray and grayish-green quartzite. Unconformably overlies Martinsburg Formation, Allentown Dolomite, Leithsville Formation, or Proterozoic rocks. About 305 m (1000 ft) thick."))
                        elif in_row.ORIG_LABEL =='Sbp':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"Thickness ranges from 76 m (250 ft) at Greenwood Lake to 122 m (400 ft) in Longwood Valley. Berkshire Valley Formation (Barnett, 1970) - Commonly yellowish-gray weathering, medium-gray to pinkish-gray, very thin to thin-bedded fossiliferous limestone interbedded with gray to greenish-gray calcareous siltstone and silty dolomite, medium-gray to light-gray dolomite conglomerate, and grayish-black, thinly laminated shale. Lower contact conformable. Thickness ranges from 27 to 38 m (90-125 ft) thick. Poxono Island Formation, (White, 1882; Barnett, 1970) - Very thin to medium-bedded sequence of medium-gray, greenish-gray, or yellowish-gray, mud-cracked dolomite; light-green, pitted, medium-grained calcareous sandstone, siltstone, and edgewise conglomerate containing gray dolomite; and quartz-pebble conglomerate containing angular to subangular pebbles as much as 2 cm (0.8 in.) long. Interbedded grayish-green shales at lower contact are transitional into underlying Longwood Shale. Thickness ranges from 49 to 84 m (160-275 ft) thick."))
                        elif in_row.ORIG_LABEL =='Cl':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"Not available"))
                        elif in_row.ORIG_LABEL =='Ymp':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"Pinkish-gray- or pinkish-buff-weathering, white to pale-pinkish-white or light-gray, fine- to medium-grained, massive to moderately well-layered gneiss composed of microcline, quartz, oligoclase, clinopyroxene, and trace amounts of epidote, biotite, titanite, and opaque minerals. Commonly interlayered with amphibolite or pyroxene amphibolite."))
                        elif in_row.ORIG_LABEL =='Sl':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"(Darton, 1894) - Dark-reddish-brown, thin- to very thick bedded shale interbedded with cross-bedded, very dark red, very thin to thin-bedded sandstone and siltstone. Lower contact conformable. About 100 m (330 ft) thick."))
                        elif in_row.ORIG_LABEL =='Yd':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"Diorite - Gray- to tan-weathering, greenish-gray to brownish-gray, medium- to coarse-grained, greasy-lustered, massive diorite containing andesine or oligoclase, clinopyroxene, hornblende, hypersthene, and sparse amounts of biotite and magnetite."))
                        elif in_row.ORIG_LABEL =='Yps':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"Gray- to buff- or tan-weathering, greenish-gray, medium- to coarse-grained, massive, indistinctly foliated syenite composed of mesoperthite to microantiperthite, oligoclase and clinopyroxene. Contains sparse amounts of quartz, titanite, magnetite, and trace amounts of pyrite"))
                        elif in_row.ORIG_LABEL =='Ypg':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"Gray- to buff- or white-weathering, greenish-gray, medium- to coarse-grained, massive, gneissoid to indistinctly foliated granite containing mesoperthite to microantiperthite, quartz, oligoclase, and clinopyroxene. Common accessory minerals include titanite, magnetite, apatite, and trace amounts of pyrite. Some phases are monzonite, quartz monzodiorite, or granodiorite. Locally includes small bodies of amphibolite not shown on map."))
                        elif in_row.ORIG_LABEL =='Mtfp':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"Tuscumbia Limestone -- light-gray partly oolitic limestone; very coarse bioclastic crinoidal limestone common; light-gray chert nodules and concretions locally abundant. Fort Payne Chert -- very light to light-olive-gray, thin to thick-bedded fine to coarse-grained bioclastic (abundant pelmatozoans) limestone containing abundant nodules, lenses and beds of light to dark-grey chert. Upper part of formation locally consists of light-bluish-gray laminated siltstone containing vugs lined or filled with quartz and scattered throughout the formation are interbeds of medium to greenish-gray shale, shaly limestone and siltstone. Lenses of dark-gray siliceous shale occur locally at the base of the Fort Payne in Wills Valley. Commonly present below the Fort Payne is a ligh-olive-gray claystone or shale (Maury Formation) which is mapped with the Fort Payne. The Tuscumbia and Fort Payne are undifferentiated in Murphrees and Wills Valleys."))
                        elif in_row.ORIG_LABEL =='Olol':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"Dark-gray argillaceous, fossiliferous medium to thick-bedded limestone; locally contains rare chert in upper part and an interval of fenestral mudstone in lower part (Mosheim Limestone Member of the Lenoir Limestone). Between Siluria and Pelham in Shelby County, the Little Oak and Lenoir Limestones are seperated by a tongue of the Athens Shale"))
                        elif in_row.ORIG_LABEL =='Ppv':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"Light-gray thin to thick-bedded quartzose sandstone and conglomerate containing interbedded dark-gray shale, siltstone, and coal. Mapped on Lookout Mountain, Blount and Chandler Mountains, and Sand Mountain northeats of Blount County, and on the mountains of Jackson, Marshall and Madison Counties north and west of the TN river."))
                        elif in_row.ORIG_LABEL =='Owa':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"Drakes Formation; shale (90%) and limestone/dolomite (10%), interbedded; gray and maroon, weathers yellowish gray; planar to irregular, thin to thick bedded; 20 to 30 feet thick. Whitewater Formation, limestone (60%) and shale (40%) interbedded; gray weathers yellowish gray; irregular to wavy, thin to medium bedded; 20 to 80 feet thick. Liberty Formation, limestone (50%) and shale (50%), interbedded; gray weathers yellowish gray; planar to irregular, thin to medium bedded; 20 to 40 feet thick. Interval ranges from 60 to 150 feet in thickness. The Geological Survey of Ohio recognizes the Cincinnati Group proposed by Meek and Worthen (1865), but at this time retains it as an informal term. The unit will be formally reinstated as a lithostratigraphic term after revision of its lower boundary and minor lithologic redescription of its units are completed. The ten formations included in the group are the (ascending) Clays Ferry Formation, the Kope Formation, the Fairview Formation, the Miamitown Shale, the Grant Lake Limestone, the Arnheim Formation, the Waynesville Formation, the Liberty Formation, the Whitewater Formation, and the Drakes Formation. Six members have been identified in the course of field mapping: the Point Pleasant Tongue of the Clays Ferry, the informal Bellevue, Corryville, Mount Auburn, and Straight Creek members of the Grant Lake Limestone, and the Preachersville Member of the Drakes Formation. The Backbone Creek and Elk Creek beds are recognized as excellent stratigraphic marker beds (Shrake and others, 1988)."))
                        elif in_row.ORIG_LABEL =='Og':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"White, light-gray, buff, or pink, generally foliated granitic gneiss, composed of sodic plagioclase, quartz, microcline, muscovite, and biotite, and locally garnet or sillimanite. Commonly contains numerous inclusions or layers of mica schist and gneiss."))
                        elif in_row.ORIG_LABEL =='JTrps':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"Sandstone (JTrps) is interbedded grayish-red to brownish-red, medium- to fine-grained, medium- to thick-bedded sandstone and brownish-to-purplish-red coarse-grained siltstone; unit is planar to ripple cross-laminated, fissile, locally calcareous, containing desiccation cracks and root casts. Upward-fining cycles are 1.8 to 4.6 m (6-15 ft) thick. Sandstone beds are coarser and thicker near conglomerate units (JTrpcq, JTrpcl). Maximum thickness about 1,100 m (3,610 ft)."))
                        elif in_row.ORIG_LABEL =='JTrpsc':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"Conglomeratic sandstone (JTrpsc) is brownish-red pebble conglomerate, medium- to coarse-grained, feldspathic sandstone and micaceous siltstone; unit is planar to low-angle trough cross laminated, burrowed, and contains local pebble layers. Unit forms upward-fining sequences 0.5 to 2.5 m (1.6-8 ft) thick. Conglomeratic sandstone thickness exceeds 800 m (2,625 ft)."))
                        elif in_row.ORIG_LABEL =='Ot':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Gray, medium-grained, generally fairly well layered to well-laminated ("pin-stripe") gneissic or schistose granofels, composed of quartz, oligoclase, biotite, muscovite, and garnet, and locally staurolite and kyanite or sillimanite. The Taine Mountain Formation of Stanley (1964) is here adopted in the Collinsville and Bristol quads., CT. Includes three pinstriped units, the Wildcat, Scranton Mountain, and Whigville Members of Stanley (1964), also adopted. Wildcat Member is the basal pinstriped gneiss unit of the Taine Mountain, which correlates with the Savoy Schist of Emerson (1898), Missisquoi Schist or Group of Richardson (1919, 1924) in MA; and the Moretown Formation of Cady (1956) in MA and VT. Inferred age is Middle Ordovician (Simpson, 1990).'))
                        elif in_row.ORIG_LABEL =='Omlc':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Middle and Lower Parts of Chickamauga Group - A sequence of about 1,400 feet of limestone in the northwest part of Valley and Ridge, which thickens and becomes more clastic to the southeast and is divided into the formations shown at right. Maximum thickness about 7,000 feet. Includes Moccasin Formation - Maroon calcareous shale, siltstone, and limestone; thin metabentonite layers in upper part; mud cracks, ripple marks common. Thickness 800 to 1,000 feet;. (Ob) Bays Formation - Maroon, well-jointed claystone and siltstone, commonly mottled greenish, evenly bedded; light- gray sandstone beds and metabentonite in upper part. Maximum thickness 1,000 feet; (Osv) Sevier Shale - Calcareous, bluish-gray shale, weathers yellowish-brown; with thin, gray limestone layers; sandstone, siltstone, and locally conglomerate to the east. Thickness 2,000 to 7,000 feet; (Oo) Ottosee Shale - Bluish-gray calcareous shale, weathers yellow; with reef lenses of coarsely crystalline reddish fossiliferous limestone ("marble"). Thickness about 1,000 feet; (Oh) Holston Formation - Pink, gray, and red coarsely crystalline limestone (Holston Marble); in many areas upper part is sandy, crossbedded ferruginous limestone and brown to greenish calcareous shale. Thickness 200 to 600 feet; (Ol) Lenoir Limestone - Nodular, argillaceous, gray limestone; in places basal sedimentary breccia, conglomerate, quartz sand; Mosheim Limestone Member (dense, light- to medium-gray limestone) near base. Thickness 25 to 500 feet; (Oa) Athens Shale - Medium- to dark-gray, calcareous, graptolitic shale; calcareous gray sandstone, siltstone, and locally fine-pebble quartz conglomerate; nodules of shaly limestone near base. Maximum thickness 1,500 feet.'))
                        elif in_row.ORIG_LABEL =='Kbcb':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Moderately to poorly sorted sand and clay deposited in delta-dominated shallow marine environments. Unit is characterized by sands containing locally abundant (F-VC grained) tourmaline and (F-VC grained) muscovite with some monazite and garnet. Clay layers are also common and some lower delta plain deposits form commercial kaolin bodies. Generally very restricted marine in eastern Georgia becoming more open marine to the east and west.'))
                        elif in_row.ORIG_LABEL =='Pnbr':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'In northern Rhode Island, consists of gray to black, fine- to coarse-grained quartz arenite, litharenite, shale, and conglomerate, with minor beds of anthracite and meta-anthracite. In southern Rhode Island, consists of meta-sandstone, meta-conglomerate, schist, carbonaceous schist, and graphite. Plant fossils are common.'))
                        elif in_row.ORIG_LABEL =='Zbs':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Green to gray, fine-grained, massive to thinly-bedded mica schist, quartzite, and marble. Schist consists of quartz plus chlorite, muscovite, and/or biotite. Includes rock mapped formerly as Sneech Pond Schist, Mussey Brook Schist, and marble.'))
                        elif in_row.ORIG_LABEL =='Zeg':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Gray, tan, greenish, or pale-pink, medium- to coarse-grained, mainly equigranular rock. Contains microcline, perthite, plagioclase, quartz, and accessory biotite, epidote, zircon, allanite, monazite, apatite, sphene, and opaque minerals; secondary muscovite, chlorite, and calcite. Mainly massive, but locally foliated and lineated. Includes rock mapped formerly as Esmond Granite.'))
                        elif in_row.ORIG_LABEL =='Zegd':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Gray, tan, greenish, or pale-pink, medium- to coarse-grained, mainly porphyritic rock (phenocrysts of microcline). Contains microcline, perthite, plagioclase, quartz, and accessory biotite, epidote, zircon, allanite, monazite, apatite, sphene, and opaque minerals; secondary muscovite, chlorite, and calcite. Mainly massive. Includes rock mapped formerly as Grant Mills Granodiorite.'))
                        elif in_row.ORIG_LABEL =='Ya':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Gray- to grayish-black, medium-grained amphibolite composed of hornblende and andesine. Some phases contain biotite and (or) clinopyroxene. Ubiquitous and associated with almost all other Middle Proterozoic units. Some amphibolite is clearly metavolcanic in origin, some is metasedimentary, and some appears to be metagabbro.'))
                        elif in_row.ORIG_LABEL =='Yf':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'White- to light-gray-weathering, white, grayish-white, or, less commonly pinkish-orange, coarse- to locally fine-crystalline calcite marble with accessory amounts of graphite, phlogopite, chondrodite, clinopyroxene, and serpentine. Contains pods and layers of clinopyroxene-garnet skarn, hornblende skarn, and clinopyroxene-rich rock. Thin layers of metaquartzite occur locally. Intruded by the Mount Eve Granite in the Pochuck Mountain area. Franklin Marble is host to the Franklin and Sterling Hill zinc ore bodies; exploited for talc and asbestiform minerals near Easton, Pennsylvania. Subdivided into an upper marble, "Wildcat marble," and a lower marble, "Franklin marble," by New Jersey Zinc Co. geologists (Hague and others, 1956).'))
                        elif in_row.ORIG_LABEL =='Ylb':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'White- to light-gray-weathering, light- to medium-gray or greenish-gray, fine- to coarse-grained, massive to moderately well layered, foliated gneiss composed of oligoclase or andesine, quartz, biotite, and, locally, garnet. Commonly interlayered with amphibolite.'))
                        elif in_row.ORIG_LABEL =='Zem':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Dark-gray, purple, or black, medium- to coarse-grained rock that may contain plagioclase, quartz, clinopyroxene, hornblende, olivine, and accessory biotite, epidote, sphene, zircon, apatite, and opaque minerals; secondary chlorite, sericite, and saussurite. Massive to variably foliated. Composition includes tonalite, quartz diorite, diorite, and gabbro. Includes rock mapped formerly as quartz diorite.'))
                        elif in_row.ORIG_LABEL =='Ym':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Light-gray- to pinkish-white-weathering, tan to pinkish-white, fine- to medium-grained, well-layered gneiss composed principally of quartz, microcline, and lesser amounts of oligoclase. Common accessory minerals include biotite, garnet, magnetite, and, locally, sillimanite.'))
                        elif in_row.ORIG_LABEL =='Jb':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Reddish-brown to brownish-purple, fine-grained sandstone, siltstone, and mudstone; sandstone commonly micaceous, interbedded with siltstone and mudstone in fining-upward sequences mostly 1.5 to 4 m (5-13 ft) thick. Red, gray and brownish-purple siltstone and black, blocky, partly dolomitic siltstone and shale common in lower part. Irregular mudcracks, symmetrical ripple marks, and burrows, as well as gypsum, glauberite, and halite pseudomorphs are abundant in red mudstone and siltstone. Gray, fine-grained sandstone may have carbonized plant remains and reptile footprints in middle and upper parts of unit. Near Morristown, beds of quartz-pebble conglomerate (unit Jbcq) as much as 0.5 m (1.6 ft) thick interfinger with beds of sandstone, siltstone, and shale. Northeast of Boonton, beds of quartz-pebble conglomerate (not mapped separately as Jbcq) occur locally with conglomerate containing abundant clasts of gneiss and granite in matrix of reddish-brown sandstone and siltstone. Maximum thickness is about 500 m (1,640 ft).'))
                        elif in_row.ORIG_LABEL =='Jtc':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Conglomerate and conglomeratic sandstone with subrounded quartzite and quartz clasts in matrix of light-red sand to brownish-red silt (Jtc) interfingers with rocks of the Towaco Formation north and west of New Vernon.'))
                        elif in_row.ORIG_LABEL =='Jt':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Reddish-brown to brownish-purple, fine- to medium-grained micaceous sandstone, siltstone, and silty mudstone in upward-fining sequences 1 to 3 m (3-10 ft) thick. Distributed throughout formation are eight or more sequences of gray to greenish- or brownish-gray, fine-grained sandstone, siltstone and calcareous siltstone and black, microlaminated calcareous siltstone and mudstone containing diagnostic pollen, fish and dinosaur tracks. Sandstone is commonly trough cross laminated; siltstone is commonly planar laminated or bioturbated, but can be indistinctly laminated to massive. Thermally metamorphosed into hornfels where in contact with Hook Mountain Basalt. Conglomerate and conglomeratic sandstone with subrounded quartzite and quartz clasts in matrix of light-red sand to brownish-red silt (Jtc) interfingers with rocks of the Towaco Formation north and west of New Vernon. Maximum thickness is about 380 m (1,250 ft).'))
                        elif in_row.ORIG_LABEL =='Jh':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Light- to dark-greenish-gray, medium- to coarse-grained, amygdaloidal basalt composed of plagioclase (typically An65 and commonly porphyritic), clinopyroxene (augite and pigeonite), and iron-titanium oxides such as magnetite and ilmenite. Locally contains small spherical to tubular cavities (gas-escape vesicles), some filled by zeolite minerals or calcite. Consists of two major flows. Base of lowest flow is intensely vesicular. Tops of flows are weathered and vesicular. Maximum thickness is about 110 m (360 ft).'))
                        elif in_row.ORIG_LABEL =='Ylo':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'White-weathering, light-greenish-gray, medium- to coarse-grained, moderately layered to indistinctly foliated gneiss and lesser amounts of granofels composed of quartz, oligoclase or andesine, and, locally, biotite, hornblende and (or) clinopyroxene. Contains thin amphibolite layers.'))
                        elif in_row.ORIG_LABEL =='Ybh':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Pinkish-gray- to medium-buff-weathering, pinkish-white or light-pinkish-gray, medium- to coarse-grained, gneissoid to indistinctly foliated granite and sparse granite gneiss composed principally of microcline microperthite, quartz, oligoclase, and hornblende. Some phases are quartz syenite or quartz monzonite. Includes small bodies of pegmatite and amphibolite not shown on map. U-Pb age approximately 1,090 Ma'))
                        elif in_row.ORIG_LABEL =='Yb':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Gray-weathering, locally rusty, gray to tan or greenish-gray, fine- to medium-coarse-grained, moderately layered and foliated gneiss that is variable in texture and composition. Composed of oligoclase, microcline microperthite, quartz, and biotite. Locally contains garnet, graphite, sillimanite, and opaque minerals.'))
                        elif in_row.ORIG_LABEL =='Mzv':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r'Undivided Mesozoic volcanic and metavolcanic rocks. Andesite and rhyolite flow rocks, greenstone, volcanic breccia and other pyroclastic rocks; in part strongly metamorphosed. Includes volcanic rocks of Franciscan Complex: basaltic pillow lava, diabase, greenstone, and minor pyroclastic rocks.'))
                        elif in_row.ORIG_LABEL =='Qu':
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', r"This surficial expression of undifferentiated sediments is similar to the Pleistocene Holocene Beach Ridge and Dune (Qbd), except the subdivisions of the Undifferentiated QuaternarySediments are not lithostratigraphic units but rather utilized in order to facilitate a better understanding of the State's geology."))
                        else:
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '10685', 2, 'N', 6, 'Unit Description: ', str(in_row.FIRST_UNITDESC.replace(u'\xfc',"").replace("?",""))))
                del in_row
                del in_rows

                query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'GEOL', OrderNumText+'_US_GEOL.jpg', 1))          #note type 'SOIL' or 'GEOL' is used internally
                if multipage_geology == True:
                    for i in range(1,page):
                        query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'GEOL', OrderNumText+'_US_GEOL'+str(i)+'.jpg', i+1))
                #result = cur.callfunc('eris_psr.CreateReport', str, (OrderIDText,))
        ##        if result == '{"RunReportResult":"OK"}':
        ##            print 'report generation success'
        ##        else:
        ##            print 'report generation failure'

            finally:
                cur.close()
                con.close()


        ### SOIL REPORT -------------------------------------------------------------------------
        print "--- starting Soil section " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        siteState = ProvStateText
        if siteState == 'HI':
            datapath_soil =PSR_config.datapath_soil_HI#r'\\cabcvan1gis001\DATA_GIS\SSURGO\CONUS_2015\gSSURGO_HI.gdb'
        elif siteState == 'AK':
            datapath_soil =PSR_config.datapath_soil_AK#r'\\cabcvan1gis001\DATA_GIS\SSURGO\CONUS_2015\gSSURGO_AK.gdb'
        else:
            datapath_soil =PSR_config.datapath_soil_CONUS#r'\\cabcvan1gis001\DATA_GIS\SSURGO\CONUS_2015\gSSURGO_CONUS_10m.gdb'

        table_muaggatt = os.path.join(datapath_soil,'muaggatt')
        table_component = os.path.join(datapath_soil,'component')
        table_chorizon = os.path.join(datapath_soil,'chorizon')
        table_chtexturegrp = os.path.join(datapath_soil,'chtexturegrp')
        masterfile = os.path.join(datapath_soil,'MUPOLYGON')
        #arcpy.MakeFeatureLayer_management(masterfile,"masterLayer")

        fc_soils = os.path.join(scratchfolder,"soils.shp")
        fc_soils_temp = os.path.join(scratchfolder,"soils_temp.shp")
        fc_soils_PR = os.path.join(scratchfolder, "soilsPR.shp")
        #fc_soils_m = os.path.join(scratchfolder,"soilsPR_m.shp")
        stable_muaggatt = os.path.join(scratch,"muaggatt")
        stable_component = os.path.join(scratch,"component")
        stable_chorizon = os.path.join(scratch,"chorizon")
        stable_chtexturegrp = os.path.join(scratch,"chtexturegrp")


        bufferSHP_soil = os.path.join(scratchfolder,"buffer_soil.shp")
        arcpy.Buffer_analysis(orderGeometryPR, bufferSHP_soil, bufferDist_soil)
        #arcpy.Clip_analysis(masterfile,bufferSHP_soil,fc_soils)
        masterLayer_soil = arcpy.mapping.Layer(masterfile)
        arcpy.SelectLayerByLocation_management(masterLayer_soil, 'intersect', bufferSHP_soil)
        if int((arcpy.GetCount_management(masterLayer_soil).getOutput(0))) != 0:
            arcpy.CopyFeatures_management(masterLayer_soil,fc_soils_temp)
            arcpy.Generalize_edit(fc_soils_temp,"4 FEET")
        arcpy.Clip_analysis(fc_soils_temp,bufferSHP_soil,fc_soils)
        arcpy.Delete_management(masterLayer_soil)
        arcpy.MakeFeatureLayer_management(fc_soils,'soillayer')

        hydrologic_dict = PSR_config.hydrologic_dict
    ##    {
    ##        "A":'Soils in this group have low runoff potential when thoroughly wet. Water is transmitted freely through the soil.',
    ##        "B":'Soils in this group have moderately low runoff potential when thoroughly wet. Water transmission through the soil is unimpeded.',
    ##        "C":'Soils in this group have moderately high runoff potential when thoroughly wet. Water transmission through the soil is somewhat restricted.',
    ##        "D":'Soils in this group have high runoff potential when thoroughly wet. Water movement through the soil is restricted or very restricted.',
    ##        "A/D":'These soils have low runoff potential when drained and high runoff potential when undrained.',
    ##        "B/D":'These soils have moderately low runoff potential when drained and high runoff potential when undrained.',
    ##        "C/D":'These soils have moderately high runoff potential when drained and high runoff potential when undrained.',
    ##        }

        hydric_dict = PSR_config.hydric_dict
    ##    {
    ##        '1':'All hydric',
    ##        '2':'Not hydric',
    ##        '3':'Partially hydric',
    ##        '4':'Unknown',
    ##        }

        if (int(arcpy.GetCount_management('soillayer').getOutput(0)) == 0):   # no soil polygons selected
            print 'no polygons selected'
            try:
                con = cx_Oracle.connect(connectionString)
                cur = con.cursor()

                erisid = erisid + 1
                query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '9334', 2, 'N', 1, 'No soil data available in the project area.', ''))

            finally:
                cur.close()
                con.close()

        else:

            arcpy.Project_management(fc_soils, fc_soils_PR, out_coordinate_system)


            ## create map keys
            #arcpy.SpatialJoin_analysis(fc_soils_PR, orderGeometryPR, fc_soils_m, "JOIN_ONE_TO_MANY", "KEEP_ALL","#", "CLOSEST","5000 Kilometers", "Distance")   # this is the reported distance
            #arcpy.AddField_management(fc_soils_m, "label", "TEXT", "", "", "", "", "NON_NULLABLE", "REQUIRED", "")
    ##        arcpy.Statistics_analysis(fc_soils_PR, os.path.join(scratchfolder,"summary_soil.dbf"), [['mukey','FIRST']],'musym')
            arcpy.Statistics_analysis(fc_soils_PR, os.path.join(scratchfolder,"summary_soil.dbf"), [['mukey','FIRST'],["Shape_Area","SUM"]],'musym')
            arcpy.Sort_management(os.path.join(scratchfolder,"summary_soil.dbf"), os.path.join(scratchfolder,"summary1_soil.dbf"), [["musym", "ASCENDING"]])
            seqarray = arcpy.da.TableToNumPyArray(os.path.join(scratchfolder,'summary1_soil.dbf'), '*')    #note: it could contain 'NOTCOM' record


            ## retrieve attributes
            unique_MuKeys = returnUniqueSetString_musym(fc_soils)
            if(len(unique_MuKeys)>0):    # special case: order only returns one "NOTCOM" category, filter out
                whereClause_selectTable = "muaggatt.mukey in " + unique_MuKeys
                arcpy.TableSelect_analysis(table_muaggatt, stable_muaggatt, whereClause_selectTable)

                whereClause_selectTable = "component.mukey in " + unique_MuKeys
                arcpy.TableSelect_analysis(table_component, stable_component, whereClause_selectTable)

                unique_CoKeys = returnUniqueSetString(stable_component, 'cokey')
                whereClause_selectTable = "chorizon.cokey in " + unique_CoKeys
                arcpy.TableSelect_analysis(table_chorizon, stable_chorizon, whereClause_selectTable)

                unique_CHKeys = returnUniqueSetString(stable_chorizon,'chkey')
                if len(unique_CHKeys) > 0:       # special case: e.g. there is only one Urban Land polygon
                    whereClause_selectTable = "chorizon.chkey in " + unique_CHKeys
                    arcpy.TableSelect_analysis(table_chtexturegrp, stable_chtexturegrp, whereClause_selectTable)


                    tablelist = [stable_muaggatt, stable_component,stable_chorizon, stable_chtexturegrp]
                    fieldlist  = PSR_config.fc_soils_fieldlist#[['muaggatt.mukey','mukey'], ['muaggatt.musym','musym'], ['muaggatt.muname','muname'],['muaggatt.drclassdcd','drclassdcd'],['muaggatt.hydgrpdcd','hydgrpdcd'],['muaggatt.hydclprs','hydclprs'], ['muaggatt.brockdepmin','brockdepmin'], ['muaggatt.wtdepannmin','wtdepannmin'], ['component.cokey','cokey'],['component.compname','compname'], ['component.comppct_r','comppct_r'], ['component.majcompflag','majcompflag'],['chorizon.chkey','chkey'],['chorizon.hzname','hzname'],['chorizon.hzdept_r','hzdept_r'],['chorizon.hzdepb_r','hzdepb_r'], ['chtexturegrp.chtgkey','chtgkey'], ['chtexturegrp.texdesc1','texdesc'], ['chtexturegrp.rvindicator','rv']]
                    keylist = PSR_config.fc_soils_keylist#['muaggatt.mukey', 'component.cokey','chorizon.chkey','chtexturegrp.chtgkey']
                    #whereClause_queryTable = "muaggatt.mukey = component.mukey and component.cokey = chorizon.cokey and chorizon.chkey = chtexturegrp.chkey and chtexturegrp.rvindicator = 'Yes'"
                    whereClause_queryTable = PSR_config.fc_soils_whereClause_queryTable#"muaggatt.mukey = component.mukey and component.cokey = chorizon.cokey and chorizon.chkey = chtexturegrp.chkey"
                    #Query tables may only be created using data from a geodatabase or an OLE DB connection
                    queryTableResult = arcpy.MakeQueryTable_management(tablelist,'queryTable','USE_KEY_FIELDS', keylist, fieldlist, whereClause_queryTable)  #note: outTable is a table view and won't persist

                    arcpy.TableToTable_conversion('queryTable',scratch, 'soilTable')  #note: 1. <null> values will be retained using .gdb, will be converted to 0 using .dbf; 2. domain values, if there are any, will be retained by using .gdb

                    dataarray = arcpy.da.TableToNumPyArray(os.path.join(scratch,'soilTable'), '*', null_value = -99)


            reportdata = []
            for i in range (0, len(seqarray)):
                mapunitdata = {}
                mukey = seqarray['FIRST_muke'][i]   #CC: if in Dev, field name is FIRST_muke, if in 007 field name is FIRST_MUKE #note the column name in the .dbf output was cut off
                print '***** map unit ' + str(i)
                print 'musym is ' + str(seqarray['MUSYM'][i])
                print 'mukey is ' + str(mukey)
                mapunitdata['Seq'] = str(i+1)    # note i starts from 0, but we want labels to start from 1

                if (seqarray['MUSYM'][i].upper() == 'NOTCOM'):
                    mapunitdata['Map Unit Name'] = 'No Digital Data Available'
                    mapunitdata['Mukey'] = mukey
                    mapunitdata['Musym'] = 'NOTCOM'
                else:
                    if 'dataarray' not in locals():           #there is only one special polygon(urban land or water)
                        cursor = arcpy.SearchCursor(stable_muaggatt, "mukey = '" + str(mukey) + "'")
                        row = cursor.next()
                        mapunitdata['Map Unit Name'] = row.muname
                        print '  map unit name: ' + row.muname
                        mapunitdata['Mukey'] = mukey          #note
                        mapunitdata['Musym'] = row.musym
                        row = None
                        cursor = None

                    elif ((returnMapUnitAttribute(dataarray, mukey, 'muname')).upper() == '?'):  #Water or Unrban Land
                        cursor = arcpy.SearchCursor(stable_muaggatt, "mukey = '" + str(mukey) + "'")
                        row = cursor.next()
                        mapunitdata['Map Unit Name'] = row.muname
                        print '  map unit name: ' + row.muname
                        mapunitdata['Mukey'] = mukey          #note
                        mapunitdata['Musym'] = row.musym
                        row = None
                        cursor = None
                    else:
                        mapunitdata['Mukey'] = returnMapUnitAttribute(dataarray, mukey, 'mukey')
                        mapunitdata['Musym'] = returnMapUnitAttribute(dataarray, mukey, 'musym')
                        mapunitdata['Map Unit Name'] = returnMapUnitAttribute(dataarray, mukey, 'muname')
                        mapunitdata['Drainage Class - Dominant'] = returnMapUnitAttribute(dataarray, mukey, 'drclassdcd')
                        mapunitdata['Hydrologic Group - Dominant'] = returnMapUnitAttribute(dataarray, mukey, 'hydgrpdcd')
                        mapunitdata['Hydric Classification - Presence'] = returnMapUnitAttribute(dataarray, mukey, 'hydclprs')
                        mapunitdata['Bedrock Depth - Min'] = returnMapUnitAttribute(dataarray, mukey, 'brockdepmin')
                        mapunitdata['Watertable Depth - Annual Min'] = returnMapUnitAttribute(dataarray, mukey, 'wtdepannmin')

                        componentdata = returnComponentAttribute(dataarray,mukey)
                        mapunitdata['component'] = componentdata
                mapunitdata["Soil_Percent"]  ="%s"%round(seqarray['SUM_Shape_'][i]/sum(seqarray['SUM_Shape_'])*100,2)+r'%'
                reportdata.append(mapunitdata)

            for mapunit in reportdata:
                print 'mapunit name: ' + mapunit['Map Unit Name']
                if 'component' in mapunit.keys():
                    print 'Major component info are printed below'
                    for comp in mapunit['component']:
                        print '    component name is ' + comp[0][0]
                        for i in range(1,len(comp)):
                            print '      '+comp[i][0] +': '+ comp[i][1]


            ## create the map
            point = arcpy.Point()
            array = arcpy.Array()
            featureList = []

            width = arcpy.Describe(bufferSHP_soil).extent.width/2
            height = arcpy.Describe(bufferSHP_soil).extent.height/2
            if (width > 662 or height > 662):
                if (width/height > 1):
                   # buffer has a wider shape
                   width = width * 1.1
                   height = width

                else:
                    # buffer has a vertically elonged shape
                    height = height * 1.1
                    width = height
            else:
                width = 662*1.1
                height = 662*1.1
            width = width + 6400     #add 2 miles to each side, for multipage soil
            height = height + 6400   #add 2 miles to each side, for multipage soil
            xCentroid = (arcpy.Describe(bufferSHP_soil).extent.XMax + arcpy.Describe(bufferSHP_soil).extent.XMin)/2
            yCentroid = (arcpy.Describe(bufferSHP_soil).extent.YMax + arcpy.Describe(bufferSHP_soil).extent.YMin)/2
            point.X = xCentroid-width
            point.Y = yCentroid+height
            array.add(point)
            point.X = xCentroid+width
            point.Y = yCentroid+height
            array.add(point)
            point.X = xCentroid+width
            point.Y = yCentroid-height
            array.add(point)
            point.X = xCentroid-width
            point.Y = yCentroid-height
            array.add(point)
            point.X = xCentroid-width
            point.Y = yCentroid+height
            array.add(point)
            feat = arcpy.Polygon(array,spatialRef)
            array.removeAll()
            featureList.append(feat)
            clipFrame = os.path.join(scratchfolder, "clipFrame.shp")
            arcpy.CopyFeatures_management(featureList, clipFrame)


            #arcpy.MakeFeatureLayer_management(clipFrame,'ClipLayer')
            #arcpy.MakeFeatureLayer_management(masterfile,"masterLayer")
            masterLayer_soil = arcpy.mapping.Layer(masterfile)
            arcpy.SelectLayerByLocation_management(masterLayer_soil, 'intersect', clipFrame)
            if int((arcpy.GetCount_management(masterLayer_soil).getOutput(0))) != 0:
                arcpy.CopyFeatures_management(masterLayer_soil,os.path.join(scratchfolder, "soil_disp.shp"))
                arcpy.Generalize_edit(os.path.join(scratchfolder, "soil_disp.shp"),"4 FEET")

            #arcpy.Clip_analysis("masterLayer","ClipLayer",os.path.join(scratchfolder, "soil_disp.shp"))
            #arcpy.Delete_management('ClipLayer')
            #arcpy.Delete_management('masterLayer')
            # add another column to soil_disp just for symbology purpose
            arcpy.AddField_management(os.path.join(scratchfolder, 'soil_disp.shp'), "FIDCP", "TEXT", "", "", "", "", "NON_NULLABLE", "REQUIRED", "")

            arcpy.CalculateField_management(os.path.join(scratchfolder, 'soil_disp.shp'), "FIDCP", "!FID!", "PYTHON_9.3")


            mxd_soil = arcpy.mapping.MapDocument(mxdfile_soil)
            df_soil = arcpy.mapping.ListDataFrames(mxd_soil,"*")[0]
            df_soil.spatialReference = spatialRef

            lyr = arcpy.mapping.ListLayers(mxd_soil, "SSURGO*", df_soil)[0]
            lyr.replaceDataSource(scratchfolder,"SHAPEFILE_WORKSPACE", "soil_disp")
            lyr.symbology.addAllValues()
            soillyr = lyr

            addBuffertoMxd("buffer_soil", df_soil)
            addOrdergeomtoMxd("ordergeoNamePR", df_soil)


            if multipage_soil == False:
                mxd_soil.saveACopy(os.path.join(scratchfolder, "mxd_soil.mxd"))
                arcpy.mapping.ExportToJPEG(mxd_soil, outputjpg_soil, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                    os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                shutil.copy(outputjpg_soil, os.path.join(report_path, 'PSRmaps', OrderNumText))
                del mxd_soil
                del df_soil

            else:   # multipage
                gridlr = "gridlr_soil"   #gdb feature class doesn't work, could be a bug. So use .shp
                gridlrshp = os.path.join(scratch, gridlr)
                arcpy.GridIndexFeatures_cartography(gridlrshp, bufferSHP_soil, "", "", "", gridsize, gridsize)  #note the tool takes featureclass name only, not the full path


                # part 1: the overview map
                #add grid layer
                gridLayer = arcpy.mapping.Layer(gridlyrfile)
                gridLayer.replaceDataSource(scratch,"FILEGDB_WORKSPACE","gridlr_soil")
                arcpy.mapping.AddLayer(df_soil,gridLayer,"Top")

                df_soil.extent = gridLayer.getExtent()
                df_soil.scale = df_soil.scale * 1.1

                mxd_soil.saveACopy(os.path.join(scratchfolder, "mxd_soil.mxd"))
                arcpy.mapping.ExportToJPEG(mxd_soil, outputjpg_soil, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                    os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                shutil.copy(outputjpg_soil, os.path.join(report_path, 'PSRmaps', OrderNumText))
                del mxd_soil
                del df_soil

                # part 2: the data driven pages maps
                page = 1

                page = int(arcpy.GetCount_management(gridlrshp).getOutput(0))  + page
                mxdMM_soil = arcpy.mapping.MapDocument(mxdMMfile_soil)

                dfMM_soil = arcpy.mapping.ListDataFrames(mxdMM_soil,"*")[0]
                dfMM_soil.spatialReference = spatialRef
                addBuffertoMxd("buffer_soil",dfMM_soil)
                addOrdergeomtoMxd("ordergeoNamePR", dfMM_soil)
                lyr = arcpy.mapping.ListLayers(mxdMM_soil, "SSURGO*", dfMM_soil)[0]
                lyr.replaceDataSource(scratchfolder,"SHAPEFILE_WORKSPACE", "soil_disp")
                lyr.symbology.addAllValues()
                soillyr = lyr

                gridlayerMM = arcpy.mapping.ListLayers(mxdMM_soil,"Grid" ,dfMM_soil)[0]
                gridlayerMM.replaceDataSource(scratch, "FILEGDB_WORKSPACE","gridlr_soil")
                arcpy.CalculateAdjacentFields_cartography(gridlrshp, "PageNumber")
                mxdMM_soil.saveACopy(os.path.join(scratchfolder, "mxdMM_soil.mxd"))

                for i in range(1,int(arcpy.GetCount_management(gridlrshp).getOutput(0))+1):
                    arcpy.SelectLayerByAttribute_management(gridlayerMM, "NEW_SELECTION", ' "PageNumber" =  ' + str(i))
                    dfMM_soil.extent = gridlayerMM.getSelectedExtent(True)
                    dfMM_soil.scale = dfMM_soil.scale * 1.1
                    arcpy.SelectLayerByAttribute_management(gridlayerMM, "CLEAR_SELECTION")

                    titleTextE = arcpy.mapping.ListLayoutElements(mxdMM_soil, "TEXT_ELEMENT", "title")[0]
                    titleTextE.text = "SSURGO Soils - Page " + str(i)
                    titleTextE.elementPositionX = 0.6156
                    arcpy.RefreshTOC()


                    arcpy.mapping.ExportToJPEG(mxdMM_soil, outputjpg_soil[0:-4]+str(i)+".jpg", "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                    if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                        os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                    shutil.copy(outputjpg_soil[0:-4]+str(i)+".jpg", os.path.join(report_path, 'PSRmaps', OrderNumText))
                del mxdMM_soil
                del dfMM_soil


            try:
                con = cx_Oracle.connect(connectionString)
                cur = con.cursor()
                soil_IDs = []
                ###cur.callproc('eris_psr.ClearOrder', (OrderIDText,))

                for mapunit in reportdata:
                    erisid = erisid + 1
                    mukey = int(mapunit['Mukey'])
                    soil_IDs.append([mapunit['Musym'],erisid])
                    cur.callproc('eris_psr.InsertOrderDetail', (OrderIDText, erisid,'9334'))
                    query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '9334', 2, 'S1', 1, 'Map Unit ' + mapunit['Musym'] + " (%s)"%mapunit["Soil_Percent"], ''))
                    query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '9334', 2, 'N', 2, 'Map Unit Name:', mapunit['Map Unit Name']))
                    if (len(mapunit) < 6):    #for Water, Urbanland and Gravel Pits
                        query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '9334', 2, 'N', 3, 'No more attributes available for this map unit',''))
                    else:           # not do for Water or urban land
                        query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '9334', 2, 'N', 3, 'Bedrock Depth - Min:',  mapunit['Bedrock Depth - Min']))
                        query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '9334', 2, 'N', 4, 'Watertable Depth - Annual Min:', mapunit['Watertable Depth - Annual Min']))
                        if (mapunit['Drainage Class - Dominant'] == '-99'):
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '9334', 2, 'N', 5, 'Drainage Class - Dominant:', 'null'))
                        else:
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '9334', 2, 'N', 5, 'Drainage Class - Dominant:', mapunit['Drainage Class - Dominant']))
                        if (mapunit['Hydrologic Group - Dominant'] == '-99'):
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '9334', 2, 'N', 6, 'Hydrologic Group - Dominant:', 'null'))
                        else:
                            query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '9334', 2, 'N', 6, 'Hydrologic Group - Dominant:', mapunit['Hydrologic Group - Dominant'] + ' - ' +hydrologic_dict[mapunit['Hydrologic Group - Dominant']]))
                        query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '9334', 2, 'N', 7, 'Major components are printed below', ''))

                        k = 7
                        if 'component' in mapunit.keys():
                            k = k + 1
                            for comp in mapunit['component']:
                                query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '9334', 2, 'S2', k, comp[0][0],''))
                                for i in range(1,len(comp)):
                                    k = k+1
                                    query = cur.callproc('eris_psr.InsertFlexRep', (OrderIDText, erisid, '9334', 2, 'S3', k, comp[i][0], comp[i][1]))

                #old: query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'SOIL'))
                query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'SOIL', OrderNumText+'_US_SOIL.jpg', 1))
                if multipage_soil == True:
                    for i in range(1,page):
                        query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'SOIL', OrderNumText+'_US_SOIL'+str(i)+'.jpg', i+1))
                #result = cur.callfunc('eris_psr.CreateReport', str, (OrderIDText,))
                # example: InsertMap(411578, ?SOIL?, ?20131002005_US_SOIL.jpg?, 1)
                #result = cur.callfunc('eris_psr.CreateReport', str, (OrderIDText,))
                #if result == '{"RunReportResult":"OK"}':
                #    print 'report generation success'
                #else:
                #    print 'report generation failure'

            finally:
                cur.close()
                con.close()





        ## Water Wells and Oil and Gas Wells -----------------------------------------------------------------
        print "--- starting WaterWells section " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        in_rows = arcpy.SearchCursor(orderGeometryPR)
        orderCentreSHP = os.path.join(scratchfolder, "SiteMarkerPR.shp")
        point1 = arcpy.Point()
        array1 = arcpy.Array()
        featureList = []
        arcpy.CreateFeatureclass_management(scratchfolder, "SiteMarkerPR.shp", "POINT", "", "DISABLED", "DISABLED", spatialRef)

        cursor = arcpy.InsertCursor(orderCentreSHP)
        feat = cursor.newRow()
        for in_row in in_rows:
            # Set X and Y for start and end points
            point1.X = in_row.xCenUTM
            point1.Y = in_row.yCenUTM
            array1.add(point1)

            centerpoint = arcpy.Multipoint(array1)
            array1.removeAll()
            featureList.append(centerpoint)
            feat.shape = point1
            cursor.insertRow(feat)
        del feat
        del cursor
        del in_row
        del in_rows
        del point1
        del array1

        arcpy.AddField_management(orderCentreSHP, "Lon_X", "DOUBLE", "12", "6", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddField_management(orderCentreSHP, "Lat_Y", "DOUBLE", "12", "6", "", "", "NULLABLE", "NON_REQUIRED", "")

        # prepare for elevation calculation
        arcpy.CalculateField_management(orderCentreSHP, "Lon_X", Lon_X, "PYTHON_9.3", "")
        arcpy.CalculateField_management(orderCentreSHP, "Lat_Y", Lat_Y, "PYTHON_9.3", "")
        arcpy.ImportToolbox(PSR_config.tbx)
        orderCentreSHP = getElevation(orderCentreSHP,["Lon_X","Lat_Y","Id"])##orderCentreSHP = arcpy.inhouseElevation_ERIS(orderCentreSHP).getOutput(0)
        Call_Google = ''
        rows = arcpy.SearchCursor(orderCentreSHP)
        for row in rows:
            if row.Elevation == -999:
                Call_Google = 'YES'
                break
            else:
                print row.Elevation
        del row
        del rows
        if Call_Google == 'YES':
            orderCentreSHP = arcpy.googleElevation_ERIS(orderCentreSHP).getOutput(0)
    ##    orderCentreSHPPR = os.path.join(scratchfolder, "SiteMarkerPR.shp")
    ##    arcpy.Project_management(orderCentreSHP,orderCentreSHPPR,out_coordinate_system)
    ##    orderCentreSHP = orderCentreSHPPR
        arcpy.AddXY_management(orderCentreSHP)

        mergelist = []
        for dsoid in dsoid_wells:
            bufferSHP_wells = os.path.join(scratchfolder,"buffer_"+dsoid+".shp")
            arcpy.Buffer_analysis(orderGeometryPR, bufferSHP_wells, str(searchRadius[dsoid])+" MILES")
            wells_clip = os.path.join(scratchfolder,'wellsclip_'+dsoid+'.shp')

            arcpy.Clip_analysis(eris_wells, bufferSHP_wells, wells_clip)
            arcpy.Select_analysis(wells_clip, os.path.join(scratchfolder,'wellsselected_'+dsoid+'.shp'), "DS_OID ="+dsoid)
            mergelist.append(os.path.join(scratchfolder,'wellsselected_'+dsoid+'.shp'))
        wells_merge = os.path.join(scratchfolder, "wells_merge.shp")
        arcpy.Merge_management(mergelist, wells_merge)
        del eris_wells
        print "--- WaterWells section, after merge " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        # Calculate Distance with integration and spatial join- can be easily done with Distance tool along with direction if ArcInfo or Advanced license
        wells_mergePR= os.path.join(scratchfolder,"wells_mergePR.shp")
        arcpy.Project_management(wells_merge, wells_mergePR, out_coordinate_system)
        arcpy.Integrate_management(wells_mergePR, ".5 Meters")

        arcpy.AddField_management(orderGeometryPR, "Elevation", "DOUBLE", "12", "6", "", "", "NULLABLE", "NON_REQUIRED", "")
        cursor = arcpy.SearchCursor(orderCentreSHP)
        row = cursor.next()
        elev_marker = row.getValue("Elevation")
        del cursor
        del row
        arcpy.CalculateField_management(orderGeometryPR, "Elevation", eval(str(elev_marker)), "PYTHON_9.3", "")

        #add distance to selected wells
        wells_sj= os.path.join(scratchfolder,"wells_sj.shp")
        wells_sja= os.path.join(scratchfolder,"wells_sja.shp")
        arcpy.SpatialJoin_analysis(wells_mergePR, orderGeometryPR, wells_sj, "JOIN_ONE_TO_MANY", "KEEP_ALL","#", "CLOSEST","5000 Kilometers", "Distance")   # this is the reported distance
        arcpy.SpatialJoin_analysis(wells_sj, orderCentreSHP, wells_sja, "JOIN_ONE_TO_MANY", "KEEP_ALL","#", "CLOSEST","5000 Kilometers", "Dist_cent")  # this is used for mapkey calculation

        if int(arcpy.GetCount_management(os.path.join(wells_merge)).getOutput(0)) != 0:
            print "--- WaterWells section, exists water wells "

            wells_sja = getElevation(wells_sja,["X","Y","ID"])#wells_sja = arcpy.inhouseElevation_ERIS(wells_sja).getOutput(0)
            elevationArray=[]
            Call_Google = ''
            rows = arcpy.SearchCursor(wells_sja)
            for row in rows:
                #print row.Elevation
                if row.Elevation == -999:
                    Call_Google = 'YES'
                    break
            del rows

            if Call_Google == 'YES':
                arcpy.ImportToolbox(PSR_config.tbx)
                wells_sja = arcpy.googleElevation_ERIS(wells_sja).getOutput(0)

            wells_sja_final= os.path.join(scratchfolder,"wells_sja_PR.shp")
            arcpy.Project_management(wells_sja,wells_sja_final,out_coordinate_system)
            wells_sja = wells_sja_final
            # Add mapkey with script from ERIS toolbox
            arcpy.AddField_management(wells_sja, "MapKeyNo", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
             # Process: Add Field for mapkey rank storage based on location and total number of keys at one location
            arcpy.AddField_management(wells_sja, "MapKeyLoc", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.AddField_management(wells_sja, "MapKeyTot", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
             # Process: Mapkey- to create mapkeys
            arcpy.ImportToolbox(PSR_config.tbx)
            arcpy.mapKey_ERIS(wells_sja)

            #Add Direction to ERIS sites
            arcpy.AddField_management(wells_sja, "Direction", "TEXT", "", "", "3", "", "NULLABLE", "NON_REQUIRED", "")
            desc = arcpy.Describe(wells_sja)
            shapefieldName = desc.ShapeFieldName
            rows = arcpy.UpdateCursor(wells_sja)
            for row in rows:
                if(row.Distance<0.001):  #give onsite, give "-" in Direction field
                    directionText = '-'
                else:
                    ref_x = row.xCenUTM      #field is directly accessible
                    ref_y = row.yCenUTM
                    feat = row.getValue(shapefieldName)
                    pnt = feat.getPart()
                    directionText = getDirectionText.getDirectionText(ref_x,ref_y,pnt.X,pnt.Y)

                row.Direction = directionText #field is directly accessible
                rows.updateRow(row)
            del rows

            wells_fin= os.path.join(scratchfolder,"wells_fin.shp")
            arcpy.Select_analysis(wells_sja, wells_fin, "\"MapKeyTot\" = 1")
            wells_disp= os.path.join(scratchfolder,"wells_disp.shp")
            arcpy.Sort_management(wells_fin, wells_disp, [["MapKeyLoc", "ASCENDING"]])

            arcpy.AddField_management(wells_disp, "Ele_diff", "DOUBLE", "12", "6", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.CalculateField_management(wells_disp, "Ele_diff", "!Elevation!-!Elevatio_1!", "PYTHON_9.3", "")
            arcpy.AddField_management(wells_disp, "eleRank", "SHORT", "12", "6", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.ImportToolbox(PSR_config.tbx)
            arcpy.symbol_ERIS(wells_disp)
             ## create a map with water wells and ogw wells
            mxd_wells = arcpy.mapping.MapDocument(PSR_config.mxdfile_wells)
            df_wells = arcpy.mapping.ListDataFrames(mxd_wells,"*")[0]
            df_wells.spatialReference = spatialRef

            lyr = arcpy.mapping.ListLayers(mxd_wells, "wells", df_wells)[0]
            lyr.replaceDataSource(scratchfolder,"SHAPEFILE_WORKSPACE", "wells_disp")
        else:
            print "--- WaterWells section, no water wells exists "
            mxd_wells = arcpy.mapping.MapDocument(PSR_config.mxdfile_wells)
            df_wells = arcpy.mapping.ListDataFrames(mxd_wells,"*")[0]
            df_wells.spatialReference = spatialRef

        for item in dsoid_wells:
            addBuffertoMxd("buffer_"+item, df_wells)
        df_wells.extent = arcpy.Describe(os.path.join(scratchfolder,"buffer_"+dsoid_wells_maxradius+'.shp')).extent
        df_wells.scale = df_wells.scale * 1.1
        addOrdergeomtoMxd("ordergeoNamePR", df_wells)

        if multipage_wells == False or int(arcpy.GetCount_management(wells_sja).getOutput(0))== 0:
            mxd_wells.saveACopy(os.path.join(scratchfolder, "mxd_wells.mxd"))
            arcpy.mapping.ExportToJPEG(mxd_wells, outputjpg_wells, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
            if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
            shutil.copy(outputjpg_wells, os.path.join(report_path, 'PSRmaps', OrderNumText))
            del mxd_wells
            del df_wells
        else:
            gridlr = "gridlr_wells"   #gdb feature class doesn't work, could be a bug. So use .shp
            gridlrshp = os.path.join(scratch, gridlr)
            arcpy.GridIndexFeatures_cartography(gridlrshp, os.path.join(scratchfolder,"buffer_"+dsoid_wells_maxradius+'.shp'), "", "", "", gridsize, gridsize)  #note the tool takes featureclass name only, not the full path
            # part 1: the overview map
            #add grid layer
            gridLayer = arcpy.mapping.Layer(gridlyrfile)
            gridLayer.replaceDataSource(scratch,"FILEGDB_WORKSPACE","gridlr_wells")
            arcpy.mapping.AddLayer(df_wells,gridLayer,"Top")
            # turn the site label off
            well_lyr = arcpy.mapping.ListLayers(mxd_wells, "wells", df_wells)[0]
            well_lyr.showLabels = False
            df_wells.extent = gridLayer.getExtent()
            df_wells.scale = df_wells.scale * 1.1
            mxd_wells.saveACopy(os.path.join(scratchfolder, "mxd_wells.mxd"))
            arcpy.mapping.ExportToJPEG(mxd_wells, outputjpg_wells, "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
            if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
            shutil.copy(outputjpg_wells, os.path.join(report_path, 'PSRmaps', OrderNumText))
            del mxd_wells
            del df_wells

            # part 2: the data driven pages
            page = 1
            page = int(arcpy.GetCount_management(gridlrshp).getOutput(0))  + page
            mxdMM_wells = arcpy.mapping.MapDocument(mxdMMfile_wells)
            dfMM_wells = arcpy.mapping.ListDataFrames(mxdMM_wells)[0]
            dfMM_wells.spatialReference = spatialRef
            for item in dsoid_wells:
                addBuffertoMxd("buffer_"+item, dfMM_wells)

            #addBuffertoMxd("buffer_"+dsoid_wells_maxradius,dfMM_wells)
            addOrdergeomtoMxd("ordergeoNamePR", dfMM_wells)
            gridlayerMM = arcpy.mapping.ListLayers(mxdMM_wells,"Grid" ,dfMM_wells)[0]
            gridlayerMM.replaceDataSource(scratch, "FILEGDB_WORKSPACE","gridlr_wells")
            arcpy.CalculateAdjacentFields_cartography(gridlrshp, "PageNumber")
            lyr = arcpy.mapping.ListLayers(mxdMM_wells, "wells", dfMM_wells)[0]   #"wells" or "Wells" doesn't seem to matter
            lyr.replaceDataSource(scratchfolder,"SHAPEFILE_WORKSPACE", "wells_disp")

            for i in range(1,int(arcpy.GetCount_management(gridlrshp).getOutput(0))+1):
                arcpy.SelectLayerByAttribute_management(gridlayerMM, "NEW_SELECTION", ' "PageNumber" =  ' + str(i))
                dfMM_wells.extent = gridlayerMM.getSelectedExtent(True)
                dfMM_wells.scale = dfMM_wells.scale * 1.1
                arcpy.SelectLayerByAttribute_management(gridlayerMM, "CLEAR_SELECTION")
                titleTextE = arcpy.mapping.ListLayoutElements(mxdMM_wells, "TEXT_ELEMENT", "MainTitleText")[0]
                titleTextE.text = "Wells & Additional Sources - Page " + str(i)
                titleTextE.elementPositionX = 0.6438
                arcpy.RefreshTOC()
                arcpy.mapping.ExportToJPEG(mxdMM_wells, outputjpg_wells[0:-4]+str(i)+".jpg", "PAGE_LAYOUT", 480, 640, 150, "False", "24-BIT_TRUE_COLOR", 85)
                if not os.path.exists(os.path.join(report_path, 'PSRmaps', OrderNumText)):
                    os.mkdir(os.path.join(report_path, 'PSRmaps', OrderNumText))
                shutil.copy(outputjpg_wells[0:-4]+str(i)+".jpg", os.path.join(report_path, 'PSRmaps', OrderNumText))
            del mxdMM_wells
            del dfMM_wells

        # send wells data to Oracle
        if (int(arcpy.GetCount_management(wells_sja).getOutput(0))== 0):
            # no records selected....
            print 'No well records are selected....'
            try:
                con = cx_Oracle.connect(connectionString)
                cur = con.cursor()
                query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'WELLS', OrderNumText+'_US_WELLS.jpg', 1))          #note type 'SOIL' or 'GEOL' is used internally
            finally:
                cur.close()
                con.close()
        else:
            try:
                con = cx_Oracle.connect(connectionString)
                cur = con.cursor()

                in_rows = arcpy.SearchCursor(wells_sja)
                for in_row in in_rows:
                    erisid = str(int(in_row.ID))
                    DS_OID=str(int(in_row.DS_OID))
                    Distance = str(float(in_row.Distance))
                    Direction = str(in_row.Direction)
                    Elevation = str(float(in_row.Elevation))
                    Elevatio_1 = str(float(in_row.Elevation) - float(in_row.Elevatio_1))
                    MapKeyLoc = str(int(in_row.MapKeyLoc))
                    MapKeyNo = str(int(in_row.MapKeyNo))

                    cur.callproc('eris_psr.InsertOrderDetail', (OrderIDText, erisid,DS_OID,Distance,Direction,Elevation,Elevatio_1,MapKeyLoc,MapKeyNo))
                del in_row
                del in_rows

                query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'WELLS', OrderNumText+'_US_WELLS.jpg', 1))          #note type 'SOIL' or 'GEOL' is used internally
                if multipage_wells == True:
                    for i in range(1,page):
                        query = cur.callproc('eris_psr.InsertMap', (OrderIDText, 'WELLS', OrderNumText+'_US_WELLS'+str(i)+'.jpg', i+1))
            finally:
                cur.close()
                con.close()


        ## Radon
        print "--- starting Radon section " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        bufferSHP_radon = os.path.join(scratchfolder,"buffer_radon.shp")
        arcpy.Buffer_analysis(orderGeometryPR, bufferSHP_radon, bufferDist_radon)

        states_clip =os.path.join(scratchfolder,'states.shp')
        arcpy.Clip_analysis(masterlyr_states, bufferSHP_radon, states_clip)

        counties_clip =os.path.join(scratchfolder,'counties.shp')
        arcpy.Clip_analysis(masterlyr_counties, bufferSHP_radon, counties_clip)

        cities_clip =os.path.join(scratchfolder,'cities.shp')
        arcpy.Clip_analysis(masterlyr_cities, bufferSHP_radon, cities_clip)

        zipcodes_clip =os.path.join(scratchfolder,'zipcodes.shp')
        arcpy.Clip_analysis(masterlyr_zipcodes, bufferSHP_radon, zipcodes_clip)

        statelist = ''
        in_rows = arcpy.SearchCursor(states_clip)
        for in_row in in_rows:
            print in_row.STUSPS
            statelist = statelist+ ',' + in_row.STUSPS
        statelist = statelist.strip(',')        #two letter state
        statelist_str = str(statelist)
        del in_rows
        del in_row

        countylist = ''
        in_rows = arcpy.SearchCursor(counties_clip)
        for in_row in in_rows:
            #print in_row.NAME
            countylist = countylist + ','+in_row.NAME
        countylist = countylist.strip(',')
        countylist_str = str(countylist.replace(u'\xed','i').replace(u'\xe1','a').replace(u'\xf1','n'))
        del in_rows
        if 'in_row' in locals():     #sometimes returns no city
            del in_row


        citylist = ''
        in_rows = arcpy.SearchCursor(cities_clip)
        for in_row in in_rows:
            #print in_row.NAME
            citylist = citylist + ','+in_row.NAME
        citylist = citylist.strip(',')
        del in_rows
        if 'in_row' in locals():     #sometimes returns no city
            del in_row

        if 'NH' in statelist:
            towns_clip =os.path.join(scratchfolder,'towns.shp')
            arcpy.Clip_analysis(masterlyr_NHTowns, bufferSHP_radon, towns_clip)
            in_rows = arcpy.SearchCursor(towns_clip)
            for in_row in in_rows:
                print in_row.NAME
                citylist = citylist + ','+in_row.NAME
            citylist = citylist.strip(',')
            del in_rows
            if 'in_row' in locals():     #sometimes returns no city
                del in_row
        citylist_str = str(citylist.replace(u'\xed','i').replace(u'\xe1','a').replace(u'\xf1','n'))

        ziplist = ''
        in_rows = arcpy.SearchCursor(zipcodes_clip)
        for in_row in in_rows:
            print in_row.ZIP
            ziplist = ziplist + ',' + in_row.ZIP
        ziplist = ziplist.strip(',')
        ziplist_str = str(ziplist)
        del in_rows
        if 'in_row' in locals():
            del in_row

        try:
            con = cx_Oracle.connect(connectionString)
            cur = con.cursor()
            ###cur.callproc('eris_psr.ClearOrder', (OrderIDText,))

            cur.callproc('eris_psr.GetRadon', (OrderIDText, statelist_str, ziplist_str, countylist_str, citylist_str))

        finally:
            cur.close()
            con.close()


    ##aspect calculation ###############################
        i=0
        imgs = []
        masterLayer_dem = arcpy.mapping.Layer(masterlyr_dem)
        bufferDistance = "0.25 MILES"
        arcpy.AddField_management(orderCentreSHP, "Aspect",  "TEXT", "", "", "1500", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.AddXY_management(orderCentreSHP)
        outBufferSHP = os.path.join(scratchfolder, "siteMarker_Buffer.shp")
        arcpy.Buffer_analysis(orderCentreSHP, outBufferSHP, bufferDistance)
        arcpy.DefineProjection_management(outBufferSHP, out_coordinate_system)
        arcpy.SelectLayerByLocation_management(masterLayer_dem, 'intersect', outBufferSHP)

        if (int((arcpy.GetCount_management(masterLayer_dem).getOutput(0)))== 0):
            print "NO records selected for US"
            columns = arcpy.UpdateCursor(orderCentreSHP)
            for column in columns:
                column.Aspect = "Not Available"
            del column
            del columns
            masterLayer_buffer = None

        else:
            # loop through the relevant records, locate the selected cell IDs
            columns = arcpy.SearchCursor(masterLayer_dem)
            for column in columns:
                img = column.getValue("image_name")
                if img ==" ":
                    print "no image found"
                else:
                    imgs.append(os.path.join(imgdir_dem,img))
                    i = i+1
                    print "found img " + img
            del column
            del columns
        if i==0:
    ##        imgdir_demCA = r"\\Cabcvan1gis001\US_DEM\DEM1"
    ##        masterlyr_demCA = r"\\Cabcvan1gis001\US_DEM\Canada_DEM_edited.shp"
            masterLayer_dem = arcpy.mapping.Layer(masterlyr_demCA)
            arcpy.SelectLayerByLocation_management(masterLayer_dem, 'intersect', outBufferSHP)
            if int((arcpy.GetCount_management(masterLayer_dem).getOutput(0))) != 0:

                columns = arcpy.SearchCursor(masterLayer_dem)
                for column in columns:
                    img = column.getValue("image_name")
                    if img.strip() !="":
                        imgs.append(os.path.join(imgdir_demCA,img))
                        print "found img " + img
                        i = i+1
                del column
                del columns

        if i >=1:

                if i>1:
                    clipped_img=''
                    n = 1
                    for im in imgs:
                        clip_name ="clip_img_"+str(n)+".img"
                        arcpy.Clip_management(im, "#",os.path.join(scratchfolder, clip_name),outBufferSHP,"#","NONE", "MAINTAIN_EXTENT")
                        clipped_img = clipped_img + os.path.join(scratchfolder, clip_name)+ ";"
                        n =n +1

                    img = "img.img"
                    arcpy.MosaicToNewRaster_management(clipped_img[0:-1],scratchfolder, img,out_coordinate_system, "32_BIT_FLOAT", "#","1", "FIRST", "#")
                elif i ==1:
                    im = imgs[0]
                    img = "img.img"
                    arcpy.Clip_management(im, "#",os.path.join(scratchfolder,img),outBufferSHP,"#","NONE", "MAINTAIN_EXTENT")
                arr =  arcpy.RasterToNumPyArray(os.path.join(scratchfolder,img))

                x,y = gradient(arr)
                slope = 57.29578*arctan(sqrt(x*x + y*y))
                aspect = 57.29578*arctan2(-x,y)

                for i in range(len(aspect)):
                        for j in range(len(aspect[i])):
                            if -180 <=aspect[i][j] <= -90:
                                aspect[i][j] = -90-aspect[i][j]
                            else :
                                aspect[i][j] = 270 - aspect[i][j]
                            if slope[i][j] ==0:
                                aspect[i][j] = -1

                # gather some information on the original file
                spatialref = arcpy.Describe(os.path.join(scratchfolder,img)).spatialReference
                cellsize1  = arcpy.Describe(os.path.join(scratchfolder,img)).meanCellHeight
                cellsize2  = arcpy.Describe(os.path.join(scratchfolder,img)).meanCellWidth
                extent     = arcpy.Describe(os.path.join(scratchfolder,img)).Extent
                pnt        = arcpy.Point(extent.XMin,extent.YMin)

                # save the raster
                aspect_tif = os.path.join(scratchfolder,"aspect.tif")
                aspect_ras = arcpy.NumPyArrayToRaster(aspect,pnt,cellsize1,cellsize2)
                arcpy.CopyRaster_management(aspect_ras,aspect_tif)
                arcpy.DefineProjection_management(aspect_tif, spatialref)


                slope_tif = os.path.join(scratchfolder,"slope.tif")
                slope_ras = arcpy.NumPyArrayToRaster(slope,pnt,cellsize1,cellsize2)
                arcpy.CopyRaster_management(slope_ras,slope_tif)
                arcpy.DefineProjection_management(slope_tif, spatialref)

                aspect_tif_prj = os.path.join(scratchfolder,"aspect_prj.tif")
                arcpy.ProjectRaster_management(aspect_tif,aspect_tif_prj, out_coordinate_system)

                rows = arcpy.da.UpdateCursor(orderCentreSHP,["POINT_X","POINT_Y","Aspect"])
                for row in rows:
                    pointX = row[0]
                    pointY = row[1]
                    location = str(pointX)+" "+str(pointY)
                    asp = arcpy.GetCellValue_management(aspect_tif_prj,location)

                    if asp.getOutput((0)) != "NoData":
                        asp_text = getDirectionText.dgrDir2txt(float(asp.getOutput((0))))
                        if float(asp.getOutput((0))) == -1:
                            asp_text = r'N/A'
                        row[2] = asp_text
                        print "assign "+asp_text
                        rows.updateRow(row)
                    else:
                        print "fail to use point XY to retrieve"
                        row[2] =-9999
                        print "assign -9999"
                        rows.updateRow(row)
                        raise ValueError('No aspect retrieved CHECK data spatial reference')
                del row
                del rows

        in_rows = arcpy.SearchCursor(orderCentreSHP)
        for in_row in in_rows:
            # there is only one line
            site_elev =  in_row.Elevation
            UTM_X = in_row.POINT_X
            UTM_Y = in_row.POINT_Y
            Aspect = in_row.Aspect
        del in_row
        del in_rows

        in_rows = arcpy.SearchCursor(orderGeometryPR)
        for in_row in in_rows:
            # there is only one line
            UTM_Zone = str(in_row.UTM)[32:44]
        del in_row
        del in_rows



        needViewer = 'N'
        try:
            con = cx_Oracle.connect(connectionString)
            cur = con.cursor()

            cur.execute("select psr_viewer from order_viewer where order_id =" + str(OrderIDText))
            t = cur.fetchone()
            if t != None:
                needViewer = t[0]

        finally:
            cur.close()
            con.close()

        if needViewer == 'Y':
            #clip wetland, flood, geology, soil and covnert .lyr to kml
            #for now, use clipFrame_topo to clip
            #added clip current topo
            viewerdir_kml = os.path.join(scratchfolder,OrderNumText+'_psrkml')
            if not os.path.exists(viewerdir_kml):
                os.mkdir(viewerdir_kml)
            viewerdir_topo = os.path.join(scratchfolder,OrderNumText+'_psrtopo')
            if not os.path.exists(viewerdir_topo):
                os.mkdir(viewerdir_topo)
            viewertemp =os.path.join(scratchfolder,'viewertemp')
            if not os.path.exists(viewertemp):
                os.mkdir(viewertemp)

            viewerdir_relief = os.path.join(scratchfolder,OrderNumText+'_psrrelief')
            if not os.path.exists(viewerdir_relief):
                os.mkdir(viewerdir_relief)

            datalyr_wetland = PSR_config.datalyr_wetland#r"E:\GISData\PSR\python\mxd\wetland_kml.lyr"
            datalyr_flood = PSR_config.datalyr_flood#r"E:\GISData\PSR\python\mxd\flood.lyr"
            datalyr_geology = PSR_config.datalyr_geology#r"E:\GISData\PSR\python\mxd\geology.lyr"
            masterfilesoil = os.path.join(datapath_soil,'MUPOLYGON')
            srGoogle = arcpy.SpatialReference(3857)   #web mercator
            srWGS84 = arcpy.SpatialReference(4326)   #WGS84

    ################################
            #wetland
            wetlandclip = os.path.join(scratch, "wetlandclip")
            mxdname = glob.glob(os.path.join(scratchfolder,'mxd_wetland.mxd'))[0]
            mxd = arcpy.mapping.MapDocument(mxdname)
            df = arcpy.mapping.ListDataFrames(mxd,"big")[0]    # the spatial reference here is UTM zone #, need to change to WGS84 Web Mercator
            df.spatialReference = srWGS84
            if siteState == 'AK':
                df.spatialReference = srGoogle
            #re-focus using Buffer layer for multipage
            if multipage_wetland == True:
                bufferLayer = arcpy.mapping.ListLayers(mxd, "Buffer", df)[0]
                df.extent = bufferLayer.getSelectedExtent(False)
                df.scale = df.scale * 1.1

            dfAsFeature = arcpy.Polygon(arcpy.Array([df.extent.lowerLeft, df.extent.lowerRight, df.extent.upperRight, df.extent.upperLeft]),
                                df.spatialReference)    #df.spatialReference is currently UTM. dfAsFeature is a feature, not even a layer
            del df, mxd
            wetland_boudnary = os.path.join(scratch,"Extent_wetland_WGS84")
            arcpy.Project_management(dfAsFeature, wetland_boudnary, srWGS84)
            arcpy.Clip_analysis(datalyr_wetland, wetland_boudnary, wetlandclip)
            del dfAsFeature

            if int(arcpy.GetCount_management(wetlandclip).getOutput(0)) != 0:
                arcpy.AddField_management(wetland_boudnary,"WETLAND_TYPE", "TEXT", "", "", "15", "", "NULLABLE", "NON_REQUIRED", "")
                wetlandclip1 = os.path.join(scratch, "wetlandclip1")
                arcpy.Union_analysis([wetlandclip,wetland_boudnary],wetlandclip1)

                keepFieldList = ("WETLAND_TYPE")
                fieldInfo = ""
                fieldList = arcpy.ListFields(wetlandclip1)
                for field in fieldList:
                    if field.name in keepFieldList:
                        if field.name == 'WETLAND_TYPE':
                            fieldInfo = fieldInfo + field.name + " " + "Wetland Type" + " VISIBLE;"
                        else:
                            pass
                    else:
                        fieldInfo = fieldInfo + field.name + " " + field.name + " HIDDEN;"
    ##            print fieldInfo

                arcpy.MakeFeatureLayer_management(wetlandclip1, r"wetlandclip_lyr", "", "", fieldInfo[:-1])
                arcpy.ApplySymbologyFromLayer_management(r"wetlandclip_lyr", datalyr_wetland)
                arcpy.LayerToKML_conversion(r"wetlandclip_lyr", os.path.join(viewerdir_kml,"wetlandclip.kmz"))
                arcpy.Delete_management(r"wetlandclip_lyr")
            else:
                print "no wetland data, no kml to folder"
                arcpy.MakeFeatureLayer_management(wetlandclip, r"wetlandclip_lyr")
                arcpy.LayerToKML_conversion(r"wetlandclip_lyr", os.path.join(viewerdir_kml,"wetlandclip_nodata.kmz"))
                arcpy.Delete_management(r"wetlandclip_lyr")
    # #######################################################################
           # NY wetland
            if ProvStateText == 'NY':
                wetlandclipNY = os.path.join(scratch, "wetlandclipNY")
                mxdname = glob.glob(os.path.join(scratchfolder,'mxd_wetlandNY.mxd'))[0]
                mxd = arcpy.mapping.MapDocument(mxdname)
                df = arcpy.mapping.ListDataFrames(mxd,"big")[0]    # the spatial reference here is UTM zone #, need to change to WGS84 Web Mercator
                df.spatialReference = srWGS84
                if multipage_wetland == True:
                    bufferLayer = arcpy.mapping.ListLayers(mxd, "Buffer", df)[0]
                    df.extent = bufferLayer.getSelectedExtent(False)
                    df.scale = df.scale * 1.1

                del df, mxd
                wetland_boudnary = os.path.join(scratch,"Extent_wetland_WGS84")
                datalyr_wetlandNYkml = PSR_config.datalyr_wetlandNYkml
                arcpy.Clip_analysis(datalyr_wetlandNYkml, wetland_boudnary, wetlandclipNY)
                if int(arcpy.GetCount_management(wetlandclipNY).getOutput(0)) != 0:
    ##                #arcpy.AddField_management(wetlandclipNY,"WETLAND_TYPE", "TEXT", "", "", "15", "", "NULLABLE", "NON_REQUIRED", "")
    ##                rows = arcpy.UpdateCursor(wetlandclipNY)
    ##                for row in rows:
    ##                    class_text = row.CLASS
    ##                    row.WETLAND_TYPE = str(class_text)
    ##                    rows.updateRow(row)
                    wetlandclip1NY = os.path.join(scratch, "wetlandclip1NY")
                    arcpy.Union_analysis([wetlandclipNY,wetland_boudnary],wetlandclip1NY)


                    keepFieldList = ("CLASS")
                    fieldInfo = ""
                    fieldList = arcpy.ListFields(wetlandclip1NY)
                    for field in fieldList:
                        if field.name in keepFieldList:
                            if field.name == 'CLASS':
                                fieldInfo = fieldInfo + field.name + " " + "Wetland CLASS" + " VISIBLE;"
                            else:
                                pass
                        else:
                            fieldInfo = fieldInfo + field.name + " " + field.name + " HIDDEN;"
    ##                print fieldInfo

                    arcpy.MakeFeatureLayer_management(wetlandclip1NY, r"wetlandclipNY_lyr", "", "", fieldInfo[:-1])
                    arcpy.ApplySymbologyFromLayer_management(r"wetlandclipNY_lyr", datalyr_wetlandNYkml)
                    arcpy.LayerToKML_conversion(r"wetlandclipNY_lyr", os.path.join(viewerdir_kml,"w_NYwetland.kmz"))
                    #arcpy.SaveToLayerFile_management(r"wetlandclipNY_lyr",os.path.join(scratchfolder,"NYwetland.lyr"))
                    arcpy.Delete_management(r"wetlandclipNY_lyr")
                else:
                    print "no wetland data, no kml to folder"
                    arcpy.MakeFeatureLayer_management(wetlandclipNY, r"wetlandclip_lyrNY")
                    arcpy.LayerToKML_conversion(r"wetlandclip_lyrNY", os.path.join(viewerdir_kml,"w_NYwetland_nodata.kmz"))
                    arcpy.Delete_management(r"wetlandclip_lyrNY")

    #################################
                datalyr_wetlandNYAPAkml = PSR_config.datalyr_wetlandNYAPAkml
                wetlandclipNYAPA = os.path.join(scratch, "wetlandclipNYAPA")
                arcpy.Clip_analysis(datalyr_wetlandNYAPAkml, wetland_boudnary, wetlandclipNYAPA)
                if int(arcpy.GetCount_management(wetlandclipNYAPA).getOutput(0)) != 0:
                    wetlandclipNYAPA1 = os.path.join(scratch, "wetlandclipNYAPA1")
                    arcpy.Union_analysis([wetlandclipNYAPA,wetland_boudnary],wetlandclipNYAPA1)

                    keepFieldList = ("ERIS_WTLD")
                    fieldInfo = ""
                    fieldList = arcpy.ListFields(wetlandclipNYAPA)
                    for field in fieldList:
                        if field.name in keepFieldList:
                            if field.name == 'ERIS_WTLD':
                                fieldInfo = fieldInfo + field.name + " " + "Wetland CLASS" + " VISIBLE;"
                            else:
                                pass
                        else:
                            fieldInfo = fieldInfo + field.name + " " + field.name + " HIDDEN;"
    ##                print fieldInfo

                    arcpy.MakeFeatureLayer_management(wetlandclipNYAPA1, r"wetlandclipNYAPA1_lyr", "", "", fieldInfo[:-1])
                    arcpy.ApplySymbologyFromLayer_management(r"wetlandclipNYAPA1_lyr", datalyr_wetlandNYAPAkml)
                    arcpy.LayerToKML_conversion(r"wetlandclipNYAPA1_lyr", os.path.join(viewerdir_kml,"w_APAwetland.kmz"))
                    #arcpy.SaveToLayerFile_management(r"wetlandclipNYAPA1_lyr",os.path.join(scratchfolder,"APAwetland.lyr"))
                    arcpy.Delete_management(r"wetlandclipNYAPA1_lyr")
                else:
                    print "no wetland data, no kml to folder"
                    arcpy.MakeFeatureLayer_management(wetlandclipNYAPA, r"wetlandclip_lyrNYAPA")
                    arcpy.LayerToKML_conversion(r"wetlandclip_lyrNYAPA", os.path.join(viewerdir_kml,"w_APAwetland_nodata.kmz"))
                    arcpy.Delete_management(r"wetlandclip_lyrNYAPA")
    ###############################
            #flood
            if not noFlood:
                floodclip1 = os.path.join(scratch, "floodclip1")
                mxdname = glob.glob(os.path.join(scratchfolder,'mxd_flood.mxd'))[0]
                mxd = arcpy.mapping.MapDocument(mxdname)
                df = arcpy.mapping.ListDataFrames(mxd,"Flood Hazard Zone")[0]    # the spatial reference here is UTM zone #, need to change to WGS84 Web Mercator
                df.spatialReference = srWGS84
                if siteState == 'AK':
                    df.spatialReference = srGoogle
                if multipage_flood == True:
                    bufferLayer = arcpy.mapping.ListLayers(mxd, "Buffer", df)[0]
                    df.extent = bufferLayer.getSelectedExtent(False)
                    df.scale = df.scale * 1.1

                dfAsFeature = arcpy.Polygon(arcpy.Array([df.extent.lowerLeft, df.extent.lowerRight, df.extent.upperRight, df.extent.upperLeft]),
                                    df.spatialReference)    #df.spatialReference is currently UTM. dfAsFeature is a feature, not even a layer
                del df, mxd
                arcpy.Project_management(dfAsFeature, os.path.join(viewertemp,"Extent_flood_WGS84.shp"), srWGS84)

        ##        try:
        ##            data_flood = PSR_config.data_flood
        ##            #arcpy.Clip_analysis(data_flood, os.path.join(viewertemp,"Extent_flood_WGS84.shp"), floodclip)
        ##            #arcpy.Clip_analysis(os.path.join(scratch, "flood"), os.path.join(viewertemp,"Extent_flood_WGS84.shp"), floodclip)
        ##            masterLayer_flood = arcpy.mapping.Layer(data_flood)
        ##            arcpy.SelectLayerByLocation_management(masterLayer_flood, 'intersect', os.path.join(viewertemp,"Extent_flood_WGS84.shp"))
        ##            if int((arcpy.GetCount_management(masterLayer_flood).getOutput(0))) != 0:
        ##                arcpy.CopyFeatures_management(masterLayer_flood,floodclip1)
        ##                arcpy.Generalize_edit(floodclip1,"40 FEET")
        ##            del masterLayer_flood
        ##
        ##        except:
        ##            print("Unexpected error:", sys.exc_info()[0])
        ##            raise

                del dfAsFeature
                floodclip = os.path.join(scratch, "floodclip")
                arcpy.Clip_analysis(PSR_config.data_flood, os.path.join(viewertemp,"Extent_flood_WGS84.shp"), floodclip)
                if int(arcpy.GetCount_management(floodclip).getOutput(0)) != 0:
                    arcpy.AddField_management(floodclip, "CLASS", "TEXT", "", "", "15", "", "NULLABLE", "NON_REQUIRED", "")
                    arcpy.AddField_management(floodclip,"ERISBIID", "TEXT", "", "", "15", "", "NULLABLE", "NON_REQUIRED", "")
                    rows = arcpy.UpdateCursor(floodclip)
                    for row in rows:
                        row.CLASS = row.ERIS_CLASS
                        ID = [id[1] for id in flood_IDs if row.ERIS_CLASS==id[0]]
                        if ID !=[]:
                            row.ERISBIID = ID[0]
                            rows.updateRow(row)
                        rows.updateRow(row)
                    del rows
                    keepFieldList = ("ERISBIID","CLASS", "FLD_ZONE","ZONE_SUBTY")
                    fieldInfo = ""
                    fieldList = arcpy.ListFields(floodclip)
                    for field in fieldList:
                        if field.name in keepFieldList:
                            if field.name =='ERISBIID':
                                fieldInfo = fieldInfo + field.name + " " + "ERISBIID" + " VISIBLE;"
                            elif field.name == 'CLASS':
                                fieldInfo = fieldInfo + field.name + " " + "Flood Zone Label" + " VISIBLE;"
                            elif field.name == 'FLD_ZONE':
                                fieldInfo = fieldInfo + field.name + " " + "Flood Zone" + " VISIBLE;"
                            elif field.name == 'ZONE_SUBTY':
                                fieldInfo = fieldInfo + field.name + " " + "Zone Subtype" + " VISIBLE;"
                            else:
                                pass
                        else:
                            fieldInfo = fieldInfo + field.name + " " + field.name + " HIDDEN;"
        ##            print fieldInfo
                    arcpy.MakeFeatureLayer_management(floodclip, "floodclip_lyr", "", "", fieldInfo[:-1])
                    arcpy.ApplySymbologyFromLayer_management(r"floodclip_lyr", datalyr_flood)
                    arcpy.LayerToKML_conversion(r"floodclip_lyr", os.path.join(viewerdir_kml,"floodclip.kmz"))
                    arcpy.Delete_management("floodclip_lyr")
                else:
                    print "no flood data to kml"
                    arcpy.MakeFeatureLayer_management(floodclip, "floodclip_lyr")
                    arcpy.LayerToKML_conversion(r"floodclip_lyr", os.path.join(viewerdir_kml,"floodclip_nodata.kmz"))
                    arcpy.Delete_management("floodclip_lyr")

    #################################
            #geology
            geologyclip = os.path.join(scratch, "geologyclip")
            mxdname = glob.glob(os.path.join(scratchfolder,'mxd_geol.mxd'))[0]
            mxd = arcpy.mapping.MapDocument(mxdname)
            df = arcpy.mapping.ListDataFrames(mxd,"*")[0]    # the spatial reference here is UTM zone #, need to change to WGS84 Web Mercator
            df.spatialReference = srWGS84
            if siteState == 'AK':
                df.spatialReference = srGoogle
            if multipage_geology == True:
                bufferLayer = arcpy.mapping.ListLayers(mxd, "Buffer", df)[0]
                df.extent = bufferLayer.getSelectedExtent(False)
                df.scale = df.scale * 1.1

            dfAsFeature = arcpy.Polygon(arcpy.Array([df.extent.lowerLeft, df.extent.lowerRight, df.extent.upperRight, df.extent.upperLeft]),
                                df.spatialReference)    #df.spatialReference is currently UTM. dfAsFeature is a feature, not even a layer
            del df, mxd
            arcpy.Project_management(dfAsFeature, os.path.join(viewertemp,"Extent_geol_WGS84.shp"), srWGS84)
            arcpy.Clip_analysis(geol_clip, os.path.join(viewertemp,"Extent_geol_WGS84.shp"), geologyclip)
            del dfAsFeature

            if int(arcpy.GetCount_management(geologyclip).getOutput(0)) != 0:
                arcpy.AddField_management(geologyclip,"ERISBIID", "TEXT", "", "", "15", "", "NULLABLE", "NON_REQUIRED", "")
                rows = arcpy.UpdateCursor(geologyclip)
                for row in rows:
                    ID = [id[1] for id in geology_IDs if row.ERIS_KEY==id[0]]
                    if ID !=[]:
                        row.ERISBIID = ID[0]
                        rows.updateRow(row)
                del rows
                keepFieldList = ("ERISBIID","ORIG_LABEL", "UNIT_NAME", "UNIT_AGE","ROCKTYPE1", "ROCKTYPE2", "UNITDESC")
                fieldInfo = ""
                fieldList = arcpy.ListFields(geologyclip)
                for field in fieldList:
                    if field.name in keepFieldList:
                        if field.name =='ERISBIID':
                            fieldInfo = fieldInfo + field.name + " " + "ERISBIID" + " VISIBLE;"
                        elif field.name == 'ORIG_LABEL':
                            fieldInfo = fieldInfo + field.name + " " + "Geologic_Unit" + " VISIBLE;"
                        elif field.name == 'UNIT_NAME':
                            fieldInfo = fieldInfo + field.name + " " + "Name" + " VISIBLE;"
                        elif field.name == 'UNIT_AGE':
                            fieldInfo = fieldInfo + field.name + " " + "Age" + " VISIBLE;"
                        elif field.name == 'ROCKTYPE1':
                            fieldInfo = fieldInfo + field.name + " " + "Primary_Rock_Type" + " VISIBLE;"
                        elif field.name == 'ROCKTYPE2':
                            fieldInfo = fieldInfo + field.name + " " + "Secondary_Rock_Type" + " VISIBLE;"
                        elif field.name == 'UNITDESC':
                            fieldInfo = fieldInfo + field.name + " " + "Unit_Description" + " VISIBLE;"
                        else:
                            pass
                    else:
                        fieldInfo = fieldInfo + field.name + " " + field.name + " HIDDEN;"
    ##            print fieldInfo
                arcpy.MakeFeatureLayer_management(geologyclip, "geologyclip_lyr", "", "", fieldInfo[:-1])
                arcpy.ApplySymbologyFromLayer_management(r"geologyclip_lyr", datalyr_geology)
                arcpy.LayerToKML_conversion(r"geologyclip_lyr", os.path.join(viewerdir_kml,"geologyclip.kmz"))
                arcpy.Delete_management("geologyclip_lyr")
            else:
    ##            print "no geology data to kml"
                arcpy.MakeFeatureLayer_management(geologyclip, "geologyclip_lyr")
                arcpy.LayerToKML_conversion(r"geologyclip_lyr", os.path.join(viewerdir_kml,"geologyclip_nodata.kmz"))
                arcpy.Delete_management("geologyclip_lyr")

    #############################################################
            #soil
            if os.path.exists((os.path.join(scratchfolder,"mxd_soil.mxd"))):
                soilclip1 = os.path.join(scratch,"soilclip1")
                mxdname = glob.glob(os.path.join(scratchfolder,'mxd_soil.mxd'))[0]
                mxd = arcpy.mapping.MapDocument(mxdname)
                df = arcpy.mapping.ListDataFrames(mxd,"*")[0]    # the spatial reference here is UTM zone #, need to change to WGS84 Web Mercator
                df.spatialReference = srWGS84
                if siteState == 'AK':
                    df.spatialReference = srGoogle
                if multipage_soil == True:
                    bufferLayer = arcpy.mapping.ListLayers(mxd, "Buffer", df)[0]
                    df.extent = bufferLayer.getSelectedExtent(False)
                    df.scale = df.scale * 1.1

                dfAsFeature = arcpy.Polygon(arcpy.Array([df.extent.lowerLeft, df.extent.lowerRight, df.extent.upperRight, df.extent.upperLeft]),
                                    df.spatialReference)    #df.spatialReference is currently UTM. dfAsFeature is a feature, not even a layer
                del df, mxd
                arcpy.Project_management(dfAsFeature, os.path.join(viewertemp,"Extent_soil_WGS84.shp"), srWGS84)
                masterLayer_soil = arcpy.mapping.Layer(masterfilesoil)
                arcpy.SelectLayerByLocation_management(masterLayer_soil, 'intersect', os.path.join(viewertemp,"Extent_soil_WGS84.shp"))
                if int((arcpy.GetCount_management(masterLayer_soil).getOutput(0))) != 0:
                    arcpy.CopyFeatures_management(masterLayer_soil,soilclip1)
                    arcpy.Generalize_edit(soilclip1, "4 FEET")
                arcpy.Delete_management(masterLayer_soil)
                soilclip = os.path.join(scratch,"soilclip")
                arcpy.Clip_analysis(soilclip1, os.path.join(viewertemp,"Extent_soil_WGS84.shp"),soilclip)
                del dfAsFeature
                if int(arcpy.GetCount_management(soilclip).getOutput(0)) != 0:
                    arcpy.AddField_management(soilclip, "Map_Unit", "TEXT", "", "", "1500", "", "NULLABLE", "NON_REQUIRED", "")
                    arcpy.AddField_management(soilclip, "Map_Unit_Name", "TEXT", "", "", "1500", "", "NULLABLE", "NON_REQUIRED", "")
                    arcpy.AddField_management(soilclip, "Dominant_Drainage_Class", "TEXT", "", "", "1500", "", "NULLABLE", "NON_REQUIRED", "")
                    arcpy.AddField_management(soilclip, "Dominant_Hydrologic_Group", "TEXT", "", "", "1500", "", "NULLABLE", "NON_REQUIRED", "")
                    arcpy.AddField_management(soilclip, "Presence_Hydric_Classification", "TEXT", "", "", "1500", "", "NULLABLE", "NON_REQUIRED", "")
                    arcpy.AddField_management(soilclip, "Min_Bedrock_Depth", "TEXT", "", "", "1500", "", "NULLABLE", "NON_REQUIRED", "")
                    arcpy.AddField_management(soilclip, "Annual_Min_Watertable_Depth", "TEXT", "", "", "1500", "", "NULLABLE", "NON_REQUIRED", "")
                    arcpy.AddField_management(soilclip, "component", "TEXT", "", "", "2500", "", "NULLABLE", "NON_REQUIRED", "")
                    arcpy.AddField_management(soilclip,"ERISBIID", "TEXT", "", "", "15", "", "NULLABLE", "NON_REQUIRED", "")
                    rows = arcpy.UpdateCursor(soilclip)
                    for row in rows:
                        for mapunit in reportdata:
                            if row.musym == mapunit["Musym"]:
                                ID = [id[1] for id in soil_IDs if row.MUSYM==id[0]]
                                if ID !=[]:
                                    row.ERISBIID = ID[0]
                                    rows.updateRow(row)
                                for key in mapunit.keys():
                                    if key =="Musym":
                                        row.Map_Unit = mapunit[key]
                                    elif key == "Map Unit Name":
                                        row.Map_Unit_Name = mapunit[key]
                                    elif key == "Bedrock Depth - Min":
                                        row.Min_Bedrock_Depth = mapunit[key]
                                    elif key =="Drainage Class - Dominant":
                                        row.Dominant_Drainage_Class = mapunit[key]
                                    elif key =="Hydric Classification - Presence":
                                        row.Presence_Hydric_Classification = mapunit[key]
                                    elif key =="Hydrologic Group - Dominant":
                                        row.Dominant_Hydrologic_Group = mapunit[key]
                                    elif key =="Watertable Depth - Annual Min":
                                        row.Annual_Min_Watertable_Depth = mapunit[key]
                                    elif key =="component":
                                        new = ''
                                        component = mapunit[key]
                                        for i in range(len(component)):
                                            for j in range(len(component[i])):
                                                for k in range(len(component[i][j])):
                                                    new = new+component[i][j][k]+" "
                                        row.component = new
                                    else:
                                        pass
                                    rows.updateRow(row)
                    del rows

                    keepFieldList = ("ERISBIID","Map_Unit", "Map_Unit_Name", "Dominant_Drainage_Class","Dominant_Hydrologic_Group", "Presence_Hydric_Classification", "Min_Bedrock_Depth","Annual_Min_Watertable_Depth","component")
                    fieldInfo = ""
                    fieldList = arcpy.ListFields(soilclip)
                    for field in fieldList:
                        if field.name in keepFieldList:
                            if field.name =='ERISBIID':
                                fieldInfo = fieldInfo + field.name + " " + "ERISBIID" + " VISIBLE;"
                            elif field.name == 'Map_Unit':
                                fieldInfo = fieldInfo + field.name + " " + "Map_Unit" + " VISIBLE;"
                            elif field.name == 'Map_Unit_Name':
                                fieldInfo = fieldInfo + field.name + " " + "Map_Unit_Name" + " VISIBLE;"
                            elif field.name == 'Dominant_Drainage_Class':
                                fieldInfo = fieldInfo + field.name + " " + "Dominant_Drainage_Class" + " VISIBLE;"
                            elif field.name == 'Dominant_Hydrologic_Group':
                                fieldInfo = fieldInfo + field.name + " " + "Dominant_Hydrologic_Group" + " VISIBLE;"
                            elif field.name == 'Presence_Hydric_Classification':
                                fieldInfo = fieldInfo + field.name + " " + "Presence_Hydric_Classification" + " VISIBLE;"
                            elif field.name == 'Min_Bedrock_Depth':
                                fieldInfo = fieldInfo + field.name + " " + "Min_Bedrock_Depth" + " VISIBLE;"
                            elif field.name == 'Annual_Min_Watertable_Depth':
                                fieldInfo = fieldInfo + field.name + " " + "Annual_Min_Watertable_Depth" + " VISIBLE;"
                            elif field.name == 'component':
                                fieldInfo = fieldInfo + field.name + " " + "component" + " VISIBLE;"
                            else:
                                pass
                        else:
                            fieldInfo = fieldInfo + field.name + " " + field.name + " HIDDEN;"
        ##            print fieldInfo

                    arcpy.MakeFeatureLayer_management(soilclip, "soilclip_lyr","", "", fieldInfo[:-1])
                    soilsymbol_copy = os.path.join(scratchfolder,"soillyr_copy.lyr")
                    arcpy.SaveToLayerFile_management(soillyr,soilsymbol_copy[:-4])
                    arcpy.ApplySymbologyFromLayer_management(r"soilclip_lyr", soilsymbol_copy)
                    arcpy.LayerToKML_conversion(r"soilclip_lyr", os.path.join(viewerdir_kml,"soilclip.kmz"))
                    arcpy.Delete_management("soilclip_lyr")
                else:
                    print "no soil data to kml"
                    arcpy.MakeFeatureLayer_management(soilclip, "soilclip_lyr")
                    arcpy.LayerToKML_conversion(r"soilclip_lyr", os.path.join(viewerdir_kml,"soilclip_nodata.kmz"))
                    arcpy.Delete_management("soilclip_lyr")
    #############################################################
            #current topo clipping for Xplorer
            if os.path.exists((os.path.join(scratchfolder,"mxd_topo.mxd"))):
                mxdname = glob.glob(os.path.join(scratchfolder,'mxd_topo.mxd'))[0]
                mxd = arcpy.mapping.MapDocument(mxdname)
                df = arcpy.mapping.ListDataFrames(mxd,"*")[0]    # the spatial reference here is UTM zone #, need to change to WGS84 Web Mercator
                df.spatialReference = srWGS84
                if siteState == 'AK':
                    df.spatialReference = srGoogle
                if multipage_topo == True:
                    bufferLayer = arcpy.mapping.ListLayers(mxd, "Buffer", df)[0]
                    df.extent = bufferLayer.getSelectedExtent(False)
                    df.scale = df.scale * 1.1

                dfAsFeature = arcpy.Polygon(arcpy.Array([df.extent.lowerLeft, df.extent.lowerRight, df.extent.upperRight, df.extent.upperLeft]),
                                    df.spatialReference)
                del df, mxd
                arcpy.Project_management(dfAsFeature, os.path.join(viewertemp,"Extent_topo_WGS84.shp"), srWGS84)
                del dfAsFeature

                tomosaiclist = []
                n = 0
                for item in glob.glob(os.path.join(scratchfolder,'*_TM_geo.tif')):
                    try:
                        arcpy.Clip_management(item,"",os.path.join(viewertemp, "topo"+str(n)+".jpg"),os.path.join(viewertemp,"Extent_topo_WGS84.shp"),"255","ClippingGeometry")
                        tomosaiclist.append(os.path.join(viewertemp, "topo"+str(n)+".jpg"))
                        n = n+1
                    except Exception, e:
                        print str(e) + item     #possibly not in the clipframe


                imagename = str(year)+".jpg"
                if tomosaiclist !=[]:
                    arcpy.MosaicToNewRaster_management(tomosaiclist, viewerdir_topo,imagename,srGoogle,"","","3","MINIMUM","MATCH")
                    desc = arcpy.Describe(os.path.join(viewerdir_topo, imagename))
                    featbound = arcpy.Polygon(arcpy.Array([desc.extent.lowerLeft, desc.extent.lowerRight, desc.extent.upperRight, desc.extent.upperLeft]),
                                        desc.spatialReference)
                    del desc
                    tempfeat = os.path.join(scratchfolder, "imgbnd_"+str(year)+ ".shp")

                    arcpy.Project_management(featbound, tempfeat, srWGS84) #function requires output not be in_memory
                    del featbound
                    desc = arcpy.Describe(tempfeat)

                    metaitem = {}
                    metaitem['type'] = 'psrtopo'
                    metaitem['imagename'] = imagename
                    metaitem['lat_sw'] = desc.extent.YMin
                    metaitem['long_sw'] = desc.extent.XMin
                    metaitem['lat_ne'] = desc.extent.YMax
                    metaitem['long_ne'] = desc.extent.XMax

                    try:
                        con = cx_Oracle.connect(connectionString)
                        cur = con.cursor()

                        cur.execute("delete from overlay_image_info where  order_id = %s and (type = 'psrtopo')" % str(OrderIDText))

                        cur.execute("insert into overlay_image_info values (%s, %s, %s, %.5f, %.5f, %.5f, %.5f, %s, '', '')" % (str(OrderIDText), str(OrderNumText), "'" + metaitem['type']+"'", metaitem['lat_sw'], metaitem['long_sw'], metaitem['lat_ne'], metaitem['long_ne'],"'"+metaitem['imagename']+"'" ) )
                        con.commit()

                    finally:
                        cur.close()
                        con.close()



            if os.path.exists(os.path.join(viewertemp,"Extent_topo_WGS84.shp")):
                topoframe = os.path.join(viewertemp,"Extent_topo_WGS84.shp")
            else:
                topoframe =clipFrame_topo
            #clip relief map
            tomosaiclist = []
            n = 0
            for item in glob.glob(os.path.join(scratchfolder,'*_hs.img')):
                try:
                    arcpy.Clip_management(item,"",os.path.join(viewertemp, "relief"+str(n)+".jpg"),topoframe,"255","ClippingGeometry")
                    tomosaiclist.append(os.path.join(viewertemp, "relief"+str(n)+".jpg"))
                    n = n+1
                except Exception, e:
                    print str(e) + item     #possibly not in the clipframe


            imagename = "relief.jpg"
            if tomosaiclist != []:
                arcpy.MosaicToNewRaster_management(tomosaiclist, viewerdir_relief,imagename,srGoogle,"","","1","MINIMUM","MATCH")
                desc = arcpy.Describe(os.path.join(viewerdir_relief, imagename))
                featbound = arcpy.Polygon(arcpy.Array([desc.extent.lowerLeft, desc.extent.lowerRight, desc.extent.upperRight, desc.extent.upperLeft]),
                                    desc.spatialReference)
                del desc
                if 'year' not in locals():
                    year = '0'
                tempfeat = os.path.join(scratchfolder, "imgbnd_"+str(year)+ ".shp")

                arcpy.Project_management(featbound, tempfeat, srWGS84) #function requires output not be in_memory
                del featbound
                desc = arcpy.Describe(tempfeat)
                metaitem = {}
                metaitem['type'] = 'psrrelief'
                metaitem['imagename'] = imagename

                metaitem['lat_sw'] = desc.extent.YMin
                metaitem['long_sw'] = desc.extent.XMin
                metaitem['lat_ne'] = desc.extent.YMax
                metaitem['long_ne'] = desc.extent.XMax

                try:
                    con = cx_Oracle.connect(connectionString)
                    cur = con.cursor()

                    cur.execute("delete from overlay_image_info where  order_id = %s and (type = 'psrrelief')" % str(OrderIDText))

                    cur.execute("insert into overlay_image_info values (%s, %s, %s, %.5f, %.5f, %.5f, %.5f, %s, '', '')" % (str(OrderIDText), str(OrderNumText), "'" + metaitem['type']+"'", metaitem['lat_sw'], metaitem['long_sw'], metaitem['lat_ne'], metaitem['long_ne'],"'"+metaitem['imagename']+"'" ) )
                    con.commit()

                finally:
                    cur.close()
                    con.close()



            #clip contour lines
            contourclip = os.path.join(scratch, "contourclip")
            arcpy.Clip_analysis(datalyr_contour,topoframe, contourclip)

            if int(arcpy.GetCount_management(contourclip).getOutput(0)) != 0:

                keepFieldList = ("CONTOURELE")
                fieldInfo = ""
                fieldList = arcpy.ListFields(contourclip)
                for field in fieldList:
                    if field.name in keepFieldList:
                        if field.name == 'CONTOURELE':
                            fieldInfo = fieldInfo + field.name + " " + "elevation" + " VISIBLE;"
                        else:
                            pass
                    else:
                        fieldInfo = fieldInfo + field.name + " " + field.name + " HIDDEN;"
    ##            print fieldInfo

                arcpy.MakeFeatureLayer_management(contourclip, r"contourclip_lyr", "", "", fieldInfo[:-1])
                arcpy.ApplySymbologyFromLayer_management(r"contourclip_lyr", datalyr_contour)
                arcpy.LayerToKML_conversion(r"contourclip_lyr", os.path.join(viewerdir_relief,"contourclip.kmz"))
                arcpy.Delete_management(r"contourclip_lyr")
            else:
                print "no contour data, no kml to folder"
                arcpy.MakeFeatureLayer_management(contourclip, r"contourclip_lyr")
                arcpy.LayerToKML_conversion(r"contourclip_lyr", os.path.join(viewerdir_relief,"contourclip_nodata.kmz"))
                arcpy.Delete_management(r"contourclip_lyr")


            if os.path.exists(os.path.join(viewer_path, OrderNumText+"_psrkml")):
                shutil.rmtree(os.path.join(viewer_path, OrderNumText+"_psrkml"))
            shutil.copytree(os.path.join(scratchfolder, OrderNumText+"_psrkml"), os.path.join(viewer_path, OrderNumText+"_psrkml"))
            url = upload_link + "PSRKMLUpload?ordernumber=" + OrderNumText
            urllib.urlopen(url)

            if os.path.exists(os.path.join(viewer_path, OrderNumText+"_psrtopo")):
                shutil.rmtree(os.path.join(viewer_path, OrderNumText+"_psrtopo"))
            shutil.copytree(os.path.join(scratchfolder, OrderNumText+"_psrtopo"), os.path.join(viewer_path, OrderNumText+"_psrtopo"))
            url = upload_link + "PSRTOPOUpload?ordernumber=" + OrderNumText
            urllib.urlopen(url)

            if os.path.exists(os.path.join(viewer_path, OrderNumText+"_psrrelief")):
                shutil.rmtree(os.path.join(viewer_path, OrderNumText+"_psrrelief"))
            shutil.copytree(os.path.join(scratchfolder, OrderNumText+"_psrrelief"), os.path.join(viewer_path, OrderNumText+"_psrrelief"))
            url = upload_link + "ReliefUpload?ordernumber=" + OrderNumText
            urllib.urlopen(url)

        try:
            con = cx_Oracle.connect(connectionString)
            cur = con.cursor()

            cur.callproc('eris_psr.UpdateOrder', (OrderIDText, UTM_Y, UTM_X, UTM_Zone, site_elev,Aspect))
            cur.callfunc('eris_psr.RunPSR', str, (OrderIDText,))
    ##        if result == 'Y':
    ##            print 'report generation success'
    ##        else:
    ##            print 'report generation failure'
    ##            cur.callproc('eris_psr.InsertPSRAudit', (OrderIDText, 'python-RunPSR','Report Failure returned'))

        finally:
            cur.close()
            con.close()

    ##    if result == 'Y':
    ##        if not os.path.exists(reportcheck_path + r'\\'+OrderNumText+'_US_PSR.pdf'):
    ##            time.sleep(10)
    ##            print 'sleep for ten seconds'
    ##            arcpy.AddWarning('pdf not there, sleep for ten seconds')
    ##    else:
    ##        raise ValueError('RunPSR returned "N"')  # this will make the program purposely fail

        print "Process completed " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    ##    shutil.copy(reportcheck_path + r'\\'+OrderNumText+'_US_PSR.pdf', scratchfolder)  # occasionally get permission denied issue here when running locally
        arcpy.SetParameterAsText(1, os.path.join(scratchfolder, OrderNumText+'_US_PSR.pdf'))



    except:
        print "redo "+ OrderIDText
        os.mkdir(os.path.join(r"E:\GISData_testing\test1","redo_%s"%OrderIDText))
##        # Get the traceback object
##        #
##        tb = sys.exc_info()[2]
##        tbinfo = traceback.format_tb(tb)[0]
##
##        # Concatenate information together concerning the error into a message string
##        #
##        pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
##        msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"
##
##
##        try:
##            con = cx_Oracle.connect(connectionString)
##            cur = con.cursor()
##            ###cur.callproc('eris_psr.ClearOrder', (OrderIDText,))
##
##
##            cur.callproc('eris_psr.InsertPSRAudit', (OrderIDText, 'python-Error Handling',pymsg))
##
##        finally:
##            cur.close()
##            con.close()
##
##        # Return python error messages for use in script tool or Python Window
##        #
##        arcpy.AddError("hit CC's error code in except: OrderID %s "%OrderIDText)
##        arcpy.AddError(pymsg)
##        arcpy.AddError(msgs)
##
##        # Print Python error messages for use in Python / Python Window
##        #
##        print pymsg + "\n"
##        print msgs
##        raise    #raise the error again
