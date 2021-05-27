import arcpy, os, sys
from os import path
import re
import gdal
from osgeo import gdal
# import rasterio

def extract_float(input_string):
    remove_chars = "'()"
    pattern = "[" + remove_chars + "]"
    new_string = re.sub(pattern, "", input_string)
    return new_string
def pixel2coord(col, row):
    """Returns global coordinates from pixel x, y coords"""
    xp = a * col + b * row + xoff
    yp = d * col + e * row + yoff
    return(xp, yp)

if __name__ == "__main__":
    
    input_tab_file = r'\\cabcvan1eap003\USGS_IN_test\JL_SAMPLES\WGS84 Converted\49_AMS_ARA007102503385.TAB'
    input_img = r'\\cabcvan1eap003\USGS_IN_test\JL_SAMPLES\WGS84 Converted\49_AMS_ARA007102503385.tif'

    tab_File = open(input_tab_file, 'r')
    all_lines = tab_File.readlines()
    source_points = ''
    gc_points = ''
    src_points = ''
    ### calculate local points in WGS84
    srWGS84 = arcpy.SpatialReference(4326)
    arcpy.DefineProjection_management(input_img, srWGS84)
    # rasterio.transform.TransformMethodsMixin .xy()
    # https://rasterio.readthedocs.io/en/latest/api/rasterio.transform.html
    ds = gdal.Open(input_img)
    xoff, a, b, yoff, d, e = ds.GetGeoTransform()
    gcp_x_1, gcp_y_1 = pixel2coord(5306,1392)
    gcp_x_2, gcp_y_2 = pixel2coord(2336,5371)
    gcp_x_3, gcp_y_3 = pixel2coord(2208,1984)
    gcp_x_4, gcp_y_4 = pixel2coord(6602,7643)
    from arcpy.sa import *
    myRas = Raster(input_img)
    for i, j in myRas:
        print(i, j, myRas[i, j])



    # for line in all_lines:
    #     gc_pnt = ''
    #     src_pnt = ''
    #     if  'Pt' in line:
    #         search_results = re.finditer(r'\(.*?\)', line) 
    #         result_gc =[]
    #         result_src =[]
    #         i = 0
    #         for item in search_results: 
    #             if i == 0:
    #                 result_gc.append(extract_float(item.group(0).split(',')[0]))
    #                 result_gc.append(extract_float(item.group(0).split(',')[1]))
    #             elif i == 1:
    #                 result_src.append(extract_float(item.group(0).split(',')[0]))
    #                 result_src.append(extract_float(item.group(0).split(',')[1]))
    #             i =+ 1
    #         gc_pnt = "'" + result_gc[0] + " " + result_gc[1] + "';"
    #         src_pnt = "'" + result_src[0] + " " + result_src[1] + "';"

    #         if gc_points == '':
    #             gc_points = gc_pnt
    #         else:
    #             gc_points = gc_points + gc_pnt
            
    #         if src_points == '':
    #             src_points = src_pnt
    #         else:
    #             src_points = src_points + src_pnt
        
    # output_geo_ref_image = r'\\cabcvan1eap003\USGS_IN_test\JL_SAMPLES\georef\67_FDOT_PAS0458-04-06.tif'



    # # arcpy.Warp_management(input_img, src_points[:-1],gc_points[:-1], output_geo_ref_image, '', '')
    # # srWGS84 = arcpy.SpatialReference(4326)
    # # arcpy.DefineProjection_management(output_geo_ref_image, srWGS84)

    # print(output_geo_ref_image)
    # # print(gc_points[:-1])

    # # print(src_points[:-1])