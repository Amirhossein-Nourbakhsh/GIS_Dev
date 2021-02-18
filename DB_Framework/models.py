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
    psr = None
    site_name = None
    customer_id = None
    radius_type = None
    company_id = None
    company_desc = None
    project_num = None
    geometry = arcpy.Geometry()
   
    def get_order(self,input_id):
        try:
            order_obj = Order
            con = cx_Oracle.connect(db_connections.connection_string)
            cursor = con.cursor()
            ### fetch order info from order table by order id
            sql_statment = "select ord.order_num, ord.address1, ord.city, ord.provstate , ord.site_name, cus.customer_id, cus.company_id, comp.company_desc, ord.pobox  from orders ord, customer cus, company comp  where ord.customer_id = cus.customer_id and cus.company_id = comp.company_id and order_id = " + str(input_id)
            cursor.execute(sql_statment)
            # cursor.execute("select order_num, address1, city, provstate, site_name, customer_id from orders where order_id =" + str(input_id))
            row = cursor.fetchone()
            if row is not None:
                self.id = input_id
                self.number = str(row[0])
                order_obj.id = input_id
                order_obj.number = str(row[0])
            else:
                del cursor 
                del row
                cursor = con.cursor()
                ### fetch order info from order table by order number
                sql_statment = sql_statment = "select ord.order_id, ord.address1, ord.city, ord.provstate, ord.site_name, cus.customer_id, cus.company_id, comp.company_desc, ord.pobox from orders ord, customer cus, company comp  where ord.customer_id = cus.customer_id and cus.company_id = comp.company_id and  order_num = '" + str(input_id) + "'"
                cursor.execute(sql_statment)
                # cursor.execute("select order_id, address1, city, provstate, site_name, customer_id from orders where order_num = '" + str(input_id) + "'")
                row = cursor.fetchone()
                if row is not None:
                    self.id =  str(row[0])
                    self.number = str(input_id)
                    order_obj.id = str(row[0])
                    order_obj.number = str(input_id)
                else:
                     return None  
            order_obj.address = str(row[1])+","+str(row[2])+","+str(row[3])
            order_obj.province = str(row[3])
            order_obj.site_name = row[4]
            order_obj.customer_id = row[5]
            order_obj.company_id = row[6]
            order_obj.company_desc = row[7]
            order_obj.project_num = row[8]
            order_obj.geometry = order_obj.__getGeometry()
            return order_obj
        finally:
            cursor.close()
            con.close()
    @classmethod
    def __getGeometry(self): # return geometry in WGS84 (GCS) / private function
        sr_wgs84 = arcpy.SpatialReference(4326)
        order_fc = db_connections.order_fc
        # orderGeom = arcpy.da.SearchCursor(orderFC,("SHAPE@"),"order_id = " + str(self.Id) ).next()[0]
        order_geom = None
        if order_geom == None:
            order_geom = arcpy.Geometry()
            where = 'order_id = ' + str(self.id)
            row = arcpy.da.SearchCursor(order_fc,("GEOMETRY_TYPE","GEOMETRY", "RADIUS_TYPE"),where).next()
            coord_string = ((row[1])[1:-1])
            coordinates = np.array(literal_eval(coord_string))
            geometry_type = row[0]
            self.radius_type = row[2]
            if geometry_type.lower()== 'point':
                order_geom = arcpy.Multipoint(arcpy.Array([arcpy.Point(*coords) for coords in coordinates]), sr_wgs84)
            elif geometry_type.lower() =='polyline':        
                order_geom = arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in coordinates]), sr_wgs84)
            elif geometry_type.lower() =='polygon':
                order_geom = arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in coordinates]), sr_wgs84)
        return order_geom.projectAs(sr_wgs84)          
    @classmethod
    def get_search_radius(self):
        try:
            con = cx_Oracle.connect(db_connections.connection_string)
            cur = con.cursor()
            cur.execute("select OMR_OID, DS_OID, SEARCH_RADIUS, REPORT_SOURCE from order_radius_psr where order_id =" + str(self.id))
            items = cur.fetchall()
            psr_obj = PSR()
            psr_obj.order_id = self.id
            for t in items:
                dso_id = t[1]
                radius = t[2]
                psr_obj.search_radius[str(dso_id)] = float(radius)
            self.psr = psr_obj
        finally:
            cur.close()
            con.close()
class PSR(object):
    order_id = ''
    omi_id = ''
    ds_oid = ''
    search_radius = {}
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
    def insert_order_detail(self,order_id,eris_id, ds_id, map_unit_key = None, distance = None, direction = None, elev_feet = None, elev_feet_dif = None, map_key_loc = None, map_key_no = None ):
        try:
            con = cx_Oracle.connect(db_connections.connection_string)
            cur = con.cursor()
            ### insert data into order_detail_psr table
            cur.callproc('eris_psr.InsertOrderDetail', (order_id, eris_id,ds_id, map_unit_key, distance, direction, elev_feet, elev_feet_dif, map_key_loc, map_key_no))
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
    def get_radon(self,order_id, state_list_str, zip_list_str, county_list_str, city_list_str):
        try:
            con = cx_Oracle.connect(db_connections.connection_string)
            cur = con.cursor()
             ### insert data into ... table 
            cur.callproc('eris_psr.GetRadon', (order_id, state_list_str, zip_list_str, county_list_str, city_list_str))
           
        finally:
            cur.close()
            con.close()
      