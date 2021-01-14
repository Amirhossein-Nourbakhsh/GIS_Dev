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
    arcpy.DefineProjection_management(config.order_geometry_gcs_shp, config.spatial_ref_gcs)
    arcpy.CopyFeatures_management(order_geometry_pcs, config.order_geometry_pcs_shp)
    arcpy.DefineProjection_management(config.order_geometry_gcs_shp, config.spatial_ref_pcs)
def return_unique_setstring_musym(table_name):
    data = arcpy.da.TableToNumPyArray(table_name, ['mukey', 'musym'])
    uniques = np.unique(data[data['musym']!='NOTCOM']['mukey'])
    if len(uniques) == 0:
        return ''
    else:
        output_string = '('
        for item in uniques:
            output_string = output_string + "'" + str(item) + "', "
        output_string = output_string[0:-2] + ")"
        return output_string
def return_unique_set_string(table_name, field_name):
    data = arcpy.da.TableToNumPyArray(table_name, [field_name])
    uniques = np.unique(data[field_name])
    if len(uniques) == 0:
        return ''
    else:
        output_string = '('
        for item in uniques:
            output_string = output_string + "'" + str(item) + "', "
        output_string = output_string[0:-2] + ")"
        return output_string
#check if an array contain the same values
def check_if_unique_value(input_array):
    value = input_array[0]
    for i in range(0,len(input_array)):
        if(input_array[i] != value):
            return False
    return True
def return_map_unit_attribute(data_array, mukey, attribute_name):   #water, urban land is not in data_array, so will return '?'
    data = data_array[data_array['mukey'] == mukey][attribute_name]
    if (len(data) == 0):
        return "?"
    else:
        if(check_if_unique_value):
            if (attribute_name == 'brockdepmin' or attribute_name == 'wtdepannmin'):
                if data[0] == -99:
                    return 'null'
                else:
                    return str(data[0]) + 'cm'
            return str(data[0])  #will convert to str no matter what type
        else:
            return "****ERROR****"
def return_componen_attribute_rv_indicator_Y(data_array,mukey):
    result_array = []
    dataarray1 = data_array[data_array['mukey'] == mukey]
    data = dataarray1[dataarray1['majcompflag'] =='Yes']      # 'majcompfla' needs to be used for .dbf table
    comps = data[['cokey','compname','comppct_r']]
    comps_sorted = np.sort(np.unique(comps), order = 'comppct_r')[::-1]     #[::-1] gives descending order
    for comp in comps_sorted:
        horizon_array = []
        keyname = comp[1] + '('+str(comp[2])+'%)'
        horizon_array.append([keyname])

        selection = data[data['cokey']==comp[0]][['mukey','cokey','compname','comppct_r','hzname','hzdept_r','hzdepb_r','texdesc']]
        selection_sorted = np.sort(selection, order = 'hzdept_r')
        for item in selection_sorted:
            horizon_label = 'horizon ' + item['hzname'] + '(' + str(item['hzdept_r']) + 'cm to '+ str(item['hzdepb_r']) + 'cm)'
            horizon_texture = item['texdesc']
            horizon_array.append([horizon_label,horizon_texture])
        result_array.append(horizon_array)

    return result_array
def get_elevation(data_set,fields):
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