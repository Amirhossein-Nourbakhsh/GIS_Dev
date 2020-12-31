import sys
import cx_Oracle
import db_connections
import arcpy
import numpy as np
import arcpy, os
from ast import literal_eval

class Order(object):
    id = ''
    number = ''
    address = ''
    province = ''
    geometry = arcpy.Geometry()
    def get_by_Id(self,order_id):
        try:
            con = cx_Oracle.connect(db_connections.connection_string)
            cursor = con.cursor()
            cursor.execute("select order_num, address1, city, provstate from orders where order_id =" + str(order_id))
            row = cursor.fetchone()
            order_obj = Order
            order_obj.id = order_id
            order_obj.number = str(row[0])
            order_obj.address = str(row[1])+","+str(row[2])+","+str(row[3])
            order_obj.province = str(row[3])
            order_obj.geometry = order_obj.__getGeometry()
            return order_obj
        finally:
            cursor.close()
            con.close()
    def getbyNumber(self,order_num):
        try:
            con = cx_Oracle.connect(db_connections.connection_string)
            cur = con.cursor()
            cur.execute("select order_id, address1, city, provstate from orders where order_num = '" + str(order_num) + "'")
            row = cur.fetchone()
            order_obj = Order
            order_obj.id = str(row[0])
            order_obj.number = order_num
            order_obj.address = str(row[1])+","+str(row[2])+","+str(row[3])
            order_obj.geometry = order_obj.__getGeometry()
            return order_obj
        finally:
            cur.close()
            con.close()   
    @classmethod
    def __getGeometry(self): # return geometry in WGS84 (GCS) / private function
        srWGS84 = arcpy.SpatialReference(4326)
        order_fc = db_connections.order_fc
        # orderGeom = arcpy.da.SearchCursor(orderFC,("SHAPE@"),"order_id = " + str(self.Id) ).next()[0]
        orderGeom = None
        if orderGeom == None:
            orderGeom = arcpy.Geometry()
            
            where = 'order_id = ' + str(self.id)
            row = arcpy.da.SearchCursor(order_fc,("GEOMETRY_TYPE","GEOMETRY"),where).next()
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
    def get_psr(self):
        try:
            con = cx_Oracle.connect(db_connections.connection_string)
            cur = con.cursor()
            cur.execute("select OMR_OID, DS_OID, SEARCH_RADIUS, REPORT_SOURCE from order_radius_psr where order_id =" + str(self.id))
            items = cur.fetchall()
            PSR_list = [] 
            for item in items:
                psr_obj = PSR()
                psr_obj.order_id = self.id
                psr_obj.omi_id = item[0]
                psr_obj.ds_oid = item[1]
                if str(psr_obj.ds_oid) == '10683':
                    psr_obj.type = 'flood'
                elif str(psr_obj.ds_oid) == '10684':
                    psr_obj.type = 'wetland'
                elif str(psr_obj.ds_oid) == '10685':
                    psr_obj.type = 'geol'
                elif str(psr_obj.ds_oid) == '9334':
                    psr_obj.type = 'soil'
                elif str(psr_obj.ds_oid) == '10689':
                    psr_obj.type = 'radon'
                elif str(psr_obj.ds_oid) == '10695':
                    psr_obj.type = 'topo'
                if not psr_obj.type == None:
                    psr_obj.search_radius = item[2]
                    psr_obj.report_source = item[3]
                    PSR_list.append(psr_obj)
            return PSR_list
        finally:
            cur.close()
            con.close()
class PSR(object):
    order_id = ''
    omi_id = ''
    ds_oid = ''
    search_radius = ''
    report_source = ''
    type = None
    def insert_map(self,order_id,psr_type, psr_filename, p_seq_no):
        try:
            con = cx_Oracle.connect(db_connections.connection_string)
            cur = con.cursor()
            ### insert data into eris_maps_psr table
            cur.callproc('eris_psr.InsertMap', (order_id, psr_type , psr_filename, p_seq_no))
        finally:
            cur.close()
            con.close()
    def insert_order_detail(self,order_id,eris_id, ds_id):
        try:
            con = cx_Oracle.connect(db_connections.connection_string)
            cur = con.cursor()
            ### insert data into order_detail_psr table
            cur.callproc('eris_psr.InsertOrderDetail', (order_id, eris_id,ds_id))
        finally:
            cur.close()
            con.close()
    def insert_flex_rep(self, order_id, eris_id, p_ds_oid, p_num, p_sub, p_count, p_flex_label, p_flex_value):
        try:
            con = cx_Oracle.connect(db_connections.connection_string)
            cur = con.cursor()
             ### insert data into ERIS_FLEX_REPORTING_PSR table 
            cur.callproc('eris_psr.InsertFlexRep', (order_id, eris_id, p_ds_oid, p_num, p_sub, p_count, p_flex_label, p_flex_value))
           
        finally:
            cur.close()
            con.close()
      