import arcpy,os
import ConfigParser
import arcpy
def server_loc_config(configpath,environment):
    configParser = ConfigParser.RawConfigParser()
    configParser.read(configpath)
    if environment == 'test':
        reportcheck_test = configParser.get('server-config','reportcheck_test')
        reportviewer_test = configParser.get('server-config','reportviewer_test')
        reportinstant_test = configParser.get('server-config','instant_test')
        reportnoninstant_test = configParser.get('server-config','noninstant_test')
        upload_viewer = configParser.get('url-config','uploadviewer')
        server_config = {'reportcheck':reportcheck_test,'viewer':reportviewer_test,'instant':reportinstant_test,'noninstant':reportnoninstant_test,'viewer_upload':upload_viewer}
        return server_config
    elif environment == 'prod':
        reportcheck_prod = configParser.get('server-config','reportcheck_prod')
        reportviewer_prod = configParser.get('server-config','reportviewer_prod')
        reportinstant_prod = configParser.get('server-config','instant_prod')
        reportnoninstant_prod = configParser.get('server-config','noninstant_prod')
        upload_viewer = configParser.get('url-config','uploadviewer_prod')
        server_config = {'reportcheck':reportcheck_prod,'viewer':reportviewer_prod,'instant':reportinstant_prod,'noninstant':reportnoninstant_prod,'viewer_upload':upload_viewer}
        return server_config
    else:
        return 'invalid server configuration'
class Report_Type:
    wetland = 'wetland'
    ny_wetland = 'ny_wetland'
    flood = 'flood'
    topo = 'topo'
    relief = 'relief'
    wells = 'wells'
    geology = 'geology'
    soil = 'soil'
    
server_environment = 'test'
server_config_file = r'\\cabcvan1gis006\GISData\ERISServerConfig.ini'
server_config = server_loc_config(server_config_file,server_environment)
connectionString = 'eris_gis/gis295@cabcvan1ora006.glaciermedia.inc:1521/GMTESTC'
report_path = server_config['noninstant']
viewer_path = server_config['viewer']
upload_link = server_config['viewer_upload']+r"/ErisInt/BIPublisherPortal_prod/Viewer.svc/"
#production: upload_link = r"http://CABCVAN1OBI002/ErisInt/BIPublisherPortal_prod/Viewer.svc/"
reportcheck_path = server_config['reportcheck']
connectionPath = r"\\cabcvan1gis005\GISData\PSR\python"

scratch_folder=  arcpy.env.scratchFolder
# temp gdb in scratch folder
temp_gdb = os.path.join(scratch_folder,r"temp.gdb")

order_geom_lyr_point = r"\\cabcvan1gis005\GISData\PSR\python\mxd\SiteMaker.lyr"
order_geom_lyr_polyline = r"\\cabcvan1gis005\GISData\PSR\python\mxd\orderLine.lyr"
order_geom_lyr_polygon = r"\\cabcvan1gis005\GISData\PSR\python\mxd\orderPoly.lyr"
buffer_lyr_file = r"\\cabcvan1gis005\GISData\PSR\python\mxd\buffer.lyr"
grid_lyr_file = r"\\cabcvan1gis005\GISData\PSR\python\mxd\Grid_hollow.lyr"


# data_flood = r'\\cabcvan1gis005\GISData\Data\PSR\PSR.gdb\S_Fld_Haz_Ar_merged2018'
data_flood = r'\\cabcvan1gis005\GISData\Data\PSR\PSR.gdb\flood_map_wgs84'

data_flood_panel = r'\\cabcvan1gis005\GISData\Data\PSR\PSR.gdb\flood_panel_map_wgs84'
data_wetland = r'\\cabcvan1gis005\GISData\Data\PSR\PSR.gdb\Merged_wetland_Final'
eris_wells = r"\\cabcvan1gis005\GISData\PSR\python\mxd\ErisWellSites.lyr"   #which contains water, oil/gas wells etc.

