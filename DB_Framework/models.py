import sys
import cx_Oracle
import db_connections
import arcpy
import numpy as np
import arcpy, os
from ast import literal_eval

class Order(object):
    Id = ''
    number = ''
    address = ''
    province = ''
    geometry = arcpy.Geometry()
    def get_by_Id(self,order_Id):
        try:
            connectionString = db_connections.connectionString
            con = cx_Oracle.connect(connectionString)
            cur = con.cursor()
            cur.execute("select order_num, address1, city, provstate from orders where order_id =" + str(order_Id))
            row = cur.fetchone()
            orderObj = Order
            orderObj.Id = order_Id
            orderObj.number = str(row[0])
            orderObj.address = str(row[1])+","+str(row[2])+","+str(row[3])
            orderObj.province = str(row[3])
            orderObj.geometry = orderObj.__getGeometry()
            return orderObj
        finally:
            cur.close()
            con.close()
    def getbyNumber(self,order_num):
        try:
            connectionString = db_connections.connectionString
            con = cx_Oracle.connect(connectionString)
            cur = con.cursor()
            cur.execute("select order_id, address1, city, provstate from orders where order_num = '" + str(order_num) + "'")
            row = cur.fetchone()
            orderObj = Order
            orderObj.Id = str(row[0])
            orderObj.number = order_num
            orderObj.address = str(row[1])+","+str(row[2])+","+str(row[3])
            orderObj.geometry = orderObj.__getGeometry()
            return orderObj
        finally:
            cur.close()
            con.close()   
    @classmethod
    def __getGeometry(self): # return geometry in WGS84 (GCS) / private function
        srWGS84 = arcpy.SpatialReference(4326)
        orderFC = db_connections.orderFC
        # orderGeom = arcpy.da.SearchCursor(orderFC,("SHAPE@"),"order_id = " + str(self.Id) ).next()[0]
        orderGeom = None
        if orderGeom == None:
            orderGeom = arcpy.Geometry()
            
            where = 'order_id = ' + str(self.Id)
            row = arcpy.da.SearchCursor(orderFC,("GEOMETRY_TYPE","GEOMETRY"),where).next()
            coord_string = ((row[1])[1:-1])
            coordinates = np.array(literal_eval(coord_string))
            geometry_type = row[0]
            if geometry_type.lower()== 'point':
                orderGeom = arcpy.Multipoint(arcpy.Array([arcpy.Point(*coords) for coords in coordinates]),srWGS84)
            elif geometry_type.lower() =='polyline':        
                orderGeom = arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in coordinates]),srWGS84)
            elif geometry_type.lower() =='polygon':
                orderGeom = arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in coordinates]),srWGS84)
        return orderGeom.projectAs(srWGS84)
    @classmethod
    def getPSR(self):
        try:
            connectionString = db_connections.connectionString
            con = cx_Oracle.connect(connectionString)
            cur = con.cursor()
            cur.execute("select OMR_OID, DS_OID, SEARCH_RADIUS, REPORT_SOURCE from order_radius_psr where order_id =" + str(self.Id))
            items = cur.fetchall()
            PSR_list = [] 
            i= 1
            for item in items:
                psrObj = PSR()
                psrObj.order_Id = self.Id
                psrObj.omi_Id = item[0]
                psrObj.ds_oId = item[1]
                if str(psrObj.ds_oId) == '10683':
                    psrObj.type = 'flood'
                elif str(psrObj.ds_oId) == '10684':
                    psrObj.type = 'wetland'
                elif str(psrObj.ds_oId) == '10685':
                    psrObj.type = 'geol'
                elif str(psrObj.ds_oId) == '9334':
                    psrObj.type = 'soil'
                elif str(psrObj.ds_oId) == '10689':
                    psrObj.type = 'radon'
                psrObj.search_radius = item[2]
                psrObj.report_source = item[3]

                PSR_list.append(psrObj)
                # print('%s. DS_Id = %s, radius= %s, reportsource = %s' %(i, psrObj.dsoid,psrObj.radius, psrObj.reportsource))
                i += 1
            return PSR_list
        finally:
            cur.close()
            con.close()
class PSR(object):
    order_Id = ''
    omi_Id = ''
    ds_oId = ''
    search_radius = ''
    report_source = ''
    type = ''
    def insert_report(orderObj,page_num):
        try:
            con = cx_Oracle.connect(db_connections.connectionString)
            cur = con.cursor()
            ### insert data into eris_maps_psr table
            print('Here call storeprocedure...')
            query = cur.callproc('eris_psr.InsertMap', (orderObj.Id, 'WETLAND', orderObj.number +'_NY_WETL'+str(page_num)+'.jpg', int(page_num)+1))
        finally:
            cur.close()
            con.close()