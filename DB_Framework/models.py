import sys
import cx_Oracle
import db_connections
import arcpy

class Order(object):
    order_Id = ''
    order_num = ''
    address = ''
    geometry = arcpy.Geometry()
    def getbyId(self,order_Id):
        try:
            connectionString = db_connections.connectionString
            con = cx_Oracle.connect(connectionString)
            cur = con.cursor()
            cur.execute("select order_num, address1, city, provstate from orders where order_id =" + str(order_Id))
            row = cur.fetchone()
            orderObj = Order
            orderObj.order_Id = order_Id
            orderObj.order_num = str(row[0])
            orderObj.address = str(row[1])+","+str(row[2])+","+str(row[3])
            orderObj.geometry = orderObj.getGeometry()
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
            orderObj.order_Id = str(row[0])
            orderObj.order_num = order_num
            orderObj.address = str(row[1])+","+str(row[2])+","+str(row[3])
            orderObj.geometry = orderObj.getGeometry()
            return orderObj
        finally:
            cur.close()
            con.close()   
    @classmethod
    def getGeometry(self): # return geometry in WGS84 (GCS)
        srWGS84 = arcpy.SpatialReference('WGS 1984')
        orderFC = db_connections.orderFC
        orderGeom = arcpy.da.SearchCursor(orderFC,("SHAPE@"),"order_id = " + str(self.order_Id) ).next()[0]
        return orderGeom.projectAs(srWGS84)
    @classmethod
    def getPSR(self):
        try:
            connectionString = db_connections.connectionString
            con = cx_Oracle.connect(connectionString)
            cur = con.cursor()
            cur.execute("select OMR_OID, DS_OID, SEARCH_RADIUS, REPORT_SOURCE from order_radius_psr where order_id =" + str(self.order_Id))
            items = cur.fetchall()
            PSR_list = [] 
            i= 1
            for item in items:
                psrObj = PSR()
                psrObj.order_Id = self.order_Id
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
    type = ''
    search_radius = ''
    report_source = ''