datalyr_wetland = r"\\cabcvan1gis005\GISData\PSR\python\mxd\wetland_kml.lyr"
##datalyr_wetlandNY = r"E:\GISData\PSR\python\mxd\wetlandNY.lyr"
datalyr_wetlandNYkml = r"\\cabcvan1gis005\GISData\PSR\python\mxd\wetlandNY_kml.lyr"
datalyr_wetlandNYAPAkml = r"\\cabcvan1gis005\GISData\PSR\python\mxd\wetlandNYAPA_kml.lyr"
datalyr_flood = r"\\cabcvan1gis005\GISData\PSR\python\mxd\flood.lyr"
data_lyr_geology = r"\\cabcvan1gis005\GISData\PSR\python\mxd\geology.lyr"
datalyr_contour = r"\\cabcvan1gis005\GISData\PSR\python\mxd\contours_largescale.lyr"
datalyr_plumetacoma = r"\\cabcvan1gis005\GISData\PSR\python\mxd\Plume.lyr"

mxdfile_wetland = r"\\cabcvan1gis005\GISData\PSR\python\mxd\wetland.mxd"
mxdfile_wetlandNY = r"\\cabcvan1gis005\GISData\PSR\python\mxd\wetlandNY_CC.mxd"
mxdMMfile_wetland = r"\\cabcvan1gis005\GISData\PSR\python\mxd\wetlandMM.mxd"
mxdMMfile_wetlandNY = r"\\cabcvan1gis005\GISData\PSR\python\mxd\wetlandMMNY.mxd"
mxd_file_flood = r"\\cabcvan1gis005\GISData\PSR\python\mxd\flood.mxd"
mxd_mm_file_flood = r"\\cabcvan1gis005\GISData\PSR\python\mxd\floodMM.mxd"

mxdfile_wells = r"\\cabcvan1gis005\GISData\PSR\python\mxd\wells.mxd"
mxdMMfile_wells = r"\\cabcvan1gis005\GISData\PSR\python\mxd\wellsMM.mxd"

# grid size
grid_size = "2 MILES"
# Explorer
data_lyr_wetland = r"\\cabcvan1gis005\GISData\PSR\python\mxd\wetland_kml.lyr"
datalyr_flood = r"\\cabcvan1gis005\GISData\PSR\python\mxd\flood.lyr"
data_lyr_geology = r"\\cabcvan1gis005\GISData\PSR\python\mxd\geology.lyr"


def output_jpg(order_obj, report_type):
    if report_type == Report_Type.wetland :
        return os.path.join(scratch_folder, str(order_obj.number) + '_US_WETL.jpg')
    elif report_type == Report_Type.ny_wetland :
         return os.path.join(scratch_folder, str(order_obj.number) + '_NY_WETL.jpg')
    elif report_type == Report_Type.flood:
        return os.path.join(scratch_folder, order_obj.number + '_US_FLOOD.jpg')
    elif report_type == Report_Type.topo:
        return os.path.join(scratch_folder, order_obj.number + '_US_TOPO.jpg')
    elif report_type == Report_Type.relief:
        return os.path.join(scratch_folder, order_obj.number + '_US_RELIEF.jpg')
    elif report_type == Report_Type.geology:
        return os.path.join(scratch_folder, order_obj.number + '_US_GEOLOGY.jpg')
    elif report_type == Report_Type.soil:
        return os.path.join(scratch_folder, order_obj.number + '_US_SOIL.jpg')
    
    
