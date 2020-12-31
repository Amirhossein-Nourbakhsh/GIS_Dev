import arcpy,os
import psr_config as config

def if_multipage(geometry_pcs_shp, report_type = None):
    multi_page = None
    geomExtent = arcpy.Describe(geometry_pcs_shp).extent
    if geomExtent.width > 1300 or geomExtent.height > 1300:
        multi_page = True
    else:
        multi_page = False
    if geomExtent.width > 500 or geomExtent.height > 500:
        if report_type in [report_type.topo, report_type.relief, report_type.wells]:
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