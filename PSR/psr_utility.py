import arcpy,os
import psr_config as config
import numpy as np

def if_multipage(geometry_pcs_shp, input_report_type = None):
    multi_page = None
    geomExtent = arcpy.Describe(geometry_pcs_shp).extent
    if geomExtent.width > 1300 or geomExtent.height > 1300:
        multi_page = True
    else:
        multi_page = False
    if geomExtent.width > 500 or geomExtent.height > 500 and multi_page == None:
        if input_report_type in [config.Report_Type.topo, config.Report_Type.relief, config.Report_Type.wells]:
            multi_page = True
    return multi_page
def add_layer_to_mxd(layer_name,data_frame,lyr_file, scale):
    layer = arcpy.mapping.Layer(lyr_file)
    layer.replaceDataSource(arcpy.env.scratchFolder,"SHAPEFILE_WORKSPACE",layer_name)
    arcpy.mapping.AddLayer(data_frame,layer,"Top")
    data_frame.extent = layer.getSelectedExtent(False)
    data_frame.scale = data_frame.scale * scale
def set_order_geometry(order_obj):
    ### set order geometry layer file
    if order_obj.geometry.type.lower() in ['point','multipoint']:
        config.order_geom_lyr_file = config.order_geom_lyr_point
    elif order_obj.geometry.type.lower() =='polyline':
        config.order_geom_lyr_file = config.order_geom_lyr_polyline
    else: #polygon
        config.order_geom_lyr_file = config.order_geom_lyr_polygon
    ### calculate order geometry in PCS
    centre_point = order_obj.geometry.trueCentroid
    config.spatial_ref_pcs = arcpy.GetUTMFromLocation(centre_point.X,centre_point.Y)
    order_geometry_pcs = order_obj.geometry.projectAs(config.spatial_ref_pcs)
    arcpy.CopyFeatures_management(order_obj.geometry, config.order_geometry_gcs_shp)
    arcpy.CopyFeatures_management(order_geometry_pcs, config.order_geometry_pcs_shp)
def return_unique_setstring_musym(table_name):
    data = arcpy.da.TableToNumPyArray(table_name, ['mukey', 'musym'])
    uniques = np.unique(data[data['musym']!='NOTCOM']['mukey'])
    if len(uniques) == 0:
        return ''
    else:
        my_tring = '('
        for item in uniques:
            my_tring = my_tring + "'" + str(item) + "', "
        my_string = my_tring[0:-2] + ")"
        return my_string
def return_unique_setString(table_name, field_name):
    data = arcpy.da.TableToNumPyArray(table_name, [field_name])
    uniques = np.unique(data[field_name])
    if len(uniques) == 0:
        return ''
    else:
        my_string = '('
        for item in uniques:
            my_string = my_string + "'" + str(item) + "', "
        my_string = my_string[0:-2] + ")"
        return my_string