from imp import reload
import arcpy, os, sys
import glob
import timeit
import shutil
import psr_utility
import psr_config as config
file_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1,os.path.join(os.path.dirname(file_path),'GIS_Utility'))
sys.path.insert(1,os.path.join(os.path.dirname(file_path),'DB_Framework'))
import gis_utility
import models
reload(sys)
class Kml_Config:
    viewer_dir_kml = None
    viewer_temp = None
    viewer_dir_topo = None
    viewer_dir_relief = None
def wetland_to_kml(order_obj):
    wetland_clip = os.path.join(config.scratch_folder, "wetland_clip.shp")
    wetland_mxd_path = os.path.join(config.scratch_folder,'mxd_wetland.mxd')
    if os.path.exists(wetland_mxd_path):
        # mxd_name = glob.glob(wetland_mxd)[0]
        wetland_mxd = arcpy.mapping.MapDocument(wetland_mxd_path)
        df = arcpy.mapping.ListDataFrames(wetland_mxd,"big")[0]    # the spatial reference here is UTM zone #, need to change to WGS84 Web Mercator
        df.spatialReference = order_obj.spatial_ref_gcs
        if order_obj.province == 'AK':
            df.spatialReference = config.spatial_ref_mercator
        #re-focus using Buffer layer for multipage
        if config.if_multi_page == True:
            buffer_layer = arcpy.mapping.ListLayers(wetland_mxd, "Buffer", df)[0]
            df.extent = buffer_layer.getSelectedExtent(False)
            df.scale = df.scale * 1.1
        #df.spatialReference is currently UTM. dfAsFeature is a feature, not even a layer
        df_as_feature = arcpy.Polygon(arcpy.Array([df.extent.lowerLeft, df.extent.lowerRight, df.extent.upperRight, df.extent.upperLeft]), df.spatialReference)
        del df, wetland_mxd
        wetland_boudnary = os.path.join(config.scratch_folder,"wetland_kml_extend.shp")
        arcpy.Project_management(df_as_feature, wetland_boudnary, order_obj.spatial_ref_gcs)
        arcpy.Clip_analysis(config.data_lyr_wetland, wetland_boudnary, wetland_clip)
        del df_as_feature
        
        wetland_clip_final = None
        if int(arcpy.GetCount_management(wetland_clip).getOutput(0)) != 0:
            arcpy.AddField_management(wetland_boudnary,"WETLAND_TYPE", "TEXT", "", "", "15", "", "NULLABLE", "NON_REQUIRED", "")
            wetland_clip_final = os.path.join(config.scratch_folder, "wetland_clip_final.shp")
            arcpy.Union_analysis([wetland_clip,wetland_boudnary],wetland_clip_final)

            keepFieldList = ("WETLAND_TYPE")
            fieldInfo = ""
            fieldList = arcpy.ListFields(wetland_clip_final)
            for field in fieldList:
                if field.name in keepFieldList:
                    if field.name == 'WETLAND_TYPE':
                        fieldInfo = fieldInfo + field.name + " " + "Wetland Type" + " VISIBLE;"
                    else:
                        pass
                else:
                    fieldInfo = fieldInfo + field.name + " " + field.name + " HIDDEN;"
            # print fieldInfo

            arcpy.MakeFeatureLayer_management(wetland_clip_final, 'wetland_clip_lyr', "", "", fieldInfo[:-1])
            arcpy.ApplySymbologyFromLayer_management('wetland_clip_lyr', config.data_lyr_wetland)
            arcpy.LayerToKML_conversion('wetland_clip_lyr', os.path.join(Kml_Config.viewer_dir_kml,"wetlandclip.kmz"))
            arcpy.Delete_management('wetland_clip_lyr')
        else:
            arcpy.AddMessage('      -- no wetland data')
            arcpy.MakeFeatureLayer_management(wetland_clip, 'wetland_clip_lyr')
            arcpy.LayerToKML_conversion('wetland_clip_lyr', os.path.join(Kml_Config.viewer_dir_kml,"wetland_clip_nodata.kmz"))
            arcpy.Delete_management('wetland_clip_lyr')
    else:
        arcpy.AddMessage('  -- Wetland report is not generatated therfore the wetland kml file cannot be exported...')
    
def convert_to_kml(order_obj):
    arcpy.AddMessage('  -- Start generating kml for explorer viewer...')
    start = timeit.default_timer() 
    
    Kml_Config.viewer_dir_kml = os.path.join(config.scratch_folder,order_obj.number + '_psr_kml')
    if not os.path.exists(Kml_Config.viewer_dir_kml):
        os.mkdir(Kml_Config.viewer_dir_kml)
        
    Kml_Config.viewer_temp =os.path.join(config.scratch_folder,'viewer_temp')
    if not os.path.exists(Kml_Config.viewer_temp):
        os.mkdir(Kml_Config.viewer_temp)
        
    Kml_Config.viewer_dir_topo = os.path.join(config.scratch_folder,order_obj.number+'_psr_topo')
    if not os.path.exists(Kml_Config.viewer_dir_topo):
        os.mkdir(Kml_Config.viewer_dir_topo)
    
    viewer_dir_relief = os.path.join(config.scratch_folder,order_obj.number+'_psr_relief')
    if not os.path.exists(viewer_dir_relief):
        os.mkdir(viewer_dir_relief)
    
    ### generate kml for wetland
    wetland_to_kml(order_obj)
        
    end = timeit.default_timer()
    arcpy.AddMessage((' -- End generating PSR Oil, Gas and Water wells report. Duration:', round(end -start,4)))