import arcpy, os, sys

def if_multipage(geometry_pcs_shp):
    geomExtent = arcpy.Describe(geometry_pcs_shp).extent
    if geomExtent.width > 1300 or geomExtent.height > 1300:
        return True
    else:
        return False
    
def add_layer_to_mxd(layer_name,data_frame,lyr_file, scale):
    layer = arcpy.mapping.Layer(lyr_file)
    layer.replaceDataSource(arcpy.env.scratchFolder,"SHAPEFILE_WORKSPACE",layer_name)
    arcpy.mapping.AddLayer(data_frame,layer,"Top")
    data_frame.extent = layer.getSelectedExtent(False)
    data_frame.scale = data_frame.scale * scale