### Basemaps
imgdir_demCA = r"\\Cabcvan1fpr009\US_DEM\DEM1"
master_lyr_dem_CA = r"\\Cabcvan1fpr009\US_DEM\Canada_DEM_edited.shp"
imgdir_dem = r"\\Cabcvan1fpr009\US_DEM\DEM13"
master_lyr_dem = r"\\cabcvan1gis005\GISData\Data\US_DEM\CellGrid_1X1Degree_NW_wgs84.shp"
master_lyr_states = r"\\cabcvan1gis005\GISData\PSR\python\mxd\USStates.lyr"
master_lyr_counties = r"\\cabcvan1gis005\GISData\PSR\python\mxd\USCounties.lyr"
master_lyr_cities = r"\\cabcvan1gis005\GISData\PSR\python\mxd\USCities.lyr"
master_lyr_nh_towns = r"\\cabcvan1gis005\GISData\PSR\python\mxd\NHTowns.lyr"
master_lyr_zip_codes = r"\\cabcvan1gis005\GISData\PSR\python\mxd\USZipcodes.lyr"
### order geometry paths config
order_geometry_pcs_shp =  os.path.join(scratch_folder,'order_geometry_pcs.shp')
order_geometry_gcs_shp =  os.path.join(scratch_folder,'order_geometry_gcs.shp')
order_buffer_shp =  os.path.join(scratch_folder,'order_buffer.shp')
order_geom_lyr_file = None
spatial_ref_pcs = None
spatial_ref_gcs = arcpy.SpatialReference(4283)
### relief report paths config
mxd_file_relief =  r"\\cabcvan1gis005\GISData\PSR\python\mxd\shadedrelief.mxd"
mxd_mm_file_relief =  r"\\cabcvan1gis005\GISData\PSR\python\mxd\shadedreliefMM.mxd"
path_shaded_relief = r"\\cabcvan1fpr009\US_DEM\hillshade13"
relief_lyr_file = r"\\cabcvan1gis005\GISData\PSR\python\mxd\relief.lyr"
data_shaded_relief = r"\\cabcvan1fpr009\US_DEM\CellGrid_1X1Degree_NW.shp"

### topo report paths config
mxd_file_topo = r"\\cabcvan1gis005\GISData\PSR\python\mxd\topo.mxd"
mxd_file_topo_Tacoma = r"\\cabcvan1gis005\GISData\PSR\python\mxd\topo_tacoma.mxd"
mxd_mm_file_topo = r"\\cabcvan1gis005\GISData\PSR\python\mxd\topoMM.mxd"
mxd_mm_file_topo_Tacoma = r"\\cabcvan1gis005\GISData\PSR\python\mxd\topoMM_tacoma.mxd"
topo_master_lyr = r"\\cabcvan1gis005\GISData\Topo_USA\masterfile\CellGrid_7_5_Minute_wgs84.shp"
data_topo = r"\\cabcvan1gis005\GISData\Topo_USA\masterfile\Cell_PolygonAll.shp"
topo_white_lyr_file = r"\\cabcvan1gis005\GISData\PSR\python\mxd\topo_white.lyr"
topo_csv_file = r"\\cabcvan1gis005\GISData\Topo_USA\masterfile\All_USTopo_T_7.5_gda_results.csv"
topo_tif_dir = r"\\cabcvan1fpr009\USGS_Topo\USGS_currentTopo_Geotiff"
topo_frame = os.path.join(scratch_folder, "topo_frame.shp")

### flood report paths config
order_buffer_flood_shp = os.path.join(scratch_folder,'order_buffer_flood.shp')
flood_selectedby_order_shp = os.path.join(scratch_folder,"flood_selectedby_order.shp")
flood_panel_selectedby_order_shp = os.path.join(scratch_folder,"flood_panel_selectedby_order.shp")

### geology report paths config
data_geology = r'\\cabcvan1gis005\GISData\Data\PSR\PSR.gdb\GEOL_DD_MERGE' ## WGS84
geology_selectedby_order_shp = os.path.join(scratch_folder,"geology_selectedby_order.shp")
mxd_file_geology = r"\\cabcvan1gis005\GISData\PSR\python\mxd\geology.mxd"
mxd_mm_file_geology = r"\\cabcvan1gis005\GISData\PSR\python\mxd\geologyMM.mxd"

### soil report paths config
# data_path_soil_HI =r'\\cabcvan1gis005\GISData\Data\CONUS_2015\gSSURGO_HI.gdb'  ## WGS84
# data_path_soil_AK =r'\\cabcvan1gis005\GISData\Data\CONUS_2015\gSSURGO_AK.gdb'  ## WGS84
# data_path_soil_CONUS =r'\\cabcvan1gis005\GISData\Data\CONUS_2015\gSSURGO_CONUS_10m.gdb'  ## WGS84

data_path_soil_HI =r'\\cabcvan1fpr009\SSURGO\CONUS_2015\gSSURGO_HI.gdb'
data_path_soil_AK =r'\\cabcvan1fpr009\SSURGO\CONUS_2015\gSSURGO_AK.gdb'
data_path_soil_CONUS =r'\\cabcvan1fpr009\SSURGO\CONUS_2015\gSSURGO_CONUS_10m.gdb'

soil_selectedby_order_shp = os.path.join(scratch_folder,"soil_selectedby_order.shp")
soil_selectedby_order_pcs_shp =  os.path.join(scratch_folder,"soil_selectedby_order_pcs.shp")
soil_selectedby_frame =  os.path.join(scratch_folder,"soil_selectedby_frame.shp")
mxd_file_soil = r"\\cabcvan1gis005\GISData\PSR\python\mxd\soil.mxd"
mxd_mm_file_soil = r"\\cabcvan1gis005\GISData\PSR\python\mxd\soilMM.mxd"
hydrologic_dict = {
        "A":'Soils in this group have low runoff potential when thoroughly wet. Water is transmitted freely through the soil.',
        "B":'Soils in this group have moderately low runoff potential when thoroughly wet. Water transmission through the soil is unimpeded.',
        "C":'Soils in this group have moderately high runoff potential when thoroughly wet. Water transmission through the soil is somewhat restricted.',
        "D":'Soils in this group have high runoff potential when thoroughly wet. Water movement through the soil is restricted or very restricted.',
        "A/D":'These soils have low runoff potential when drained and high runoff potential when undrained.',
        "B/D":'These soils have moderately low runoff potential when drained and high runoff potential when undrained.',
        "C/D":'These soils have moderately high runoff potential when drained and high runoff potential when undrained.',
        }

hydric_dict = {
        '1':'All hydric',
        '2':'Not hydric',
        '3':'Partially hydric',
        '4':'Unknown',
        }

fc_soils_field_list  = [['muaggatt.mukey','mukey'], ['muaggatt.musym','musym'], ['muaggatt.muname','muname'],['muaggatt.drclassdcd','drclassdcd'],['muaggatt.hydgrpdcd','hydgrpdcd'],['muaggatt.hydclprs','hydclprs'], ['muaggatt.brockdepmin','brockdepmin'], ['muaggatt.wtdepannmin','wtdepannmin'], ['component.cokey','cokey'],['component.compname','compname'], ['component.comppct_r','comppct_r'], ['component.majcompflag','majcompflag'],['chorizon.chkey','chkey'],['chorizon.hzname','hzname'],['chorizon.hzdept_r','hzdept_r'],['chorizon.hzdepb_r','hzdepb_r'], ['chtexturegrp.chtgkey','chtgkey'], ['chtexturegrp.texdesc1','texdesc'], ['chtexturegrp.rvindicator','rv']]
fc_soils_key_list = ['muaggatt.mukey', 'component.cokey','chorizon.chkey','chtexturegrp.chtgkey']
fc_soils_where_clause_query_table = "muaggatt.mukey = component.mukey and component.cokey = chorizon.cokey and chorizon.chkey = chtexturegrp.chkey"
### ogw report paths config
order_centre_point_pcs = os.path.join(scratch_folder, "order_centre_point_pcs.shp")
tbx = r"\\cabcvan1gis005\GISData\PSR\python\ERIS.tbx"

### Rado report config
states_selectedby_order = os.path.join(scratch_folder,"states_selectedby_order.shp")
counties_selectedby_order = os.path.join(scratch_folder,"counties_selectedby_order.shp")
cities_selectedby_order = os.path.join(scratch_folder,"cities_selectedby_order.shp")